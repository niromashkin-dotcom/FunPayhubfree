# plugins/autobump_plugin.py
"""
AutoBump Plugin
Periodically raises (bumps) lots in selected FunPay categories
so they stay on top and get more views = more sales.

Configuration (configs/plugins/autobump_plugin.json):
    enabled: bool                — plugin on/off (managed by manager)
    interval_minutes: int        — how often to check (default 30)
    bump_interval_minutes: int   — min minutes between bumps of same category (default 240, ~FunPay limit)
    categories: list[int]        — category IDs to bump (empty = all your categories)
    only_active_hours: bool      — restrict to active_hours_start..end
    active_hours_start: int      — 0-23 (default 9)
    active_hours_end: int        — 0-23 (default 23)
    max_bumps_per_hour: int      — safety throttle (default 10)
    dry_run: bool                — log what would happen but don't actually bump
"""
import time
import threading
import json
from datetime import datetime, timedelta
from collections import deque
from pathlib import Path

from plugins.plugin_base import PluginBase
from runtime.http_client import HTTPClient, HTTPClientError


DEFAULT_CONFIG = {
    "enabled":              False,
    "interval_minutes":     30,
    "bump_interval_minutes": 240,
    "categories":           [],          # empty list = all detected categories
    "only_active_hours":    False,
    "active_hours_start":   9,
    "active_hours_end":     23,
    "max_bumps_per_hour":   10,
    "dry_run":              False,
}


class AutoBumpPlugin(PluginBase):
    PLUGIN_INFO = {
        "name":        "AutoBump",
        "version":     "1.0.0",
        "author":      "FunPay Hub",
        "description": "Автоматическое поднятие лотов на FunPay по расписанию",
        "dependencies": [],
        "optional_dependencies": [],
    }

    execution_mode = "inprocess"

    CONFIG_SCHEMA = [
        {
            "key": "enabled",
            "type": "toggle",
            "label": "Включить автоподнятие",
            "hint": "Главный переключатель плагина",
            "default": False,
        },
        {
            "key": "interval_minutes",
            "type": "slider",
            "label": "Интервал проверки",
            "hint": "Как часто плагин просыпается и проверяет нужно ли бампить",
            "min": 5, "max": 240, "step": 5,
            "default": 30,
            "suffix": " мин",
        },
        {
            "key": "bump_interval_minutes",
            "type": "slider",
            "label": "Минимальный интервал между бампами одной категории",
            "hint": "FunPay ограничивает: ~4 часа на категорию. Меньше нельзя.",
            "min": 60, "max": 720, "step": 30,
            "default": 240,
            "suffix": " мин",
        },
        {
            "key": "categories",
            "type": "categories",
            "label": "Категории для бампа",
            "hint": "Пусто = автоматически все твои категории",
            "default": [],
        },
        {
            "key": "only_active_hours",
            "type": "toggle",
            "label": "Работать только в активные часы",
            "default": False,
        },
        {
            "key": "active_hours_start",
            "type": "slider",
            "label": "Начало активных часов",
            "min": 0, "max": 23, "step": 1,
            "default": 9,
            "suffix": ":00",
        },
        {
            "key": "active_hours_end",
            "type": "slider",
            "label": "Конец активных часов",
            "min": 0, "max": 23, "step": 1,
            "default": 23,
            "suffix": ":00",
        },
        {
            "key": "max_bumps_per_hour",
            "type": "slider",
            "label": "Лимит бампов в час",
            "hint": "Защита от спама. FunPay может банить за слишком частые запросы.",
            "min": 1, "max": 30, "step": 1,
            "default": 10,
        },
        {
            "key": "dry_run",
            "type": "toggle",
            "label": "DRY-RUN режим (только логировать, не бампить)",
            "hint": "Включи когда тестируешь. Выключи когда готов к реальному бампу.",
            "default": True,
        },
    ]

    def __init__(self, module_name: str, state_api, event_bus):
        super().__init__(module_name, state_api, event_bus)
        self.http_client = HTTPClient()
        self._thread = None
        self._stop_event = threading.Event()
        self._last_bump_per_cat = {}     # cat_id -> timestamp of last bump
        self._bump_history = deque(maxlen=200)  # recent bump events
        self._stats = {
            "total_bumps":   0,
            "total_skipped": 0,
            "total_errors":  0,
            "last_run":      None,
            "last_bump":     None,
        }

    # ---------------------- LIFECYCLE ----------------------

    def on_load(self):
        self.load_config(DEFAULT_CONFIG)
        self._log("Загружен. Конфиг: " + json.dumps(self.config, ensure_ascii=False))

    def on_enable(self):
        if self._thread and self._thread.is_alive():
            self._log("Поток уже запущен, пропускаю")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="AutoBumpLoop")
        self._thread.start()
        self._log(f"Запущен. Интервал проверки: {self.config.get('interval_minutes')} мин")

    def on_disable(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._log("Остановлен")

    def on_unload(self):
        self.on_disable()

    def on_error(self, error):
        self._log(f"Ошибка: {error}", level="error")
        self._stats["total_errors"] += 1

    # ---------------------- MAIN LOOP ----------------------

    def _loop(self):
        """Main worker loop — checks every interval_minutes."""
        # Small delay before first run (let app fully initialize)
        time.sleep(5)

        while not self._stop_event.is_set():
            try:
                self._run_once()
            except Exception as e:
                self._log(f"Ошибка в цикле: {e}", level="error")
                self._stats["total_errors"] += 1

            # Sleep with periodic wake-ups so we react to stop quickly
            interval_sec = max(60, int(self.config.get("interval_minutes", 30)) * 60)
            for _ in range(interval_sec):
                if self._stop_event.is_set():
                    return
                time.sleep(1)

    def _run_once(self):
        """One pass of bumping."""
        self._stats["last_run"] = datetime.now().isoformat(timespec="seconds")

        # Active hours check
        if self.config.get("only_active_hours"):
            now_h = datetime.now().hour
            h_start = int(self.config.get("active_hours_start", 9))
            h_end   = int(self.config.get("active_hours_end", 23))
            in_range = (h_start <= now_h < h_end) if h_start < h_end \
                       else (now_h >= h_start or now_h < h_end)
            if not in_range:
                self._log(f"Вне активных часов ({h_start}-{h_end}), пропуск")
                return

        # Rate limiting per hour
        hour_ago = time.time() - 3600
        recent = sum(1 for ts, _, _ in self._bump_history if ts > hour_ago)
        max_per_hour = int(self.config.get("max_bumps_per_hour", 10))
        if recent >= max_per_hour:
            self._log(f"Лимит {max_per_hour}/час достигнут ({recent}), пропуск")
            return

        # Get categories to bump
        cats = self._get_target_categories()
        if not cats:
            self._log("Нет категорий для поднятия")
            return

        bump_interval = int(self.config.get("bump_interval_minutes", 240)) * 60
        now = time.time()

        for cat_id in cats:
            if self._stop_event.is_set():
                return

            last = self._last_bump_per_cat.get(cat_id, 0)
            if last > 0 and (now - last) < bump_interval:
                wait_min = int((bump_interval - (now - last)) / 60)
                self._stats["total_skipped"] += 1
                continue

            ok, msg = self._bump_category(cat_id)
            if ok:
                self._last_bump_per_cat[cat_id] = now
                self._stats["total_bumps"] += 1
                self._stats["last_bump"] = datetime.now().isoformat(timespec="seconds")
                self._bump_history.append((now, cat_id, "ok"))
            else:
                self._stats["total_errors"] += 1
                self._bump_history.append((now, cat_id, msg or "fail"))

            time.sleep(2)  # tiny gap between requests

    # ---------------------- HELPERS ----------------------

    def _get_target_categories(self):
        """Return list of category IDs to bump.
        If config.categories is empty -> auto-detect from lots."""
        configured = self.config.get("categories") or []
        if configured:
            return [int(c) for c in configured if str(c).strip().isdigit()]

        # Auto-detect from active lots
        try:
            data = self.http_client.get("http://127.0.0.1:5000/api/seller/lots", timeout=10)
            lots = data.get("lots") if isinstance(data, dict) else data
            if not isinstance(lots, list):
                return []
            cats = set()
            for lot in lots:
                cid = lot.get("category_id") or lot.get("subcategory_id") or lot.get("cat_id")
                if cid:
                    try:
                        cats.add(int(cid))
                    except (ValueError, TypeError):
                        pass
            return list(cats)
        except Exception as e:
            self._log(f"Не удалось получить лоты: {e}", level="warn")
            return []

    def _bump_category(self, cat_id):
        """Call /api/seller/categories/<id>/raise."""
        if self.config.get("dry_run"):
            self._log(f"[DRY-RUN] Бамп категории {cat_id}")
            return True, "dry-run"

        try:
            self.http_client.post(
                f"http://127.0.0.1:5000/api/seller/categories/{cat_id}/raise",
                headers={"Content-Type": "application/json"},
                json={},
                timeout=15
            )
            self._log(f"Категория {cat_id} поднята")
            return True, None
        except HTTPClientError as e:
            msg = f"HTTP error: {e}"
            self._log(f"Ошибка бампа {cat_id}: {msg}", level="warn")
            return False, msg
        except Exception as e:
            self._log(f"Исключение при бампе {cat_id}: {e}", level="error")
            return False, str(e)

    def _log(self, message, level="info"):
        """Log via event_bus if available, else print."""
        prefix = f"[AutoBump] {message}"
        try:
            if self.event_bus and hasattr(self.event_bus, "emit"):
                self.event_bus.emit("plugin_log", {
                    "plugin": self.module_name,
                    "level":  level,
                    "message": message,
                    "ts": int(time.time())
                })
        except Exception:
            pass
        print(prefix)

    # ---------------------- PUBLIC GETTERS (for UI) ----------------------

    # ---------------------- ACTIONS (called from UI) ----------------------

    def action_test_bump(self, payload):
        """Manually trigger one bump pass — for testing from UI."""
        try:
            self._log("=== ACTION: Test bump triggered from UI ===")
            self._run_once()
            return {
                "ok": True,
                "stats": self._stats,
                "message": "Тестовый прогон выполнен. Смотри логи."
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def action_reset_stats(self, payload):
        """Reset statistics counters."""
        self._stats = {
            "total_bumps":   0,
            "total_skipped": 0,
            "total_errors":  0,
            "last_run":      None,
            "last_bump":     None,
        }
        self._bump_history.clear()
        self._last_bump_per_cat.clear()
        return {"ok": True}

    def get_logs(self):
        """Return recent bump events as log lines for UI."""
        import datetime as _dt
        out = []
        for ts, cat_id, result in list(self._bump_history)[-30:]:
            tstr = _dt.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
            out.append({
                "time": tstr,
                "level": "info" if result == "ok" else "warn",
                "message": f"Категория {cat_id}: {result}"
            })
        return out

    def get_stats(self):
        return {
            **self._stats,
            "recent_bumps": [
                {"ts": ts, "category": cid, "result": res}
                for ts, cid, res in list(self._bump_history)[-20:]
            ],
            "thread_alive": bool(self._thread and self._thread.is_alive()),
        }


# Optional: expose a way to query stats from outside
def get_plugin_stats(plugin_manager):
    p = plugin_manager.plugins.get("autobump_plugin")
    if not p:
        return None
    return p.get_stats() if hasattr(p, "get_stats") else None