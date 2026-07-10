"""
FunPay Hub - Clean Plugin Bootstrap
Initializes plugin system WITHOUT Cardinal/RuntimeOrchestrator/dashboard.
Provides:
  - EventBus
  - RuntimeLog
  - PluginManager
  - RuntimeController
  - HubStateAPI (proxy to our own Flask endpoints — no Cardinal needed)

Usage in funpayhub_main.py:
    from hub_bootstrap import init_plugin_system
    runtime_controller, runtime_log, notification_manager, event_bus = init_plugin_system()
    app.runtime_controller    = runtime_controller
    app.runtime_log           = runtime_log
    app.notification_manager  = notification_manager
"""
# Загрузка переменных окружения из .env
from dotenv import load_dotenv
load_dotenv()


import os
import time
import json
import re
import threading
from typing import Any, List, Optional
import logging
from runtime.http_client import HTTPClient, HTTPClientError
from security.secrets_manager import SecretsManager

_http_client = HTTPClient()

_last_supplier_state = {}


# ---------------------------------------------------------------------
# HubStateAPI — replaces Cardinal-bound StateAPI
# Plugins can read state via plugin.state_api.get_balance(), etc.
# We fetch from our own Flask backend (running on 127.0.0.1:5000).
# ---------------------------------------------------------------------

class HubStateAPI:
    """Lightweight state API that talks to our own Flask backend
    instead of holding a Cardinal reference."""

    def __init__(self, base_url: str = "http://127.0.0.1:5000"):
        self._base_url = base_url
        self._lock = threading.RLock()
        # Cache (TTL 5 seconds) so plugins don't spam our backend
        self._cache = {}
        self._cache_ttl = 5

    def _fetch(self, path: str, timeout: float = 3.0):
        try:
            now = time.time()
            cached = self._cache.get(path)
            if cached and (now - cached[0]) < self._cache_ttl:
                return cached[1]
            data = _http_client.get(self._base_url + path, timeout=timeout)
            if data is not None:
                self._cache[path] = (now, data)
                return data
        except Exception:
            pass
        return None

    # ---- Public API expected by plugins ----

    def get_state(self) -> dict:
        ov = self._fetch("/api/seller/overview") or {}
        bal = self._fetch("/api/seller/balance/full") or {}
        return {
            "profile": ov,
            "balance": bal.get("available_rub") or bal.get("balance") or 0,
            "lots": [],
            "status": "online" if ov else "offline",
            "last_update": time.time(),
        }

    def get_balance(self) -> float:
        bal = self._fetch("/api/seller/balance/full") or {}
        try:
            v = bal.get("available_rub") or bal.get("balance") or 0
            return float(v) if v is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    def get_withdrawable(self) -> float:
        return self.get_balance()

    def get_lots(self) -> List[dict]:
        data = self._fetch("/api/seller/lots") or {}
        lots = data.get("lots") if isinstance(data, dict) else data
        return lots if isinstance(lots, list) else []

    def get_total_lots(self) -> int:
        return len(self.get_lots())

    def get_active_lots(self) -> int:
        return sum(1 for l in self.get_lots() if l.get("active", True))

    def get_profile(self) -> dict:
        return self._fetch("/api/seller/overview") or {}

    def get_username(self) -> str:
        p = self.get_profile()
        return p.get("username", "Unknown")

    def get_user_id(self) -> Optional[int]:
        p = self.get_profile()
        return p.get("id") or p.get("user_id")

    def get_status(self) -> str:
        ov = self._fetch("/api/seller/overview")
        return "online" if ov else "offline"

    def get_last_update(self) -> float:
        return time.time()

    def get_logs(self, limit: int = 50) -> List[str]:
        return []

    def is_online(self) -> bool:
        return self.get_status() == "online"

    def to_dict(self) -> dict:
        return self.get_state()


# ---------------------------------------------------------------------
# Main init function
# ---------------------------------------------------------------------



# B18: 60s background worker
def _start_background_worker(seller_service, event_bus, interval_sec=60, verbose=True):
    import threading, time, traceback
    
    def _worker_loop():
        if verbose:
            print("[Worker] Started - tick every " + str(interval_sec) + "s")
        time.sleep(8)
        tick = 0
        while True:
            tick += 1
            try:
                result = seller_service.collect_account_notifications()
                if isinstance(result, dict):
                    nc = result.get("new_count", 0)
                    if nc > 0 or tick % 10 == 0:
                        print("[Worker] tick #" + str(tick) + " new_count=" + str(nc))
            except Exception as e:
                print("[Worker] tick #" + str(tick) + " ERROR: " + str(e))
                traceback.print_exc()
            time.sleep(interval_sec)
    
    t = threading.Thread(target=_worker_loop, name="BackgroundCollector", daemon=True)
    t.start()
    return t


def init_plugin_system(plugins_dir: str = "plugins", verbose: bool = True):
    """Initialize plugin system without Cardinal / second Flask.
    Returns: (runtime_controller, runtime_log, notification_manager, event_bus)
    Any of these may be None if init failed for that part."""

    runtime_controller   = None
    runtime_log          = None
    notification_manager = None
    event_bus            = None

    # 0. Database — init tables
    try:
        from runtime.database.base import init_db
        init_db()
        if verbose:
            print("[Bootstrap] Database tables ready")
    except Exception as e:
        print(f"[Bootstrap] Database init failed: {e}")

    # 1. RuntimeLog
    try:
        from runtime.runtime_log import RuntimeLog
        runtime_log = RuntimeLog()
        if verbose:
            print("[Bootstrap] RuntimeLog ready")
    except Exception as e:
        print(f"[Bootstrap] RuntimeLog failed: {e}")

    # 2. EventBus
    try:
        from eventbus import EventBus
        event_bus = EventBus()
        if verbose:
            print("[Bootstrap] EventBus ready")
    except Exception as e:
        print(f"[Bootstrap] EventBus failed: {e}")

    # 2.1. Inject event_bus into seller_service_singleton (POST-INIT INJECTION)
    # This is what enables seller_service to publish new_order/new_message events
    # to AutoSMM, autoreply engine and notification UI.
    if event_bus:
        try:
            from runtime.seller_service import seller_service_singleton as _svc
            _svc.event_bus = event_bus
            if verbose:
                print("[Bootstrap] event_bus injected into seller_service")
        except Exception as _e:
            print(f"[Bootstrap] event_bus inject failed: {_e}")

    # 3. PluginManager
    plugin_manager = None
    try:
        from plugins.plugin_manager import PluginManager
        state_api = HubStateAPI()
        plugin_manager = PluginManager(state_api=state_api, event_bus=event_bus)
        if verbose:
            print("[Bootstrap] PluginManager ready")
    except Exception as e:
        print(f"[Bootstrap] PluginManager failed: {e}")
        import traceback; traceback.print_exc()

    # 4. Load plugins from plugins/
    if plugin_manager:
        try:
            from plugins.loader import load_plugins
            results = load_plugins(plugin_manager, plugins_dir)
            loaded = sum(1 for v in results.values() if v)
            if verbose:
                print(f"[Bootstrap] Loaded {loaded}/{len(results)} plugins")
        except Exception as e:
            print(f"[Bootstrap] load_plugins failed: {e}")
            import traceback; traceback.print_exc()

    # 5. RuntimeController
    if plugin_manager and runtime_log and event_bus:
        try:
            from runtime.runtime_controller import RuntimeController
            runtime_controller = RuntimeController(plugin_manager, runtime_log, event_bus)
            if verbose:
                print("[Bootstrap] RuntimeController ready")
        except Exception as e:
            print(f"[Bootstrap] RuntimeController failed: {e}")
            import traceback; traceback.print_exc()

    # 6. NotificationManager (optional)
    try:
        from runtime.notifications.notification_manager import NotificationManager
        notification_manager = NotificationManager()
        if event_bus:
            try:
                notification_manager.subscribe_to_event_bus(event_bus)
            except Exception:
                pass
        if verbose:
            print("[Bootstrap] NotificationManager ready")
    except Exception as e:
        if verbose:
            print(f"[Bootstrap] NotificationManager skipped: {e}")

    if verbose:
        print("[Bootstrap] === Plugin system ready ===")


    # 7. AutoReply Engine (subscribes to event_bus, sends messages from rules)
    try:
        from runtime.autoreply_engine import AutoReplyEngine
        import runtime.autoreply_engine as _ar_mod
        from runtime.seller_service import seller_service_singleton as _svc_for_ar
        if event_bus and _svc_for_ar:
            _autosmm_plugin = None
            if plugin_manager:
                _autosmm_plugin = plugin_manager.plugins.get("autosmm_plugin")
            _ar_mod.autoreply_engine_singleton = AutoReplyEngine(event_bus, _svc_for_ar, autosmm_plugin=_autosmm_plugin)
            _ar_mod.autoreply_engine_singleton.subscribe()
            if verbose:
                print("[Bootstrap] AutoReplyEngine ready")
    except Exception as _e:
        print(f"[Bootstrap] AutoReplyEngine failed: {_e}")
        import traceback; traceback.print_exc()

    # 7.1 Order Payment Tracker
    try:
        from runtime.order_tracker import get_tracker
        from runtime.seller_service import seller_service_singleton as _svc_ot
        if event_bus and _svc_ot:
            _tracker = get_tracker(event_bus=event_bus, seller_service=_svc_ot)
            if _tracker:
                if verbose:
                    print("[Bootstrap] OrderPaymentTracker ready")
    except Exception as _e_ot:
        print(f"[Bootstrap] OrderPaymentTracker failed: {_e_ot}")
        import traceback; traceback.print_exc()

    # 7.2 Order Flow Manager (полный цикл заказа, Этап C)
    try:
        from runtime.order_flow import OrderFlowManager
        from runtime.seller_service import seller_service_singleton as _svc_of
        _tg_url = os.environ.get("TELEGRAM_BOT_URL", "")
        _admin_id = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "")
        if event_bus and _svc_of:
            _ofm = OrderFlowManager(
                seller_service=_svc_of,
                event_bus=event_bus,
                telegram_bot_url=_tg_url,
                admin_chat_id=_admin_id,
            )
            _ofm.start()
            # Store on app for access from plugins
            if hasattr(event_bus, '_order_flow'):
                pass
            event_bus._order_flow_manager = _ofm
            if verbose:
                print("[Bootstrap] OrderFlowManager ready (Stage C)")
    except Exception as _e_of:
        print(f"[Bootstrap] OrderFlowManager failed: {_e_of}")
        import traceback; traceback.print_exc()

    # B18: start background worker (60s tick)
    try:
        from runtime.seller_service import seller_service_singleton as _svc_b18
        _start_background_worker(_svc_b18, event_bus, interval_sec=60, verbose=verbose)
        if verbose:
            print("[Bootstrap] Background worker started (60s)")
    except Exception as _ew_b18:
        print("[Bootstrap] Background worker failed: " + str(_ew_b18))

    # G2: Auto market update on startup + every 3 hours
    try:
        from runtime.seller_service import seller_service_singleton as _svc_g2
        _start_market_auto_update(_svc_g2, interval_sec=3 * 60 * 60, verbose=verbose)
        if verbose:
            print("[Bootstrap] Market auto-update started (3h)")
    except Exception as _ew_g2:
        print("[Bootstrap] Market auto-update failed: " + str(_ew_g2))

    # G2: Health check every 60 seconds
    try:
        _start_health_check(interval_sec=60, verbose=verbose, plugin_manager=plugin_manager)
        if verbose:
            print("[Bootstrap] Health check started (60s)")
    except Exception as _ew_hc:
        print("[Bootstrap] Health check failed: " + str(_ew_hc))

    # G7: Auto backup every 6 hours
    try:
        _start_auto_backup(interval_sec=6 * 60 * 60, verbose=verbose)
        if verbose:
            print("[Bootstrap] Auto backup started (6h)")
    except Exception as _ew_ab:
        print("[Bootstrap] Auto backup failed: " + str(_ew_ab))

    return runtime_controller, runtime_log, notification_manager, event_bus


# ---------------------------------------------------------------------
# G2: Market auto-update
# ---------------------------------------------------------------------

def _start_market_auto_update(seller_service, interval_sec=3 * 60 * 60, verbose=True):
    import threading, time

    def _update():
        if verbose:
            print("[System] Автообновление рынка при запуске")
        _do_market_update(seller_service, verbose=verbose)
        while True:
            time.sleep(interval_sec)
            if verbose:
                print("[System] Плановое обновление рынка (каждые 3ч)")
            _do_market_update(seller_service, verbose=verbose)

    t = threading.Thread(target=_update, name="MarketAutoUpdate", daemon=True)
    t.start()
    return t


def _do_market_update(seller_service, verbose=True):
    try:
        _http_client.post("http://127.0.0.1:5000/api/market/heatmap", json={}, timeout=30)
        _http_client.get("http://127.0.0.1:5000/api/market/niches", timeout=15)
        _http_client.get("http://127.0.0.1:5000/api/market/competitors", timeout=15)
        _http_client.get("http://127.0.0.1:5000/api/market/ratings", timeout=15)
        if verbose:
            print("[System] Рынок обновлён")
    except Exception as e:
        print(f"[System] Ошибка обновления рынка: {e}")


# G7: Auto backup
def _start_auto_backup(interval_sec=6 * 60 * 60, verbose=True):
    import threading, time, shutil, os

    def _backup_loop():
        while True:
            time.sleep(interval_sec)
            try:
                _do_auto_backup(verbose=verbose)
            except Exception as e:
                print(f"[Backup] ERROR: {e}")

    t = threading.Thread(target=_backup_loop, name="AutoBackup", daemon=True)
    t.start()
    return t


def _do_auto_backup(verbose=True):
    src_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "configs",
        "plugins",
    )
    dst_dir = os.path.join(src_dir, "backups")
    os.makedirs(dst_dir, exist_ok=True)
    if not os.path.isdir(src_dir):
        return
    for fname in os.listdir(src_dir):
        if fname.endswith(".json"):
            src = os.path.join(src_dir, fname)
            dst = os.path.join(dst_dir, fname)
            try:
                shutil.copy2(src, dst)
            except Exception as e:
                print(f"[Backup] copy {fname} err: {e}")
    if verbose:
        print("[Backup] configs backed up")


# ---------------------------------------------------------------------
# G2: Health check every 60 seconds
# ---------------------------------------------------------------------

def _start_health_check(interval_sec=60, verbose=True, plugin_manager=None):
    import threading, time, logging

    logger = logging.getLogger("FunPayHUB.Health")

    def _notify_telegram(text):
        try:
            import os, json
            cfg_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "configs",
                "plugins",
                "telegram_notifier_plugin.json",
            )
            with open(cfg_path, encoding="utf-8") as f:
                tg_cfg = json.load(f)
            token = tg_cfg.get("bot_token", "")
            chat_id = tg_cfg.get("chat_id", "")
            if token and chat_id:
                _http_client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                    timeout=10,
                )
        except Exception:
            pass

    def _check(plugin_manager=None):
        while True:
            time.sleep(interval_sec)
            try:
                _run_health_check(verbose=verbose, plugin_manager=plugin_manager)
                logger.info("Health check tick completed")
            except Exception as e:
                logger.error(f"Health check tick failed: {e}")

    t = threading.Thread(target=_check, name="HealthCheck", daemon=True)
    t.start()
    return t


def _run_health_check(verbose=True, plugin_manager=None):
    import logging, time
    logger = logging.getLogger("FunPayHUB.Health")
    secrets = SecretsManager()

    suppliers = [
        ("gorgonaboosts", "https://api.gorgonaboost.xyz/stock", {"Authorization": f"Bearer {secrets.get_secret('GORGONABOOSTS_API_KEY', '')}"}),
        ("holdboost", "https://api.holdboost.store/v1/external/stock", {"X-API-Key": secrets.get_secret('HOLDBOOST_API_KEY', '')}),
        ("shopclaude", None, None),
        ("kosell", "https://api.kosell.store/products", {"Authorization": f"Bearer {secrets.get_secret('KOSELL_API_KEY', '')}"}),
    ]

    for name, url, headers in suppliers:
        if not url:
            continue
        max_attempts = 3
        attempt = 0
        ok = False
        last_error = ""
        while attempt < max_attempts:
            attempt += 1
            try:
                _http_client.get(url, headers=headers, timeout=10)
                ok = True
                break
            except HTTPClientError as e:
                last_error = f"HTTP {e.status_code}"
                logger.debug(f"Health check {name} attempt {attempt} failed: {e}")
                time.sleep(10)
            except Exception as e:
                last_error = str(e)
                logger.debug(f"Health check {name} attempt {attempt} failed: {e}")
                time.sleep(10)

        prev = _last_supplier_state.get(name, False)
        if ok and not prev:
            msg = f"✅ {name} снова работает"
            logger.info(msg)
            _notify_telegram(msg)
            _last_supplier_state[name] = True
            if plugin_manager:
                try:
                    if name == "gorgonaboosts":
                        plugin_manager.plugins.get("autodonate_plugin")._activate_supplier_lots("gorgonaboosts")
                    elif name == "holdboost":
                        plugin_manager.plugins.get("autodonate_plugin")._activate_supplier_lots("holdboost")
                    elif name == "kosell":
                        plugin_manager.plugins.get("autodonate_plugin")._activate_supplier_lots("kosell")
                except Exception:
                    pass
        elif not ok and prev:
            msg = f"❌ {name} недоступен ({last_error}) после {attempt} попыток"
            logger.warning(msg)
            _notify_telegram(msg)
            _last_supplier_state[name] = False
            if plugin_manager:
                try:
                    if name == "gorgonaboosts":
                        plugin_manager.plugins.get("autodonate_plugin")._deactivate_supplier_lots("gorgonaboosts")
                    elif name == "holdboost":
                        plugin_manager.plugins.get("autodonate_plugin")._deactivate_supplier_lots("holdboost")
                    elif name == "kosell":
                        plugin_manager.plugins.get("autodonate_plugin")._deactivate_supplier_lots("kosell")
                except Exception:
                    pass
        elif not ok and not prev:
            logger.warning(f"❌ {name} недоступен ({last_error}) после {attempt} попыток")
