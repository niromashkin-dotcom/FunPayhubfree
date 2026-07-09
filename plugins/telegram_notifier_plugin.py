"""
Telegram Notifier Plugin for FunPay Hub
Real Telegram Bot API integration with inline keyboard, polling, and deduplication
"""
import time
import threading
import json
from typing import Any, Optional, Dict, List
from plugins.plugin_base import PluginBase
from runtime.http_client import HTTPClient, HTTPClientError

DEFAULT_CONFIG = {
    "enabled": True,
    "bot_token": "",
    "chat_id": "",
    "notify_on": ["new_order", "order_completed", "order_failed", "low_balance", "error"],
    "min_interval_seconds": 30,
    "polling_interval_seconds": 2,
}

MENU_KEYBOARD = {
    "inline_keyboard": [
        [{"text": "📊 Ситуация на рынке", "callback_data": "market"}, {"text": "💰 Баланс", "callback_data": "balance"}],
        [{"text": "📋 Отчёт", "callback_data": "report"}, {"text": "🏥 Состояние системы", "callback_data": "health"}],
        [{"text": "🎯 Создать лоты", "callback_data": "generate_lots"}, {"text": "⏹ Снять все лоты", "callback_data": "deactivate_lots"}],
        [{"text": "🔄 Авто-создание ON/OFF", "callback_data": "toggle_auto_lots"}, {"text": "🧪 Симуляция", "callback_data": "simulate"}],
    ]
}


class TelegramNotifierPlugin(PluginBase):
    PLUGIN_INFO = {
        "name": "Telegram Notifier",
        "version": "2.0.0",
        "author": "FunPay Hub",
        "description": "Отправка уведомлений в Telegram через Bot API с inline-кнопками",
        "dependencies": [],
        "optional_dependencies": [],
    }

    execution_mode = "inprocess"

    CONFIG_SCHEMA = [
        {"key": "enabled", "type": "toggle", "label": "Включить плагин", "default": True},
        {"key": "bot_token", "type": "password", "label": "Telegram bot_token", "default": ""},
        {"key": "chat_id", "type": "text", "label": "Telegram chat_id", "default": ""},
        {"key": "min_interval_seconds", "type": "slider", "label": "Мин. интервал между сообщениями (сек)", "min": 5, "max": 300, "step": 5, "default": 30},
    ]

    def __init__(self, module_name, state_api, event_bus):
        super().__init__(module_name, state_api, event_bus)
        self.http_client = HTTPClient()
        self._last_sent = 0
        self._lock = threading.Lock()
        self._polling_thread = None
        self._polling_stop = threading.Event()
        self._last_update_id = 0

    def on_load(self):
        self.load_config(DEFAULT_CONFIG)
        if not self.config.get("bot_token"):
            self.config["bot_token"] = self.get_secret("TELEGRAM_NOTIFIER_BOT_TOKEN", "").strip()
        if not self.config.get("chat_id"):
            self.config["chat_id"] = self.get_secret("TELEGRAM_NOTIFIER_CHAT_ID", "").strip()

    def on_enable(self):
        self._start_polling()

    def on_disable(self):
        self._stop_polling()

    def on_unload(self):
        self._stop_polling()

    # ====================================================================
    # EVENT NOTIFICATIONS
    # ====================================================================

    def on_event(self, event):
        try:
            event_type = getattr(event, "type", None) or (event.get("type") if isinstance(event, dict) else None)
        except Exception:
            event_type = None

        events = self.config.get("notify_on", DEFAULT_CONFIG["notify_on"])
        if event_type not in events:
            return

        text = None
        if event_type == "new_order":
            title = event.get("title", "") if isinstance(event, dict) else getattr(event, "title", "")
            buyer = event.get("buyer", "") if isinstance(event, dict) else getattr(event, "buyer", "")
            text = f"🔔 Новый заказ: {title} от {buyer}"
        elif event_type == "order_completed":
            title = event.get("title", "") if isinstance(event, dict) else getattr(event, "title", "")
            text = f"✅ Заказ выполнен: {title}"
        elif event_type == "order_failed":
            msg = event.get("message", "Ошибка") if isinstance(event, dict) else getattr(event, "message", "Ошибка")
            text = f"❌ Ошибка: {msg}"
        elif event_type == "low_balance":
            balance = event.get("balance", "?") if isinstance(event, dict) else getattr(event, "balance", "?")
            text = f"⚠️ Низкий баланс: {balance}"
        elif event_type == "error":
            msg = event.get("message", "Unknown error") if isinstance(event, dict) else getattr(event, "message", "Unknown error")
            text = f"❌ Ошибка: {msg}"

        if text:
            self._send_telegram(text)

    # ====================================================================
    # TELEGRAM API
    # ====================================================================

    def _send_telegram(self, text, reply_markup=None, parse_mode="HTML", bypass_rate_limit=False):
        token = self.config.get("bot_token", "").strip()
        chat = self.config.get("chat_id", "").strip()
        if not token or not chat:
            return

        min_interval = int(self.config.get("min_interval_seconds", DEFAULT_CONFIG["min_interval_seconds"]))
        now = time.time()
        with self._lock:
            if not bypass_rate_limit and now - self._last_sent < min_interval:
                return
            self._last_sent = now

        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat,
                "text": text,
                "parse_mode": parse_mode,
            }
            if reply_markup:
                payload["reply_markup"] = json.dumps(reply_markup)
            data = self.http_client.post(url, json=payload, timeout=10)
            if not data.get("ok"):
                self._log(f"TG error: {data.get('description', str(data)[:200])}", level="warn")
        except HTTPClientError as e:
            self._log(f"TG error: {e.body[:200] if e.body else e.last_error}", level="warn")
        except Exception as e:
            self._log(f"TG send err: {e}", level="warn")

    def _answer_callback(self, callback_query_id, text=None, show_alert=False):
        token = self.config.get("bot_token", "").strip()
        if not token:
            return
        try:
            url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
            payload = {"callback_query_id": callback_query_id}
            if text:
                payload["text"] = text
            if show_alert:
                payload["show_alert"] = True
            self.http_client.post(url, json=payload, timeout=5)
        except Exception:
            pass

    def _edit_message(self, chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
        token = self.config.get("bot_token", "").strip()
        if not token:
            return
        try:
            url = f"https://api.telegram.org/bot{token}/editMessageText"
            payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": parse_mode,
            }
            if reply_markup:
                payload["reply_markup"] = json.dumps(reply_markup)
            self.http_client.post(url, json=payload, timeout=10)
        except Exception:
            pass

    # ====================================================================
    # POLLING
    # ====================================================================

    def _start_polling(self):
        if self._polling_thread and self._polling_thread.is_alive():
            return
        self._polling_stop.clear()
        self._polling_thread = threading.Thread(target=self._polling_loop, daemon=True, name="TG_Polling")
        self._polling_thread.start()
        self._log("Telegram polling started")

    def _stop_polling(self):
        self._polling_stop.set()
        if self._polling_thread and self._polling_thread.is_alive():
            self._polling_thread.join(timeout=3)

    def _polling_loop(self):
        token = self.config.get("bot_token", "").strip()
        if not token:
            return
        offset = self._last_update_id
        interval = int(self.config.get("polling_interval_seconds", DEFAULT_CONFIG["polling_interval_seconds"]))
        while not self._polling_stop.is_set():
            try:
                data = self.http_client.get(
                    f"https://api.telegram.org/bot{token}/getUpdates",
                    params={"offset": offset + 1, "timeout": 5, "allowed_updates": ["message", "callback_query"]},
                    timeout=10,
                )
                if not data.get("ok"):
                    time.sleep(interval)
                    continue
                updates = data.get("result", [])
                for upd in updates:
                    offset = max(offset, upd.get("update_id", 0))
                    self._handle_update(upd)
            except Exception:
                pass
            time.sleep(interval)
        self._log("Telegram polling stopped")

    def _handle_update(self, upd):
        if "message" in upd:
            msg = upd["message"]
            text = (msg.get("text") or "").strip()
            chat_id = msg.get("chat", {}).get("id")
            if not chat_id or not text:
                return
            if text.startswith("/start") or text == "/menu":
                self._send_main_menu(chat_id)
        elif "callback_query" in upd:
            cb = upd["callback_query"]
            data = cb.get("data", "")
            chat_id = cb.get("message", {}).get("chat", {}).get("id")
            message_id = cb.get("message", {}).get("message_id")
            callback_id = cb.get("id")
            if not chat_id:
                return
            self._answer_callback(callback_id, "⏳ Обрабатываю...")
            processing_msg = "⏳ Обрабатываю..."
            if message_id:
                self._edit_message(chat_id, message_id, processing_msg, None)
            else:
                self._send_telegram(processing_msg, None, bypass_rate_limit=True)
            response = self._handle_callback(data)
            if message_id:
                self._edit_message(chat_id, message_id, response, MENU_KEYBOARD)
            else:
                self._send_telegram(response, MENU_KEYBOARD, bypass_rate_limit=True)

    def _handle_callback(self, data: str) -> str:
        try:
            if data == "market":
                return self._build_market_report()
            elif data == "balance":
                return self._build_balance_report()
            elif data == "report":
                return self._build_sales_report()
            elif data == "health":
                return self._build_health_report()
            elif data == "generate_lots":
                return self._handle_generate_lots()
            elif data == "deactivate_lots":
                return self._handle_deactivate_lots()
            elif data == "toggle_auto_lots":
                return self._handle_toggle_auto_lots()
            elif data == "simulate":
                return self._handle_simulate()
            elif data == "start_system":
                return "🚀 Функция запуска системы в разработке.\n\n⏳ Ожидайте обновления!"
            elif data == "stop_system":
                return "⏹ Функция остановки системы в разработке.\n\n⏳ Ожидайте обновления!"
            return "❓ Неизвестная команда"
        except Exception as e:
            return f"❌ Ошибка: {e}"

    def _handle_generate_lots(self) -> str:
        try:
            j = self.http_client.post("http://127.0.0.1:5000/api/lots/generate", json={"dry_run": False}, timeout=120)
            if j.get("ok"):
                lots = j.get("lots", [])
                autosmm = sum(1 for l in lots if l.get("marker", "").startswith("[AS#"))
                gorgona_1m = sum(1 for l in lots if "[GB#1]" in l.get("marker", ""))
                gorgona_3m = sum(1 for l in lots if "[GB#3]" in l.get("marker", ""))
                holdboost_1m = sum(1 for l in lots if "[HB#1]" in l.get("marker", ""))
                holdboost_3m = sum(1 for l in lots if "[HB#3]" in l.get("marker", ""))
                kosell = sum(1 for l in lots if "[KS#" in l.get("marker", ""))
                total = len(lots)
                return (
                    f"🎯 Создано лотов: {total}\n\n"
                    f"• AutoSMM: {autosmm} шт (основных)\n"
                    f"• GorgonaBoosts 1м: {gorgona_1m} шт\n"
                    f"• GorgonaBoosts 3м: {gorgona_3m} шт\n"
                    f"• HoldBoost 1м: {holdboost_1m} шт\n"
                    f"• HoldBoost 3м: {holdboost_3m} шт\n"
                    f"• Kosell: {kosell} шт\n\n"
                    f"Всего: {total} лотов"
                )
            return f"❌ Ошибка генерации: {j.get('error', 'unknown')}"
        except HTTPClientError as e:
            return f"❌ Ошибка генерации: {e.body[:200] if e.body else e.last_error}"
        except Exception as e:
            return f"❌ Ошибка: {e}"

    def _handle_deactivate_lots(self) -> str:
        try:
            j = self.http_client.post("http://127.0.0.1:5000/api/dev/lots/deactivate_all", json={}, timeout=30)
            count = j.get("deactivated", 0)
            return f"⏹ Снято лотов: {count} шт"
        except Exception as e:
            return f"❌ Ошибка: {e}"

    def _handle_toggle_auto_lots(self) -> str:
        try:
            j = self.http_client.post("http://127.0.0.1:5000/api/system/settings/auto_lots", json={}, timeout=10)
            state = j.get("auto_lots_enabled", False)
            return f"🔄 Авто-создание лотов: {'ВКЛ' if state else 'ВЫКЛ'}"
        except Exception as e:
            return f"❌ Ошибка: {e}"

    def _handle_simulate(self) -> str:
        try:
            j = self.http_client.post("http://127.0.0.1:5000/api/system/simulate", json={}, timeout=180)
            report = j.get("report", "Нет данных")
            dry_run_off = j.get("dry_run_off", False)
            msg = f"🧪 РЕЗУЛЬТАТЫ СИМУЛЯЦИИ\n\n{report}"
            if dry_run_off:
                msg += "\n\n✅ DRY_RUN автоматически снят!"
            return msg[:4000]
        except Exception as e:
            return f"❌ Ошибка симуляции: {e}"

    def _send_main_menu(self, chat_id):
        text = (
            "👋 Привет! Я бот FunPay Hub.\n\n"
            "Выберите действие:"
        )
        self._send_telegram(text, reply_markup=MENU_KEYBOARD)

    # ====================================================================
    # REPORTS
    # ====================================================================

    def _api_get(self, path: str) -> Any:
        try:
            return self.http_client.get(f"http://127.0.0.1:5000{path}", timeout=15)
        except Exception:
            pass
        return None

    def _build_market_report(self) -> str:
        try:
            heatmap = self.http_client.post("http://127.0.0.1:5000/api/market/heatmap", json={}, timeout=30) or {}
            
            niches = self.http_client.get("http://127.0.0.1:5000/api/market/niches", timeout=15) or {}
            
            competitors = self.http_client.get("http://127.0.0.1:5000/api/market/competitors", timeout=15) or {}
            
            niche_list = niches.get("niches", []) if isinstance(niches, dict) else []
            comp_list = competitors.get("competitors", []) if isinstance(competitors, dict) else []
            
            if not niche_list and not comp_list:
                return "📊 Ситуация на рынке:\n\n⏳ Обновляю рынок... Подождите 30 сек"
            
            lines = ["📊 Ситуация на рынке:", ""]
            
            if niche_list:
                top_profit = sorted(niche_list, key=lambda x: x.get("margin", 0), reverse=True)[:5]
                lines.append("🔥 Топ-5 прибыльных:")
                for i, n in enumerate(top_profit, 1):
                    lines.append(f"{i}. {n.get('name', '—')} — маржа {n.get('margin', '?')}%")
                lines.append("")
                
                top_active = sorted(niche_list, key=lambda x: x.get("competition", 0), reverse=True)[:5]
                lines.append("⚡ Топ-5 активных:")
                for i, n in enumerate(top_active, 1):
                    lines.append(f"{i}. {n.get('name', '—')} — {n.get('competition', '?')} продавцов")
                lines.append("")
                
                top_rated = sorted(niche_list, key=lambda x: x.get("score", 0), reverse=True)[:5]
                lines.append("🏆 Топ-5 лучших:")
                for i, n in enumerate(top_rated, 1):
                    lines.append(f"{i}. {n.get('name', '—')} — оценка {n.get('score', '?')}")
            else:
                lines.append("⚠️ Ниши ещё не отсканированы")
            
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Ошибка получения данных: {e}"

    def _build_balance_report(self) -> str:
        data = self._api_get("/api/seller/balance/full")
        if not data:
            return "💰 Баланс:\n\n⚠️ Данные временно недоступны."
        balance = data.get("balance", {})
        total = balance.get("total_rub", 0)
        updated = data.get("updated_at", 0)
        updated_str = time.strftime("%d.%m.%Y %H:%M", time.localtime(updated)) if updated else "—"
        lines = [f"💰 Баланс: {total:.2f} ₽", f"🕐 Обновлено: {updated_str}", ""]
        history = data.get("history", [])
        if history:
            today = time.strftime("%Y-%m-%d")
            today_in = sum(1 for h in history if h.get("date", "").startswith(today))
            lines.append(f"📈 Поступлений сегодня: +{today_in} операций")
        return "\n".join(lines)

    def _build_sales_report(self) -> str:
        sales = self._api_get("/api/seller/sales")
        orders = self._api_get("/api/seller/orders")
        lines = ["📋 Отчёт за сегодня:", ""]
        if sales:
            stats = sales.get("stats", {})
            day_sum = stats.get("day_sum", 0)
            day_count = stats.get("day_count", 0)
            lines.append(f"🛒 Заказов: {day_count}")
            lines.append(f"💰 Выручка: {day_sum:.2f} ₽")
        if orders:
            order_list = orders.get("orders", []) if isinstance(orders, dict) else []
            lines.append(f"📦 Всего заказов: {len(order_list)}")
        return "\n".join(lines) if len(lines) > 2 else "📋 Отчёт:\n\n⚠️ Данные временно недоступны."

    def _build_health_report(self) -> str:
        health = self._api_get("/api/system/health")
        if not health:
            return "🏥 Система:\n\n⚠️ Данные временно недоступны."
        status = health.get("status", "unknown")
        issues = health.get("issues", [])
        plugins_count = health.get("plugins_count", 7)
        lines = ["🏥 Система:", f"✅ Статус: {status}", f"✅ Плагинов: {plugins_count} активных"]
        if issues:
            lines.append(f"❌ Ошибок: {len(issues)}")
            for issue in issues[:3]:
                lines.append(f"  • {issue}")
        else:
            lines.append("✅ Ошибок: 0")
        return "\n".join(lines)

    # ====================================================================
    # HELPERS
    # ====================================================================

    def _log(self, message, level="info"):
        print(f"[TelegramNotifierPlugin] {message}")

    def action_test(self, payload=None):
        self._send_main_menu(self.config.get("chat_id", ""))
        return {
            "ok": True,
            "message": "Меню отправлено в Telegram",
        }
