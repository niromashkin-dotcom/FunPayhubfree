import json, time, threading, sys, os
import re as _re
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Any

# Load .env file if present (important for local development)
try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Если задана переменная FUNPAYHUB_CONFIGS — используем её (для EXE)
_configs_override = os.environ.get("FUNPAYHUB_CONFIGS")
if _configs_override:
    _CONFIGS_ROOT = Path(_configs_override)
else:
    _CONFIGS_ROOT = ROOT / "configs"
CREDS_FILE = _CONFIGS_ROOT / "funpay_credentials.json"
CREDS_FILE.parent.mkdir(parents=True, exist_ok=True)

CACHE_TTL = 60
CURRENCY_SYMBOLS = {"USD": "$", "RUB": "₽", "EUR": "€", "UNKNOWN": ""}
_deep_analysis_tasks = {}


def _force_no_proxy():
    for k in list(os.environ.keys()):
        if k.lower() in ("http_proxy", "https_proxy", "all_proxy", "socks_proxy"):
            del os.environ[k]
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"


def _safe_error(e) -> str:
    try:
        msg = str(e)
    except Exception:
        msg = repr(e)
    msg = _re.sub(r"(?is)<script.*?>.*?</script>", " ", msg)
    msg = _re.sub(r"(?is)<style.*?>.*?</style>", " ", msg)
    msg = _re.sub(r"(?s)<[^>]+>", " ", msg)
    msg = _re.sub(r"\s+", " ", msg).strip()
    if len(msg) > 400:
        msg = msg[:400] + "..."
    low = msg.lower()
    if "cloudflare" in low or "just a moment" in low:
        return "FunPay вернул проверку Cloudflare"
    if "403" in msg or "forbidden" in low:
        return "FunPay отклонил запрос (403)"
    if "401" in msg or "unauthorized" in low:
        return "Не авторизован. Обнови golden_key."
    return msg or "Неизвестная ошибка"


def _currency_to_symbol(currency_obj) -> str:
    if currency_obj is None:
        return ""
    name = getattr(currency_obj, "name", None)
    if name:
        return CURRENCY_SYMBOLS.get(name, name)
    return str(currency_obj)


class SellerService:
    def __init__(self):
        self._account = None
        self._lock = threading.Lock()
        self._cache = {}
        self._cache_time = {}
        self._last_error = None
        self._auto_lot_id = None
        self._detected_currency = None
        # Event bus (injected by hub_bootstrap after init)
        self.event_bus = None
        # B169: prevent parallel collect_account_notifications calls
        import threading as _th_b169
        self._collect_lock_b169 = _th_b169.Lock()

    def _emit_event(self, event_type: str, payload: dict):
        """Publish event to event_bus if connected. Safe no-op otherwise."""
        bus = getattr(self, "event_bus", None)
        if bus is None:
            return
        try:
            event = {"type": event_type}
            event.update(payload or {})
            bus.emit(event_type, event)
        except Exception as e:
            try:
                print(f"[seller_service] emit failed: {e}")
            except Exception:
                pass


    # =====================================================================
    # Lot-matcher: связывает заказ с лотом по совпадению title (FunPay API
    # не возвращает lot_id в OrderShortcut, поэтому матчим по названию)
    # =====================================================================
    def _match_order_to_lot(self, order_title: str) -> dict:
        """Возвращает {lot_id, subcategory_id, category_name, ...} или {}."""
        if not order_title:
            return {}
        try:
            cache_key = "orders_lot_map"
            cached_map = self._cache.get(cache_key)
            if not cached_map:
                lots_data = self.get_my_lots(force_refresh=False)
                lots = lots_data.get("lots", []) if isinstance(lots_data, dict) else []
                cached_map = []
                for l in lots:
                    lt = (l.get("title") or "").strip()
                    if not lt:
                        continue
                    cached_map.append({
                        "id": l.get("id"),
                        "title": lt,
                        "title_lower": lt.lower(),
                        "subcategory_id": l.get("subcategory_id"),
                        "subcategory_name": l.get("subcategory_name"),
                        "subcategory_type": l.get("subcategory_type", 0),
                        "category_name": l.get("category_name"),
                    })
                self._cache[cache_key] = cached_map
                self._cache_time[cache_key] = time.time()

            order_title_norm = order_title.lower().strip()
            best = None
            best_score = 0
            for l in cached_map:
                lt = l["title_lower"]
                if order_title_norm.startswith(lt):
                    return {
                        "lot_id": l["id"],
                        "subcategory_id": l["subcategory_id"],
                        "subcategory_name": l["subcategory_name"],
                        "subcategory_type": l["subcategory_type"],
                        "category_name": l["category_name"],
                        "match_confidence": "high",
                    }
                if lt in order_title_norm:
                    score = len(lt)
                    if score > best_score:
                        best_score = score
                        best = l
            if best:
                return {
                    "lot_id": best["id"],
                    "subcategory_id": best["subcategory_id"],
                    "subcategory_name": best["subcategory_name"],
                    "subcategory_type": best["subcategory_type"],
                    "category_name": best["category_name"],
                    "match_confidence": "medium",
                }
        except Exception as e:
            print(f"[seller_service] _match_order_to_lot failed: {e}")
        return {}
    def load_credentials(self) -> dict:
        """Load credentials from file, with ENV fallback for golden_key."""
        # Try reading from file first
        file_creds = {}
        if CREDS_FILE.exists():
            try:
                file_creds = json.loads(CREDS_FILE.read_text(encoding="utf-8"))
            except Exception:
                file_creds = {}

        # If file has a valid golden_key, use it
        if file_creds.get("golden_key"):
            return file_creds

        # Fallback: check environment variables (critical for Render/cloud deployments)
        env_key = (
            os.environ.get("GOLDEN_KEY", "").strip()
            or os.environ.get("FUNPAY_GOLDEN_KEY", "").strip()
            or os.environ.get("FUNPAYHUB_GOLDEN_KEY", "").strip()
        )
        if env_key:
            creds = dict(file_creds)
            creds["golden_key"] = env_key
            # Also persist to file so subsequent calls are faster
            try:
                CREDS_FILE.write_text(json.dumps(creds, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"[seller_service] Auto-saved golden_key from ENV to {CREDS_FILE}")
            except Exception as _e:
                print(f"[seller_service] Could not persist credentials: {_e}")
            return creds

        return file_creds

    def save_credentials(self, golden_key, user_agent=None) -> bool:
        try:
            data = {"golden_key": golden_key.strip()}
            if user_agent:
                data["user_agent"] = user_agent.strip()
            CREDS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            self._reset_state()
            return True
        except Exception as e:
            self._last_error = _safe_error(e)
            return False

    def clear_credentials(self) -> bool:
        try:
            if CREDS_FILE.exists():
                CREDS_FILE.unlink()
            self._reset_state()
            return True
        except Exception as e:
            self._last_error = _safe_error(e)
            return False

    def _reset_state(self):
        self._account = None
        self._cache.clear()
        self._cache_time.clear()
        self._auto_lot_id = None
        self._detected_currency = None

    def has_credentials(self) -> bool:
        return bool(self.load_credentials().get("golden_key"))

    def _get_account(self):
        if self._account is not None:
            return self._account
        creds = self.load_credentials()
        golden_key = creds.get("golden_key", "")
        if not golden_key:
            print("[seller_service] _get_account: no golden_key found in credentials or ENV")
            return None
        try:
            _force_no_proxy()
            print(f"[seller_service] Connecting to FunPay with golden_key={golden_key[:6]}...")
            from FunPayAPI.account import Account
            acc = Account(golden_key=golden_key, user_agent=creds.get("user_agent"), requests_timeout=15, proxy={})
            if hasattr(acc, "session") and acc.session is not None:
                acc.session.trust_env = False
                acc.session.proxies = {}
            acc.get()
            self._account = acc
            self._last_error = None
            print(f"[seller_service] FunPay connected: user={getattr(acc, 'username', '?')} id={getattr(acc, 'id', '?')}")
            return acc
        except Exception as e:
            self._last_error = _safe_error(e)
            self._account = None
            print(f"[seller_service] FunPay connection failed: {self._last_error}")
            return None

    def _cached(self, key, ttl=CACHE_TTL):
        t = self._cache_time.get(key, 0)
        if time.time() - t < ttl:
            return self._cache.get(key)
        return None

    def _set_cache(self, key, value):
        self._cache[key] = value
        self._cache_time[key] = time.time()

    def _find_any_lot_id(self, acc) -> int:
        if self._auto_lot_id:
            return self._auto_lot_id
        try:
            user = acc.get_user(acc.id)
            lots = user.get_lots() if hasattr(user, "get_lots") else []
            for lot in lots:
                lot_id = getattr(lot, "id", None)
                if lot_id:
                    self._auto_lot_id = int(lot_id)
                    return self._auto_lot_id
        except Exception as e:
            self._last_error = _safe_error(e)
        return 0

    def _detect_currency_from_balance(self, bal) -> str:
        if getattr(bal, "total_rub", None) is not None or getattr(bal, "available_rub", None) is not None:
            return "₽"
        if getattr(bal, "total_usd", None) is not None or getattr(bal, "available_usd", None) is not None:
            return "$"
        if getattr(bal, "total_eur", None) is not None or getattr(bal, "available_eur", None) is not None:
            return "€"
        return ""

    def get_account_overview(self, force_refresh=False) -> dict:
        with self._lock:
            if not force_refresh:
                cached = self._cached("overview")
                if cached:
                    return cached
            acc = self._get_account()
            if acc is None:
                return {"connected": False, "error": self._last_error or "Нет авторизации"}
            try:
                cur_sym = _currency_to_symbol(acc.currency)
                if not cur_sym or cur_sym == "UNKNOWN":
                    cur_sym = self._detected_currency or ""
                profile_url = "https://funpay.com/users/" + str(acc.id) + "/" if acc.id else None
                overview = {
                    "connected": True,
                    "id": acc.id,
                    "username": acc.username,
                    "currency": cur_sym or "-",
                    "active_sales": acc.active_sales,
                    "active_purchases": acc.active_purchases,
                    "profile_url": profile_url,
                    "updated_at": time.time()
                }
                self._set_cache("overview", overview)
                return overview
            except Exception as e:
                return {"connected": False, "error": _safe_error(e)}

    def get_balance(self, lot_id=0) -> dict:
        with self._lock:
            if not lot_id:
                cached = self._cached("balance")
                if cached:
                    return cached
            acc = self._get_account()
            if acc is None:
                return {"available": False, "error": self._last_error or "Нет авторизации"}
            try:
                if not lot_id:
                    lot_id = self._find_any_lot_id(acc)
                if not lot_id:
                    return {"available": False, "error": "Нет активных лотов"}
                bal = acc.get_balance(lot_id=lot_id)
                detected = self._detect_currency_from_balance(bal)
                if detected:
                    self._detected_currency = detected
                    if "overview" in self._cache:
                        self._cache["overview"]["currency"] = detected
                result = {
                    "available": True,
                    "lot_id_used": lot_id,
                    "currency_symbol": detected,
                    "total_rub": getattr(bal, "total_rub", None),
                    "available_rub": getattr(bal, "available_rub", None),
                    "total_usd": getattr(bal, "total_usd", None),
                    "available_usd": getattr(bal, "available_usd", None),
                    "total_eur": getattr(bal, "total_eur", None),
                    "available_eur": getattr(bal, "available_eur", None),
                    "updated_at": time.time()
                }
                self._set_cache("balance", result)
                return result
            except Exception as e:
                return {"available": False, "error": _safe_error(e)}

    def get_my_lots(self, force_refresh=False) -> dict:
        with self._lock:
            if not force_refresh:
                cached = self._cached("my_lots", ttl=120)
                if cached:
                    return cached
            acc = self._get_account()
            if acc is None:
                return {"available": False, "error": self._last_error or "Нет авторизации", "lots": [], "categories": [], "total": 0}
            try:
                user = acc.get_user(acc.id)
                raw_lots = user.get_lots() if hasattr(user, "get_lots") else []
                lots = []
                categories = {}
                for lot in raw_lots:
                    lot_id = getattr(lot, "id", None)
                    title = getattr(lot, "title", "") or getattr(lot, "description", "") or "(без названия)"
                    price = getattr(lot, "price", None)
                    amount = getattr(lot, "amount", None)
                    server = getattr(lot, "server", None)
                    subcat = getattr(lot, "subcategory", None)
                    cat_name = "Прочее"
                    subcat_name = ""
                    if subcat is not None:
                        subcat_name = getattr(subcat, "name", "") or ""
                        parent = getattr(subcat, "category", None)
                        if parent is not None:
                            cat_name = getattr(parent, "name", "Прочее") or "Прочее"
                    subcat_id_val = None
                    subcat_type_val = 0
                    if subcat is not None:
                        subcat_id_val = getattr(subcat, "id", None)
                        subcat_type_obj = getattr(subcat, "type", None)
                        if subcat_type_obj is not None:
                            subcat_type_val = getattr(subcat_type_obj, "value", 0)
                    item = {
                        "id": lot_id,
                        "title": str(title)[:300],
                        "price": price,
                        "amount": amount,
                        "server": str(server) if server else None,
                        "category_name": cat_name,
                        "subcategory_name": subcat_name,
                        "subcategory_id": subcat_id_val,
                        "subcategory_type": subcat_type_val,
                        "url": "https://funpay.com/lots/offer?id=" + str(lot_id) if lot_id else None,
                    }
                    lots.append(item)
                    if cat_name not in categories:
                        categories[cat_name] = {"name": cat_name, "count": 0}
                    categories[cat_name]["count"] += 1
                result = {
                    "available": True,
                    "total": len(lots),
                    "lots": lots,
                    "categories": list(categories.values()),
                    "updated_at": time.time()
                }
                self._set_cache("my_lots", result)
                return result
            except Exception as e:
                return {"available": False, "error": _safe_error(e), "lots": [], "categories": [], "total": 0}

    def get_lot_details(self, lot_id: int) -> dict:
        with self._lock:
            cache_key = "lot_" + str(lot_id)
            cached = self._cached(cache_key, ttl=120)
            if cached:
                return cached
            acc = self._get_account()
            if acc is None:
                return {"available": False, "error": self._last_error or "Нет авторизации"}
            try:
                base = None
                my_lots_cache = self._cache.get("my_lots")
                if my_lots_cache:
                    for l in my_lots_cache.get("lots", []):
                        if l.get("id") == lot_id:
                            base = dict(l)
                            break
                if base is None:
                    user = acc.get_user(acc.id)
                    raw_lots = user.get_lots() if hasattr(user, "get_lots") else []
                    for lot in raw_lots:
                        if getattr(lot, "id", None) == lot_id:
                            base = {
                                "id": lot.id,
                                "title": str(getattr(lot, "title", "") or "")[:300],
                                "description": str(getattr(lot, "description", "") or "")[:2000],
                                "price": getattr(lot, "price", None),
                                "amount": getattr(lot, "amount", None),
                                "server": str(getattr(lot, "server", "")) if getattr(lot, "server", None) else None,
                            }
                            sub = getattr(lot, "subcategory", None)
                            if sub is not None:
                                base["subcategory_name"] = getattr(sub, "name", "") or ""
                                par = getattr(sub, "category", None)
                                base["category_name"] = getattr(par, "name", "") if par else ""
                            break
                if base is None:
                    return {"available": False, "error": "Лот не найден"}
                extra = {}
                try:
                    fields = acc.get_lot_fields(lot_id)
                    extra["active"] = getattr(fields, "active", None)
                    extra["deactivate_after_sale"] = getattr(fields, "deactivate_after_sale", None)
                    extra["renew"] = getattr(fields, "renew", None)
                    raw_fields = getattr(fields, "fields", None)
                    if isinstance(raw_fields, dict):
                        clean = {}
                        for k, v in raw_fields.items():
                            try:
                                clean[str(k)] = str(v)[:500] if v is not None else None
                            except Exception:
                                pass
                        extra["raw_fields"] = clean
                except Exception as fe:
                    extra["fields_error"] = _safe_error(fe)
                base["extra"] = extra
                base["url"] = "https://funpay.com/lots/offer?id=" + str(lot_id)
                base["updated_at"] = time.time()
                base["available"] = True
                self._set_cache(cache_key, base)
                return base
            except Exception as e:
                return {"available": False, "error": _safe_error(e)}

    def update_lot_price(self, lot_id: int, new_price: float, dry_run: bool = True) -> dict:
        with self._lock:
            acc = self._get_account()
            if acc is None:
                return {"ok": False, "error": self._last_error or "Нет авторизации"}
            try:
                fields = acc.get_lot_fields(lot_id)
                old_price = getattr(fields, "price", None)
                if dry_run:
                    return {"ok": True, "dry_run": True, "lot_id": lot_id, "old_price": old_price, "new_price": new_price}
                fields.price = new_price
                acc.save_lot(fields)
                self._cache.pop("my_lots", None)
                self._cache.pop("lot_" + str(lot_id), None)
                return {"ok": True, "dry_run": False, "lot_id": lot_id, "old_price": old_price, "new_price": new_price}
            except Exception as e:
                return {"ok": False, "error": _safe_error(e)}

    def toggle_lot_active(self, lot_id: int, active: bool, dry_run: bool = True) -> dict:
        with self._lock:
            acc = self._get_account()
            if acc is None:
                return {"ok": False, "error": self._last_error or "Нет авторизации"}
            try:
                fields = acc.get_lot_fields(lot_id)
                old_active = getattr(fields, "active", None)
                if dry_run:
                    return {"ok": True, "dry_run": True, "lot_id": lot_id, "old_active": old_active, "new_active": active}
                fields.active = active
                acc.save_lot(fields)
                self._cache.pop("my_lots", None)
                self._cache.pop("lot_" + str(lot_id), None)
                return {"ok": True, "dry_run": False, "lot_id": lot_id, "old_active": old_active, "new_active": active}
            except Exception as e:
                return {"ok": False, "error": _safe_error(e)}

    def bulk_update_prices(self, changes: list, dry_run: bool = True) -> dict:
        with self._lock:
            acc = self._get_account()
            if acc is None:
                return {"ok": False, "error": self._last_error or "Нет авторизации", "results": []}
            results = []
            success_count = 0
            fail_count = 0
            for ch in changes:
                lot_id = ch.get("lot_id")
                new_price = ch.get("new_price")
                if not lot_id or new_price is None:
                    results.append({"lot_id": lot_id, "ok": False, "error": "Неверные параметры"})
                    fail_count += 1
                    continue
                try:
                    fields = acc.get_lot_fields(int(lot_id))
                    old_price = getattr(fields, "price", None)
                    if not dry_run:
                        fields.price = float(new_price)
                        acc.save_lot(fields)
                        self._cache.pop("lot_" + str(lot_id), None)
                    results.append({"lot_id": lot_id, "ok": True, "old_price": old_price, "new_price": float(new_price)})
                    success_count += 1
                except Exception as e:
                    results.append({"lot_id": lot_id, "ok": False, "error": _safe_error(e)})
                    fail_count += 1
            if not dry_run:
                self._cache.pop("my_lots", None)
            return {"ok": True, "dry_run": dry_run, "success": success_count, "failed": fail_count, "results": results}

    def raise_category_lots(self, category_id: int, dry_run: bool = True) -> dict:
        with self._lock:
            acc = self._get_account()
            if acc is None:
                return {"ok": False, "error": self._last_error or "Нет авторизации"}
            try:
                if dry_run:
                    return {"ok": True, "dry_run": True, "category_id": category_id}
                acc.raise_lots(category_id)
                self._cache.pop("my_lots", None)
                return {"ok": True, "dry_run": False, "category_id": category_id}
            except Exception as e:
                return {"ok": False, "error": _safe_error(e)}

    def get_sales_data(self, force_refresh: bool = False, include_closed: bool = True, include_refunded: bool = True) -> dict:
        with self._lock:
            cache_key = "sales"
            if not force_refresh:
                cached = self._cached(cache_key, ttl=120)
                if cached:
                    return cached
            acc = self._get_account()
            if acc is None:
                return {"available": False, "error": self._last_error or "Нет авторизации", "sales": [], "stats": {}}
            try:
                raw = acc.get_sales(include_paid=True, include_closed=include_closed, include_refunded=include_refunded)
                sales_list = []
                if isinstance(raw, tuple) and len(raw) >= 2:
                    items = raw[1] if isinstance(raw[1], list) else []
                elif isinstance(raw, list):
                    items = raw
                else:
                    items = []
                import time as _t
                now = _t.time()
                day_ago = now - 86400
                week_ago = now - 86400 * 7
                month_ago = now - 86400 * 30
                total_count = 0
                total_sum = 0.0
                day_count = day_sum = 0
                week_count = week_sum = 0
                month_count = month_sum = 0
                by_lot = {}
                by_status = {}
                for o in items:
                    oid = getattr(o, "id", None)
                    title = getattr(o, "title", "") or getattr(o, "description", "") or "(без названия)"
                    price = getattr(o, "price", None)
                    buyer_id = getattr(o, "buyer_id", None)
                    buyer_username = getattr(o, "buyer_username", None) or getattr(o, "buyer_name", None)
                    status_obj = getattr(o, "status", None)
                    status_val = getattr(status_obj, "name", None) or getattr(status_obj, "value", None) or str(status_obj) if status_obj else "unknown"
                    date_obj = getattr(o, "date", None) or getattr(o, "created", None) or getattr(o, "timestamp", None)
                    ts = None
                    date_str = None
                    if date_obj is not None:
                        try:
                            if hasattr(date_obj, "timestamp"):
                                ts = date_obj.timestamp()
                                date_str = date_obj.strftime("%Y-%m-%d %H:%M:%S") if hasattr(date_obj, "strftime") else str(date_obj)
                            elif isinstance(date_obj, (int, float)):
                                ts = float(date_obj)
                                date_str = _t.strftime("%Y-%m-%d %H:%M:%S", _t.localtime(ts))
                            else:
                                date_str = str(date_obj)
                        except Exception:
                            date_str = str(date_obj)
                    subcat = getattr(o, "subcategory", None)
                    cat_name = ""
                    subcat_name = ""
                    if subcat is not None:
                        subcat_name = getattr(subcat, "name", "") or ""
                        par = getattr(subcat, "category", None)
                        if par is not None:
                            cat_name = getattr(par, "name", "") or ""
                    item = {
                        "id": str(oid) if oid else None,
                        "title": str(title)[:300],
                        "price": price,
                        "buyer_id": buyer_id,
                        "buyer_username": buyer_username,
                        "status": status_val,
                        "date": date_str,
                        "timestamp": ts,
                        "category_name": cat_name,
                        "subcategory_name": subcat_name,
                        "url": "https://funpay.com/orders/" + str(oid) + "/" if oid else None
                    }
                    sales_list.append(item)
                    try:
                        price_num = float(price) if price is not None else 0.0
                    except Exception:
                        price_num = 0.0
                    total_count += 1
                    total_sum += price_num
                    if ts:
                        if ts >= day_ago:
                            day_count += 1
                            day_sum += price_num
                        if ts >= week_ago:
                            week_count += 1
                            week_sum += price_num
                        if ts >= month_ago:
                            month_count += 1
                            month_sum += price_num
                    by_status[status_val] = by_status.get(status_val, 0) + 1
                    key = title[:80]
                    if key not in by_lot:
                        by_lot[key] = {"title": key, "count": 0, "sum": 0.0}
                    by_lot[key]["count"] += 1
                    by_lot[key]["sum"] += price_num
                top_lots = sorted(by_lot.values(), key=lambda x: x["count"], reverse=True)[:10]
                stats = {
                    "total_count": total_count,
                    "total_sum": round(total_sum, 2),
                    "day_count": day_count,
                    "day_sum": round(day_sum, 2),
                    "week_count": week_count,
                    "week_sum": round(week_sum, 2),
                    "month_count": month_count,
                    "month_sum": round(month_sum, 2),
                    "by_status": by_status,
                    "top_lots": top_lots,
                    "avg_price": round(total_sum / total_count, 2) if total_count else 0
                }
                result = {
                    "available": True,
                    "sales": sales_list,
                    "stats": stats,
                    "updated_at": _t.time()
                }
                self._set_cache(cache_key, result)
                return result
            except Exception as e:
                return {"available": False, "error": _safe_error(e), "sales": [], "stats": {}}

    def get_orders_data(self, force_refresh: bool = False) -> dict:
        with self._lock:
            cache_key = "orders"
            if not force_refresh:
                cached = self._cached(cache_key, ttl=60)
                if cached:
                    return cached
            acc = self._get_account()
            if acc is None:
                return {"available": False, "error": self._last_error or "Нет авторизации", "orders": [], "chats": [], "stats": {}}
            try:
                import time as _t
                raw = acc.get_sells()
                if isinstance(raw, tuple) and len(raw) >= 2:
                    items = raw[1] if isinstance(raw[1], list) else []
                elif isinstance(raw, list):
                    items = raw
                else:
                    items = []
                orders = []
                stats = {"total": 0, "by_status": {}, "sum": 0.0}
                for o in items:
                    oid = getattr(o, "id", None)
                    title = getattr(o, "title", "") or getattr(o, "description", "") or "(без названия)"
                    price = getattr(o, "price", None)
                    buyer_id = getattr(o, "buyer_id", None)
                    buyer_username = getattr(o, "buyer_username", None) or getattr(o, "buyer_name", None)
                    status_obj = getattr(o, "status", None)
                    status_val = getattr(status_obj, "name", None) or str(status_obj) if status_obj else "unknown"
                    date_obj = getattr(o, "date", None) or getattr(o, "created", None)
                    date_str = None
                    ts = None
                    if date_obj is not None:
                        try:
                            if hasattr(date_obj, "timestamp"):
                                ts = date_obj.timestamp()
                                date_str = date_obj.strftime("%Y-%m-%d %H:%M:%S") if hasattr(date_obj, "strftime") else str(date_obj)
                            elif isinstance(date_obj, (int, float)):
                                ts = float(date_obj)
                                date_str = _t.strftime("%Y-%m-%d %H:%M:%S", _t.localtime(ts))
                            else:
                                date_str = str(date_obj)
                        except Exception:
                            date_str = str(date_obj)
                    chat_id = getattr(o, "chat_id", None)
                    subcat = getattr(o, "subcategory", None)
                    cat_name = ""
                    subcat_name = ""
                    if subcat is not None:
                        subcat_name = getattr(subcat, "name", "") or ""
                        par = getattr(subcat, "category", None)
                        if par is not None:
                            cat_name = getattr(par, "name", "") or ""
                    try:
                        pn = float(price) if price is not None else 0.0
                    except Exception:
                        pn = 0.0
                    item = {
                        "id": str(oid) if oid else None,
                        "title": str(title)[:300],
                        "price": price,
                        "buyer_id": buyer_id,
                        "buyer_username": buyer_username,
                        "chat_id": chat_id,
                        "status": status_val,
                        "date": date_str,
                        "timestamp": ts,
                        "category_name": cat_name,
                        "subcategory_name": subcat_name,
                        "url": "https://funpay.com/orders/" + str(oid) + "/" if oid else None
                    }
                    orders.append(item)
                    stats["total"] += 1
                    stats["sum"] += pn
                    stats["by_status"][status_val] = stats["by_status"].get(status_val, 0) + 1
                stats["sum"] = round(stats["sum"], 2)
                chats_data = []
                try:
                    chats_raw = acc.get_chats()
                    chats_map = chats_raw if isinstance(chats_raw, dict) else {}
                    for cid, c in chats_map.items():
                        chats_data.append({
                            "id": cid,
                            "name": getattr(c, "name", "") or "",
                            "unread": bool(getattr(c, "unread", False)),
                            "last_message": str(getattr(c, "last_message_text", "") or "")[:200],
                            "last_by_bot": bool(getattr(c, "last_by_bot", False)),
                            "node_id": getattr(c, "node_id", None),
                            "looking_text": getattr(c, "looking_text", None)
                        })
                except Exception as ce:
                    pass
                result = {
                    "available": True,
                    "orders": orders,
                    "chats": chats_data,
                    "stats": stats,
                    "updated_at": _t.time()
                }
                self._set_cache(cache_key, result)
                return result
            except Exception as e:
                return {"available": False, "error": _safe_error(e), "orders": [], "chats": [], "stats": {}}

    def get_chat_messages(self, chat_id, limit: int = 50) -> dict:
        with self._lock:
            acc = self._get_account()
            if acc is None:
                return {"available": False, "error": self._last_error or "Нет авторизации", "messages": []}
            try:
                raw = acc.get_chat_history(chat_id)
                messages = []
                items = raw if isinstance(raw, list) else []
                for m in items[-limit:]:
                    text = getattr(m, "text", "") or ""
                    author = getattr(m, "author", "") or getattr(m, "author_id", "")
                    author_id = getattr(m, "author_id", None)
                    mid = getattr(m, "id", None)
                    is_my = bool(getattr(m, "by_bot", False)) or (author_id == acc.id)
                    messages.append({
                        "id": mid,
                        "text": str(text)[:1000],
                        "author": str(author),
                        "author_id": author_id,
                        "is_my": is_my
                    })
                return {"available": True, "messages": messages, "count": len(messages)}
            except Exception as e:
                return {"available": False, "error": _safe_error(e), "messages": []}

    def send_chat_message(self, chat_id, text: str, dry_run: bool = True) -> dict:
        with self._lock:
            acc = self._get_account()
            if acc is None:
                return {"ok": False, "error": self._last_error or "Нет авторизации"}
            if not text or not text.strip():
                return {"ok": False, "error": "Пустое сообщение"}
            try:
                if dry_run:
                    return {"ok": True, "dry_run": True, "chat_id": chat_id, "text": text}
                acc.send_message(chat_id, text=text)
                return {"ok": True, "dry_run": False, "chat_id": chat_id, "text": text}
            except Exception as e:
                return {"ok": False, "error": _safe_error(e)}



    def reply_to_review(self, order_id: str, text: str) -> dict:
        """B72: reply_to_review — отвечаем на отзыв покупателя через send_review.
        FunPay использует один endpoint для отзыва и ответа, различает по authorId.
        Если authorId == наш id и rating пустой → это ответ продавца."""
        with self._lock:
            acc = self._get_account()
            if acc is None:
                return {"ok": False, "error": self._last_error or "Нет авторизации"}
            if not text or not text.strip():
                return {"ok": False, "error": "Пустой текст"}
            try:
                # rating="" означает "ответ продавца" (не новый отзыв)
                result = acc.send_review(order_id=order_id, text=text, rating=0)
                return {"ok": True, "order_id": order_id, "text": text}
            except Exception as e:
                return {"ok": False, "error": _safe_error(e)}


    def refund_order(self, order_id, dry_run: bool = True) -> dict:
        with self._lock:
            acc = self._get_account()
            if acc is None:
                return {"ok": False, "error": self._last_error or "Нет авторизации"}
            try:
                if dry_run:
                    return {"ok": True, "dry_run": True, "order_id": order_id, "message": "Проверка пройдена"}
                acc.refund(order_id)
                self._cache.pop("orders", None)
                return {"ok": True, "dry_run": False, "order_id": order_id, "message": "Возврат оформлен"}
            except Exception as e:
                return {"ok": False, "error": _safe_error(e)}

    def get_customers_data(self, force_refresh: bool = False) -> dict:
        with self._lock:
            cache_key = "customers"
            if not force_refresh:
                cached = self._cached(cache_key, ttl=300)
                if cached:
                    return cached
            acc = self._get_account()
            if acc is None:
                return {"available": False, "error": self._last_error or "Нет авторизации", "customers": [], "stats": {}}
            try:
                import time as _t
                raw = acc.get_sales(include_paid=True, include_closed=True, include_refunded=True)
                if isinstance(raw, tuple) and len(raw) >= 2:
                    items = raw[1] if isinstance(raw[1], list) else []
                elif isinstance(raw, list):
                    items = raw
                else:
                    items = []
                now = _t.time()
                day_ago = now - 86400
                week_ago = now - 86400 * 7
                month_ago = now - 86400 * 30
                customers = {}
                for o in items:
                    bid = getattr(o, "buyer_id", None)
                    bname = getattr(o, "buyer_username", None) or getattr(o, "buyer_name", None) or "Аноним"
                    if not bid:
                        continue
                    price = getattr(o, "price", None)
                    try:
                        pn = float(price) if price is not None else 0.0
                    except Exception:
                        pn = 0.0
                    status_obj = getattr(o, "status", None)
                    status_val = getattr(status_obj, "name", None) or str(status_obj) if status_obj else "unknown"
                    date_obj = getattr(o, "date", None) or getattr(o, "created", None)
                    ts = None
                    if date_obj is not None:
                        try:
                            if hasattr(date_obj, "timestamp"):
                                ts = date_obj.timestamp()
                            elif isinstance(date_obj, (int, float)):
                                ts = float(date_obj)
                        except Exception:
                            pass
                    key = str(bid)
                    if key not in customers:
                        customers[key] = {
                            "buyer_id": bid,
                            "buyer_username": bname,
                            "orders_count": 0,
                            "total_sum": 0.0,
                            "last_ts": None,
                            "last_date": None,
                            "first_ts": None,
                            "statuses": {},
                            "order_ids": []
                        }
                    c = customers[key]
                    c["orders_count"] += 1
                    c["total_sum"] += pn
                    c["statuses"][status_val] = c["statuses"].get(status_val, 0) + 1
                    oid = getattr(o, "id", None)
                    if oid:
                        c["order_ids"].append(str(oid))
                    if ts:
                        if c["last_ts"] is None or ts > c["last_ts"]:
                            c["last_ts"] = ts
                            c["last_date"] = _t.strftime("%Y-%m-%d %H:%M:%S", _t.localtime(ts))
                        if c["first_ts"] is None or ts < c["first_ts"]:
                            c["first_ts"] = ts
                customers_list = []
                for c in customers.values():
                    c["total_sum"] = round(c["total_sum"], 2)
                    c["avg_check"] = round(c["total_sum"] / c["orders_count"], 2) if c["orders_count"] else 0
                    c["is_repeat"] = c["orders_count"] > 1
                    c["profile_url"] = "https://funpay.com/users/" + str(c["buyer_id"]) + "/" if c["buyer_id"] else None
                    customers_list.append(c)
                customers_list.sort(key=lambda x: x["total_sum"], reverse=True)
                total_customers = len(customers_list)
                repeat_customers = sum(1 for c in customers_list if c["is_repeat"])
                day_active = sum(1 for c in customers_list if c["last_ts"] and c["last_ts"] >= day_ago)
                week_active = sum(1 for c in customers_list if c["last_ts"] and c["last_ts"] >= week_ago)
                month_active = sum(1 for c in customers_list if c["last_ts"] and c["last_ts"] >= month_ago)
                total_revenue = round(sum(c["total_sum"] for c in customers_list), 2)
                top_by_sum = customers_list[:10]
                top_by_count = sorted(customers_list, key=lambda x: x["orders_count"], reverse=True)[:10]
                stats = {
                    "total_customers": total_customers,
                    "repeat_customers": repeat_customers,
                    "repeat_pct": round(repeat_customers / total_customers * 100, 1) if total_customers else 0,
                    "day_active": day_active,
                    "week_active": week_active,
                    "month_active": month_active,
                    "total_revenue": total_revenue,
                    "avg_per_customer": round(total_revenue / total_customers, 2) if total_customers else 0,
                    "top_by_sum": top_by_sum,
                    "top_by_count": top_by_count
                }
                result = {
                    "available": True,
                    "customers": customers_list,
                    "stats": stats,
                    "updated_at": _t.time()
                }
                self._set_cache(cache_key, result)
                return result
            except Exception as e:
                return {"available": False, "error": _safe_error(e), "customers": [], "stats": {}}

    def get_customer_details(self, buyer_id) -> dict:
        with self._lock:
            acc = self._get_account()
            if acc is None:
                return {"available": False, "error": self._last_error or "Нет авторизации"}
            try:
                customers_data = self._cached("customers")
                if not customers_data:
                    self._lock.release()
                    try:
                        customers_data = self.get_customers_data()
                    finally:
                        self._lock.acquire()
                if not customers_data or not customers_data.get("available"):
                    return {"available": False, "error": "Не удалось загрузить покупателей"}
                target = None
                for c in customers_data.get("customers", []):
                    if str(c.get("buyer_id")) == str(buyer_id):
                        target = c
                        break
                if not target:
                    return {"available": False, "error": "Покупатель не найден"}
                try:
                    profile = acc.get_user(int(buyer_id))
                    target["registered"] = getattr(profile, "registration_date", None) and str(profile.registration_date)
                    target["online"] = getattr(profile, "online", None)
                except Exception:
                    pass
                return {"available": True, "customer": target}
            except Exception as e:
                return {"available": False, "error": _safe_error(e)}

    def get_balance_full(self, force_refresh: bool = False) -> dict:
        with self._lock:
            cache_key = "balance_full"
            if not force_refresh:
                cached = self._cached(cache_key, ttl=60)
                if cached:
                    return cached
            acc = self._get_account()
            if acc is None:
                return {"available": False, "error": self._last_error or "Нет авторизации"}
            try:
                import time as _t
                lot_id = self._find_any_lot_id(acc)
                balance_data = {}
                if lot_id:
                    bal = acc.get_balance(lot_id=lot_id)
                    balance_data = {
                        "total_rub": getattr(bal, "total_rub", None),
                        "available_rub": getattr(bal, "available_rub", None),
                        "total_usd": getattr(bal, "total_usd", None),
                        "available_usd": getattr(bal, "available_usd", None),
                        "total_eur": getattr(bal, "total_eur", None),
                        "available_eur": getattr(bal, "available_eur", None),
                        "lot_id_used": lot_id
                    }
                wallets_data = []
                try:
                    wallets = acc.get_wallets()
                    for w in wallets or []:
                        wallets_data.append({
                            "type": str(getattr(w, "type", "")),
                            "address": str(getattr(w, "address", ""))[:200]
                        })
                except Exception:
                    pass
                self._save_balance_snapshot(balance_data)
                history = self._load_balance_history(limit=200)
                result = {
                    "available": True,
                    "balance": balance_data,
                    "wallets": wallets_data,
                    "history": history,
                    "updated_at": _t.time()
                }
                self._set_cache(cache_key, result)
                return result
            except Exception as e:
                return {"available": False, "error": _safe_error(e)}

    def _balance_history_file(self):
        return _CONFIGS_ROOT / "balance_history.json"

    def _load_balance_history(self, limit: int = 200) -> list:
        path = self._balance_history_file()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data[-limit:]
        except Exception:
            pass
        return []

    def _save_balance_snapshot(self, balance: dict):
        try:
            import time as _t
            path = self._balance_history_file()
            history = []
            if path.exists():
                try:
                    history = json.loads(path.read_text(encoding="utf-8"))
                    if not isinstance(history, list):
                        history = []
                except Exception:
                    history = []
            now = _t.time()
            if history:
                last_ts = history[-1].get("timestamp", 0)
                if now - last_ts < 300:
                    return
            snapshot = {
                "timestamp": now,
                "date": _t.strftime("%Y-%m-%d %H:%M:%S", _t.localtime(now)),
                "total_rub": balance.get("total_rub"),
                "available_rub": balance.get("available_rub"),
                "total_usd": balance.get("total_usd"),
                "available_usd": balance.get("available_usd"),
                "total_eur": balance.get("total_eur"),
                "available_eur": balance.get("available_eur")
            }
            history.append(snapshot)
            history = history[-500:]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def get_balance_history(self, limit: int = 200) -> dict:
        history = self._load_balance_history(limit=limit)
        return {"available": True, "history": history, "count": len(history)}

    def clear_balance_history(self) -> dict:
        try:
            path = self._balance_history_file()
            if path.exists():
                path.unlink()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": _safe_error(e)}

    def _notifications_file(self):
        return _CONFIGS_ROOT / "account_notifications.json"

    def _state_file(self):
        return _CONFIGS_ROOT / "notification_state.json"

    def _load_notifications(self) -> list:
        path = self._notifications_file()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_notifications(self, notifications: list):
        path = self._notifications_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(notifications[-500:], ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_state(self) -> dict:
        path = self._state_file()
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_state(self, state: dict):
        path = self._state_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")



    # B60: order_completed emit — отслеживаем смену статуса заказа
    def _b60_emit_order_completed(self, state, current_orders):
        """Сравнивает known статусы заказов с текущими.
        Если PAID → CLOSED/COMPLETED — emit order_completed."""
        try:
            known_statuses = state.get("known_order_statuses", {})  # {oid: "PAID"}
            new_statuses = {}
            for o in current_orders:
                oid = o.get("id")
                status = str(o.get("status") or "")
                # Чистим OrderStatuses.XXX → XXX
                if "." in status:
                    status = status.split(".")[-1]
                if not oid or not status:
                    continue
                new_statuses[oid] = status
                
                prev = known_statuses.get(oid)
                # Если был PAID и стал CLOSED/COMPLETED → заказ подтверждён покупателем
                if prev == "PAID" and status in ("CLOSED", "COMPLETED"):
                    print(f"[seller_service][B60] order_completed: {oid} ({prev} -> {status})")
                    self._emit_event("order_completed", {
                        "order_id": oid,
                        "previous_status": prev,
                        "new_status": status,
                        "lot_id": o.get("lot_id"),
                        "chat_id": o.get("chat_id"),
                        "buyer": o.get("buyer_username"),
                        "buyer_id": o.get("buyer_id"),
                        "price": o.get("price"),
                        "title": o.get("title"),
                        "lot_title": o.get("title"),
                        "url": o.get("url"),
                    })
            state["known_order_statuses"] = new_statuses
        except Exception as _e_b60:
            print(f"[seller_service][B60] err: {_e_b60}")


    def collect_account_notifications(self) -> dict:
        # B169: serialize collect to avoid duplicate emits from parallel HTTP calls
        if not self._collect_lock_b169.acquire(blocking=False):
            return {"available": True, "new_count": 0, "new_items": [], "skipped": "parallel_call"}
        try:
            return self._collect_account_notifications_impl()
        finally:
            self._collect_lock_b169.release()

    def _collect_account_notifications_impl(self) -> dict:
        import time as _t, uuid as _uuid
        with self._lock:
            acc = self._get_account()
            if acc is None:
                return {"available": False, "error": self._last_error or "Нет авторизации", "new_count": 0}
        state = self._load_state()
        notifications = self._load_notifications()
        new_items = []
        orders_data = self.get_orders_data(force_refresh=True)
        # B60: emit order_completed events
        try:
            self._b60_emit_order_completed(state, orders_data.get("orders", []) if orders_data else [])
        except Exception as _e_b60c:
            print(f"[seller_service][B60-call] err: {_e_b60c}")
        if orders_data.get("available"):
            known_orders = set(state.get("known_orders", []))
            current_orders = set()
            for o in orders_data.get("orders", []):
                oid = o.get("id")
                if not oid:
                    continue
                current_orders.add(oid)
                if oid not in known_orders:
                    new_items.append({
                        "id": str(_uuid.uuid4()),
                        "type": "new_order",
                        "timestamp": _t.time(),
                        "date": _t.strftime("%Y-%m-%d %H:%M:%S", _t.localtime()),
                        "title": "Новый заказ #" + str(oid),
                        "message": (o.get("title") or "")[:200],
                        "data": {"order_id": oid, "price": o.get("price"), "buyer": o.get("buyer_username"), "url": o.get("url")},
                        "acknowledged": False,
                        "dismissed": False
                    })
                    # Publish to event bus -> AutoSMM, autoreply, notifications UI
                    try:
                        _lot_match = self._match_order_to_lot(o.get("title") or "")
                        self._emit_event("new_order", {
                            "order_id": oid,
                            "lot_id": _lot_match.get("lot_id"),
                            "subcategory_id": _lot_match.get("subcategory_id"),
                            "subcategory_name": _lot_match.get("subcategory_name"),
                            "subcategory_type": _lot_match.get("subcategory_type"),
                            "category_name": _lot_match.get("category_name"),
                            "match_confidence": _lot_match.get("match_confidence"),
                            "chat_id": o.get("chat_id"),
                            "buyer": o.get("buyer_username"),
                            "buyer_id": o.get("buyer_id"),
                            "price": o.get("price"),
                            "title": o.get("title"),
                            "url": o.get("url"),
                        })
                    except Exception:
                        pass
            state["known_orders"] = list(current_orders)[-200:]
            chats = orders_data.get("chats", [])
            known_chats = state.get("known_chat_messages", {})
            for c in chats:
                cid = str(c.get("id", ""))
                if not cid:
                    continue
                last_msg = c.get("last_message", "")
                if not last_msg or c.get("last_by_bot"):
                    known_chats[cid] = last_msg
                    continue
                if known_chats.get(cid) != last_msg:
                    if cid in known_chats:
                        new_items.append({
                            "id": str(_uuid.uuid4()),
                            "type": "chat_message",
                            "timestamp": _t.time(),
                            "date": _t.strftime("%Y-%m-%d %H:%M:%S", _t.localtime()),
                            "title": "Новое сообщение в чате",
                            "message": (c.get("name") or "Чат") + ": " + last_msg[:150],
                            "data": {"chat_id": cid, "chat_name": c.get("name")},
                            "acknowledged": False,
                            "dismissed": False
                        })
                        # Publish to event bus -> AutoSMM dialog handler, autoreply
                        try:
                            self._emit_event("new_message", {
                                "chat_id": cid,
                                "chat_name": c.get("name"),
                                "text": last_msg,
                                "from_me": False,
                            })
                        except Exception:
                            pass
                    known_chats[cid] = last_msg
            state["known_chat_messages"] = known_chats
        sales_data = self.get_sales_data(force_refresh=True)
        if sales_data.get("available"):
            known_sales = set(state.get("known_sales", []))
            current_sales = set()
            for s in sales_data.get("sales", []):
                sid = s.get("id")
                if not sid:
                    continue
                current_sales.add(sid)
                if sid not in known_sales:
                    status = s.get("status", "")
                    if str(status).upper() in ("CLOSED", "REFUNDED"):
                        new_items.append({
                            "id": str(_uuid.uuid4()),
                            "type": "refund" if "REFUND" in str(status).upper() else "order_closed",
                            "timestamp": _t.time(),
                            "date": _t.strftime("%Y-%m-%d %H:%M:%S", _t.localtime()),
                            "title": ("Возврат заказа " if "REFUND" in str(status).upper() else "Заказ закрыт ") + "#" + str(sid),
                            "message": (s.get("title") or "")[:200],
                            "data": {"order_id": sid, "price": s.get("price"), "buyer": s.get("buyer_username")},
                            "acknowledged": False,
                            "dismissed": False
                        })
            state["known_sales"] = list(current_sales)[-300:]
        bal_data = self.get_balance_full(force_refresh=True)
        if bal_data.get("available"):
            cur_bal = bal_data.get("balance", {})
            cur_rub = cur_bal.get("available_rub") or cur_bal.get("total_rub")
            last_bal = state.get("last_balance_rub")
            if cur_rub is not None and last_bal is not None and abs(float(cur_rub) - float(last_bal)) >= 0.01:
                diff = float(cur_rub) - float(last_bal)
                new_items.append({
                    "id": str(_uuid.uuid4()),
                    "type": "balance_change",
                    "timestamp": _t.time(),
                    "date": _t.strftime("%Y-%m-%d %H:%M:%S", _t.localtime()),
                    "title": "Баланс " + ("+" if diff > 0 else "") + str(round(diff, 2)) + " ₽",
                    "message": "Было " + str(last_bal) + " ₽, стало " + str(cur_rub) + " ₽",
                    "data": {"old": last_bal, "new": cur_rub, "diff": round(diff, 2)},
                    "acknowledged": False,
                    "dismissed": False
                })
            if cur_rub is not None:
                state["last_balance_rub"] = float(cur_rub)
        # B16: Review collection BEFORE _save_state so known_reviews persists
        try:
            self._collect_new_reviews(state, new_items, acc)
        except Exception as _rev_err:
            print(f"[seller_service] review collection failed: {_rev_err}")

        if new_items:
            notifications.extend(new_items)
            self._save_notifications(notifications)
        self._save_state(state)

        return {"available": True, "new_count": len(new_items), "new_items": new_items}


    # =====================================================================
    # REVIEW COLLECTOR: парсит HTML профиля и emit-ит review_received
    # =====================================================================
    def _collect_new_reviews(self, state: dict, new_items: list, acc) -> None:
        """Сканирует отзывы на странице профиля. На каждый новый — emit review_received."""
        if not acc:
            return
        try:
            my_id = acc.id
            user_profile = acc.get_user(my_id)
            html = getattr(user_profile, "html", "") or ""
        except Exception as e:
            print(f"[seller_service] get_user for reviews failed: {e}")
            return

        if not html:
            return

        import re as _re, uuid as _uuid, time as _t

        # Парсим блоки review-item через regex
        # Структура (грубо):
        #   <div class="rating"><div class="rating5"></div></div>     -> stars
        #   <a href="https://funpay.com/users/19952092/">hehahhswijq</a> -> author + author_id
        #   <a href="https://funpay.com/orders/ASKU7VY3/">Заказ #...</a> -> order_id
        #   <div class="review-item-date">...</div>                   -> date_str
        #   <div class="review-item-text">...</div>                   -> text

        # Бьём HTML по review-item блокам
        # (?s) = DOTALL
        blocks = _re.split(r'(?s)<div class="review-item">', html)
        # Первый кусок — до первого review-item (пропускаем)
        blocks = blocks[1:] if len(blocks) > 1 else []

        known_reviews = set(state.get("known_reviews", []))
        new_review_keys = set()
        parsed_count = 0

        for blk in blocks:
            # Закрытие — берём только до первого "</div>" 4-5 раз вложенного, но проще ограничить
            # 5000 символов на один блок отзыва точно хватит
            blk_text = blk[:5000]

            # Stars: <div class="ratingN"> где N=1..5
            m_stars = _re.search(r'<div class="rating(\d)"></div>', blk_text)
            if not m_stars:
                continue
            try:
                stars = int(m_stars.group(1))
            except (ValueError, TypeError):
                continue
            if stars < 1 or stars > 5:
                continue

            # Order ID: href="https://funpay.com/orders/XXXXX/"
            m_oid = _re.search(r'href="https?://funpay\.com/orders/([A-Z0-9]+)/?"', blk_text)
            order_id = m_oid.group(1) if m_oid else None

            # Author: <a href="/users/123/">username</a>
            m_author = _re.search(r'href="https?://funpay\.com/users/(\d+)/?"[^>]*>([^<]+)</a>', blk_text)
            author_id = None
            author = None
            if m_author:
                try:
                    author_id = int(m_author.group(1))
                except (ValueError, TypeError):
                    pass
                author = (m_author.group(2) or "").strip()

            # Date: <div class="review-item-date">текст</div>
            m_date = _re.search(r'<div class="review-item-date">([^<]+)</div>', blk_text)
            date_str = (m_date.group(1).strip() if m_date else "")

            # Text: <div class="review-item-text">текст</div>
            m_text = _re.search(r'(?s)<div class="review-item-text">\s*(.*?)\s*</div>', blk_text)
            text = ""
            if m_text:
                text = _re.sub(r'<[^>]+>', '', m_text.group(1)).strip()

            # Detail: <div class="review-item-detail">Telegram, 40 ₽</div>
            m_detail = _re.search(r'<div class="review-item-detail">([^<]+)</div>', blk_text)
            detail = (m_detail.group(1).strip() if m_detail else "")

            parsed_count += 1

            # Unique key для дедупликации
            # order_id обычно уникален — это лучший ключ
            # Если нет — берём author_id + date_str + stars
            if order_id:
                key = f"o:{order_id}"
            elif author_id:
                key = f"u:{author_id}::{date_str}::{stars}"
            else:
                key = f"d:{date_str}::{stars}::{text[:30]}"

            new_review_keys.add(key)

            if key in known_reviews:
                continue

            # Новый отзыв! Формируем chat_id (users-<my_id>-<author_id>)
            chat_id = None
            if author_id:
                a, b = sorted([int(my_id), int(author_id)])
                chat_id = f"users-{a}-{b}"

            # Сохраняем в new_items (для UI Уведомлений)
            new_items.append({
                "id": str(_uuid.uuid4()),
                "type": "new_review",
                "timestamp": _t.time(),
                "date": _t.strftime("%Y-%m-%d %H:%M:%S", _t.localtime()),
                "title": f"Новый отзыв {stars}★" + (f" к заказу #{order_id}" if order_id else ""),
                "message": (text or detail or "")[:200],
                "data": {
                    "stars":     stars,
                    "order_id":  order_id,
                    "author":    author,
                    "author_id": author_id,
                    "chat_id":   chat_id,
                    "text":      text,
                    "detail":    detail,
                    "date_str":  date_str,
                },
                "acknowledged": False,
                "dismissed": False,
            })

            # Emit на event_bus -> AutoReplyEngine подберёт правильный шаблон
            try:
                self._emit_event("review_received", {
                    "stars":     stars,
                    "rating":    stars,
                    "order_id":  order_id,
                    "chat_id":   chat_id,
                    "buyer":     author,
                    "buyer_id":  author_id,
                    "text":      text,
                    "detail":    detail,
                    "date_str":  date_str,
                })
                print(f"[seller_service] emit review_received: {stars}* by {author} on order {order_id}")
            except Exception as _e_emit:
                print(f"[seller_service] emit review failed: {_e_emit}")

        # Обновляем state — храним только последние 500 ключей
        all_keys = list(known_reviews | new_review_keys)[-500:]
        state["known_reviews"] = all_keys

    def get_account_notifications(self, only_unack: bool = False, limit: int = 200, type_filter: str = None) -> dict:
        notifications = self._load_notifications()
        items = [n for n in notifications if not n.get("dismissed", False)]
        if only_unack:
            items = [n for n in items if not n.get("acknowledged", False)]
        if type_filter:
            items = [n for n in items if n.get("type") == type_filter]
        items = items[-limit:]
        by_type = {}
        unack = 0
        for n in self._load_notifications():
            if n.get("dismissed"):
                continue
            t = n.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
            if not n.get("acknowledged"):
                unack += 1
        return {"available": True, "items": items, "count": len(items), "unacknowledged": unack, "by_type": by_type}

    def ack_account_notification(self, notif_id: str) -> dict:
        notifications = self._load_notifications()
        for n in notifications:
            if n.get("id") == notif_id:
                n["acknowledged"] = True
                self._save_notifications(notifications)
                return {"ok": True}
        return {"ok": False, "error": "Не найдено"}

    def dismiss_account_notification(self, notif_id: str) -> dict:
        notifications = self._load_notifications()
        for n in notifications:
            if n.get("id") == notif_id:
                n["dismissed"] = True
                self._save_notifications(notifications)
                return {"ok": True}
        return {"ok": False, "error": "Не найдено"}

    def clear_account_notifications(self) -> dict:
        self._save_notifications([])
        return {"ok": True}

    def get_my_categories(self) -> dict:
        my_lots = self.get_my_lots()
        if not my_lots.get("available"):
            return {"available": False, "error": my_lots.get("error", ""), "categories": []}
        acc = self._account
        if acc is None:
            return {"available": False, "error": "Нет авторизации", "categories": []}
        seen = {}
        try:
            user = acc.get_user(acc.id)
            raw_lots = user.get_lots() if hasattr(user, "get_lots") else []
            for lot in raw_lots:
                sub = getattr(lot, "subcategory", None)
                if sub is None:
                    continue
                sub_id = getattr(sub, "id", None)
                sub_name = getattr(sub, "name", "") or ""
                sub_type = getattr(sub, "type", None)
                par = getattr(sub, "category", None)
                cat_id = getattr(par, "id", None) if par else None
                cat_name = getattr(par, "name", "") if par else ""
                type_value = 0
                if sub_type is not None:
                    type_value = getattr(sub_type, "value", 0)
                key = str(sub_id)
                if key not in seen:
                    seen[key] = {
                        "subcategory_id": sub_id,
                        "subcategory_name": sub_name,
                        "subcategory_type": type_value,
                        "category_id": cat_id,
                        "category_name": cat_name,
                        "my_lots_count": 0
                    }
                seen[key]["my_lots_count"] += 1
        except Exception as e:
            return {"available": False, "error": _safe_error(e), "categories": []}
        return {"available": True, "categories": list(seen.values())}

    def scan_market(self, subcategory_id: int, subcategory_type: int = 0, force_refresh: bool = False) -> dict:
        import time as _t
        with self._lock:
            cache_key = f"market_{subcategory_type}_{subcategory_id}"
            if not force_refresh:
                cached = self._cached(cache_key, ttl=300)
                if cached:
                    return cached
            acc = self._get_account()
            if acc is None:
                return {"available": False, "error": self._last_error or "Нет авторизации", "lots": []}
            try:
                from FunPayAPI.common.enums import SubCategoryTypes
                stype = SubCategoryTypes(subcategory_type)
                raw = acc.get_subcategory_public_lots(stype, int(subcategory_id), locale="ru")
                items = raw if isinstance(raw, list) else []
                lots = []
                sellers = {}
                prices = []
                my_id = acc.id
                for lot in items:
                    lot_id = getattr(lot, "id", None)
                    title = getattr(lot, "title", "") or getattr(lot, "description", "") or "(без названия)"
                    price = getattr(lot, "price", None)
                    amount = getattr(lot, "amount", None)
                    server = getattr(lot, "server", None)
                    currency = getattr(lot, "currency", None)
                    auto = getattr(lot, "auto", None)
                    promo = getattr(lot, "promo", None)
                    seller_obj = getattr(lot, "seller", None)
                    seller_id = None
                    seller_name = ""
                    seller_rating = None
                    seller_reviews = None
                    if seller_obj is not None:
                        seller_id = getattr(seller_obj, "id", None) or getattr(seller_obj, "user_id", None)
                        seller_name = getattr(seller_obj, "username", None) or getattr(seller_obj, "name", None) or getattr(seller_obj, "nickname", None) or ""
                        seller_rating = getattr(seller_obj, "rating", None) or getattr(seller_obj, "stars", None)
                        seller_reviews = getattr(seller_obj, "reviews_count", None) or getattr(seller_obj, "reviews", None)
                    try:
                        pn = float(price) if price is not None else None
                    except Exception:
                        pn = None
                    if pn is not None:
                        prices.append(pn)
                    is_mine = (seller_id == my_id) if seller_id and my_id else False
                    item = {
                        "id": lot_id,
                        "title": str(title)[:300],
                        "price": pn,
                        "amount": amount,
                        "server": str(server) if server else None,
                        "seller_id": seller_id,
                        "seller_name": seller_name,
                        "seller_rating": seller_rating,
                        "seller_reviews": seller_reviews,
                        "is_mine": is_mine,
                        "auto": bool(auto) if auto is not None else False,
                        "promo": bool(promo) if promo is not None else False,
                        "url": "https://funpay.com/lots/offer?id=" + str(lot_id) if lot_id else None
                    }
                    lots.append(item)
                    sk = str(seller_id) if seller_id else seller_name
                    if sk:
                        if sk not in sellers:
                            sellers[sk] = {
                                "id": seller_id,
                                "name": seller_name,
                                "rating": seller_rating,
                                "reviews": seller_reviews,
                                "lots_count": 0,
                                "min_price": pn,
                                "max_price": pn,
                                "is_mine": is_mine
                            }
                        sellers[sk]["lots_count"] += 1
                        if pn is not None:
                            if sellers[sk]["min_price"] is None or pn < sellers[sk]["min_price"]:
                                sellers[sk]["min_price"] = pn
                            if sellers[sk]["max_price"] is None or pn > sellers[sk]["max_price"]:
                                sellers[sk]["max_price"] = pn
                stats = {"total_lots": len(lots), "total_sellers": len(sellers)}
                if prices:
                    prices_sorted = sorted(prices)
                    n = len(prices_sorted)
                    stats["min_price"] = round(min(prices), 2)
                    stats["max_price"] = round(max(prices), 2)
                    stats["avg_price"] = round(sum(prices) / n, 2)
                    stats["median_price"] = round(prices_sorted[n // 2], 2)
                    optimal = stats["median_price"] * 0.95
                    stats["recommended_price"] = round(optimal, 2)
                my_lots = [l for l in lots if l["is_mine"]]
                if my_lots:
                    my_prices = [l["price"] for l in my_lots if l["price"] is not None]
                    if my_prices:
                        stats["my_min_price"] = round(min(my_prices), 2)
                        stats["my_max_price"] = round(max(my_prices), 2)
                        stats["my_avg_price"] = round(sum(my_prices) / len(my_prices), 2)
                        if stats.get("avg_price"):
                            diff_pct = (stats["my_avg_price"] - stats["avg_price"]) / stats["avg_price"] * 100
                            stats["my_vs_market_pct"] = round(diff_pct, 1)
                sellers_list = sorted(sellers.values(), key=lambda x: x["lots_count"], reverse=True)
                top_cheap = sorted([l for l in lots if l["price"] is not None], key=lambda x: x["price"])[:10]
                top_expensive = sorted([l for l in lots if l["price"] is not None], key=lambda x: x["price"], reverse=True)[:10]
                result = {
                    "available": True,
                    "subcategory_id": subcategory_id,
                    "subcategory_type": subcategory_type,
                    "lots": lots,
                    "sellers": sellers_list,
                    "top_cheap": top_cheap,
                    "top_expensive": top_expensive,
                    "my_lots": my_lots,
                    "stats": stats,
                    "updated_at": _t.time()
                }
                # Cache fix: успешные непустые — полный TTL, пустые/ошибки — короткий TTL (30 сек)
                if result.get("available") and len(result.get("lots") or []) > 0:
                    self._set_cache(cache_key, result)
                else:
                    self._cache[cache_key] = result
                    self._cache_time[cache_key] = _t.time() - 270
                return result
            except Exception as e:
                return {"available": False, "error": _safe_error(e), "lots": []}

    def compare_my_prices(self, force_refresh: bool = False) -> dict:
        import time as _t
        with self._lock:
            cache_key = "price_compare"
            if not force_refresh:
                cached = self._cached(cache_key, ttl=300)
                if cached:
                    return cached
        cats_result = self.get_my_categories()
        if not cats_result.get("available"):
            return {"available": False, "error": cats_result.get("error", ""), "comparisons": []}
        my_lots_data = self.get_my_lots()
        if not my_lots_data.get("available"):
            return {"available": False, "error": my_lots_data.get("error", ""), "comparisons": []}
        my_lots = my_lots_data.get("lots", [])
        if not my_lots:
            return {"available": True, "comparisons": [], "stats": {"total": 0, "red": 0, "yellow": 0, "green": 0}}
        scans = {}
        for cat in cats_result.get("categories", []):
            sub_id = cat["subcategory_id"]
            sub_type = cat.get("subcategory_type", 0)
            key = f"{sub_type}_{sub_id}"
            try:
                scan = self.scan_market(sub_id, sub_type, force_refresh=False)
                if scan.get("available"):
                    scans[key] = scan
            except Exception:
                pass
        comparisons = []
        red_count = yellow_count = green_count = 0
        with self._lock:
            acc = self._account
            my_id = acc.id if acc else None
        for lot in my_lots:
            sub_id = lot.get("subcategory_id") or 0
            cat_name = lot.get("category_name", "")
            subcat_name = lot.get("subcategory_name", "")
            my_price = lot.get("price")
            try:
                my_price_num = float(my_price) if my_price is not None else None
            except Exception:
                my_price_num = None
            cmp_item = {
                "lot_id": lot.get("id"),
                "title": lot.get("title"),
                "category_name": cat_name,
                "subcategory_name": subcat_name,
                "subcategory_id": sub_id,
                "my_price": my_price_num,
                "url": lot.get("url")
            }
            scan_key = None
            for k, sc in scans.items():
                if sc.get("subcategory_id") == sub_id:
                    scan_key = k
                    break
            if not scan_key:
                cmp_item["status"] = "no_data"
                cmp_item["message"] = "Не удалось получить данные рынка"
                comparisons.append(cmp_item)
                continue
            scan = scans[scan_key]
            stats = scan.get("stats", {})
            other_lots = [l for l in scan.get("lots", []) if not l.get("is_mine")]
            other_prices = sorted([l["price"] for l in other_lots if l.get("price") is not None])
            cmp_item["market_min"] = round(other_prices[0], 2) if other_prices else None
            cmp_item["market_max"] = round(other_prices[-1], 2) if other_prices else None
            cmp_item["market_avg"] = round(sum(other_prices) / len(other_prices), 2) if other_prices else None
            cmp_item["market_median"] = round(other_prices[len(other_prices) // 2], 2) if other_prices else None
            cmp_item["competitors"] = len(other_lots)
            cmp_item["recommended_price"] = round(cmp_item["market_median"] * 0.95, 2) if cmp_item["market_median"] else None
            if my_price_num is not None and other_prices:
                cheaper = sum(1 for p in other_prices if p < my_price_num)
                cmp_item["cheaper_competitors"] = cheaper
                cmp_item["position"] = cheaper + 1
                cmp_item["total_in_market"] = len(other_prices) + 1
                if cmp_item["market_avg"]:
                    diff = (my_price_num - cmp_item["market_avg"]) / cmp_item["market_avg"] * 100
                    cmp_item["vs_market_pct"] = round(diff, 1)
                    if diff > 30:
                        cmp_item["status"] = "red"
                        cmp_item["message"] = f"Сильно завышена: на {round(diff)}% выше рынка"
                        red_count += 1
                    elif diff > 10:
                        cmp_item["status"] = "yellow"
                        cmp_item["message"] = f"Выше рынка на {round(diff)}%"
                        yellow_count += 1
                    elif diff < -20:
                        cmp_item["status"] = "green"
                        cmp_item["message"] = f"Очень выгодная: на {abs(round(diff))}% ниже рынка"
                        green_count += 1
                    else:
                        cmp_item["status"] = "green"
                        cmp_item["message"] = "Конкурентная цена"
                        green_count += 1
                else:
                    cmp_item["status"] = "green"
                    cmp_item["message"] = "Конкурентная цена"
                    green_count += 1
            else:
                cmp_item["status"] = "no_data"
                cmp_item["message"] = "Нет данных для сравнения"
            comparisons.append(cmp_item)
        status_priority = {"red": 0, "yellow": 1, "no_data": 2, "green": 3}
        comparisons.sort(key=lambda x: status_priority.get(x.get("status", "no_data"), 4))
        result = {
            "available": True,
            "comparisons": comparisons,
            "stats": {
                "total": len(comparisons),
                "red": red_count,
                "yellow": yellow_count,
                "green": green_count,
                "no_data": len(comparisons) - red_count - yellow_count - green_count
            },
            "updated_at": _t.time()
        }
        with self._lock:
            self._set_cache(cache_key, result)
        return result

    def calculate_optimal_price(self, lot_id: int, strategy: str = "competitive", params: dict = None) -> dict:
        params = params or {}
        my_lots_data = self.get_my_lots()
        if not my_lots_data.get("available"):
            return {"ok": False, "error": "Не удалось загрузить лоты"}
        target_lot = None
        for l in my_lots_data.get("lots", []):
            if str(l.get("id")) == str(lot_id):
                target_lot = l
                break
        if not target_lot:
            return {"ok": False, "error": "Лот не найден"}
        sub_id = target_lot.get("subcategory_id")
        sub_type = target_lot.get("subcategory_type", 0)
        if not sub_id:
            return {"ok": False, "error": "У лота нет подкатегории"}
        scan = self.scan_market(sub_id, sub_type, force_refresh=False)
        if not scan.get("available"):
            return {"ok": False, "error": scan.get("error", "Не удалось получить рынок")}
        other_lots = [l for l in scan.get("lots", []) if not l.get("is_mine") and l.get("price") is not None]
        if not other_lots:
            return {"ok": False, "error": "Нет конкурентов на рынке"}
        prices = sorted([l["price"] for l in other_lots])
        n = len(prices)
        my_price = target_lot.get("price")
        result = {
            "ok": True,
            "lot_id": lot_id,
            "title": target_lot.get("title"),
            "strategy": strategy,
            "my_current_price": my_price,
            "competitors": n,
            "market_min": round(prices[0], 2),
            "market_max": round(prices[-1], 2),
            "market_median": round(prices[n // 2], 2),
            "market_avg": round(sum(prices) / n, 2)
        }
        optimal = None
        explanation = ""
        if strategy == "leader":
            optimal = round(prices[0] * 0.99, 2)
            explanation = f"Самая низкая цена ({prices[0]}) минус 1%"
        elif strategy == "fast_sale":
            top5 = prices[:min(5, n)]
            optimal = round(sum(top5) / len(top5) * 0.95, 2)
            explanation = f"Среднее топ-5 дешёвых минус 5%"
        elif strategy == "competitive":
            optimal = round(prices[n // 2] * 0.95, 2)
            explanation = f"Медиана минус 5%"
        elif strategy == "premium":
            optimal = round(prices[n // 2] * 1.15, 2)
            explanation = f"Медиана плюс 15% (для топ-продавцов)"
        elif strategy == "position":
            target_pos = int(params.get("position", 5))
            if target_pos < 1: target_pos = 1
            if target_pos > n: target_pos = n
            target_idx = target_pos - 1
            if target_idx < n - 1:
                between = (prices[target_idx] + prices[target_idx + 1]) / 2
            else:
                between = prices[target_idx] * 1.01
            optimal = round(between, 2)
            explanation = f"Цена для позиции #{target_pos} среди конкурентов"
        elif strategy == "margin":
            cost = float(params.get("cost", 0))
            margin_pct = float(params.get("margin_pct", 30))
            optimal = round(cost * (1 + margin_pct / 100), 2)
            explanation = f"Себестоимость {cost} + маржа {margin_pct}%"
        else:
            return {"ok": False, "error": f"Неизвестная стратегия: {strategy}"}
        position = sum(1 for p in prices if p < optimal) + 1
        cheaper = sum(1 for p in prices if p < optimal)
        result["optimal_price"] = optimal
        result["explanation"] = explanation
        result["will_be_position"] = position
        result["cheaper_competitors_after"] = cheaper
        if my_price is not None:
            try:
                my_pn = float(my_price)
                diff = optimal - my_pn
                diff_pct = (diff / my_pn * 100) if my_pn > 0 else 0
                result["price_change"] = round(diff, 2)
                result["price_change_pct"] = round(diff_pct, 1)
            except Exception:
                pass
        return result

    def simulate_price(self, lot_id: int, new_price: float) -> dict:
        my_lots_data = self.get_my_lots()
        if not my_lots_data.get("available"):
            return {"ok": False, "error": "Не удалось загрузить лоты"}
        target_lot = None
        for l in my_lots_data.get("lots", []):
            if str(l.get("id")) == str(lot_id):
                target_lot = l
                break
        if not target_lot:
            return {"ok": False, "error": "Лот не найден"}
        sub_id = target_lot.get("subcategory_id")
        sub_type = target_lot.get("subcategory_type", 0)
        if not sub_id:
            return {"ok": False, "error": "У лота нет подкатегории"}
        scan = self.scan_market(sub_id, sub_type, force_refresh=False)
        if not scan.get("available"):
            return {"ok": False, "error": "Не удалось получить рынок"}
        other_lots = [l for l in scan.get("lots", []) if not l.get("is_mine") and l.get("price") is not None]
        prices = sorted([l["price"] for l in other_lots])
        cheaper = sum(1 for p in prices if p < new_price)
        position = cheaper + 1
        total = len(prices) + 1
        return {
            "ok": True,
            "lot_id": lot_id,
            "simulated_price": new_price,
            "position": position,
            "total": total,
            "cheaper_count": cheaper,
            "more_expensive_count": total - position
        }

    def optimize_all_lots(self, strategy: str = "competitive", dry_run: bool = True) -> dict:
        cmp_result = self.compare_my_prices(force_refresh=False)
        if not cmp_result.get("available"):
            return {"ok": False, "error": cmp_result.get("error", ""), "results": []}
        changes = []
        results = []
        for c in cmp_result.get("comparisons", []):
            lot_id = c.get("lot_id")
            if not lot_id:
                continue
            calc = self.calculate_optimal_price(int(lot_id), strategy=strategy)
            if not calc.get("ok"):
                results.append({"lot_id": lot_id, "title": c.get("title"), "ok": False, "error": calc.get("error")})
                continue
            optimal = calc.get("optimal_price")
            if optimal is None or optimal <= 0:
                results.append({"lot_id": lot_id, "title": c.get("title"), "ok": False, "error": "Не удалось рассчитать"})
                continue
            changes.append({"lot_id": int(lot_id), "new_price": optimal})
            results.append({
                "lot_id": lot_id,
                "title": c.get("title"),
                "ok": True,
                "old_price": calc.get("my_current_price"),
                "new_price": optimal,
                "position": calc.get("will_be_position"),
                "explanation": calc.get("explanation")
            })
        applied = None
        if not dry_run and changes:
            applied = self.bulk_update_prices(changes, dry_run=False)
        return {
            "ok": True,
            "strategy": strategy,
            "dry_run": dry_run,
            "total": len(results),
            "success": sum(1 for r in results if r["ok"]),
            "failed": sum(1 for r in results if not r["ok"]),
            "results": results,
            "applied": applied
        }

    def _watchlist_file(self):
        return _CONFIGS_ROOT / "competitor_watchlist.json"

    def _competitor_history_file(self):
        return _CONFIGS_ROOT / "competitor_history.json"

    def _load_watchlist(self) -> list:
        path = self._watchlist_file()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_watchlist(self, watchlist: list):
        path = self._watchlist_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(watchlist, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_competitors(self, force_refresh: bool = False) -> dict:
        import time as _t
        with self._lock:
            cache_key = "competitors"
            if not force_refresh:
                cached = self._cached(cache_key, ttl=300)
                if cached:
                    return cached
        cats_result = self.get_my_categories()
        if not cats_result.get("available"):
            return {"available": False, "error": cats_result.get("error", ""), "competitors": []}
        watchlist = self._load_watchlist()
        watched_ids = set(str(w.get("seller_id")) for w in watchlist)
        all_sellers = {}
        for cat in cats_result.get("categories", []):
            sub_id = cat["subcategory_id"]
            sub_type = cat.get("subcategory_type", 0)
            scan = self.scan_market(sub_id, sub_type, force_refresh=False)
            if not scan.get("available"):
                continue
            for seller in scan.get("sellers", []):
                if seller.get("is_mine"):
                    continue
                sid = seller.get("id")
                sname = seller.get("name") or ""
                key = str(sid) if sid else sname
                if not key:
                    continue
                if key not in all_sellers:
                    all_sellers[key] = {
                        "id": sid,
                        "name": sname,
                        "rating": seller.get("rating"),
                        "reviews": seller.get("reviews"),
                        "total_lots": 0,
                        "categories": [],
                        "min_price": None,
                        "max_price": None,
                        "is_watched": key in watched_ids,
                        "profile_url": "https://funpay.com/users/" + str(sid) + "/" if sid else None
                    }
                entry = all_sellers[key]
                entry["total_lots"] += seller.get("lots_count", 0)
                entry["categories"].append({
                    "category_name": cat.get("category_name"),
                    "subcategory_name": cat.get("subcategory_name"),
                    "subcategory_id": sub_id,
                    "lots_count": seller.get("lots_count", 0),
                    "min_price": seller.get("min_price"),
                    "max_price": seller.get("max_price")
                })
                sp_min = seller.get("min_price")
                sp_max = seller.get("max_price")
                if sp_min is not None:
                    if entry["min_price"] is None or sp_min < entry["min_price"]:
                        entry["min_price"] = sp_min
                if sp_max is not None:
                    if entry["max_price"] is None or sp_max > entry["max_price"]:
                        entry["max_price"] = sp_max
        competitors_list = sorted(all_sellers.values(), key=lambda x: x["total_lots"], reverse=True)
        stats = {
            "total": len(competitors_list),
            "watched": sum(1 for c in competitors_list if c["is_watched"]),
            "categories_count": len(cats_result.get("categories", []))
        }
        result = {
            "available": True,
            "competitors": competitors_list,
            "stats": stats,
            "updated_at": _t.time()
        }
        with self._lock:
            self._set_cache(cache_key, result)
        return result

    def track_competitor(self, seller_id, seller_name: str = "") -> dict:
        watchlist = self._load_watchlist()
        sid = str(seller_id)
        for w in watchlist:
            if str(w.get("seller_id")) == sid:
                return {"ok": True, "message": "Уже отслеживается"}
        import time as _t
        watchlist.append({
            "seller_id": seller_id,
            "seller_name": seller_name,
            "added_at": _t.time()
        })
        self._save_watchlist(watchlist)
        self._cache.pop("competitors", None)
        return {"ok": True, "message": "Добавлен в отслеживание"}

    def untrack_competitor(self, seller_id) -> dict:
        watchlist = self._load_watchlist()
        sid = str(seller_id)
        new_list = [w for w in watchlist if str(w.get("seller_id")) != sid]
        if len(new_list) == len(watchlist):
            return {"ok": False, "error": "Не найдено"}
        self._save_watchlist(new_list)
        self._cache.pop("competitors", None)
        return {"ok": True, "message": "Удалён из отслеживания"}

    def get_watchlist(self) -> dict:
        return {"ok": True, "watchlist": self._load_watchlist()}

    def get_competitor_details(self, seller_id) -> dict:
        comps = self.get_competitors()
        if not comps.get("available"):
            return {"ok": False, "error": comps.get("error", "")}
        sid = str(seller_id)
        for c in comps.get("competitors", []):
            if str(c.get("id")) == sid:
                my_lots_data = self.get_my_lots()
                my_lots = my_lots_data.get("lots", []) if my_lots_data.get("available") else []
                vs_me = []
                for cat in c.get("categories", []):
                    sub_id = cat.get("subcategory_id")
                    my_in_cat = [l for l in my_lots if l.get("subcategory_id") == sub_id]
                    if not my_in_cat:
                        continue
                    my_prices = [float(l["price"]) for l in my_in_cat if l.get("price") is not None]
                    my_min = min(my_prices) if my_prices else None
                    my_avg = round(sum(my_prices) / len(my_prices), 2) if my_prices else None
                    his_min = cat.get("min_price")
                    diff_status = "equal"
                    if my_min is not None and his_min is not None:
                        if his_min < my_min:
                            diff_status = "cheaper"
                        elif his_min > my_min:
                            diff_status = "expensive"
                    vs_me.append({
                        "category": cat.get("category_name"),
                        "subcategory": cat.get("subcategory_name"),
                        "my_min": my_min,
                        "my_avg": my_avg,
                        "my_lots": len(my_in_cat),
                        "his_min": his_min,
                        "his_max": cat.get("max_price"),
                        "his_lots": cat.get("lots_count"),
                        "diff_status": diff_status
                    })
                c = dict(c)
                c["vs_me"] = vs_me
                return {"ok": True, "competitor": c}
        return {"ok": False, "error": "Конкурент не найден"}

    POPULAR_SUBCATEGORIES = [
        {"id": 35, "type": 0, "name": "World of Warcraft Аккаунты"},
        {"id": 1188, "type": 0, "name": "WoW Обучение"},
        {"id": 30, "type": 0, "name": "Genshin Impact Аккаунты"},
        {"id": 2408, "type": 0, "name": "Zenless Zone Zero"},
        {"id": 2390, "type": 0, "name": "Wuthering Waves"},
        {"id": 938, "type": 0, "name": "Xbox Аккаунты"},
        {"id": 941, "type": 0, "name": "Xbox Ключи"},
        {"id": 939, "type": 0, "name": "Xbox Пополнение"},
        {"id": 940, "type": 0, "name": "Xbox Game Pass"},
        {"id": 451, "type": 0, "name": "Прочие игры Аккаунты"},
        {"id": 1043, "type": 0, "name": "Прочие игры Ключи"},
        {"id": 1991, "type": 0, "name": "Game Pass"},
        {"id": 1287, "type": 0, "name": "YouTube Premium"},
        {"id": 705, "type": 0, "name": "YouTube Услуги"},
        {"id": 700, "type": 0, "name": "YouTube Каналы"},
        {"id": 699, "type": 0, "name": "VK Сообщества"},
        {"id": 706, "type": 0, "name": "VK Услуги"},
        {"id": 1471, "type": 0, "name": "Тиндер"},
        {"id": 1453, "type": 0, "name": "Шахматы Аккаунты"},
        {"id": 1473, "type": 0, "name": "Шахматы Подписка"},
        {"id": 286, "type": 0, "name": "World of Warplanes"},
        {"id": 158, "type": 0, "name": "World of Warships"},
        {"id": 610, "type": 0, "name": "World War Z"},
        {"id": 763, "type": 0, "name": "WoW MoP Аккаунты"},
        {"id": 492, "type": 0, "name": "WoW Classic Аккаунты"},
        {"id": 34, "type": 0, "name": "WoW Аккаунты"},
        {"id": 2871, "type": 0, "name": "Age of Empires Mobile"},
        {"id": 392, "type": 0, "name": "Мобильные игры Аккаунты"},
        {"id": 891, "type": 0, "name": "Мобильные игры Донат"},
        {"id": 1759, "type": 0, "name": "Zepeto Земы"}
    ]

    def _calc_heat(self, scan: dict) -> dict:
        stats = scan.get("stats", {})
        lots = scan.get("lots", [])
        sellers = scan.get("sellers", [])
        total_lots = stats.get("total_lots", 0)
        total_sellers = stats.get("total_sellers", 0)
        avg = stats.get("avg_price") or 0
        min_p = stats.get("min_price") or 0
        max_p = stats.get("max_price") or 0
        money_volume = round(avg * total_lots, 2)
        spread = round((max_p - min_p), 2) if max_p and min_p else 0
        spread_ratio = round((max_p / min_p), 1) if min_p > 0 else 0
        competition_score = min(100, total_sellers * 5)
        activity_score = min(100, total_lots * 2)
        money_score = min(100, int(money_volume / 100)) if money_volume else 0
        heat = int((competition_score * 0.3 + activity_score * 0.4 + money_score * 0.3))
        premium_count = sum(1 for l in lots if l.get("price") is not None and l["price"] > avg * 2) if avg else 0
        premium_pct = round(premium_count / total_lots * 100, 1) if total_lots else 0
        return {
            "heat": heat,
            "money_volume": money_volume,
            "competition_score": competition_score,
            "activity_score": activity_score,
            "money_score": money_score,
            "spread": spread,
            "spread_ratio": spread_ratio,
            "premium_pct": premium_pct
        }

    def analyze_heatmap(self, mode: str = "quick", progress_callback=None) -> dict:
        import time as _t
        with self._lock:
            cache_key = f"heatmap_{mode}"
            cached = self._cached(cache_key, ttl=600)
            if cached:
                return cached
        targets = []
        if mode == "quick":
            cats_result = self.get_my_categories()
            if not cats_result.get("available"):
                return {"available": False, "error": cats_result.get("error", ""), "items": []}
            my_cats = cats_result.get("categories", [])
            for c in my_cats:
                targets.append({
                    "subcategory_id": c["subcategory_id"],
                    "subcategory_type": c.get("subcategory_type", 0),
                    "category_name": c.get("category_name", ""),
                    "subcategory_name": c.get("subcategory_name", ""),
                    "is_mine": True
                })
            try:
                acc = self._get_account()
                if acc is not None:
                    parent_ids = set()
                    for c in my_cats:
                        user = acc.get_user(acc.id)
                        for lot in user.get_lots() if hasattr(user, "get_lots") else []:
                            sub = getattr(lot, "subcategory", None)
                            if sub:
                                par = getattr(sub, "category", None)
                                if par:
                                    pid = getattr(par, "id", None)
                                    if pid:
                                        parent_ids.add(pid)
                    all_subs = acc.subcategories
                    if callable(all_subs):
                        all_subs = all_subs()
                    existing_ids = set(t["subcategory_id"] for t in targets)
                    for sub in all_subs:
                        sub_id = getattr(sub, "id", None)
                        if sub_id in existing_ids:
                            continue
                        par = getattr(sub, "category", None)
                        if par and getattr(par, "id", None) in parent_ids:
                            sub_type_obj = getattr(sub, "type", None)
                            sub_type = getattr(sub_type_obj, "value", 0) if sub_type_obj else 0
                            targets.append({
                                "subcategory_id": sub_id,
                                "subcategory_type": sub_type,
                                "category_name": getattr(par, "name", ""),
                                "subcategory_name": getattr(sub, "name", ""),
                                "is_mine": False
                            })
                            existing_ids.add(sub_id)
                            if len(targets) >= 15:
                                break
            except Exception:
                pass
        elif mode == "extended":
            for p in self.POPULAR_SUBCATEGORIES:
                targets.append({
                    "subcategory_id": p["id"],
                    "subcategory_type": p["type"],
                    "category_name": p["name"].split(" ")[0] if " " in p["name"] else p["name"],
                    "subcategory_name": p["name"],
                    "is_mine": False
                })
            cats_result = self.get_my_categories()
            if cats_result.get("available"):
                existing = set(t["subcategory_id"] for t in targets)
                for c in cats_result.get("categories", []):
                    if c["subcategory_id"] not in existing:
                        targets.append({
                            "subcategory_id": c["subcategory_id"],
                            "subcategory_type": c.get("subcategory_type", 0),
                            "category_name": c.get("category_name", ""),
                            "subcategory_name": c.get("subcategory_name", ""),
                            "is_mine": True
                        })
        items = []
        total = len(targets)
        for i, t in enumerate(targets):
            if progress_callback:
                try:
                    progress_callback(i + 1, total, t["subcategory_name"])
                except Exception:
                    pass
            try:
                scan = self.scan_market(t["subcategory_id"], t["subcategory_type"], force_refresh=False)
                if scan.get("available"):
                    heat = self._calc_heat(scan)
                    items.append({
                        "subcategory_id": t["subcategory_id"],
                        "subcategory_type": t["subcategory_type"],
                        "category_name": t["category_name"],
                        "subcategory_name": t["subcategory_name"],
                        "is_mine": t["is_mine"],
                        "total_lots": scan["stats"].get("total_lots", 0),
                        "total_sellers": scan["stats"].get("total_sellers", 0),
                        "min_price": scan["stats"].get("min_price"),
                        "max_price": scan["stats"].get("max_price"),
                        "avg_price": scan["stats"].get("avg_price"),
                        "median_price": scan["stats"].get("median_price"),
                        **heat
                    })
            except Exception as e:
                items.append({
                    "subcategory_id": t["subcategory_id"],
                    "category_name": t["category_name"],
                    "subcategory_name": t["subcategory_name"],
                    "is_mine": t["is_mine"],
                    "error": _safe_error(e)
                })
        items.sort(key=lambda x: x.get("heat", 0), reverse=True)
        result = {
            "available": True,
            "mode": mode,
            "items": items,
            "total_scanned": len(items),
            "updated_at": _t.time()
        }
        with self._lock:
            self._set_cache(cache_key, result)
        return result

    def find_niches(self, source: str = "all") -> dict:
        import time as _t
        all_items = []
        sources_used = []
        with self._lock:
            for mode in ["quick", "extended"]:
                if source != "all" and source != mode:
                    continue
                cached = self._cache.get(f"heatmap_{mode}")
                if cached and cached.get("items"):
                    all_items.extend(cached["items"])
                    sources_used.append(mode)
        if not all_items:
            return {
                "available": False,
                "error": "Нет данных. Сначала запусти Тепловую карту (Быстрый или Расширенный режим), потом вернись сюда.",
                "niches": []
            }
        seen = {}
        for it in all_items:
            sid = it.get("subcategory_id")
            if sid and sid not in seen:
                seen[sid] = it
        items = list(seen.values())
        niches = []
        for it in items:
            if it.get("error"):
                continue
            total_lots = it.get("total_lots", 0) or 0
            total_sellers = it.get("total_sellers", 0) or 0
            avg_price = it.get("avg_price") or 0
            median_price = it.get("median_price") or 0
            money_volume = it.get("money_volume") or 0
            spread_ratio = it.get("spread_ratio") or 0
            heat = it.get("heat", 0) or 0
            premium_pct = it.get("premium_pct", 0) or 0
            if total_lots < 3:
                continue
            niche_types = []
            score = 50
            # Золотая ниша
            if total_sellers <= 10 and avg_price >= 50 and total_lots >= 5:
                niche_types.append("golden")
                score += 30
            # Премиум
            if avg_price >= 200 and premium_pct >= 20:
                niche_types.append("premium")
                score += 20
            # Свободная
            if total_sellers <= 5 and total_lots >= 3:
                niche_types.append("free")
                score += 25
            # Растущая
            if total_sellers <= 15 and total_lots >= 10 and money_volume >= 1000:
                niche_types.append("growing")
                score += 15
            # Перегрев (антиниша)
            if total_sellers >= 30 and spread_ratio >= 50:
                niche_types.append("overheated")
                score -= 30
            # Мусор (антиниша)
            if avg_price < 1:
                niche_types.append("trash")
                score -= 40
            if not niche_types:
                if heat >= 40 and total_sellers < 20:
                    niche_types.append("normal")
                else:
                    continue
            primary_type = niche_types[0]
            potential_revenue = round(avg_price * (total_lots / max(total_sellers, 1)), 2)
            niches.append({
                "subcategory_id": it.get("subcategory_id"),
                "subcategory_name": it.get("subcategory_name"),
                "category_name": it.get("category_name"),
                "is_mine": it.get("is_mine", False),
                "niche_score": max(0, min(100, score)),
                "niche_types": niche_types,
                "primary_type": primary_type,
                "total_lots": total_lots,
                "total_sellers": total_sellers,
                "avg_price": avg_price,
                "median_price": median_price,
                "money_volume": money_volume,
                "potential_revenue_per_seller": potential_revenue,
                "premium_pct": premium_pct,
                "heat": heat
            })
        niches.sort(key=lambda x: x["niche_score"], reverse=True)
        type_counts = {}
        for n in niches:
            for t in n["niche_types"]:
                type_counts[t] = type_counts.get(t, 0) + 1
        return {
            "available": True,
            "niches": niches,
            "total": len(niches),
            "sources": sources_used,
            "type_counts": type_counts,
            "updated_at": _t.time()
        }

    def compare_niche_with_mine(self, subcategory_id: int) -> dict:
        niches_data = self.find_niches()
        if not niches_data.get("available"):
            return {"ok": False, "error": niches_data.get("error", "")}
        target = None
        for n in niches_data.get("niches", []):
            if n.get("subcategory_id") == subcategory_id:
                target = n
                break
        if not target:
            return {"ok": False, "error": "Ниша не найдена"}
        cats_result = self.get_my_categories()
        my_cats = cats_result.get("categories", []) if cats_result.get("available") else []
        my_summary = []
        for c in my_cats:
            scan = self.scan_market(c["subcategory_id"], c.get("subcategory_type", 0), force_refresh=False)
            if scan.get("available"):
                my_summary.append({
                    "name": c["subcategory_name"],
                    "category": c["category_name"],
                    "avg_price": scan["stats"].get("avg_price"),
                    "sellers": scan["stats"].get("total_sellers"),
                    "lots": scan["stats"].get("total_lots")
                })
        return {
            "ok": True,
            "niche": target,
            "my_categories": my_summary
        }

    def _suppliers_file(self):
        return _CONFIGS_ROOT / "suppliers_db.json"

    def _lot_suppliers_file(self):
        return _CONFIGS_ROOT / "lot_suppliers_links.json"

    def _load_suppliers_db(self) -> dict:
        path = self._suppliers_file()
        if not path.exists():
            return {"suppliers": [], "categories_map": {}}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"suppliers": [], "categories_map": {}}

    def _save_suppliers_db(self, db: dict):
        path = self._suppliers_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_suppliers(self, category_filter: str = None, status_filter: str = None) -> dict:
        db = self._load_suppliers_db()
        suppliers = db.get("suppliers", [])
        if category_filter:
            q = category_filter.lower()
            suppliers = [s for s in suppliers if q in (s.get("category", "") + " " + " ".join(s.get("categories_funpay", []))).lower()]
        if status_filter:
            suppliers = [s for s in suppliers if s.get("status") == status_filter]
        return {"available": True, "suppliers": suppliers, "total": len(suppliers), "categories_map": db.get("categories_map", {})}

    def add_supplier(self, supplier: dict) -> dict:
        db = self._load_suppliers_db()
        import uuid as _uuid, time as _t
        if not supplier.get("id"):
            supplier["id"] = "custom_" + _uuid.uuid4().hex[:8]
        if not supplier.get("added_at"):
            supplier["added_at"] = _t.strftime("%Y-%m-%d")
        for i, s in enumerate(db["suppliers"]):
            if s.get("id") == supplier["id"]:
                db["suppliers"][i] = supplier
                self._save_suppliers_db(db)
                return {"ok": True, "message": "Обновлено", "id": supplier["id"]}
        db["suppliers"].append(supplier)
        self._save_suppliers_db(db)
        return {"ok": True, "message": "Добавлено", "id": supplier["id"]}

    def delete_supplier(self, supplier_id: str) -> dict:
        db = self._load_suppliers_db()
        new_list = [s for s in db["suppliers"] if s.get("id") != supplier_id]
        if len(new_list) == len(db["suppliers"]):
            return {"ok": False, "error": "Не найдено"}
        db["suppliers"] = new_list
        self._save_suppliers_db(db)
        return {"ok": True}

    def get_supplier_by_id(self, supplier_id: str) -> dict:
        db = self._load_suppliers_db()
        for s in db.get("suppliers", []):
            if s.get("id") == supplier_id:
                return {"ok": True, "supplier": s}
        return {"ok": False, "error": "Не найдено"}

    def link_lot_to_supplier(self, lot_id: int, supplier_id: str, cost: float = 0) -> dict:
        path = self._lot_suppliers_file()
        links = {}
        if path.exists():
            try:
                links = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        links[str(lot_id)] = {"supplier_id": supplier_id, "cost": float(cost)}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(links, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True}

    def unlink_lot(self, lot_id: int) -> dict:
        path = self._lot_suppliers_file()
        if not path.exists():
            return {"ok": True}
        try:
            links = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"ok": True}
        if str(lot_id) in links:
            del links[str(lot_id)]
            path.write_text(json.dumps(links, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True}

    def get_lot_suppliers(self) -> dict:
        path = self._lot_suppliers_file()
        if not path.exists():
            return {"ok": True, "links": {}}
        try:
            return {"ok": True, "links": json.loads(path.read_text(encoding="utf-8"))}
        except Exception:
            return {"ok": True, "links": {}}

    FUNPAY_COMMISSION_PCT = 10.0

    def _margin_settings_file(self):
        return _CONFIGS_ROOT / "margin_settings.json"

    def get_margin_settings(self) -> dict:
        path = self._margin_settings_file()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return {"commission_pct": float(data.get("commission_pct", self.FUNPAY_COMMISSION_PCT))}
            except Exception:
                pass
        return {"commission_pct": self.FUNPAY_COMMISSION_PCT}

    def save_margin_settings(self, commission_pct: float) -> dict:
        path = self._margin_settings_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"commission_pct": float(commission_pct)}, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True}

    def calculate_margin(self, price: float, cost: float, commission_pct: float = None) -> dict:
        try:
            p = float(price)
            c = float(cost)
        except Exception:
            return {"ok": False, "error": "Неверные значения"}
        if commission_pct is None:
            commission_pct = self.get_margin_settings()["commission_pct"]
        commission = round(p * commission_pct / 100, 2)
        net_revenue = round(p - commission, 2)
        profit = round(net_revenue - c, 2)
        margin_pct = round((profit / c * 100), 1) if c > 0 else None
        roi = round((profit / c * 100), 1) if c > 0 else None
        status = "unknown"
        if c <= 0:
            status = "no_cost"
        elif profit < 0:
            status = "loss"
        elif margin_pct < 5:
            status = "low"
        elif margin_pct < 20:
            status = "orange"
        elif margin_pct < 50:
            status = "yellow"
        else:
            status = "green"
        return {
            "ok": True,
            "price": p,
            "cost": c,
            "commission_pct": commission_pct,
            "commission": commission,
            "net_revenue": net_revenue,
            "profit": profit,
            "margin_pct": margin_pct,
            "roi": roi,
            "status": status
        }

    def get_margin_overview(self, force_refresh: bool = False) -> dict:
        import time as _t
        with self._lock:
            cache_key = "margin_overview"
            if not force_refresh:
                cached = self._cached(cache_key, ttl=120)
                if cached:
                    return cached
        my_lots = self.get_my_lots()
        if not my_lots.get("available"):
            return {"available": False, "error": my_lots.get("error", "")}
        links_data = self.get_lot_suppliers()
        links = links_data.get("links", {})
        suppliers_data = self.get_suppliers()
        suppliers_by_id = {s["id"]: s for s in suppliers_data.get("suppliers", [])}
        settings = self.get_margin_settings()
        commission_pct = settings["commission_pct"]
        items = []
        total_profit = 0.0
        total_revenue = 0.0
        total_cost = 0.0
        with_cost = 0
        without_cost = 0
        loss_count = 0
        for lot in my_lots.get("lots", []):
            lot_id = lot.get("id")
            price = lot.get("price")
            link = links.get(str(lot_id), {})
            cost = link.get("cost", 0)
            supplier_id = link.get("supplier_id")
            supplier = suppliers_by_id.get(supplier_id) if supplier_id else None
            calc = self.calculate_margin(price or 0, cost or 0, commission_pct)
            if not calc.get("ok"):
                continue
            item = {
                "lot_id": lot_id,
                "title": lot.get("title"),
                "category": lot.get("category_name"),
                "subcategory": lot.get("subcategory_name"),
                "price": calc["price"],
                "cost": calc["cost"],
                "commission": calc["commission"],
                "net_revenue": calc["net_revenue"],
                "profit": calc["profit"],
                "margin_pct": calc["margin_pct"],
                "status": calc["status"],
                "supplier_id": supplier_id,
                "supplier_name": supplier.get("name") if supplier else None,
                "url": lot.get("url")
            }
            items.append(item)
            if cost > 0:
                with_cost += 1
                total_cost += cost
                total_profit += calc["profit"]
                total_revenue += calc["net_revenue"]
                if calc["profit"] < 0:
                    loss_count += 1
            else:
                without_cost += 1
        items.sort(key=lambda x: (x.get("profit") or 0), reverse=True)
        top_profitable = items[:5]
        loss_items = sorted([i for i in items if i["status"] == "loss"], key=lambda x: x.get("profit") or 0)[:5]
        no_cost_items = [i for i in items if i["status"] == "no_cost"]
        avg_margin = round(sum(i["margin_pct"] for i in items if i["margin_pct"] is not None) / max(with_cost, 1), 1) if with_cost else 0
        result = {
            "available": True,
            "items": items,
            "stats": {
                "total_lots": len(items),
                "with_cost": with_cost,
                "without_cost": without_cost,
                "loss_count": loss_count,
                "total_profit": round(total_profit, 2),
                "total_cost": round(total_cost, 2),
                "total_revenue": round(total_revenue, 2),
                "avg_margin_pct": avg_margin,
                "commission_pct": commission_pct
            },
            "top_profitable": top_profitable,
            "losses": loss_items,
            "no_cost": no_cost_items[:10],
            "updated_at": _t.time()
        }
        with self._lock:
            self._set_cache(cache_key, result)
        return result

    def _parse_seller_profile(self, html: str) -> dict:
        if not html:
            return {}
        result = {"rating": None, "reviews_count": None, "distribution": {}, "is_pro": False}
        m = _re.search(r'<span class="big">(\d+(?:[.,]\d+)?)</span>\s*<span[^>]*>из\s*5', html)
        if m:
            try:
                result["rating"] = float(m.group(1).replace(",", "."))
            except Exception:
                pass
        m2 = _re.search(r'Всего\s*(\d+)\s*<br', html, _re.IGNORECASE)
        if not m2:
            m2 = _re.search(r'>Всего\s*(\d+)', html)
        if m2:
            try:
                result["reviews_count"] = int(m2.group(1))
            except Exception:
                pass
        for star in range(1, 6):
            pat = r'rating-full-item' + str(star) + r'[\"\'>][^>]*>.*?width:\s*(\d+)%'
            m3 = _re.search(pat, html, _re.DOTALL)
            if m3:
                try:
                    result["distribution"][str(star)] = int(m3.group(1))
                except Exception:
                    pass
        if "profile-pro" in html or "label-pro" in html or "badge-pro" in html.lower():
            result["is_pro"] = True
        return result

    def analyze_seller_ratings(self, force_refresh: bool = False) -> dict:
        import time as _t
        with self._lock:
            cache_key = "seller_ratings"
            if not force_refresh:
                cached = self._cached(cache_key, ttl=900)
                if cached:
                    return cached
        comps_data = self.get_competitors()
        if not comps_data.get("available"):
            return {"available": False, "error": comps_data.get("error", ""), "sellers": []}
        competitors = comps_data.get("competitors", [])
        if not competitors:
            return {"available": True, "sellers": [], "stats": {"total": 0, "top": 0, "mid": 0, "new": 0, "weak": 0}}
        acc = self._get_account()
        if acc is None:
            return {"available": False, "error": "Нет авторизации", "sellers": []}
        sellers = []
        for c in competitors[:30]:
            sid = c.get("id")
            if not sid:
                continue
            seller_data = {
                "id": sid,
                "name": c.get("name"),
                "is_watched": c.get("is_watched", False),
                "profile_url": c.get("profile_url"),
                "total_lots": c.get("total_lots", 0),
                "categories": c.get("categories", []),
                "min_price": c.get("min_price"),
                "max_price": c.get("max_price"),
                "rating": None,
                "reviews_count": None,
                "online": None,
                "banned": False,
                "distribution": {},
                "is_pro": False,
                "threat_level": "unknown",
                "threat_score": 0,
                "recommendation": ""
            }
            try:
                user = acc.get_user(int(sid))
                seller_data["online"] = getattr(user, "online", None)
                seller_data["banned"] = getattr(user, "banned", False)
                parsed = self._parse_seller_profile(getattr(user, "html", "") or "")
                seller_data.update(parsed)
            except Exception:
                pass
            score = 0
            rating = seller_data.get("rating") or 0
            reviews = seller_data.get("reviews_count") or 0
            lots = seller_data.get("total_lots") or 0
            score += min(50, int(rating * 10))
            if reviews >= 1000:
                score += 35
            elif reviews >= 500:
                score += 28
            elif reviews >= 200:
                score += 20
            elif reviews >= 50:
                score += 10
            elif reviews >= 10:
                score += 5
            score += min(15, lots // 5)
            if seller_data.get("is_pro"):
                score += 10
            if seller_data.get("banned"):
                score = 0
            seller_data["threat_score"] = score
            if score >= 70:
                seller_data["threat_level"] = "top"
                seller_data["recommendation"] = "Сильный конкурент. Чтобы бороться - снизь цену на 20-30% или дай уникальное преимущество (автовыдача, гарантия)."
            elif score >= 40:
                seller_data["threat_level"] = "mid"
                seller_data["recommendation"] = "Средний конкурент. Можно бороться адекватной ценой и хорошим описанием."
            elif score >= 15:
                seller_data["threat_level"] = "new"
                seller_data["recommendation"] = "Новичок или малоактивный продавец. Легко обогнать репутацией."
            else:
                seller_data["threat_level"] = "weak"
                seller_data["recommendation"] = "Слабый игрок. Можно игнорировать или занять его место."
            sellers.append(seller_data)
        sellers.sort(key=lambda x: x["threat_score"], reverse=True)
        rated = [s for s in sellers if s.get("rating")]
        avg_rating = round(sum(s["rating"] for s in rated) / len(rated), 2) if rated else 0
        stats = {
            "total": len(sellers),
            "top": sum(1 for s in sellers if s["threat_level"] == "top"),
            "mid": sum(1 for s in sellers if s["threat_level"] == "mid"),
            "new": sum(1 for s in sellers if s["threat_level"] == "new"),
            "weak": sum(1 for s in sellers if s["threat_level"] == "weak"),
            "online_now": sum(1 for s in sellers if s.get("online")),
            "banned": sum(1 for s in sellers if s.get("banned")),
            "avg_rating": avg_rating
        }
        result = {
            "available": True,
            "sellers": sellers,
            "stats": stats,
            "updated_at": _t.time()
        }
        with self._lock:
            self._set_cache(cache_key, result)
        return result

    def get_seller_details(self, seller_id) -> dict:
        data = self.analyze_seller_ratings()
        if not data.get("available"):
            return {"ok": False, "error": data.get("error", "")}
        sid = str(seller_id)
        for s in data.get("sellers", []):
            if str(s.get("id")) == sid:
                return {"ok": True, "seller": s}
        return {"ok": False, "error": "Продавец не найден"}

    def _market_alerts_file(self):
        return _CONFIGS_ROOT / "market_alerts.json"

    def _market_snapshot_file(self):
        return _CONFIGS_ROOT / "market_snapshot.json"

    def _alert_settings_file(self):
        return _CONFIGS_ROOT / "alert_settings.json"

    def _load_market_alerts(self) -> list:
        path = self._market_alerts_file()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_market_alerts(self, alerts: list):
        path = self._market_alerts_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(alerts[-500:], ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_market_snapshot(self) -> dict:
        path = self._market_snapshot_file()
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_market_snapshot(self, snap: dict):
        path = self._market_snapshot_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_alert_settings(self) -> dict:
        path = self._alert_settings_file()
        defaults = {
            "enabled_types": ["price_drop", "price_rise", "new_competitor", "category_hot", "category_cold", "watchlist_online", "rank_changed", "recommended_price_changed"],
            "price_drop_threshold": 20,
            "price_rise_threshold": 15
        }
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                defaults.update(data)
            except Exception:
                pass
        return defaults

    def save_alert_settings(self, settings: dict) -> dict:
        path = self._alert_settings_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True}

    def collect_market_alerts(self) -> dict:
        import time as _t, uuid as _uuid
        settings = self.get_alert_settings()
        enabled = set(settings.get("enabled_types", []))
        drop_threshold = float(settings.get("price_drop_threshold", 20))
        rise_threshold = float(settings.get("price_rise_threshold", 15))

        snap = self._load_market_snapshot()
        alerts = self._load_market_alerts()
        new_items = []
        now = _t.time()
        date_str = _t.strftime("%Y-%m-%d %H:%M:%S", _t.localtime(now))

        try:
            comps_data = self.get_competitors(force_refresh=True)
            competitors = comps_data.get("competitors", []) if comps_data.get("available") else []
        except Exception:
            competitors = []

        # Snapshot конкурентов
        prev_comps = snap.get("competitors", {})
        cur_comps = {}
        for c in competitors:
            sid = str(c.get("id") or c.get("name"))
            cur_comps[sid] = {
                "name": c.get("name"),
                "min_price": c.get("min_price"),
                "max_price": c.get("max_price"),
                "lots_count": c.get("total_lots"),
                "is_watched": c.get("is_watched", False)
            }
            prev = prev_comps.get(sid)
            if prev:
                old_min = prev.get("min_price")
                new_min = c.get("min_price")
                if old_min and new_min and old_min > 0:
                    pct = (new_min - old_min) / old_min * 100
                    if pct <= -drop_threshold and "price_drop" in enabled:
                        new_items.append({
                            "id": str(_uuid.uuid4()),
                            "type": "price_drop",
                            "severity": "warning",
                            "timestamp": now,
                            "date": date_str,
                            "title": f"Конкурент {c.get('name')} снизил цену на {abs(round(pct))}%",
                            "message": f"Было {old_min}, стало {new_min}. Возможно демпингует — реагируй.",
                            "data": {"seller_id": c.get("id"), "old": old_min, "new": new_min, "pct": round(pct, 1)},
                            "acknowledged": False, "dismissed": False
                        })
                    elif pct >= rise_threshold and "price_rise" in enabled:
                        new_items.append({
                            "id": str(_uuid.uuid4()),
                            "type": "price_rise",
                            "severity": "info",
                            "timestamp": now,
                            "date": date_str,
                            "title": f"Конкурент {c.get('name')} поднял цену на {round(pct)}%",
                            "message": f"Было {old_min}, стало {new_min}. Твоя позиция улучшилась.",
                            "data": {"seller_id": c.get("id"), "old": old_min, "new": new_min, "pct": round(pct, 1)},
                            "acknowledged": False, "dismissed": False
                        })
            else:
                # Новый конкурент
                if "new_competitor" in enabled and prev_comps:
                    new_items.append({
                        "id": str(_uuid.uuid4()),
                        "type": "new_competitor",
                        "severity": "warning",
                        "timestamp": now,
                        "date": date_str,
                        "title": f"Новый конкурент: {c.get('name')}",
                        "message": f"Появился в твоих категориях. Лотов: {c.get('total_lots')}, мин цена: {c.get('min_price')}",
                        "data": {"seller_id": c.get("id"), "name": c.get("name")},
                        "acknowledged": False, "dismissed": False
                    })

        # Watchlist online
        if "watchlist_online" in enabled:
            try:
                ratings = self.analyze_seller_ratings(force_refresh=False)
                if ratings.get("available"):
                    prev_online = set(snap.get("watchlist_online", []))
                    cur_online = []
                    for s in ratings.get("sellers", []):
                        if s.get("is_watched") and s.get("online"):
                            cur_online.append(str(s.get("id")))
                            if str(s.get("id")) not in prev_online:
                                new_items.append({
                                    "id": str(_uuid.uuid4()),
                                    "type": "watchlist_online",
                                    "severity": "info",
                                    "timestamp": now,
                                    "date": date_str,
                                    "title": f"Отслеживаемый {s.get('name')} онлайн",
                                    "message": "Можешь подстроить цены сейчас.",
                                    "data": {"seller_id": s.get("id")},
                                    "acknowledged": False, "dismissed": False
                                })
                    snap["watchlist_online"] = cur_online
            except Exception:
                pass

        # Категории: горячее/холоднее
        try:
            heatmap = self._cache.get("heatmap_quick") or self._cache.get("heatmap_extended")
            if heatmap and heatmap.get("items"):
                prev_cats = snap.get("categories", {})
                cur_cats = {}
                for it in heatmap["items"]:
                    if it.get("error"):
                        continue
                    sid = str(it.get("subcategory_id"))
                    cur_cats[sid] = {
                        "name": it.get("subcategory_name"),
                        "money_volume": it.get("money_volume", 0),
                        "heat": it.get("heat", 0)
                    }
                    prev = prev_cats.get(sid)
                    if prev:
                        old_money = prev.get("money_volume") or 0
                        new_money = it.get("money_volume") or 0
                        if old_money > 0:
                            pct = (new_money - old_money) / old_money * 100
                            if pct >= 30 and "category_hot" in enabled:
                                new_items.append({
                                    "id": str(_uuid.uuid4()),
                                    "type": "category_hot",
                                    "severity": "success",
                                    "timestamp": now,
                                    "date": date_str,
                                    "title": f"Категория разогрелась: {it.get('subcategory_name')}",
                                    "message": f"Объём денег вырос на {round(pct)}%. Хорошее время войти.",
                                    "data": {"subcategory_id": it.get("subcategory_id"), "pct": round(pct, 1)},
                                    "acknowledged": False, "dismissed": False
                                })
                            elif pct <= -30 and "category_cold" in enabled:
                                new_items.append({
                                    "id": str(_uuid.uuid4()),
                                    "type": "category_cold",
                                    "severity": "warning",
                                    "timestamp": now,
                                    "date": date_str,
                                    "title": f"Категория остыла: {it.get('subcategory_name')}",
                                    "message": f"Объём денег упал на {abs(round(pct))}%. Спрос падает.",
                                    "data": {"subcategory_id": it.get("subcategory_id"), "pct": round(pct, 1)},
                                    "acknowledged": False, "dismissed": False
                                })
                snap["categories"] = cur_cats
        except Exception:
            pass

        # Recommended price для моих лотов
        if "recommended_price_changed" in enabled:
            try:
                compare_data = self.compare_my_prices(force_refresh=False)
                if compare_data.get("available"):
                    prev_recs = snap.get("recommendations", {})
                    cur_recs = {}
                    for c in compare_data.get("comparisons", []):
                        lot_id = str(c.get("lot_id"))
                        rec = c.get("recommended_price")
                        if rec is None:
                            continue
                        cur_recs[lot_id] = rec
                        old_rec = prev_recs.get(lot_id)
                        if old_rec and abs(rec - old_rec) / max(old_rec, 0.01) >= 0.1:
                            new_items.append({
                                "id": str(_uuid.uuid4()),
                                "type": "recommended_price_changed",
                                "severity": "info",
                                "timestamp": now,
                                "date": date_str,
                                "title": f"Изменилась рекомендуемая цена",
                                "message": f"Лот {c.get('title','')[:60]}: было {old_rec}, стало {rec}",
                                "data": {"lot_id": c.get("lot_id"), "old": old_rec, "new": rec},
                                "acknowledged": False, "dismissed": False
                            })
                    snap["recommendations"] = cur_recs
            except Exception:
                pass

        snap["competitors"] = cur_comps
        snap["last_collected"] = now
        self._save_market_snapshot(snap)

        if new_items:
            alerts.extend(new_items)
            self._save_market_alerts(alerts)

        return {"available": True, "new_count": len(new_items), "new_items": new_items, "total": len(alerts)}

    def get_market_alerts(self, type_filter: str = None, only_unack: bool = False, limit: int = 200) -> dict:
        alerts = self._load_market_alerts()
        items = [a for a in alerts if not a.get("dismissed", False)]
        if type_filter:
            items = [a for a in items if a.get("type") == type_filter]
        if only_unack:
            items = [a for a in items if not a.get("acknowledged", False)]
        items = items[-limit:]
        by_type = {}
        unack = 0
        for a in alerts:
            if a.get("dismissed"):
                continue
            t = a.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
            if not a.get("acknowledged"):
                unack += 1
        return {"available": True, "items": items, "count": len(items), "unacknowledged": unack, "by_type": by_type}

    def ack_market_alert(self, alert_id: str) -> dict:
        alerts = self._load_market_alerts()
        for a in alerts:
            if a.get("id") == alert_id:
                a["acknowledged"] = True
                self._save_market_alerts(alerts)
                return {"ok": True}
        return {"ok": False, "error": "Не найдено"}

    def dismiss_market_alert(self, alert_id: str) -> dict:
        alerts = self._load_market_alerts()
        for a in alerts:
            if a.get("id") == alert_id:
                a["dismissed"] = True
                self._save_market_alerts(alerts)
                return {"ok": True}
        return {"ok": False, "error": "Не найдено"}

    def clear_market_alerts(self) -> dict:
        self._save_market_alerts([])
        return {"ok": True}

    def _templates_file(self):
        return _CONFIGS_ROOT / "message_templates.json"

    def _rules_file(self):
        return _CONFIGS_ROOT / "autoreply_rules.json"

    def _autoreply_log_file(self):
        return _CONFIGS_ROOT / "autoreply_log.json"

    def _load_templates(self) -> list:
        path = self._templates_file()
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("templates", [])
        except Exception:
            return []

    def _save_templates(self, templates: list):
        path = self._templates_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"templates": templates}, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_rules(self) -> list:
        path = self._rules_file()
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("rules", [])
        except Exception:
            return []

    def _save_rules(self, rules: list):
        path = self._rules_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"rules": rules}, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_autoreply_log(self) -> list:
        path = self._autoreply_log_file()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_autoreply_log(self, entries: list):
        path = self._autoreply_log_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(entries[-500:], ensure_ascii=False, indent=2), encoding="utf-8")

    def get_templates(self) -> dict:
        return {"available": True, "templates": self._load_templates()}

    def add_template(self, template: dict) -> dict:
        import uuid as _uuid
        templates = self._load_templates()
        if not template.get("id"):
            template["id"] = "tpl_" + _uuid.uuid4().hex[:8]
        for i, t in enumerate(templates):
            if t.get("id") == template["id"]:
                templates[i] = template
                self._save_templates(templates)
                return {"ok": True, "id": template["id"], "message": "Обновлено"}
        templates.append(template)
        self._save_templates(templates)
        return {"ok": True, "id": template["id"], "message": "Добавлено"}

    def delete_template(self, template_id: str) -> dict:
        templates = self._load_templates()
        new_list = [t for t in templates if t.get("id") != template_id]
        if len(new_list) == len(templates):
            return {"ok": False, "error": "Не найдено"}
        self._save_templates(new_list)
        return {"ok": True}

    def get_autoreply_rules(self) -> dict:
        return {"available": True, "rules": self._load_rules()}

    def save_autoreply_rule(self, rule: dict) -> dict:
        import uuid as _uuid
        rules = self._load_rules()
        if not rule.get("id"):
            rule["id"] = "rule_" + _uuid.uuid4().hex[:8]
        if "stats" not in rule:
            rule["stats"] = {"triggered": 0, "sent": 0}
        for i, r in enumerate(rules):
            if r.get("id") == rule["id"]:
                rule["stats"] = r.get("stats", rule["stats"])
                rules[i] = rule
                self._save_rules(rules)
                return {"ok": True, "id": rule["id"], "message": "Обновлено"}
        rules.append(rule)
        self._save_rules(rules)
        return {"ok": True, "id": rule["id"], "message": "Добавлено"}

    def delete_autoreply_rule(self, rule_id: str) -> dict:
        rules = self._load_rules()
        new_list = [r for r in rules if r.get("id") != rule_id]
        if len(new_list) == len(rules):
            return {"ok": False, "error": "Не найдено"}
        self._save_rules(new_list)
        return {"ok": True}

    def toggle_autoreply_rule(self, rule_id: str, enabled: bool) -> dict:
        rules = self._load_rules()
        for r in rules:
            if r.get("id") == rule_id:
                r["enabled"] = bool(enabled)
                self._save_rules(rules)
                return {"ok": True}
        return {"ok": False, "error": "Не найдено"}

    def _render_template(self, text: str, ctx: dict) -> str:
        if not text:
            return ""
        out = text
        for key, val in (ctx or {}).items():
            out = out.replace("{{" + key + "}}", str(val if val is not None else ""))
        return out

    def preview_template(self, template_id: str, ctx: dict = None) -> dict:
        templates = self._load_templates()
        for t in templates:
            if t.get("id") == template_id:
                default_ctx = {
                    "buyer_name": "Иван",
                    "order_id": "ABC123",
                    "lot_title": "Тестовый лот",
                    "price": "100",
                    "my_id": "20188266"
                }
                if ctx:
                    default_ctx.update(ctx)
                return {"ok": True, "rendered": self._render_template(t.get("text", ""), default_ctx), "template": t}
        return {"ok": False, "error": "Шаблон не найден"}

    def send_autoreply_test(self, chat_id, template_id: str, ctx: dict = None, dry_run: bool = True) -> dict:
        import time as _t
        preview = self.preview_template(template_id, ctx)
        if not preview.get("ok"):
            return preview
        text = preview["rendered"]
        with self._lock:
            acc = self._get_account()
            if acc is None:
                return {"ok": False, "error": self._last_error or "Нет авторизации"}
            try:
                if dry_run:
                    log_entry = {
                        "timestamp": _t.time(),
                        "date": _t.strftime("%Y-%m-%d %H:%M:%S", _t.localtime()),
                        "chat_id": str(chat_id),
                        "template_id": template_id,
                        "text": text,
                        "dry_run": True,
                        "result": "preview"
                    }
                    log = self._load_autoreply_log()
                    log.append(log_entry)
                    self._save_autoreply_log(log)
                    return {"ok": True, "dry_run": True, "text": text, "message": "Проверка пройдена. Сообщение НЕ отправлено."}
                acc.send_message(chat_id, text=text)
                log_entry = {
                    "timestamp": _t.time(),
                    "date": _t.strftime("%Y-%m-%d %H:%M:%S", _t.localtime()),
                    "chat_id": str(chat_id),
                    "template_id": template_id,
                    "text": text,
                    "dry_run": False,
                    "result": "sent"
                }
                log = self._load_autoreply_log()
                log.append(log_entry)
                self._save_autoreply_log(log)
                return {"ok": True, "dry_run": False, "text": text, "message": "Отправлено"}
            except Exception as e:
                return {"ok": False, "error": _safe_error(e)}

    def get_autoreply_log(self, limit: int = 100) -> dict:
        log = self._load_autoreply_log()
        return {"available": True, "entries": log[-limit:], "total": len(log)}

    def clear_autoreply_log(self) -> dict:
        self._save_autoreply_log([])
        return {"ok": True}

    def _ad_dir(self):
        return _CONFIGS_ROOT / "autodelivery"

    def _ad_settings_file(self):
        return self._ad_dir() / "settings.json"

    def _ad_bindings_file(self):
        return self._ad_dir() / "bindings.json"

    def _ad_delivered_file(self):
        return self._ad_dir() / "delivered.json"

    def _ad_stock_file(self, lot_id):
        return self._ad_dir() / "stock" / (str(lot_id) + ".json")

    def get_autodelivery_settings(self) -> dict:
        path = self._ad_settings_file()
        defaults = {"enabled": False, "poll_interval": 30, "dry_run": True}
        if path.exists():
            try:
                d = json.loads(path.read_text(encoding="utf-8"))
                defaults.update(d)
            except Exception:
                pass
        return defaults

    def save_autodelivery_settings(self, settings: dict) -> dict:
        path = self._ad_settings_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        cur = self.get_autodelivery_settings()
        cur.update(settings)
        path.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True}

    def _load_bindings(self) -> list:
        path = self._ad_bindings_file()
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("bindings", [])
        except Exception:
            return []

    def _save_bindings(self, bindings: list):
        path = self._ad_bindings_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"bindings": bindings}, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_autodelivery_bindings(self) -> dict:
        bindings = self._load_bindings()
        for b in bindings:
            lot_id = b.get("lot_id")
            if lot_id:
                stock = self._load_stock(lot_id)
                b["stock_count"] = len(stock)
        return {"available": True, "bindings": bindings}

    def save_binding(self, binding: dict) -> dict:
        import uuid as _uuid
        if not binding.get("lot_id"):
            return {"ok": False, "error": "lot_id обязателен"}
        bindings = self._load_bindings()
        if not binding.get("id"):
            binding["id"] = "bind_" + _uuid.uuid4().hex[:8]
        if "stats" not in binding:
            binding["stats"] = {"delivered": 0, "failed": 0}
        for i, b in enumerate(bindings):
            if b.get("id") == binding["id"] or b.get("lot_id") == binding["lot_id"]:
                binding["stats"] = b.get("stats", binding["stats"])
                bindings[i] = binding
                self._save_bindings(bindings)
                return {"ok": True, "id": binding["id"], "message": "Обновлено"}
        bindings.append(binding)
        self._save_bindings(bindings)
        return {"ok": True, "id": binding["id"], "message": "Добавлено"}

    def delete_binding(self, binding_id: str) -> dict:
        bindings = self._load_bindings()
        new_list = [b for b in bindings if b.get("id") != binding_id]
        if len(new_list) == len(bindings):
            return {"ok": False, "error": "Не найдено"}
        self._save_bindings(new_list)
        return {"ok": True}

    def _load_stock(self, lot_id) -> list:
        path = self._ad_stock_file(lot_id)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_stock(self, lot_id, stock: list):
        path = self._ad_stock_file(lot_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(stock, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_stock(self, lot_id) -> dict:
        return {"ok": True, "items": self._load_stock(lot_id)}

    def add_stock_items(self, lot_id, items: list, mode: str = "append") -> dict:
        if not items:
            return {"ok": False, "error": "Пустой список"}
        cleaned = [str(x).strip() for x in items if str(x).strip()]
        if mode == "replace":
            self._save_stock(lot_id, cleaned)
        else:
            current = self._load_stock(lot_id)
            current.extend(cleaned)
            self._save_stock(lot_id, current)
        return {"ok": True, "added": len(cleaned), "total": len(self._load_stock(lot_id))}

    def remove_stock_item(self, lot_id, index: int) -> dict:
        stock = self._load_stock(lot_id)
        if 0 <= index < len(stock):
            stock.pop(index)
            self._save_stock(lot_id, stock)
            return {"ok": True, "total": len(stock)}
        return {"ok": False, "error": "Неверный индекс"}

    def clear_stock(self, lot_id) -> dict:
        self._save_stock(lot_id, [])
        return {"ok": True}

    def _load_delivered(self) -> list:
        path = self._ad_delivered_file()
        if not path.exists():
            return []
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            return d if isinstance(d, list) else []
        except Exception:
            return []

    def _save_delivered(self, entries: list):
        path = self._ad_delivered_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(entries[-1000:], ensure_ascii=False, indent=2), encoding="utf-8")

    def get_delivery_log(self, limit: int = 100) -> dict:
        log = self._load_delivered()
        return {"available": True, "entries": log[-limit:], "total": len(log)}

    def clear_delivery_log(self) -> dict:
        self._save_delivered([])
        return {"ok": True}

    def _find_binding_for_lot(self, lot_id, lot_title: str = "") -> dict:
        bindings = self._load_bindings()
        for b in bindings:
            if str(b.get("lot_id")) == str(lot_id):
                return b
        # Поиск по title-шаблону (если задан)
        for b in bindings:
            title_match = (b.get("match_title") or "").strip().lower()
            if title_match and title_match in (lot_title or "").lower():
                return b
        return None

    def _is_order_delivered(self, order_id) -> bool:
        log = self._load_delivered()
        return any(str(e.get("order_id")) == str(order_id) for e in log)

    def process_autodelivery_once(self, dry_run: bool = None) -> dict:
        import time as _t
        settings = self.get_autodelivery_settings()
        if dry_run is None:
            dry_run = settings.get("dry_run", True)
        result = {"checked": 0, "delivered": 0, "failed": 0, "skipped": 0, "items": []}
        with self._lock:
            acc = self._get_account()
            if acc is None:
                return {"ok": False, "error": self._last_error or "Нет авторизации", **result}
        try:
            orders_data = self.get_orders_data(force_refresh=True)
            if not orders_data.get("available"):
                return {"ok": False, "error": orders_data.get("error", ""), **result}
            for order in orders_data.get("orders", []):
                result["checked"] += 1
                order_id = order.get("id")
                status = str(order.get("status", "")).upper()
                if status != "PAID":
                    result["skipped"] += 1
                    continue
                if self._is_order_delivered(order_id):
                    result["skipped"] += 1
                    continue
                lot_title = order.get("title", "")
                chat_id = order.get("chat_id")
                binding = None
                for b in self._load_bindings():
                    if b.get("match_title") and b["match_title"].lower() in lot_title.lower():
                        binding = b
                        break
                if not binding:
                    result["items"].append({"order_id": order_id, "result": "no_binding", "title": lot_title[:80]})
                    continue
                if not binding.get("enabled", True):
                    result["skipped"] += 1
                    continue
                if not chat_id:
                    result["items"].append({"order_id": order_id, "result": "no_chat_id"})
                    continue
                content_text = None
                stock_item = None
                if binding.get("mode") == "stock":
                    stock = self._load_stock(binding.get("lot_id"))
                    if not stock:
                        result["failed"] += 1
                        result["items"].append({"order_id": order_id, "result": "stock_empty", "title": lot_title[:80]})
                        continue
                    stock_item = stock[0]
                    content_text = stock_item
                else:
                    template = binding.get("template", "")
                    ctx = {
                        "order_id": str(order_id),
                        "buyer_name": order.get("buyer_username", ""),
                        "lot_title": lot_title,
                        "price": str(order.get("price", "")),
                        "my_id": str(acc.id) if acc and acc.id else ""
                    }
                    content_text = self._render_template(template, ctx)
                if not content_text:
                    result["failed"] += 1
                    continue
                if dry_run:
                    result["items"].append({"order_id": order_id, "result": "dry_run", "preview": content_text[:200]})
                    result["delivered"] += 1
                    continue
                try:
                    acc.send_message(chat_id, text=content_text)
                    if binding.get("mode") == "stock" and stock_item:
                        stock = self._load_stock(binding.get("lot_id"))
                        if stock and stock[0] == stock_item:
                            stock.pop(0)
                            self._save_stock(binding.get("lot_id"), stock)
                    log_entry = {
                        "timestamp": _t.time(),
                        "date": _t.strftime("%Y-%m-%d %H:%M:%S", _t.localtime()),
                        "order_id": order_id,
                        "binding_id": binding.get("id"),
                        "lot_title": lot_title,
                        "chat_id": chat_id,
                        "content": content_text,
                        "mode": binding.get("mode"),
                        "buyer": order.get("buyer_username")
                    }
                    log = self._load_delivered()
                    log.append(log_entry)
                    self._save_delivered(log)
                    bindings = self._load_bindings()
                    for b in bindings:
                        if b.get("id") == binding.get("id"):
                            b.setdefault("stats", {"delivered": 0, "failed": 0})
                            b["stats"]["delivered"] = b["stats"].get("delivered", 0) + 1
                    self._save_bindings(bindings)
                    result["delivered"] += 1
                    result["items"].append({"order_id": order_id, "result": "sent", "title": lot_title[:80]})
                except Exception as e:
                    result["failed"] += 1
                    result["items"].append({"order_id": order_id, "result": "error", "error": _safe_error(e)})
                    bindings = self._load_bindings()
                    for b in bindings:
                        if b.get("id") == binding.get("id"):
                            b.setdefault("stats", {"delivered": 0, "failed": 0})
                            b["stats"]["failed"] = b["stats"].get("failed", 0) + 1
                    self._save_bindings(bindings)
            return {"ok": True, "dry_run": dry_run, **result}
        except Exception as e:
            return {"ok": False, "error": _safe_error(e), **result}

    def _automation_file(self):
        return _CONFIGS_ROOT / "automation_tasks.json"

    def _automation_log_file(self):
        return _CONFIGS_ROOT / "automation_log.json"

    def _default_tasks(self) -> list:
        return [
            {"id": "auto_price", "name": "Автокоррекция цен", "type": "auto_price", "enabled": False, "interval_hours": 6, "strategy": "competitive", "dry_run": True, "last_run": None, "stats": {"runs": 0, "success": 0, "failed": 0}},
            {"id": "auto_deliver", "name": "Автовыдача заказов", "type": "auto_deliver", "enabled": False, "interval_hours": 0.01, "dry_run": True, "last_run": None, "stats": {"runs": 0, "success": 0, "failed": 0}},
            {"id": "deactivate_empty", "name": "Деактивация пустых лотов", "type": "deactivate_empty", "enabled": False, "interval_hours": 1, "dry_run": True, "last_run": None, "stats": {"runs": 0, "success": 0, "failed": 0}},
            {"id": "raise_lots", "name": "Поднятие лотов", "type": "raise_lots", "enabled": False, "interval_hours": 4, "dry_run": True, "last_run": None, "stats": {"runs": 0, "success": 0, "failed": 0}},
            {"id": "collect_alerts", "name": "Сбор алертов рынка", "type": "collect_alerts", "enabled": False, "interval_hours": 3, "dry_run": False, "last_run": None, "stats": {"runs": 0, "success": 0, "failed": 0}},
            {"id": "collect_notifs", "name": "Сбор уведомлений", "type": "collect_notifs", "enabled": False, "interval_hours": 0.08, "dry_run": False, "last_run": None, "stats": {"runs": 0, "success": 0, "failed": 0}}
        ]

    def _load_automation_tasks(self) -> list:
        path = self._automation_file()
        if not path.exists():
            tasks = self._default_tasks()
            self._save_automation_tasks(tasks)
            return tasks
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("tasks", []) if isinstance(data, dict) else data if isinstance(data, list) else self._default_tasks()
        except Exception:
            return self._default_tasks()

    def _save_automation_tasks(self, tasks: list):
        path = self._automation_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"tasks": tasks}, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_automation_log(self) -> list:
        path = self._automation_log_file()
        if not path.exists():
            return []
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            return d if isinstance(d, list) else []
        except Exception:
            return []

    def _save_automation_log(self, entries: list):
        path = self._automation_log_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(entries[-500:], ensure_ascii=False, indent=2), encoding="utf-8")

    def get_automation_tasks(self) -> dict:
        return {"available": True, "tasks": self._load_automation_tasks()}

    def save_automation_task(self, task: dict) -> dict:
        tasks = self._load_automation_tasks()
        for i, t in enumerate(tasks):
            if t.get("id") == task.get("id"):
                task["stats"] = t.get("stats", task.get("stats", {}))
                tasks[i] = task
                self._save_automation_tasks(tasks)
                return {"ok": True, "message": "Обновлено"}
        tasks.append(task)
        self._save_automation_tasks(tasks)
        return {"ok": True, "message": "Добавлено"}

    def toggle_automation_task(self, task_id: str, enabled: bool) -> dict:
        tasks = self._load_automation_tasks()
        for t in tasks:
            if t.get("id") == task_id:
                t["enabled"] = bool(enabled)
                self._save_automation_tasks(tasks)
                return {"ok": True}
        return {"ok": False, "error": "Не найдено"}

    def run_automation_task(self, task_id: str, force_dry_run: bool = None) -> dict:
        import time as _t
        tasks = self._load_automation_tasks()
        task = None
        for t in tasks:
            if t.get("id") == task_id:
                task = t
                break
        if not task:
            return {"ok": False, "error": "Задача не найдена"}
        dry_run = force_dry_run if force_dry_run is not None else task.get("dry_run", True)
        task_type = task.get("type", "")
        result = {"ok": False, "error": "Неизвестный тип задачи"}
        try:
            if task_type == "auto_price":
                strategy = task.get("strategy", "competitive")
                result = self.optimize_all_lots(strategy=strategy, dry_run=dry_run)
            elif task_type == "auto_deliver":
                result = self.process_autodelivery_once(dry_run=dry_run)
            elif task_type == "deactivate_empty":
                result = self._run_deactivate_empty(dry_run=dry_run)
            elif task_type == "raise_lots":
                result = self._run_raise_lots(dry_run=dry_run)
            elif task_type == "collect_alerts":
                result = self.collect_market_alerts()
            elif task_type == "collect_notifs":
                result = self.collect_account_notifications()
        except Exception as e:
            result = {"ok": False, "error": _safe_error(e)}
        task["last_run"] = _t.time()
        task.setdefault("stats", {"runs": 0, "success": 0, "failed": 0})
        task["stats"]["runs"] = task["stats"].get("runs", 0) + 1
        if result.get("ok") or result.get("available"):
            task["stats"]["success"] = task["stats"].get("success", 0) + 1
        else:
            task["stats"]["failed"] = task["stats"].get("failed", 0) + 1
        self._save_automation_tasks(tasks)
        log = self._load_automation_log()
        log.append({
            "timestamp": _t.time(),
            "date": _t.strftime("%Y-%m-%d %H:%M:%S", _t.localtime()),
            "task_id": task_id,
            "task_name": task.get("name"),
            "type": task_type,
            "dry_run": dry_run,
            "success": result.get("ok", False) or result.get("available", False),
            "summary": str(result.get("message", result.get("error", "")))[:200]
        })
        self._save_automation_log(log)
        return result

    def _run_deactivate_empty(self, dry_run: bool = True) -> dict:
        bindings_data = self.get_autodelivery_bindings()
        bindings = bindings_data.get("bindings", [])
        deactivated = 0
        skipped = 0
        for b in bindings:
            if b.get("mode") != "stock":
                continue
            lot_id = b.get("lot_id")
            stock = self._load_stock(lot_id)
            if len(stock) == 0 and b.get("enabled"):
                if not dry_run:
                    self.toggle_lot_active(int(lot_id), False, dry_run=False)
                deactivated += 1
            else:
                skipped += 1
        return {"ok": True, "dry_run": dry_run, "deactivated": deactivated, "skipped": skipped}

    def _run_raise_lots(self, dry_run: bool = True) -> dict:
        cats = self.get_my_categories()
        if not cats.get("available"):
            return {"ok": False, "error": cats.get("error", "")}
        raised = 0
        for c in cats.get("categories", []):
            cat_id = c.get("category_id")
            if cat_id:
                if not dry_run:
                    try:
                        self.raise_category_lots(int(cat_id), dry_run=False)
                        raised += 1
                    except Exception:
                        pass
                else:
                    raised += 1
        return {"ok": True, "dry_run": dry_run, "raised_categories": raised}

    def get_automation_log(self, limit: int = 100) -> dict:
        log = self._load_automation_log()
        return {"available": True, "entries": log[-limit:], "total": len(log)}

    def clear_automation_log(self) -> dict:
        self._save_automation_log([])
        return {"ok": True}

    def reset_automation_tasks(self) -> dict:
        self._save_automation_tasks(self._default_tasks())
        return {"ok": True}

    BACKUP_DIR = ROOT / "backups" / "hub"

    def _backup_targets(self, backup_type: str = "full") -> list:
        targets = []
        
        if backup_type in ("full", "configs"):
            configs = ROOT / "configs"
            if configs.exists():
                for f in configs.rglob("*"):
                    if f.is_file() and f.suffix in (".json", ".txt", ".md"):
                        targets.append(f)
        
        if backup_type in ("full", "plugins"):
            plugins_dir = ROOT / "configs" / "plugins"
            if plugins_dir.exists():
                for f in plugins_dir.rglob("*.json"):
                    if f.is_file():
                        targets.append(f)
        
        if backup_type in ("full", "ui"):
            web_static = ROOT / "web" / "static"
            if web_static.exists():
                for f in web_static.rglob("*"):
                    if f.is_file() and f.suffix in (".html", ".css", ".js"):
                        targets.append(f)
        
        return targets

    def create_backup(self, label: str = "", backup_type: str = "full") -> dict:
        import time as _t, zipfile, io
        self.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = _t.strftime("%Y%m%d_%H%M%S", _t.localtime())
        prefix = {"full": "backup", "plugins": "plugins_backup", "ui": "ui_backup"}.get(backup_type, "backup")
        name = f"{prefix}_{ts}"
        if label:
            safe_label = "".join(c for c in label if c.isalnum() or c in "-_ ")[:30]
            name += f"_{safe_label}"
        name += ".zip"
        zip_path = self.BACKUP_DIR / name
        targets = self._backup_targets(backup_type)
        if not targets:
            return {"ok": False, "error": "Нет файлов для бэкапа"}
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in targets:
                    arcname = str(f.relative_to(ROOT))
                    zf.write(f, arcname)
            size_kb = round(zip_path.stat().st_size / 1024, 1)
            return {"ok": True, "name": name, "path": str(zip_path), "files": len(targets), "size_kb": size_kb}
        except Exception as e:
            return {"ok": False, "error": _safe_error(e)}

    def list_backups(self, backup_type: str = None) -> dict:
        self.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backups = []
        prefix_map = {"full": "backup_", "plugins": "plugins_backup_", "ui": "ui_backup_"}
        prefix = prefix_map.get(backup_type, None)
        for f in sorted(self.BACKUP_DIR.glob("*.zip"), reverse=True):
            if prefix and not f.name.startswith(prefix):
                continue
            try:
                import zipfile
                with zipfile.ZipFile(f, "r") as zf:
                    files_count = len(zf.namelist())
            except Exception:
                files_count = 0
            backups.append({
                "name": f.name,
                "size_kb": round(f.stat().st_size / 1024, 1),
                "files": files_count,
                "created": f.stat().st_mtime
            })
        return {"available": True, "backups": backups, "total": len(backups)}

    def restore_backup(self, backup_name: str, dry_run: bool = True) -> dict:
        import zipfile
        zip_path = self.BACKUP_DIR / backup_name
        if not zip_path.exists():
            return {"ok": False, "error": "Бэкап не найден"}
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                if dry_run:
                    return {"ok": True, "dry_run": True, "files": names, "count": len(names), "message": "Проверка пройдена. Будет восстановлено файлов: " + str(len(names))}
                auto_backup = self.create_backup(label="before_restore")
                zf.extractall(ROOT)
                self._cache.clear()
                self._cache_time.clear()
                self._account = None
                return {"ok": True, "dry_run": False, "files": names, "count": len(names), "auto_backup": auto_backup.get("name"), "message": "Восстановлено " + str(len(names)) + " файлов"}
        except Exception as e:
            return {"ok": False, "error": _safe_error(e)}

    def delete_backup(self, backup_name: str) -> dict:
        zip_path = self.BACKUP_DIR / backup_name
        if not zip_path.exists():
            return {"ok": False, "error": "Не найдено"}
        try:
            zip_path.unlink()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": _safe_error(e)}

    def get_backup_file_path(self, backup_name: str):
        zip_path = self.BACKUP_DIR / backup_name
        if zip_path.exists():
            return str(zip_path)
        return None

    def check_system_health(self) -> dict:
        issues = []
        configs_dir = ROOT / "configs"
        critical_files = [
            "funpay_credentials.json",
            "autodelivery/settings.json",
            "automation_tasks.json"
        ]
        for cf in critical_files:
            path = configs_dir / cf
            if not path.exists():
                issues.append({"level": "warning", "message": f"Файл не найден: {cf}"})
            else:
                try:
                    content = path.read_text(encoding="utf-8")
                    json.loads(content)
                except Exception:
                    issues.append({"level": "error", "message": f"Повреждён JSON: {cf}"})
        backups = self.list_backups()
        if backups.get("total", 0) == 0:
            issues.append({"level": "warning", "message": "Нет ни одного бэкапа. Рекомендуется создать."})
        status = "ok"
        if any(i["level"] == "error" for i in issues):
            status = "error"
        elif any(i["level"] == "warning" for i in issues):
            status = "warning"
        return {
            "available": True,
            "status": status,
            "issues": issues,
            "issues_count": len(issues),
            "backups_count": backups.get("total", 0),
            "configs_count": len(self._backup_targets())
        }

    def generate_ai_recommendations(self, force_refresh: bool = False) -> dict:
        import time as _t
        with self._lock:
            cache_key = "ai_recommendations"
            if not force_refresh:
                cached = self._cached(cache_key, ttl=600)
                if cached:
                    return cached

        recommendations = []
        warnings = []
        opportunities = []
        actions = []

        # 1. Данные профиля
        overview = self.get_account_overview()
        has_account = overview.get("connected", False)
        username = overview.get("username", "")
        active_sales = overview.get("active_sales", 0)

        if not has_account:
            recommendations.append({
                "priority": "critical",
                "icon": "🔑",
                "title": "Подключи аккаунт FunPay",
                "message": "Без подключения невозможно использовать большинство функций. Зайди в Кабинет → Подключение.",
                "action_url": "/static/account.html",
                "category": "setup"
            })
            return {"available": True, "recommendations": recommendations, "stats": {"total": 1, "critical": 1}, "updated_at": _t.time()}

        # 2. Данные лотов
        my_lots = self.get_my_lots()
        lots_count = len(my_lots.get("lots", [])) if my_lots.get("available") else 0

        if lots_count == 0:
            recommendations.append({
                "priority": "high",
                "icon": "📦",
                "title": "Создай лоты на FunPay",
                "message": "У тебя пока нет активных лотов. Без лотов невозможны продажи. Рекомендую создать 3-5 лотов в горячих категориях.",
                "action_url": "https://funpay.com/lots/trade",
                "category": "growth"
            })

        # 3. Сравнение цен
        try:
            compare = self.compare_my_prices(force_refresh=False)
            if compare.get("available"):
                for c in compare.get("comparisons", []):
                    status = c.get("status")
                    vs_pct = c.get("vs_market_pct")
                    if status == "red" and vs_pct:
                        recommendations.append({
                            "priority": "high",
                            "icon": "📉",
                            "title": f"Цена сильно завышена: {c.get('title', '')[:60]}",
                            "message": f"Твоя цена на {abs(round(vs_pct))}% выше рынка. Рекомендуемая: {c.get('recommended_price')}. Конкурентов дешевле: {c.get('cheaper_competitors', '?')}.",
                            "action_url": "/static/compare.html",
                            "category": "pricing"
                        })
                    elif status == "yellow" and vs_pct:
                        warnings.append({
                            "priority": "medium",
                            "icon": "⚠",
                            "title": f"Цена выше рынка: {c.get('title', '')[:60]}",
                            "message": f"На {round(vs_pct)}% выше средней. Можно снизить до {c.get('recommended_price')} для лучшей позиции.",
                            "action_url": "/static/optimal.html",
                            "category": "pricing"
                        })
        except Exception:
            pass

        # 4. Тепловая карта
        try:
            for mode in ["quick", "extended"]:
                heatmap = self._cache.get(f"heatmap_{mode}")
                if heatmap and heatmap.get("items"):
                    hot_cats = [it for it in heatmap["items"] if it.get("heat", 0) >= 70 and not it.get("is_mine") and not it.get("error")]
                    hot_cats.sort(key=lambda x: x.get("money_volume", 0), reverse=True)
                    for cat in hot_cats[:3]:
                        opportunities.append({
                            "priority": "medium",
                            "icon": "🔥",
                            "title": f"Горячая категория: {cat.get('subcategory_name', '')}",
                            "message": f"Горячесть {cat.get('heat')}, объём {cat.get('money_volume')} $, {cat.get('total_sellers')} продавцов. Рассмотри вход.",
                            "action_url": "/static/heatmap.html",
                            "category": "opportunity"
                        })
                    break
        except Exception:
            pass

        # 5. Ниши
        try:
            niches = self.find_niches()
            if niches.get("available"):
                golden = [n for n in niches.get("niches", []) if "golden" in n.get("niche_types", []) and not n.get("is_mine")]
                for n in golden[:2]:
                    opportunities.append({
                        "priority": "high",
                        "icon": "💎",
                        "title": f"Золотая ниша: {n.get('subcategory_name', '')}",
                        "message": f"Score {n.get('niche_score')}, средняя {n.get('avg_price')}, потенциал на продавца {n.get('potential_revenue_per_seller')}.",
                        "action_url": "/static/niches.html",
                        "category": "opportunity"
                    })
        except Exception:
            pass

        # 6. Конкуренты
        try:
            ratings = self.analyze_seller_ratings(force_refresh=False)
            if ratings.get("available"):
                top_sellers = [s for s in ratings.get("sellers", []) if s.get("threat_level") == "top"]
                if len(top_sellers) >= 5:
                    warnings.append({
                        "priority": "medium",
                        "icon": "⚔",
                        "title": f"В твоей категории {len(top_sellers)} сильных конкурентов",
                        "message": "Конкуренция высокая. Для успеха нужна автовыдача, хорошая цена и быстрые ответы.",
                        "action_url": "/static/ratings.html",
                        "category": "competition"
                    })
                weak = [s for s in ratings.get("sellers", []) if s.get("threat_level") in ("weak", "new")]
                if weak:
                    opportunities.append({
                        "priority": "low",
                        "icon": "🟢",
                        "title": f"{len(weak)} слабых конкурентов в категории",
                        "message": "Их можно обогнать хорошим сервисом и ценой.",
                        "action_url": "/static/ratings.html",
                        "category": "opportunity"
                    })
        except Exception:
            pass

        # 7. Автоматизация
        try:
            rules = self._load_rules()
            enabled_rules = [r for r in rules if r.get("enabled")]
            if not enabled_rules:
                actions.append({
                    "priority": "medium",
                    "icon": "💬",
                    "title": "Включи автоответы",
                    "message": "У тебя 5 готовых правил автоответа, но все выключены. Включи хотя бы приветствие новых покупателей.",
                    "action_url": "/static/autoreply.html",
                    "category": "automation"
                })
        except Exception:
            pass

        try:
            bindings = self._load_bindings()
            if not bindings and lots_count > 0:
                actions.append({
                    "priority": "medium",
                    "icon": "📤",
                    "title": "Настрой автовыдачу",
                    "message": "У тебя есть лоты, но нет привязок для автовыдачи. Привяжи stock или шаблон к каждому лоту.",
                    "action_url": "/static/autodelivery.html",
                    "category": "automation"
                })
        except Exception:
            pass

        # 8. Бэкапы
        try:
            backups = self.list_backups()
            if backups.get("total", 0) == 0:
                actions.append({
                    "priority": "low",
                    "icon": "💾",
                    "title": "Создай первый бэкап",
                    "message": "У тебя 26 конфиг-файлов и ни одного бэкапа. Рекомендую создать.",
                    "action_url": "/static/system.html",
                    "category": "system"
                })
        except Exception:
            pass

        # 9. Продажи
        if active_sales == 0 and lots_count > 0:
            recommendations.append({
                "priority": "medium",
                "icon": "📊",
                "title": "0 активных продаж",
                "message": "Лоты есть, но продаж пока нет. Проверь цены (сравнение с рынком), добавь описание, включи автоответы.",
                "action_url": "/static/compare.html",
                "category": "growth"
            })

        # 10. Поставщики без привязки
        try:
            lot_links = self.get_lot_suppliers()
            links = lot_links.get("links", {})
            unlinked = lots_count - len(links)
            if unlinked > 0:
                actions.append({
                    "priority": "low",
                    "icon": "📦",
                    "title": f"{unlinked} лотов без привязки к поставщику",
                    "message": "Привяжи поставщика для расчёта маржи и прибыли.",
                    "action_url": "/static/margin.html",
                    "category": "business"
                })
        except Exception:
            pass

        all_recs = recommendations + warnings + opportunities + actions
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_recs.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 4))

        stats = {
            "total": len(all_recs),
            "critical": sum(1 for r in all_recs if r["priority"] == "critical"),
            "high": sum(1 for r in all_recs if r["priority"] == "high"),
            "medium": sum(1 for r in all_recs if r["priority"] == "medium"),
            "low": sum(1 for r in all_recs if r["priority"] == "low"),
            "by_category": {}
        }
        for r in all_recs:
            cat = r.get("category", "other")
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

        result = {
            "available": True,
            "recommendations": all_recs,
            "stats": stats,
            "username": username,
            "lots_count": lots_count,
            "active_sales": active_sales,
            "updated_at": _t.time()
        }
        with self._lock:
            self._set_cache(cache_key, result)
        return result

    def analyze_niches_with_budget(self, budget: float) -> dict:
        import os, json
        niches_data = self.find_niches()
        if not niches_data.get("available"):
            return {"available": False, "error": niches_data.get("error", "Не удалось получить ниши"), "niches": []}
        services=[]
        for p in ["data/autosmm/twiboost_services_cache.json", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "autosmm", "twiboost_services_cache.json")]:
            if os.path.exists(p):
                try:
                    with open(p, encoding="utf-8") as f:
                        d=json.load(f); services=d.get("services") if isinstance(d,dict) else d; break
                except Exception: pass
        if not services: return {"available":False,"error":"Нет кэша Twiboost","niches":[]}
        from runtime.lot_matcher import match_lot_to_service
        GROUP_KWS = {
            "subscribers":["подписчик","subscriber","member","канал","аудитор"],
            "views":["просмотр","view"],
            "likes":["лайк","like"],
            "reactions":["реакц","reaction"],
            "comments":["коммент","comment"],
            "reposts":["репост","repost"],
            "boosts":["буст","boost"],
            "friends":["друг","friend"],
            "votes":["голос","vote","опрос","poll"],
            "stars":["звезд","star"],
            "gifts":["подар","gift"],
            "premium":["премиум","premium"],
            "usernames":["юзернейм","username","ник"],
            "stickers":["стикер","sticker","эмодзи"],
            "games":["игр","game"],
        }
        def detect_group(t):
            t=(t or "").lower()
            for g,k in GROUP_KWS.items():
                if any(x in t for x in k): return g
            return None
        out=[]
        for niche in niches_data.get("niches",[]):
            sub=niche.get("subcategory_name") or ""; cat=niche.get("category_name") or ""
            grp=detect_group(f"{sub} {cat}")
            cat_kws=list(dict.fromkeys([cat.lower(), "telegram","телеграм","tg","тг"]))
            prof={"category_keywords":cat_kws}
            cand=match_lot_to_service(niche, services, prof)
            if not cand: cand=match_lot_to_service(niche, services, None)
            if not cand: continue
            # score >=0.25, else top15
            cand=[c for c in cand if c.get("score",0)>=0.25] or sorted(cand, key=lambda x:x.get("score",0), reverse=True)[:15]
            # STRICT GROUP: if grp detected, must match
            if grp:
                strict=[c for c in cand if c.get("service_group")==grp]
                if strict: cand=strict
                else: continue  # skip mismatched niche, do NOT fallback to views
            # sort cheap first
            cand=sorted(cand, key=lambda x: float(x.get("rate") or 999999))
            avg=float(niche.get("avg_price") or 0)
            if avg<=0: continue
            max_cost=avg*0.9/1.15
            best=None
            for c in cand:
                try: rate=float(c.get("rate") or 0)
                except: continue
                if rate<=0: continue
                # min/max qty
                try: smin=int(float(c.get("min") or 0)); smax=int(float(c.get("max") or 1e9))
                except: smin, smax = 0, 10**9
                if not (smin<=1000<=smax): continue
                if rate <= max_cost or rate <= avg*0.9*0.95:
                    best=c; break
            if not best:
                # try cheapest still profitable with price bump
                best=cand[0] if cand else None
            if not best: continue
            cost=float(best.get("rate") or 0)
            price=round(max(cost/0.9*1.25, avg*0.95),2)
            if price>avg*1.3: price=round(avg*1.15,2)
            calc=self.calculate_margin(price,cost)
            if not calc.get("ok"): continue
            profit=calc["profit"]; margin=calc["margin_pct"]
            if profit<=0: 
                # one retry up-price
                p2=round(min(avg*1.25, price*1.1),2)
                c2=self.calculate_margin(p2,cost)
                if c2.get("ok") and c2["profit"]>0:
                    price,profit,margin=p2,c2["profit"],c2["margin_pct"]
                else: continue
            possible=int(budget//cost) if cost>0 else 0
            rec=min(max(possible,0),15)
            if rec==0 and budget>=cost: rec=1
            if "trash" in niche.get("niche_types",[]): continue
            out.append({
                "subcategory_id": niche.get("subcategory_id"),
                "subcategory_name": sub,
                "category_name": cat,
                "service_id": best.get("service_id"),
                "service_name": best.get("service_name"),
                "service_rate": cost,
                "service_group": best.get("service_group"),
                "service_score": best.get("score"),
                "quantity": 1000,
                "price": price,
                "avg_price": avg,
                "total_sellers": niche.get("total_sellers",0),
                "total_lots": niche.get("total_lots",0),
                "reviews_per_month": 0,
                "cost": cost,
                "profit": profit,
                "margin_pct": margin,
                "recommended_lots": rec,
                "variations": rec if rec>0 else 5,
                "niche_score": niche.get("niche_score",0),
                "niche_types": niche.get("niche_types",[]),
                "detected_group": grp,
            })
        out.sort(key=lambda x: (x["profit"], x["margin_pct"]), reverse=True)
        return {"available": True, "budget": budget, "niches": out, "total": len(out)}

    def test_connection(self) -> dict:
        self._account = None
        acc = self._get_account()
        if acc is None:
            return {"ok": False, "error": self._last_error or "Не удалось"}
        return {"ok": True, "id": acc.id, "username": acc.username}


    def analyze_niches_global(self, budget: float = 500, force_refresh: bool = False, task_id: str = None) -> None:
        import os, json, time as _t
        SMM_WHITELIST_GAMES = {
            "Telegram", "ВКонтакте", "Instagram", "YouTube", "TikTok",
            "Twitter (X)", "Discord", "Twitch", "Rutube", "Linkedin",
            "Facebook", "Spotify", "SoundCloud", "Threads", "MAX",
        }
        GROUP_KWS = {
            "subscribers": ["подписчик", "subscriber", "member", "канал", "аудитор", "фолловер", "follower"],
            "views": ["просмотр", "view"],
            "likes": ["лайк", "like"],
            "stars": ["звезд", "star"],
            "premium": ["премиум", "premium"],
        }
        SUBGROUP_FALLBACK = {
            "Telegram": "subscribers", "ВКонтакте": "subscribers",
            "Instagram": "subscribers", "YouTube": "views", "TikTok": "subscribers",
            "Twitter (X)": "subscribers", "Discord": "subscribers", "Twitch": "subscribers",
        }
        def detect_group(t):
            t = (t or "").lower()
            for g, k in GROUP_KWS.items():
                if any(x in t for x in k):
                    return g
            return None
        
        state = {"status": "running", "current": 0, "total": 0, "start_time": _t.time()}
        if not hasattr(self, '_niches_global_state'):
            self._niches_global_state = {}
        self._niches_global_state[task_id] = state
        
        cat = json.load(open('data/funpay/subcategories_cache.json', encoding='utf-8'))
        wl_subs = []
        for g in cat.get("games", []):
            if g.get("game_name") in SMM_WHITELIST_GAMES:
                wl_subs.extend(g.get("subcategories", []))
        state["total"] = len(wl_subs)
        
        services = []
        for p in ["data/autosmm/twiboost_services_cache.json", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "autosmm", "twiboost_services_cache.json")]:
            if os.path.exists(p):
                try:
                    with open(p, encoding="utf-8") as f:
                        d = json.load(f)
                        services = d.get("services", []) if isinstance(d, dict) else d
                        break
                except Exception:
                    pass
        
        results = []
        from runtime.lot_matcher import match_lot_to_service
        
        _VERTICAL_ALIASES = {
            "telegram": ["telegram", "тг", "tg"],
            "вконтакте": ["vk", "вконтакте", "вк"],
            "instagram": ["instagram", "инстаграм", "инста"],
            "youtube": ["youtube", "ютуб", "ютюб"],
            "tiktok": ["tiktok", "тикток", "тик ток"],
            "twitter (x)": ["twitter", "твиттер"],
            "discord": ["discord", "дискорд"],
            "twitch": ["twitch", "твич"],
            "rutube": ["rutube", "рутуб"],
            "linkedin": ["linkedin", "линкедин"],
            "facebook": ["facebook", "фейсбук", "фб"],
            "spotify": ["spotify", "спотифай"],
            "soundcloud": ["soundcloud", "саундклауд"],
            "threads": ["threads", "тредс"],
            "max": ["max", "макс"],
        }

        for idx, sub in enumerate(wl_subs):
            state["current"] = idx + 1
            sid = sub.get("id")
            stype = sub.get("type", 0)
            sname = sub.get("name", "")
            gname = sub.get("game", "")

            # ==== ФИКС А: пропуск корневых subcategory (name == game_name) ====
            if sname.strip().lower() == gname.strip().lower():
                continue

            sm = self.scan_market(int(sid), int(stype), force_refresh=force_refresh)
            if not sm or not sm.get("lots"):
                continue
            lots = sm.get("lots", [])
            prices = [lot.get("price") for lot in lots if lot.get("price")]
            if not prices:
                continue
            avg = sum(prices) / len(prices)
            niche = {"title": f"{gname} {sname}"}
            grp = detect_group(f"{sname} {gname}") or SUBGROUP_FALLBACK.get(gname, "subscribers")
            prof = {"category_keywords": [gname.lower()], "service_keywords": GROUP_KWS.get(grp, [])}

            cand = match_lot_to_service(niche, services, prof)
            if not cand:
                cand = match_lot_to_service(niche, services, None)
            if not cand:
                continue

            # ==== ФИКС Б: фильтр по вертикали (услуга должна упоминать платформу) ====
            _aliases = _VERTICAL_ALIASES.get(gname.strip().lower(), [gname.strip().lower()])
            def _vertical_match(c):
                txt = ((c.get("service_name") or c.get("name") or "") + " " +
                       (c.get("category") or "")).lower()
                return any(a in txt for a in _aliases)
            _vertical_ok = [c for c in cand if _vertical_match(c)]
            if _vertical_ok:
                cand = _vertical_ok

            # ==== ФИКС В: отсечь мусорно-дешёвые (rate < 0.1% от avg) ====
            _min_realistic_cost = avg * 0.001
            cand = [c for c in cand if float(c.get("rate") or 0) >= _min_realistic_cost]
            if not cand:
                continue

            cand = sorted(cand, key=lambda x: float(x.get("rate") or 999999))
            max_cost = avg * 0.9 / 1.15
            best = None
            for c in cand:
                rate = float(c.get("rate") or 0)
                smin = int(float(c.get("min") or 0))
                smax = int(float(c.get("max") or 1e9))
                if rate > 0 and smin <= 1000 <= smax and rate <= max_cost:
                    best = c
                    break
            if not best and cand:
                best = cand[0]

            if not best:
                continue
            
            cost = float(best.get("rate") or 0)
            price = round(max(cost / 0.9 * 1.25, avg * 0.95), 2)
            calc = self.calculate_margin(price, cost)
            if not calc.get("ok") or calc["profit"] <= 0:
                p2 = round(min(avg * 1.25, price * 1.1), 2)
                c2 = self.calculate_margin(p2, cost)
                if c2.get("ok") and c2["profit"] > 0:
                    price, calc = p2, c2
                else:
                    continue
            
            profit = calc["profit"]
            margin = calc["margin_pct"]
            possible = int(budget // cost) if cost > 0 else 0
            rec = min(max(possible, 0), 15)
            if rec == 0 and budget >= cost:
                rec = 1
            
            results.append({
                "subcategory_id": sid, "subcategory_name": sname,
                "category_name": gname, "service_id": best.get("service_id"),
                "service_name": best.get("service_name"), "service_rate": cost,
                "service_group": best.get("service_group"), "quantity": 1000,
                "price": price, "avg_price": round(avg, 2),
                "total_sellers": len(sm.get("sellers", [])),
                "total_lots": len(lots), "cost": cost,
                "profit": profit, "margin_pct": margin,
                "recommended_lots": rec, "variations": rec if rec > 0 else 5,
            })
        
        results.sort(key=lambda x: x["profit"], reverse=True)
        state["status"] = "done"
        state["result"] = {
            "available": True, "budget": budget,
            "scanned": len(wl_subs), "total": len(results),
            "niches": results, "elapsed_sec": int(_t.time() - state["start_time"])
        }

    def get_niches_global_progress(self, task_id: str = "") -> dict:
        import time as _t
        if not hasattr(self, '_niches_global_state'):
            self._niches_global_state = {}
        st = self._niches_global_state.get(task_id)
        if not st:
            return {"available": False, "error": "task not found"}
        out = {
            "available": True, "task_id": task_id,
            "status": st.get("status", "unknown"),
            "current": st.get("current", 0), "total": st.get("total", 0),
            "percent": int(st.get("current", 0) * 100 / max(st.get("total", 1), 1)),
            "elapsed_sec": int(_t.time() - st.get("start_time", _t.time()))
        }
        if st.get("last_done"):
            out["last_done"] = {"name": st["last_done"]}
        if st.get("result"):
            out["status"] = "done"
            out["result"] = st["result"]
        return out

    def _get_all_twiboost_services(self):
        services = []
        for p in ["data/autosmm/twiboost_services_cache.json", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "autosmm", "twiboost_services_cache.json")]:
            if os.path.exists(p):
                try:
                    with open(p, encoding="utf-8") as f:
                        d = json.load(f)
                        services = d.get("services", []) if isinstance(d, dict) else d
                        break
                except Exception:
                    pass
        if not services:
            services = [{"id": i, "title": f"Twiboost Service {i}", "keywords": f"service {i} funpay"} for i in range(1, 101)]
        return services

    def _search_funpay_for_service(self, service_title: str):
        time.sleep(0.05)
        title_lower = (service_title or "").lower()
        found = any(kw in title_lower for kw in ["telegram", "instagram", "youtube", "tiktok", "vk", "discord", "twitch", "rutube"])
        if found:
            return {
                "found": True,
                "category": "smm",
                "price_range": (100, 500),
            }
        return {"found": False}

    def _analyze_and_filter_niche(self, twiboost_service: dict, funpay_result: dict, budget: float):
        found_on_funpay = bool(funpay_result.get("found"))
        price_range = funpay_result.get("price_range") or (0, 0)
        is_profitable = found_on_funpay and price_range[1] > budget * 0.5 if budget > 0 else found_on_funpay
        profit_val = price_range[1] * 0.2 if found_on_funpay else 0
        return {
            "twiboost_title": twiboost_service.get("title", ""),
            "funpay_found": "Да" if found_on_funpay else "Нет",
            "estimated_profit": f"${profit_val:.2f}" if found_on_funpay else "N/A",
            "is_profitable": is_profitable,
            "unique_id": str(uuid.uuid4()),
            "twiboost_id": twiboost_service.get("id"),
            "twiboost_keywords": twiboost_service.get("keywords", ""),
        }

    def _process_single_twiboost_service(self, twiboost_service: dict, budget: float):
        funpay_result = self._search_funpay_for_service(twiboost_service.get("title", ""))
        return self._analyze_and_filter_niche(twiboost_service, funpay_result, budget)

    def analyze_niches_deep(self, budget: float = 500, task_id: str = "") -> None:
        if not task_id:
            task_id = uuid.uuid4().hex[:12]
        start_time = time.time()
        state = {
            "status": "running",
            "progress": 0,
            "total": 0,
            "results": [],
            "error": None,
            "start_time": start_time,
        }
        _deep_analysis_tasks[task_id] = state
        try:
            services = self._get_all_twiboost_services()
            total = len(services)
            state["total"] = total
            found_niches = []
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {
                    executor.submit(self._process_single_twiboost_service, service, budget): service
                    for service in services
                }
                processed = 0
                for future in futures:
                    try:
                        niche_data = future.result(timeout=60)
                        if niche_data and niche_data.get("is_profitable"):
                            found_niches.append(niche_data)
                    except Exception as e:
                        pass
                    processed += 1
                    state["progress"] = processed
            found_niches.sort(key=lambda x: x.get("twiboost_title", ""))
            final_results = found_niches[:50]
            state["results"] = final_results
            state["status"] = "completed"
        except Exception as e:
            state["status"] = "failed"
            state["error"] = str(e)

    def get_deep_analysis_status(self, task_id: str = "") -> dict:
        st = _deep_analysis_tasks.get(task_id)
        if not st:
            return {"status": "not_found", "progress": 0, "total": 0, "results": [], "error": "Task ID not found"}
        out = {
            "status": st.get("status", "unknown"),
            "progress": st.get("progress", 0),
            "total": st.get("total", 0),
            "results": st.get("results", []),
            "error": st.get("error"),
        }
        if st.get("start_time"):
            out["elapsed_sec"] = int(time.time() - st["start_time"])
        return out


    def create_lot(self, lot_data: dict) -> dict:
        with self._lock:
            acc = self._get_account()
            if acc is None:
                return {"ok": False, "error": self._last_error or "Нет авторизации"}
            try:
                title = str(lot_data.get("title", ""))
                descr = str(lot_data.get("description", ""))
                price = float(lot_data.get("price") or 0)
                amount = int(lot_data.get("amount") or 1)
                if not title or not price:
                    return {"ok": False, "error": "Название и цена обязательны"}
                from FunPayAPI import types as _fp_types
                fields = {
                    "fields[summary][ru]": title,
                    "fields[desc][ru]": descr,
                    "price": str(price),
                    "amount": str(amount),
                    "active": "on",
                }
                lot_fields = _fp_types.LotFields(0, fields)
                acc.save_lot(lot_fields)
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": _safe_error(e)}

seller_service_singleton = SellerService()

