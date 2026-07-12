"""
AutoReply Engine for FunPay Hub.

Subscribes to event bus and dispatches messages based on rules
stored in configs/autoreply_rules.json + configs/message_templates.json.
"""
import json
import time
import threading
from pathlib import Path
from typing import Optional

try:
    from runtime.plugin_markers import has_any_marker
except Exception:
    def has_any_marker(t): return False


def _project_root() -> Path:
    import sys, os
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _configs_dir() -> Path:
    import os
    override = os.environ.get("FUNPAYHUB_CONFIGS")
    if override:
        return Path(override)
    return _project_root() / "configs"


# ---------------------------------------------------------------------
# Shared chat-lock registry
# ---------------------------------------------------------------------

class ChatLockRegistry:
    def __init__(self):
        self._locks = {}
        self._lock = threading.RLock()

    def acquire(self, chat_id, owner: str, ttl_seconds: int = 1800) -> bool:
        cid = str(chat_id)
        with self._lock:
            now = time.time()
            cur = self._locks.get(cid)
            if cur and cur.get("until", 0) > now and cur.get("owner") != owner:
                return False
            self._locks[cid] = {"owner": owner, "until": now + ttl_seconds}
            return True

    def release(self, chat_id, owner=None) -> bool:
        cid = str(chat_id)
        with self._lock:
            cur = self._locks.get(cid)
            if not cur:
                return False
            if owner and cur.get("owner") != owner:
                return False
            self._locks.pop(cid, None)
            return True

    def is_locked(self, chat_id, by_other_than=None) -> bool:
        cid = str(chat_id)
        with self._lock:
            cur = self._locks.get(cid)
            if not cur:
                return False
            if cur.get("until", 0) < time.time():
                self._locks.pop(cid, None)
                return False
            if by_other_than is None:
                return True
            return cur.get("owner") != by_other_than

    def owner(self, chat_id):
        cid = str(chat_id)
        with self._lock:
            cur = self._locks.get(cid)
            if not cur or cur.get("until", 0) < time.time():
                return None
            return cur.get("owner")


chat_lock_registry = ChatLockRegistry()


# ---------------------------------------------------------------------
# AutoReply Engine
# ---------------------------------------------------------------------

class AutoReplyEngine:
    def __init__(self, event_bus, seller_service, autosmm_plugin=None):
        self.event_bus = event_bus
        self.svc = seller_service
        self.autosmm_plugin = autosmm_plugin
        self._lock = threading.RLock()
        self._recent = {}
        self._cooldown_seconds = 60

    def _is_processed_by_autosmm(self, order_id: str) -> bool:
        if not self.autosmm_plugin or not order_id:
            return False
        try:
            return str(order_id) in getattr(self.autosmm_plugin, "_processed_orders_ttl", set())
        except Exception:
            return False

    def subscribe(self):
        if not self.event_bus:
            print("[AutoReply] No event_bus")
            return
        self.event_bus.subscribe("new_message",     self._on_new_message, priority=50)
        self.event_bus.subscribe("new_order",       self._on_new_order, priority=50)
        self.event_bus.subscribe("review_received", self._on_review, priority=50)
        print("[AutoReply] Engine subscribed to: new_message, new_order, review_received (priority=50)")

    def _load_rules(self):
        path = _configs_dir() / "autoreply_rules.json"
        if not path.exists():
            print("[AutoReply] autoreply_rules.json NOT FOUND at", path)
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "rules" in data:
                return data["rules"]
            if isinstance(data, list):
                return data
        except Exception as e:
            print(f"[AutoReply] Failed to load rules: {e}")
        return []

    def _load_templates(self):
        path = _configs_dir() / "message_templates.json"
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "templates" in data:
                out = {}
                for t in data["templates"]:
                    tid = t.get("id") or t.get("name")
                    if tid:
                        out[tid] = t
                return out
            if isinstance(data, list):
                out = {}
                for t in data:
                    tid = t.get("id") or t.get("name")
                    if tid:
                        out[tid] = t
                return out
            if isinstance(data, dict):
                return data
        except Exception as e:
            print(f"[AutoReply] Failed to load templates: {e}")
        return {}

    def _resolve_template(self, template_id):
        templates = self._load_templates()
        t = templates.get(template_id)
        if not t:
            print(f"[AutoReply] template_id '{template_id}' not found")
            return None
        if isinstance(t, str):
            return t
        return t.get("text") or t.get("template") or t.get("body") or ""

    def _sent_log_path(self) -> Path:
        return _configs_dir() / "autoreply_sent.json"

    def _load_sent_log(self) -> dict:
        path = self._sent_log_path()
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_sent_log(self, data: dict):
        try:
            path = self._sent_log_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[AutoReply] sent_log save failed: {e}")

    def _is_recent(self, chat_id, rule_id, context_key=None) -> bool:
        """
        Persistent anti-spam check.

        For 'new_chat' / 'order_paid' rules — sends ONCE per chat forever
        (we don't greet the same buyer twice — bad UX, buyer thinks bot is broken).

        For 'keyword' rules — uses cooldown (1 hour) so buyer can ask again later.
        For 'review_received' rules — uses context_key (order_id) so we reply once per review.
        """
        # context_key allows per-order tracking (for reviews)
        key = "{}::{}".format(chat_id, rule_id)
        if context_key:
            key += "::" + str(context_key)

        log = self._load_sent_log()

        # If already sent — block forever (for greeting/order rules)
        # For keywords — allow re-trigger after 1 hour
        existing_ts = log.get(key)
        if existing_ts:
            # Cooldown rules: only keyword has finite cooldown
            if rule_id and "keyword" in str(rule_id).lower():
                if time.time() - existing_ts < 3600:  # 1 hour for keyword
                    return True
            else:
                # Forever for greeting / order_paid / review
                return True

        # Mark as sent NOW
        log[key] = time.time()
        # Limit size — keep only last 5000 entries
        if len(log) > 5000:
            sorted_items = sorted(log.items(), key=lambda x: x[1], reverse=True)[:5000]
            log = dict(sorted_items)
        self._save_sent_log(log)
        return False

    def _send(self, chat_id, text):
        # B45: my_id via multiple paths — пробуем разные способы достать id продавца
        try:
            if text and ("{{my_id}}" in text or "{my_id}" in text):
                _myid = ""
                # Способ 1: self.seller_service._get_account().id
                try:
                    if hasattr(self, "seller_service") and self.seller_service:
                        _acc = self.seller_service._get_account()
                        if _acc:
                            _myid = str(_acc.id)
                except Exception:
                    pass
                # Способ 2: глобальный singleton
                if not _myid:
                    try:
                        from runtime.seller_service import seller_service_singleton as _sv
                        if _sv:
                            _acc = _sv._get_account()
                            if _acc:
                                _myid = str(_acc.id)
                    except Exception:
                        pass
                # Способ 3: HTTP запрос (последний шанс)
                if not _myid:
                    try:
                        from runtime.http_client import HTTPClient
                        from bot.config import get_hub_url
                        _req = HTTPClient()
                        d = _req.get(f"{get_hub_url()}/api/funpay/me", timeout=3)
                        _myid = str((d or {}).get("data", {}).get("user_id") or "")
                    except Exception:
                        pass
                if _myid:
                    text = text.replace("{{my_id}}", _myid)
                    text = text.replace("{my_id}", _myid)
                    print(f"[AutoReply][B45] my_id resolved: {_myid}")
                else:
                    print(f"[AutoReply][B45] my_id NOT resolved")
                    text = text.replace("{{my_id}}", "")
                    text = text.replace("{my_id}", "")
        except Exception as _e_b45:
            print(f"[AutoReply][B45] err: {_e_b45}")
        # B37: sandbox redirect — если chat_id это sandbox, шлём туда
        if str(chat_id) == "sandbox-test-chat":
            try:
                from runtime.http_client import HTTPClient
                from bot.config import get_hub_url
                _b37_req = HTTPClient()
                _b37_req.post(f"{get_hub_url()}/api/dev/sandbox/seller_send",
                              json={"text": text, "source": "autoreply"}, timeout=5)
                print(f"[AutoReply][SANDBOX] -> {text[:60]}")
            except Exception as _e_b37:
                print(f"[AutoReply][SANDBOX err] {_e_b37}")
            return
        if not chat_id or not text:
            return False
        if chat_lock_registry.is_locked(chat_id, by_other_than="autoreply"):
            owner = chat_lock_registry.owner(chat_id)
            print(f"[AutoReply] Chat {chat_id} locked by '{owner}' — skip")
            return False
        try:
            res = self.svc.send_chat_message(chat_id, text, dry_run=False)
            print(f"[AutoReply] Sent to chat {chat_id}: {text[:80]}")
            return True
        except Exception as e:
            print(f"[AutoReply] Send failed: {e}")
            return False

    def _render(self, template_text, ctx):
        if not template_text:
            return ""
        out = template_text
        try:
            for k, v in (ctx or {}).items():
                out = out.replace("{{" + k + "}}", str(v))
        except Exception:
            pass
        return out

    # ----- event handlers -----

    def _on_new_message(self, event):
        # B29: skip if chat is locked by another plugin (AutoSMM dialog)
        try:
            _cid = event.get("chat_id") if isinstance(event, dict) else getattr(event, "chat_id", None)
            if _cid and chat_lock_registry.is_locked(_cid, by_other_than="autoreply"):
                _own = chat_lock_registry.owner(_cid)
                print("[AutoReply] skip new_message in chat " + str(_cid) + " - locked by " + str(_own))
                return
        except Exception as _e_b29m:
            print("[AutoReply] B29 msg skip-check error: " + str(_e_b29m))
        if not isinstance(event, dict):
            return
        chat_id = event.get("chat_id")
        text = (event.get("text") or "").lower().strip()
        from_me = event.get("from_me", False)
        if from_me or not chat_id or not text:
            return

        rules = self._load_rules()
        enabled_rules = [r for r in rules if r.get("enabled")]
        
        for r in enabled_rules:
            trig = (r.get("trigger") or "").lower()
            rid = r.get("id", "unknown")
            conditions = r.get("conditions") or {}

            if trig in ("new_chat", "new_message"):
                # Check keyword conditions
                keywords = conditions.get("keywords") or []
                if keywords:
                    continue  # handled below
                if self._is_recent(chat_id, rid):
                    continue
                tpl = self._resolve_template(r.get("template_id"))
                if not tpl:
                    continue
                msg = self._render(tpl, {
                    "buyer_name": event.get("chat_name", ""),
                    "chat_name": event.get("chat_name", ""),
                })
                self._send(chat_id, msg)

            elif trig == "keyword":
                keywords = conditions.get("keywords") or []
                if not keywords:
                    continue
                matched = False
                for kw in keywords:
                    if kw and kw.lower() in text:
                        matched = True
                        break
                if not matched:
                    continue
                if self._is_recent(chat_id, rid):
                    continue
                tpl = self._resolve_template(r.get("template_id"))
                if not tpl:
                    continue
                msg = self._render(tpl, {"buyer_name": event.get("chat_name", "")})
                self._send(chat_id, msg)

    def _on_new_order(self, event):
        # B29: skip if lot has plugin marker - AutoSMM handles it
        try:
            from runtime.plugin_markers import has_any_marker
            _title = ""
            if isinstance(event, dict):
                _title = event.get("title") or event.get("lot_title") or ""
            else:
                _title = getattr(event, "title", "") or getattr(event, "lot_title", "") or ""
            if has_any_marker(_title):
                print("[AutoReply] skip new_order - lot has plugin marker: " + _title[:60])
                return
        except Exception as _e_b29:
            print("[AutoReply] B29 skip-check error: " + str(_e_b29))
        if not isinstance(event, dict):
            return
        chat_id = event.get("chat_id")
        if not chat_id:
            return

        order_id = event.get("order_id")
        if self._is_processed_by_autosmm(str(order_id) if order_id else ""):
            print("[AutoReplyEngine] Skipping reply for order " + str(order_id) + " as AutoSMM already processed it.")
            return

        # PLUGIN MARKER CHECK: если в названии лота есть маркер плагина — пропускаем
        # (плагин типа AutoSMM сам ведёт диалог с покупателем)
        order_title = event.get("title", "") or ""
        if has_any_marker(order_title):
            print(f"[AutoReply] skip new_order — lot has plugin marker: {order_title[:60]}")
            return

        rules = self._load_rules()
        enabled_rules = [r for r in rules if r.get("enabled")]
        
        for r in enabled_rules:
            trig = (r.get("trigger") or "").lower()
            rid = r.get("id", "unknown")
            # order_paid OR a generic new_chat that fires once per chat
            if trig in ("order_paid", "new_order", "new_chat"):
                if self._is_recent(chat_id, rid):
                    continue
                tpl = self._resolve_template(r.get("template_id"))
                if not tpl:
                    continue
                msg = self._render(tpl, {
                    "buyer_name": event.get("buyer", ""),
                    "order_id": event.get("order_id", ""),
                    "price": event.get("price", ""),
                })
                self._send(chat_id, msg)

    def _on_review(self, event):
        if not isinstance(event, dict):
            return
        # B74: skip review for AS-marker orders (AutoSMM handles them)
        try:
            _title = event.get("title") or event.get("lot_title") or ""
            from runtime.plugin_markers import has_any_marker
            if _title and has_any_marker(_title):
                print(f"[AutoReply] skip review — AS marker: {_title[:50]}")
                return
        except Exception:
            pass

        order_id = event.get("order_id")
        if self._is_processed_by_autosmm(str(order_id) if order_id else ""):
            print("[AutoReplyEngine] Skipping review for order " + str(order_id) + " as AutoSMM already processed it.")
            return

        chat_id = event.get("chat_id")
        rating = event.get("rating")
        try:
            rating = int(rating) if rating is not None else None
        except (ValueError, TypeError):
            rating = None
        if not chat_id or rating is None:
            return

        rules = self._load_rules()
        enabled_rules = [r for r in rules if r.get("enabled")]
        
        for r in enabled_rules:
            trig = (r.get("trigger") or "").lower()
            if trig != "review_received":
                continue
            rid = r.get("id", "review")
            conditions = r.get("conditions") or {}
            rmin = conditions.get("rating_min")
            rmax = conditions.get("rating_max")
            try:
                rmin = int(rmin) if rmin is not None else 1
                rmax = int(rmax) if rmax is not None else 5
            except (ValueError, TypeError):
                rmin, rmax = 1, 5
            if not (rmin <= rating <= rmax):
                continue
            if self._is_recent(chat_id, rid, context_key=event.get("order_id")):
                continue
            tpl = self._resolve_template(r.get("template_id"))
            if not tpl:
                continue
            msg = self._render(tpl, {
                "buyer_name": event.get("buyer", ""),
                "rating": rating,
                "order_id": event.get("order_id", ""),
            })
            self._send(chat_id, msg)


autoreply_engine_singleton: Optional[AutoReplyEngine] = None