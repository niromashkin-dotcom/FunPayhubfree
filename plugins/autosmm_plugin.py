""" 
Auto SMM Plugin for FunPay Hub
Integration with Twiboost API (https://twiboost.com)
"""
import os
import time
import threading
import json
import re
from collections import deque
from pathlib import Path
from urllib.parse import urlparse

from plugins.plugin_base import PluginBase
from runtime.http_client import HTTPClient, HTTPClientError
from runtime.order_tracker import get_supplier_order_registry

try:
    from runtime.ttl_cache import TTLSet
except Exception:
    TTLSet = None

try:
    from expiringdict import ExpiringDict
except Exception:
    ExpiringDict = None

# Cross-plugin chat lock (prevents autoreply from interfering with active SMM dialog)
try:
    from runtime.autoreply_engine import chat_lock_registry
except Exception:
    chat_lock_registry = None

try:
    from runtime.plugin_markers import has_marker_for
except Exception:
    def has_marker_for(text, code): return None

# ====================================================================
# DEFAULTS
# ====================================================================

DEFAULT_CONFIG = {
    "enabled": False,
    "api_key": "",
    "api_url": "https://twiboost.com/api/v2",
    "looksmm_api_key": "",
    "looksmm_api_url": "https://looksmm.ru/api/v2",
    "use_looksmm_if_cheaper": True,
    "ask_confirmation": True,
    "auto_refund": True,
    "dry_run": True,
    "check_interval_minutes": 5,
    "min_balance_alert": 50,
    "test_mode": False,
    "test_chat_id": "",
    "lot_mapping": {},
    "allowed_domains": [
        "vk.com", "vk.ru",
        "t.me", "telegram.me", "telegram.org",
        "instagram.com", "instagr.am",
        "tiktok.com",
        "youtube.com", "youtu.be",
        "twitter.com", "x.com",
        "twitch.tv",
        "facebook.com", "fb.com",
        "discord.gg", "discord.com",
        "ok.ru", "odnoklassniki.ru",
        "boosty.to",
    ],
    "msg_ask_link": "🎉 Спасибо за заказ! Мы уже начали работу.\n\n📎 Пожалуйста, пришлите ссылку на канал/группу, куда нужно выполнить услугу.\n\n⏱ Время выполнения: 1-24 часа.",
    "msg_invalid_link": "⚠️ Ссылка не подходит. Поддерживаемые сайты:\n{domains}\n\nПришлите корректную ссылку.",
    "msg_confirm": "✅ Отлично! Проверьте данные:\n🔗 Ссылка: {link}\n📊 Услуга: {service_name}\n🔢 Количество: {quantity}\n\nНапишите «да» для подтверждения.",
    "msg_order_created": "🚀 Заказ принят в работу!\n\n📋 ID заказа: {twi_id}\n⏱ Ориентировочное время: 1-24 часа.\n\nМы сообщим о готовности! 💙",
    "msg_provider_done": "📦 Отправка выполнена!\n\n⏰ Отображение займёт 30 минут — 1 час.\nКак только всё отобразится, попрошу подтвердить заказ.",
    "msg_ready_to_confirm": "🎉 Заказ полностью выполнен!\n\n📊 Услуга: {service_name}\n✅ Выдано: {delivered}/{quantity}\n\n🙏 Пожалуйста, подтвердите выполнение заказа и оставьте 5 звёзд ⭐⭐⭐⭐⭐",
    "review_reply_5star": "💙 Огромное спасибо за ваш отзыв! Мы стараемся для вас! ⭐⭐⭐⭐⭐ Ждём вас снова! 🎉",
    "review_reply_4star": "🙏 Спасибо за отзыв! Постараемся стать ещё лучше! 💪 Рады будем видеть вас снова! 💙",
    "review_reply_1to3": "😔 Нам очень жаль, что вам не понравилось. Напишите нам — мы обязательно всё решим и компенсируем! 🙏💙",
    "msg_thanks_after_confirm": "🙏 Спасибо за подтверждение заказа!\n\nБудем очень рады вашему отзыву ⭐⭐⭐⭐⭐\nЭто очень помогает развиваться 💎",
    "msg_completed": "🎊 Готово! Ваш заказ выполнен!\n\n✅ Проверьте результат и подтвердите заказ на FunPay.\n⭐ Будем рады вашему отзыву!\n\nСпасибо что выбрали нас! 💙",
    "msg_partial": "⚠️ Заказ выполнен частично:\n\n📊 Услуга: {service_name}\n✅ Выдано: {delivered} из {quantity}\n💰 Возвращаем разницу через возврат заказа.",
    "msg_error": "😔 К сожалению, произошла техническая ошибка.\n\n🔄 Возврат средств будет произведён автоматически.\n\nПриносим извинения за неудобства! 🙏",
    "msg_no_mapping": "⚠️ Этот лот пока не настроен в системе. Продавец будет уведомлён.",
    "msg_refund_trigger": "возврат,вернуть,рефанд,refund,отмена",
    "msg_refund_response": "📋 Ваш запрос на возврат принят!\n\n⏱ Обработка в течение 24 часов.\n📩 Мы сообщим о результате.\n\nСпасибо за обращение! 🙏",
}

class AutoSMMPlugin(PluginBase):
    PLUGIN_INFO = {
        "name": "Auto SMM",
        "version": "1.0.0",
        "author": "FunPay Hub",
        "description": "Автоматическая обработка SMM-заказов через Twiboost API",
        "dependencies": [],
        "optional_dependencies": [],
    }

    execution_mode = "inprocess"

    CONFIG_SCHEMA = [
        {"key": "enabled", "type": "toggle", "label": "Включить плагин", "default": False},
        {'key': 'test_mode', 'type': 'toggle', 'label': '🧪 TEST режим', 'default': False,
         'hint': 'Реагировать только на test_chat_id'},
        {'key': 'test_chat_id', 'type': 'text', 'label': '🧪 Tester chat_id', 'default': '',
         'hint': 'Формат: users-XXX-YYY'},
        {"key": "api_key", "type": "password", "label": "API ключ Twiboost",
         "hint": "Личный кабинет Twiboost -> API",
         "default": ""},
        {"key": "ask_confirmation", "type": "toggle",
         "label": "Запрашивать подтверждение 'да' перед заказом",
         "hint": "Безопасно (защита от опечаток покупателя), но медленнее",
         "default": True},
        {"key": "auto_refund", "type": "toggle",
         "label": "Авто-возврат при ошибке",
         "default": True},
        {"key": "dry_run", "type": "toggle",
         "label": "DRY-RUN режим (тест без реальных заказов)",
         "hint": "ВКЛЮЧИ это для проверки на первых заказах",
         "default": True},
        {"key": "check_interval_minutes", "type": "slider",
         "label": "Интервал проверки статуса заказов",
         "min": 1, "max": 60, "step": 1, "default": 5, "suffix": " мин"},
        {"key": "min_balance_alert", "type": "slider",
         "label": "Уведомлять если баланс ниже",
         "min": 10, "max": 1000, "step": 10, "default": 50, "suffix": " (в валюте Twiboost)"},
        {"key": "msg_ask_link", "type": "textarea", "rows": 4,
         "label": "Сообщение: запрос ссылки",
         "default": DEFAULT_CONFIG["msg_ask_link"]},
        {"key": "msg_confirm", "type": "textarea", "rows": 6,
         "label": "Сообщение: подтверждение",
         "hint": "Доступные плейсхолдеры: {link} {service_name} {quantity}",
         "default": DEFAULT_CONFIG["msg_confirm"]},
        {"key": "msg_order_created", "type": "textarea", "rows": 4,
         "label": "Сообщение: заказ создан",
         "hint": "Плейсхолдеры: {twi_id} {service_name} {quantity}",
         "default": DEFAULT_CONFIG["msg_order_created"]},
        {"key": "lot_mapping", "type": "lot_mapping",
         "label": "Привязка лотов FunPay -> услуг Twiboost",
         "hint": "Какому лоту FunPay соответствует какая услуга Twiboost и сколько единиц заказывать",
         "default": {}},
        {"key": "msg_completed", "type": "textarea", "rows": 4,
         "label": "Сообщение: заказ выполнен",
         "hint": "Плейсхолдеры: {service_name} {quantity} {delivered}",
         "default": DEFAULT_CONFIG["msg_completed"]},
    ]

    def __init__(self, module_name, state_api, event_bus):
        super().__init__(module_name, state_api, event_bus)
        self.http_client = HTTPClient()
        from bot.config import get_hub_url
        self.hub_url = get_hub_url()

        self._stop = threading.Event()
        self._worker = None
        self._lock = threading.RLock()
        self._dialogs = {}
        self._processed_orders = {}  # order_id -> timestamp for dedup (msg dedup kept)
        self._processed_orders_ttl = TTLSet(ttl_seconds=60) if TTLSet else set()
        self._processed_reviews = ExpiringDict(max_len=1000, max_age_seconds=24*60*60) if ExpiringDict else {}
        self._chat_locks = {}
        self._chat_locks_lock = threading.Lock()
        self._active = {}
        self._stats = {
            "total_orders": 0,
            "completed": 0,
            "partial": 0,
            "failed": 0,
            "refunded": 0,
            "balance": None,
            "last_check": None,
            "last_error": None,
        }
        self._log_buffer = deque(maxlen=50)
        self._data_dir = self._get_data_dir()
        self._orders_file = self._data_dir / "active_orders.json"
        self._load_active_orders()

    def _get_chat_lock(self, chat_id):
        with self._chat_locks_lock:
            if chat_id not in self._chat_locks:
                self._chat_locks[chat_id] = threading.Lock()
            return self._chat_locks[chat_id]

    # ====================================================================
    # LIFECYCLE
    # ====================================================================

    def on_load(self):
        self.load_config(DEFAULT_CONFIG)
        if not self.config.get("api_key"):
            self.config["api_key"] = self.get_secret("AUTOSMM_API_KEY", "")
        if not self.config.get("looksmm_api_key"):
            self.config["looksmm_api_key"] = self.get_secret("LOOKSMM_API_KEY", "")
        self._log("Плагин загружен")

    def on_enable(self):
        if self._worker and self._worker.is_alive():
            self._log("Воркер уже запущен")
            return
        self._stop.clear()
        self._worker = threading.Thread(target=self._loop, daemon=True, name="AutoSMMWorker")
        self._worker.start()
        self._log(f"Запущен. Интервал проверки: {self.config.get('check_interval_minutes', 5)} мин")
        threading.Thread(target=self._check_balance, daemon=True).start()

    def on_disable(self):
        self._stop.set()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=5)
        self._save_active_orders()
        self._log("Остановлен")

    def on_unload(self):
        self.on_disable()

    def on_error(self, err):
        self._log(f"Ошибка: {err}", level="error")
        self._stats["last_error"] = str(err)[:200]

    # ====================================================================
    # MAIN BACKGROUND LOOP
    # ====================================================================

    def _loop(self):
        time.sleep(5)
        last_balance_check = 0
        while not self._stop.is_set():
            try:
                self._check_active_orders()
                if time.time() - last_balance_check > 900:
                    self._check_balance(); self._check_balance_and_deactivate(); self._check_balance_and_deactivate()
                    last_balance_check = time.time()
            except Exception as e:
                self._log(f"Ошибка в воркере: {e}", level="error")
            interval = max(60, int(self.config.get("check_interval_minutes", 5)) * 60)
            for _ in range(interval):
                if self._stop.is_set():
                    return
                time.sleep(1)

    # ====================================================================
    # CHECK ACTIVE ORDERS
    # ====================================================================

    def _check_active_orders(self):
        with self._lock:
            order_ids = list(self._active.keys())
        if not order_ids:
            self._stats["last_check"] = self._now_str()
            return
        ids_str = ",".join(str(i) for i in order_ids[:50])
        api_key = self.config.get("api_key", "").strip()
        if not api_key:
            return
        try:
            url = self.config.get("api_url", DEFAULT_CONFIG["api_url"])
            data = self.http_client.get(url, params={
                "action": "status",
                "orders": ids_str,
                "key": api_key,
            }, timeout=20)
        except HTTPClientError as e:
            self._log(f"Не удалось получить статусы: HTTP {e.status_code}", level="warn")
            return
        except Exception as e:
            self._log(f"Ошибка проверки статусов: {e}", level="warn")
            return
        self._stats["last_check"] = self._now_str()
        if not isinstance(data, dict):
            return
        for tid_str, status_obj in data.items():
            try:
                tid = int(tid_str)
            except (ValueError, TypeError):
                continue
            with self._lock:
                order_data = self._active.get(tid)
            if not order_data:
                continue
            if isinstance(status_obj, str):
                self._log(f"Заказ #{tid}: {status_obj}", level="warn")
                continue
            if not isinstance(status_obj, dict):
                continue
            status = (status_obj.get("status") or "").strip()
            remains = status_obj.get("remains")
            try:
                remains = int(remains) if remains is not None else 0
            except (ValueError, TypeError):
                remains = 0
            quantity = order_data.get("quantity", 0)
            delivered = max(0, quantity - remains)
            if status == "Completed":
                self._on_order_completed(tid, order_data, delivered, quantity)
            elif status == "Partial":
                self._on_order_partial(tid, order_data, delivered, quantity)
            elif status in ("Canceled", "Fail"):
                self._on_order_failed(tid, order_data, status)

    def _on_order_completed(self, tid, order_data, delivered, quantity):
        chat_id = order_data.get("chat_id")
        try:
            if chat_lock_registry and chat_id:
                chat_lock_registry.release(chat_id, owner="autosmm")
        except Exception:
            pass
        service_name = order_data.get("service_name", "услуга")
        msg = self.config.get("msg_completed", DEFAULT_CONFIG["msg_completed"]).format(
            service_name=service_name,
            quantity=quantity,
            delivered=delivered,
        )
        if chat_id:
            self._send_message(chat_id, msg)
        self._stats["completed"] += 1
        self._log(f"✅ Заказ #{tid} выполнен ({delivered}/{quantity})")
        with self._lock:
            self._active.pop(tid, None)
        self._save_active_orders()

    def _on_order_partial(self, tid, order_data, delivered, quantity):
        chat_id = order_data.get("chat_id")
        try:
            if chat_lock_registry and chat_id:
                chat_lock_registry.release(chat_id, owner="autosmm")
        except Exception:
            pass
        service_name = order_data.get("service_name", "услуга")
        msg = self.config.get("msg_partial", DEFAULT_CONFIG["msg_partial"]).format(
            service_name=service_name,
            quantity=quantity,
            delivered=delivered,
        )
        if chat_id:
            self._send_message(chat_id, msg)
        self._stats["partial"] += 1
        self._log(f"⚠️ Заказ #{tid} частично выполнен ({delivered}/{quantity})")
        with self._lock:
            self._active.pop(tid, None)
        self._save_active_orders()

    def _on_order_failed(self, tid, order_data, status):
        chat_id = order_data.get("chat_id")
        try:
            if chat_lock_registry and chat_id:
                chat_lock_registry.release(chat_id, owner="autosmm")
        except Exception:
            pass
        fp_order_id = order_data.get("fp_order_id")
        msg = self.config.get("msg_error", DEFAULT_CONFIG["msg_error"]).format(
            error=f"Заказ {status} на стороне сервиса."
        )
        if chat_id:
            self._send_message(chat_id, msg)
        if self.config.get("auto_refund") and fp_order_id:
            self._refund_order(fp_order_id, reason=f"SMM order {status}")
        self._stats["failed"] += 1
        self._log(f"❌ Заказ #{tid} провален ({status})", level="warn")
        logger.error("ORDER_FAILED: tid=%s status=%s fp_order_id=%s", tid, status, fp_order_id)
        try:
            if getattr(self, "event_bus", None):
                self.event_bus.emit("order_failed", {
                    "order_id": tid,
                    "fp_order_id": fp_order_id,
                    "status": status,
                    "source": "autosmm",
                    "reason": f"SMM order {status}",
                })
        except Exception:
            pass
        with self._lock:
            self._active.pop(tid, None)
        self._save_active_orders()

    # ====================================================================
    # BALANCE CHECK
    # ====================================================================

    def _check_balance(self):
        api_key = self.config.get("api_key", "").strip()
        if not api_key:
            return
        try:
            url = self.config.get("api_url", DEFAULT_CONFIG["api_url"])
            j = self.http_client.get(url, params={"action": "balance", "key": api_key}, timeout=15)
            balance = float(j.get("balance", 0))
            currency = j.get("currency", "")
            self._stats["balance"] = f"{balance:.2f} {currency}"
            threshold = float(self.config.get("min_balance_alert", 50))
            if balance < threshold:
                self._log(f"⚠️ Низкий баланс Twiboost: {balance:.2f} {currency} (порог {threshold})", level="warn")
                self._notify_telegram(f"⚠️ Низкий баланс Twiboost: {balance:.2f} {currency}")
        except Exception as e:
            self._log(f"Не удалось проверить баланс: {e}", level="warn")

    # ====================================================================
    # PUBLIC EVENT HANDLERS
    # ====================================================================

    def on_event(self, event):
        try:
            event_type = getattr(event, "type", None) or (event.get("type") if isinstance(event, dict) else None)
        except Exception:
            event_type = None
        if event_type == "new_order":
            self._on_new_order(event)
        elif event_type == "new_message":
            self._on_new_message(event)
        elif event_type in ("order_completed", "order_closed"):
            self._on_order_completed(event)
        elif event_type == "review_received":
            self._on_review_received(event)

    def _on_new_order(self, event):
        if self.config.get("test_mode"):
            tcid = (self.config.get("test_chat_id") or "").strip()
            ecid = str(event.get("chat_id") if isinstance(event, dict) else getattr(event, "chat_id", "") or "")
            if ecid != "sandbox-test-chat" and tcid and ecid != tcid:
                self._log("[TEST] ignore new_order from " + ecid + " (not tester)")
                return
            elif tcid:
                self._log("[TEST] processing new_order from tester " + ecid)
        try:
            order_id = event.get("order_id") if isinstance(event, dict) else getattr(event, "order_id", None)
            lot_id = event.get("lot_id") if isinstance(event, dict) else getattr(event, "lot_id", None)
            chat_id = event.get("chat_id") if isinstance(event, dict) else getattr(event, "chat_id", None)
            buyer = event.get("buyer") if isinstance(event, dict) else getattr(event, "buyer", "buyer")
        except Exception:
            return
        if not order_id or not chat_id:
            return

        order_id_str = str(order_id)
        if order_id_str in self._processed_orders_ttl:
            self._log(f'[Dedupe] Skipped duplicate: chat={chat_id} order={order_id}')
            return

        chat_lock = self._get_chat_lock(str(chat_id))
        with chat_lock:
            if order_id_str in self._processed_orders_ttl:
                self._log(f'[Dedupe] Skipped duplicate: chat={chat_id} order={order_id}')
                return
            self._processed_orders_ttl.add(order_id_str)

            order_title_for_marker = ""
            try:
                if isinstance(event, dict):
                    order_title_for_marker = event.get("title", "") or ""
                else:
                    order_title_for_marker = getattr(event, "title", "") or ""
            except Exception:
                order_title_for_marker = ""

            marker_service_id = has_marker_for(order_title_for_marker, "AS")

            lot_cfg = None
            if marker_service_id:
                _b40_name, _b40_min = self._b40_resolve_service_info(marker_service_id)
                _b40_qty = self._b40_parse_quantity_from_title(order_title_for_marker) or _b40_min or 1000
                lot_cfg = {
                    "service_id": marker_service_id,
                    "quantity": _b40_qty,
                    "service_name": _b40_name,
                }
                try:
                    print(f"[AutoSMM] Marker AS#{marker_service_id} detected for order {order_id}")
                except Exception:
                    pass
            else:
                mapping = self.config.get("lot_mapping", {})
                lot_cfg = mapping.get(str(lot_id))

            if not lot_cfg:
                return

            with self._lock:
                self._dialogs[str(chat_id)] = {
                    "state": "await_link",
                    "order_id": order_id,
                    "lot_id": lot_id,
                "service_id": lot_cfg.get("service_id"),
                "quantity": lot_cfg.get("quantity"),
                "service_name": lot_cfg.get("service_name", "услуга"),
                "buyer": buyer,
                "created_at": time.time(),
            }

        try:
            if chat_lock_registry and chat_id:
                chat_lock_registry.acquire(chat_id, owner="autosmm", ttl_seconds=1800)
        except Exception:
            pass

        msg = self.config.get("msg_ask_link", DEFAULT_CONFIG["msg_ask_link"])
        self._send_message(chat_id, msg)
        self._log(f"🆕 Новый заказ #{order_id} -> ждём ссылку")
        lot_title = ""
        try:
            lot_title = event.get("title", "") if isinstance(event, dict) else getattr(event, "title", "")
        except Exception:
            lot_title = ""
        price = ""
        try:
            price = event.get("price", "") if isinstance(event, dict) else getattr(event, "price", "")
        except Exception:
            price = ""
        self._notify_telegram(f"🔔 Новый заказ!\n📦 {lot_title}\n👤 {buyer}\n💰 {price} ₽\n🔧 AutoSMM")

    def _on_new_message(self, event):
        if self.config.get("test_mode"):
            tcid = (self.config.get("test_chat_id") or "").strip()
            ecid = str(event.get("chat_id") if isinstance(event, dict) else getattr(event, "chat_id", "") or "")
            if ecid != "sandbox-test-chat" and tcid and ecid != tcid:
                return
        try:
            chat_id = event.get("chat_id") if isinstance(event, dict) else getattr(event, "chat_id", None)
            text = event.get("text") if isinstance(event, dict) else getattr(event, "text", "")
            from_me = event.get("from_me") if isinstance(event, dict) else getattr(event, "from_me", False)
        except Exception:
            return

        if from_me or not chat_id or not text:
            return

        # Защита от повторной обработки одного сообщения (если пришло менее 5 сек назад)
        import time as _t_msg
        _last_ts = self._processed_orders.get(f'_last_msg_{chat_id}')
        if _last_ts and _t_msg.time() - _last_ts < 5:
            self._log(f'[DEDUP] Ignore rapid message in {chat_id}')
            return
        self._processed_orders[f'_last_msg_{chat_id}'] = _t_msg.time()

        if from_me or not chat_id or not text:
            return

        chat_id_str = str(chat_id)
        with self._lock:
            dialog = self._dialogs.get(chat_id_str)
        if not dialog:
            return

        order_id = dialog.get("order_id")
        order_id_str = str(order_id) if order_id else ""
        if order_id_str in self._processed_orders_ttl:
            self._log(f'[Dedupe] Skipped duplicate message: chat={chat_id_str} order={order_id}')
            with self._lock:
                self._dialogs.pop(chat_id_str, None)
            return

        text_clean = text.strip()
        lower = text_clean.lower()

        refund_words = self.config.get("msg_refund_trigger", DEFAULT_CONFIG.get("msg_refund_trigger", "возврат,вернуть,рефанд,refund,отмена")).split(",")
        refund_words = [w.strip() for w in refund_words if w.strip()]
        if any(lower.startswith(w) for w in refund_words):
            msg = self.config.get("msg_refund_response", "Запрос на возврат принят. Обработка 24 часа.")
            self._send_message(chat_id, msg)
            return

        state = dialog.get("state") if dialog else None

        if state == "await_link":
            self._handle_link(chat_id_str, text_clean, dialog)
        elif state == "await_confirm":
            lower = text_clean.lower()
            if any(lower.startswith(w) for w in ("да", "+", "yes", "ok", "ок", "y", "д", "ага", "ыыы", "конечно", "подтверждаю", "верно")):
                order_id_for_dedup = dialog.get("order_id")
                if order_id_for_dedup and str(order_id_for_dedup) in self._processed_orders_ttl:
                    self._log(f'[Dedupe] Skipped duplicate: chat={chat_id_str} order={order_id_for_dedup}')
                    return
                if order_id_for_dedup:
                    self._processed_orders_ttl.add(str(order_id_for_dedup))
                self._handle_confirm(chat_id_str, dialog)
            elif lower in ("нет", "-", "no"):
                self._send_message(chat_id, "Пришлите новую ссылку.")
                with self._lock:
                    dialog["state"] = "await_link"
            else:
                if self._looks_like_url(text_clean):
                    self._handle_link(chat_id_str, text_clean, dialog)

    def _handle_link(self, chat_id, link, dialog):
        if not self._is_allowed_domain(link):
            allowed = self.config.get("allowed_domains", DEFAULT_CONFIG["allowed_domains"])
            domains_str = ", ".join(allowed[:10]) + ("..." if len(allowed) > 10 else "")
            msg = self.config.get("msg_invalid_link", DEFAULT_CONFIG["msg_invalid_link"]).format(domains=domains_str)
            self._send_message(chat_id, msg)
            return
        with self._lock:
            dialog["link"] = link
        if self.config.get("ask_confirmation"):
            with self._lock:
                dialog["state"] = "await_confirm"
            msg = self.config.get("msg_confirm", DEFAULT_CONFIG["msg_confirm"]).format(
                link=link,
                service_name=dialog.get("service_name", "услуга"),
                quantity=dialog.get("quantity", "?"),
            )
            self._send_message(chat_id, msg)
        else:
            self._handle_confirm(chat_id, dialog)

    def _handle_confirm(self, chat_id, dialog):
        link = dialog.get("link")
        service_id = dialog.get("service_id")
        quantity = dialog.get("quantity")
        fp_order_id = dialog.get("order_id")
        service_name = dialog.get("service_name", "услуга")
        if not all([link, service_id, quantity, fp_order_id]):
            self._send_message(chat_id, "❌ Внутренняя ошибка: не хватает данных заказа.")
            return

        chat_lock = self._get_chat_lock(str(chat_id))
        with chat_lock:
            order_id_str = str(fp_order_id)
            if order_id_str in self._processed_orders_ttl:
                self._log(f'[Dedupe] Skipped duplicate: chat={chat_id} order={fp_order_id}')
                return
            self._processed_orders_ttl.add(order_id_str)

            if self.config.get("dry_run"):
                twi_id = f"DRY-{int(time.time())}"
                self._log(f"[DRY-RUN] Создал бы заказ: service={service_id} qty={quantity} link={link}")
            else:
                # Idempotency check: skip if order already sent to a supplier
                registry = get_supplier_order_registry()
                if registry.is_registered(str(fp_order_id), "twiboost") or registry.is_registered(str(fp_order_id), "looksmm"):
                    self._log(f"⚠️ Заказ #{fp_order_id} уже создан у поставщика (idempotency), пропускаю")
                    self._send_message(chat_id, "✅ Заказ уже обрабатывается. Ожидайте выполнения.")
                    with self._lock:
                        self._dialogs.pop(chat_id, None)
                    return
                twi_id, provider = self._create_order_with_fallback(service_id, link, quantity)
                if twi_id:
                    registry.register(str(fp_order_id), provider or "twiboost", str(twi_id))
                if not twi_id:
                    msg = self.config.get("msg_error", DEFAULT_CONFIG["msg_error"]).format(
                        error="Не удалось создать заказ"
                    )
                    self._send_message(chat_id, msg)
                    if self.config.get("auto_refund"):
                        self._refund_order(fp_order_id, "Order creation failed")
                    with self._lock:
                        self._dialogs.pop(chat_id, None)
                    return
            with self._lock:
                self._active[int(twi_id) if isinstance(twi_id, int) or (isinstance(twi_id, str) and twi_id.isdigit()) else twi_id] = {
                    "fp_order_id": fp_order_id,
                    "chat_id": chat_id,
                    "service_id": service_id,
                    "service_name": service_name,
                    "quantity": quantity,
                    "link": link,
                    "created_at": time.time(),
                }
                self._dialogs.pop(chat_id, None)
        self._save_active_orders()
        self._stats["total_orders"] += 1
        msg = self.config.get("msg_order_created", DEFAULT_CONFIG["msg_order_created"]).format(
            twi_id=twi_id, service_name=service_name, quantity=quantity
        )
        self._send_message(chat_id, msg)
        self._log(f"✨ Создан заказ Twi #{twi_id} (FP #{fp_order_id}, qty={quantity})")

    # ====================================================================
    # TWIBOOST API
    # ====================================================================

    def _create_twiboost_order(self, service_id, link, quantity):
        api_key = self.config.get("api_key", "").strip()
        if not api_key:
            self._log("API key не задан", level="error")
            return None
        try:
            url = self.config.get("api_url", DEFAULT_CONFIG["api_url"])
            j = self.http_client.get(url, params={
                "action": "add",
                "service": service_id,
                "link": link,
                "quantity": quantity,
                "key": api_key,
            }, timeout=30)
            order_id = j.get("order")
            if not order_id:
                err = j.get("error", str(j))
                self._log(f"Twiboost error: {err}", level="error")
                self._notify_telegram(f"❌ Ошибка API Twiboost!\n📝 {err}")
                return None
            return order_id
        except HTTPClientError as e:
            self._log(f"Twiboost недоступен после всех попыток: {e}", level="error")
            self._notify_telegram(f"❌ Ошибка API Twiboost!\n📝 {e}")
            return None
        except Exception as e:
            self._log(f"Twiboost exception: {e}", level="error")
            self._notify_telegram(f"❌ Ошибка API Twiboost!\n📝 {e}")
            return None

    def _check_looksmm_price(self, service_id, quantity):
        api_key = self.config.get("looksmm_api_key", "").strip()
        api_url = self.config.get("looksmm_api_url", DEFAULT_CONFIG.get("looksmm_api_url", "https://looksmm.ru/api/v2")).rstrip("/")
        if not api_key:
            return None
        try:
            services = self.http_client.get(api_url, params={
                "key": api_key,
                "action": "services",
            }, timeout=20)
            if not isinstance(services, list):
                return None
            for s in services:
                if str(s.get("service") or s.get("service_id") or s.get("id")) == str(service_id):
                    rate = float(s.get("rate", 0) or 0)
                    return rate * quantity
            return None
        except Exception:
            return None

    def _create_looksmm_order(self, service_id, link, quantity):
        api_key = self.config.get("looksmm_api_key", "").strip()
        api_url = self.config.get("looksmm_api_url", DEFAULT_CONFIG.get("looksmm_api_url", "https://looksmm.ru/api/v2")).rstrip("/")
        if not api_key:
            return None
        try:
            j = self.http_client.get(api_url, params={
                "key": api_key,
                "action": "add",
                "service": service_id,
                "link": link,
                "quantity": quantity,
            }, timeout=30)
            order_id = j.get("order")
            if not order_id:
                err = j.get("error", str(j))
                self._log(f"LookSMM error: {err}", level="error")
                return None
            return str(order_id)
        except HTTPClientError as e:
            self._log(f"LookSMM недоступен после всех попыток: {e}", level="error")
            return None
        except Exception as e:
            self._log(f"LookSMM exception: {e}", level="error")
            return None

    def _create_order_with_fallback(self, service_id, link, quantity):
        use_looksmm = self.config.get("use_looksmm_if_cheaper", True)
        twi_price = None
        looksmm_price = None

        if use_looksmm:
            looksmm_price = self._check_looksmm_price(service_id, quantity)

        if looksmm_price is not None:
            twi_price = self._check_twiboost_price(service_id, quantity)

        if looksmm_price is not None and (twi_price is None or looksmm_price < twi_price):
            self._log(f"💰 Использую LookSMM (дешевле на {abs((twi_price or 0) - looksmm_price):.2f}₽)")
            order_id = self._create_looksmm_order(service_id, link, quantity)
            if order_id:
                return order_id, "looksmm"
            self._log("LookSMM не доступен, fallback на Twiboost", level="warn")

        self._log("Использую Twiboost (LookSMM дороже или недоступен)")
        order_id = self._create_twiboost_order(service_id, link, quantity)
        if order_id:
            return order_id, "twiboost"
        return None, None

    def _check_twiboost_price(self, service_id, quantity):
        api_key = self.config.get("api_key", "").strip()
        if not api_key:
            return None
        try:
            url = self.config.get("api_url", DEFAULT_CONFIG["api_url"])
            services = self.http_client.get(url, params={
                "action": "services",
                "key": api_key,
            }, timeout=20)
            if not isinstance(services, list):
                return None
            for s in services:
                if str(s.get("service") or s.get("service_id") or s.get("id")) == str(service_id):
                    rate = float(s.get("rate", 0) or 0)
                    return rate * quantity
            return None
        except Exception:
            return None

    # ====================================================================
    # FUNPAY HELPERS
    # ====================================================================

    def _on_order_completed(self, event):
        try:
            chat_id = event.get("chat_id") if isinstance(event, dict) else getattr(event, "chat_id", None)
            order_id = event.get("order_id") if isinstance(event, dict) else getattr(event, "order_id", None)
            title = event.get("title") if isinstance(event, dict) else getattr(event, "title", "")
            if not chat_id:
                return
            if self.config.get("test_mode"):
                tcid = (self.config.get("test_chat_id") or "").strip()
                ecid = str(chat_id or "")
                if ecid != "sandbox-test-chat" and tcid and ecid != tcid:
                    return
            try:
                from runtime.plugin_markers import has_marker_for
                if not has_marker_for(title or "", "AS"):
                    self._log(f"[B62] skip order_completed {order_id} — no AS marker")
                    return
            except Exception:
                pass
            msg = self.config.get("msg_thanks_after_confirm", DEFAULT_CONFIG.get("msg_thanks_after_confirm", "Спасибо!"))
            self._send_message(chat_id, msg)
            self._log(f"🙏 order_completed -> sent thanks to {chat_id} (order {order_id})")
            try:
                if chat_lock_registry and chat_id:
                    chat_lock_registry.release(chat_id, owner="autosmm")
            except Exception:
                pass
        except Exception as e:
            self._log(f"[B62] on_order_completed err: {e}", level="warn")

    def _on_review_received(self, event):
        try:
            order_id = event.get("order_id") if isinstance(event, dict) else getattr(event, "order_id", None)
            chat_id = event.get("chat_id") if isinstance(event, dict) else getattr(event, "chat_id", None)
            stars = int(event.get("stars") or event.get("rating") or 0)
            title = event.get("title") if isinstance(event, dict) else getattr(event, "title", "")
            if not order_id:
                self._log(f"[B71] review without order_id, skip")
                return
            order_id_str = str(order_id)
            if order_id_str in self._processed_reviews:
                self._log(f'[Dedupe] Skipped duplicate review: order={order_id}')
                return
            if order_id_str in self._processed_orders_ttl:
                self._log(f'[Dedupe] Skipped duplicate review: order={order_id}')
                return
            if self.config.get("test_mode"):
                tcid = (self.config.get("test_chat_id") or "").strip()
                ecid = str(chat_id or "")
                if ecid != "sandbox-test-chat" and tcid and ecid != tcid:
                    return
            try:
                from runtime.plugin_markers import has_marker_for
                if title and not has_marker_for(title, "AS"):
                    self._log(f"[B71] skip review for non-AS order {order_id}")
                    return
            except Exception:
                pass
            if stars >= 5:
                tpl_key = "review_reply_5star"
            elif stars == 4:
                tpl_key = "review_reply_4star"
            else:
                tpl_key = "review_reply_1to3"
            reply_text = self.config.get(tpl_key, DEFAULT_CONFIG.get(tpl_key, "Спасибо за отзыв!"))
            if str(chat_id) == "sandbox-test-chat":
                self._send_message(chat_id, f"[💬 ОТВЕТ НА ОТЗЫВ {stars}★] {reply_text}")
                self._log(f"[B71][SANDBOX] review_reply {stars}* -> {reply_text[:60]}")
                return
            try:
                data = self.http_client.post(
                    self.hub_url + "/api/seller/reviews/reply",
                    json={"order_id": order_id, "text": reply_text},
                    timeout=10
                )
                if data.get("ok"):
                    self._log(f"[B71] ✅ Reply to review {stars}* on order {order_id}: {reply_text[:50]}")
                    self._processed_reviews[order_id_str] = True
                else:
                    self._log(f"[B71] Reply failed: body={data}", level="warn")
            except Exception as e:
                self._log(f"[B71] HTTP err: {e}", level="warn")
        except Exception as ex:
            self._log(f"[B71] on_review_received err: {ex}", level="warn")

    # ====================================================================
    # HELPERS
    # ====================================================================

    def _notify_telegram(self, text):
        try:
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
                self.http_client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                    timeout=10,
                )
        except Exception:
            pass

    def _b40_resolve_service_info(self, service_id):
        try:
            import os, json
            cache_paths = [
                "data/autosmm/twiboost_services_cache.json",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "autosmm", "twiboost_services_cache.json"),
            ]
            for p in cache_paths:
                if os.path.exists(p):
                    with open(p, encoding="utf-8") as f:
                        data = json.load(f)
                    services = data.get("services") if isinstance(data, dict) else (data if isinstance(data, list) else [])
                    for s in services:
                        if str(s.get("service_id")) == str(service_id):
                            return (s.get("name", f"Service #{service_id}"), s.get("min"))
                    break
        except Exception as e:
            print(f"[AutoSMM][B40] resolve_service err: {e}")
        return (f"Service #{service_id}", None)

    def _b40_parse_quantity_from_title(self, title):
        import re
        if not title:
            return None
        clean = re.sub(r'\[[A-Z]{2,4}#[A-Za-z0-9_-]+\]', '', title)
        clean = re.sub(r'(202\d|201\d)', '', clean)
        matches = re.findall(r'(\d{2,7})', clean)
        candidates = [int(m) for m in matches if 50 <= int(m) <= 1000000]
        if candidates:
            return max(candidates)
        return None

    def _send_message(self, chat_id, text):
        if getattr(self, "_msg_manager", None) is not None:
            try:
                self._msg_manager.send("", str(chat_id), "plugin", "autosmm_message", {"text": text}, force=True)
                return
            except Exception:
                pass
        self._log(f"[MessageManager] Not available, cannot send message to {chat_id}", level="warn")

    def _refund_order(self, fp_order_id, reason=""):
        if self.config.get("dry_run"):
            self._log(f"[DRY-RUN] Возврат заказа {fp_order_id}: {reason}")
            self._stats["refunded"] += 1
            return
        try:
            self.http_client.post(self.hub_url + f"/api/seller/orders/{fp_order_id}/refund",
                                  headers={"Content-Type": "application/json"},
                                  json={},
                                  timeout=15)
            self._stats["refunded"] += 1
            self._log(f"💰 Возврат заказа FP #{fp_order_id}: {reason}")
        except Exception as e:
            self._log(f"Возврат провалился: {e}", level="error")

    def _is_allowed_domain(self, url):
        allowed = self.config.get("allowed_domains", DEFAULT_CONFIG["allowed_domains"])
        try:
            url_check = url if "://" in url else "https://" + url
            host = urlparse(url_check).hostname or ""
            host = host.lower().replace("www.", "")
            return any(host == d or host.endswith("." + d) for d in allowed)
        except Exception:
            return False

    def _looks_like_url(self, text):
        return bool(re.search(r"(https?://|t\.me/|vk\.com/|instagram\.com/|tiktok\.com/|youtube\.com/|youtu\.be/)", text, re.I))

    def _get_data_dir(self):
        import sys
        if getattr(sys, "frozen", False):
            base = Path(sys.executable).resolve().parent
        else:
            base = Path(__file__).resolve().parent.parent
        d = base / "data" / "autosmm"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _load_active_orders(self):
        try:
            if self._orders_file.exists():
                data = json.loads(self._orders_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._active = {int(k) if str(k).isdigit() else k: v for k, v in data.items()}
        except Exception:
            self._active = {}

    def _save_active_orders(self):
        try:
            with self._lock:
                snapshot = {str(k): v for k, v in self._active.items()}
            self._orders_file.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _now_str(self):
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def _log(self, message, level="info"):
        ts = time.strftime("%H:%M:%S")
        self._log_buffer.append({"time": ts, "level": level, "message": message})
        print(f"[AutoSMM] {message}")
        if level == "error":
            self._stats["last_error"] = message[:200]

    # ====================================================================
    # ACTIONS (for UI)
    # ====================================================================

    def action_check_balance(self, payload):
        self._check_balance(); self._check_balance_and_deactivate(); self._check_balance_and_deactivate()
        return {
            "ok": True,
            "balance": self._stats.get("balance"),
            "message": f"Баланс: {self._stats.get('balance') or '—'}"
        }

    def action_test_api(self, payload):
        api_key = self.config.get("api_key", "").strip()
        if not api_key:
            return {"ok": False, "error": "API ключ не задан"}
        try:
            url = self.config.get("api_url", DEFAULT_CONFIG["api_url"])
            j = self.http_client.get(url, params={"action": "balance", "key": api_key}, timeout=15)
            return {"ok": True, "message": f"✅ API работает. Баланс: {j.get('balance')} {j.get('currency')}"}
        except HTTPClientError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def action_load_services(self, payload):
        api_key = self.config.get("api_key", "").strip()
        if not api_key:
            return {"ok": False, "error": "API ключ не задан"}
        try:
            url = self.config.get("api_url", DEFAULT_CONFIG["api_url"])
            services = self.http_client.get(url, params={"action": "services", "key": api_key}, timeout=30)
            return {"ok": True, "count": len(services), "services": services[:500], "message": f"Загружено {len(services)} услуг (показано первые 500)"}
        except HTTPClientError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # MATCH PROFILES
    MATCH_PROFILES = {
        "telegram": {
            "category_keywords": ["telegram", "телеграм", "tg "],
            "service_keywords": ["подписчик", "subscriber", "member", "участник", "просмотр", "view", "реакция", "boost", "буст", "комент"],
            "exclude_keywords": [],
        },
        "vk": {
            "category_keywords": ["вконтакте", "вк ", "vk ", " vk"],
            "service_keywords": ["подписчик", "лайк", "like", "просмотр", "репост", "друзья", "follower"],
            "exclude_keywords": [],
        },
        "instagram": {
            "category_keywords": ["instagram", "инстаграм", "инста"],
            "service_keywords": ["подписчик", "follower", "лайк", "like", "просмотр", "view", "комент"],
            "exclude_keywords": [],
        },
        "tiktok": {
            "category_keywords": ["tiktok", "тикток", "тик ток", "тик-ток"],
            "service_keywords": ["подписчик", "follower", "лайк", "like", "просмотр", "view"],
            "exclude_keywords": [],
        },
        "youtube": {
            "category_keywords": ["youtube", "ютуб", "ютюб"],
            "service_keywords": ["подписчик", "subscriber", "просмотр", "view", "лайк", "like"],
            "exclude_keywords": [],
        },
    }

    def _services_cache_file(self):
        return self._data_dir / "twiboost_services_cache.json"

    def _save_services_cache(self, services):
        try:
            self._services_cache_file().write_text(
                json.dumps({"updated_at": time.time(), "services": services}, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            self._log(f"save services cache failed: {e}", level="warn")

    def _load_services_cache(self):
        try:
            f = self._services_cache_file()
            if not f.exists():
                return None
            data = json.loads(f.read_text(encoding="utf-8"))
            if time.time() - data.get("updated_at", 0) > 86400:
                return None
            return data.get("services") or []
        except Exception:
            return None

    def _fetch_twiboost_services(self, force_refresh=False):
        if not force_refresh:
            cached = self._load_services_cache()
            if cached:
                return cached
        api_key = self.config.get("api_key", "").strip()
        if not api_key:
            return None
        try:
            url = self.config.get("api_url", DEFAULT_CONFIG["api_url"])
            services = self.http_client.get(url, params={"action": "services", "key": api_key}, timeout=30)
            if not isinstance(services, list):
                return None
            normalized = []
            for s in services:
                normalized.append({
                    "service_id": s.get("service") or s.get("service_id") or s.get("id"),
                    "name": s.get("name") or "",
                    "category": s.get("category") or "",
                    "rate": s.get("rate"),
                    "min": s.get("min"),
                    "max": s.get("max"),
                    "type": s.get("type"),
                })
            self._save_services_cache(normalized)
            self._log(f"Загружено {len(normalized)} услуг Twiboost")
            return normalized
        except HTTPClientError as e:
            self._log(f"Twiboost services недоступен: {e}", level="error")
            return None
        except Exception as e:
            self._log(f"fetch services failed: {e}", level="error")
            return None

    def _fetch_my_lots(self):
        try:
            data = self.http_client.get(self.hub_url + "/api/seller/lots", timeout=10)
            return data.get("lots", []) if isinstance(data, dict) else []
        except Exception as e:
            self._log(f"fetch my lots failed: {e}", level="warn")
            return []

    def _detect_profile_for_lot(self, lot):
        text = ((lot.get("category_name", "") or "") + " " +
                (lot.get("subcategory_name", "") or "") + " " +
                (lot.get("title", "") or "")).lower()
        for prof_name, prof in self.MATCH_PROFILES.items():
            cat_kws = prof.get("category_keywords", [])
            if any(kw.lower() in text for kw in cat_kws):
                return prof_name, prof
        return None, None

    def action_load_twiboost_services(self, payload=None):
        payload = payload or {}
        force = bool(payload.get("force", True))
        services = self._fetch_twiboost_services(force_refresh=force)
        if services is None:
            return {"ok": False, "error": "Не удалось загрузить каталог Twiboost. Проверь API ключ."}
        return {
            "ok": True,
            "count": len(services),
            "message": f"Загружено {len(services)} услуг",
            "sample": services[:5],
        }

    def action_scan_my_lots(self, payload=None):
        from runtime.lot_matcher import auto_build_mapping
        services = self._fetch_twiboost_services(force_refresh=False)
        if services is None:
            return {"ok": False, "error": "Каталог Twiboost пуст. Сначала загрузи каталог (API key)."}
        my_lots = self._fetch_my_lots()
        if not my_lots:
            return {"ok": False, "error": "Нет моих лотов на FunPay (или backend недоступен)."}
        results_by_profile = {}
        no_profile_lots = []
        for lot in my_lots:
            prof_name, prof = self._detect_profile_for_lot(lot)
            if prof_name is None:
                no_profile_lots.append({
                    "id": lot.get("id"),
                    "title": lot.get("title"),
                    "category_name": lot.get("category_name"),
                })
                continue
            results_by_profile.setdefault(prof_name, {"profile": prof, "lots": []})
            results_by_profile[prof_name]["lots"].append(lot)
        all_auto = {}
        all_suggested = {}
        all_skipped = []
        for prof_name, group in results_by_profile.items():
            res = auto_build_mapping(group["lots"], services, group["profile"], auto_threshold=0.75)
            for lot_id, m in res["auto"].items():
                m["profile"] = prof_name
                all_auto[lot_id] = m
            for lot_id, m in res["suggested"].items():
                m["profile"] = prof_name
                all_suggested[lot_id] = m
            all_skipped.extend(res["skipped"])
        return {
            "ok": True,
            "stats": {
                "total_lots": len(my_lots),
                "auto_matched": len(all_auto),
                "needs_review": len(all_suggested),
                "skipped": len(all_skipped),
                "no_matching_profile": len(no_profile_lots),
            },
            "auto": all_auto,
            "suggested": all_suggested,
            "skipped": all_skipped,
            "no_profile": no_profile_lots,
            "services_count": len(services),
        }

    def action_apply_auto_match(self, payload=None):
        scan = self.action_scan_my_lots()
        if not scan.get("ok"):
            return scan
        auto = scan.get("auto") or {}
        if not auto:
            return {"ok": True, "applied": 0, "message": "Нет высокоуверенных совпадений для авто-привязки."}
        mapping = dict(self.config.get("lot_mapping") or {})
        applied = 0
        for lot_id, m in auto.items():
            mapping[str(lot_id)] = {
                "service_id": m["service_id"],
                "service_name": m["service_name"],
                "quantity": m.get("quantity") or 0,
                "auto": True,
                "match_score": m.get("score"),
                "profile": m.get("profile"),
            }
            applied += 1
        self.config["lot_mapping"] = mapping
        self.save_config()
        self._log(f"Авто-привязано {applied} лотов")
        return {"ok": True, "applied": applied, "mapping_size": len(mapping)}

    def action_confirm_suggested(self, payload=None):
        payload = payload or {}
        lot_id = str(payload.get("lot_id") or "")
        service_id = payload.get("service_id")
        quantity = payload.get("quantity") or 0
        service_name = payload.get("service_name", "")
        if not lot_id or not service_id:
            return {"ok": False, "error": "lot_id и service_id обязательны"}
        mapping = dict(self.config.get("lot_mapping") or {})
        mapping[lot_id] = {
            "service_id": service_id,
            "service_name": service_name,
            "quantity": int(quantity),
            "auto": False,
            "manual": True,
        }
        self.config["lot_mapping"] = mapping
        self.save_config()
        self._log(f"Ручная привязка: lot {lot_id} -> service {service_id}")
        return {"ok": True, "lot_id": lot_id, "service_id": service_id}

    def action_remove_mapping(self, payload=None):
        payload = payload or {}
        lot_id = str(payload.get("lot_id") or "")
        if not lot_id:
            return {"ok": False, "error": "lot_id обязателен"}
        mapping = dict(self.config.get("lot_mapping") or {})
        if lot_id in mapping:
            del mapping[lot_id]
            self.config["lot_mapping"] = mapping
            self.save_config()
            self._log(f"Удалена привязка lot {lot_id}")
            return {"ok": True, "removed": lot_id}
        return {"ok": False, "error": "Привязка не найдена"}

    def action_get_current_mappings(self, payload=None):
        mapping = self.config.get("lot_mapping") or {}
        my_lots = self._fetch_my_lots()
        lots_by_id = {str(l.get("id")): l for l in my_lots}
        enriched = []
        for lot_id, m in mapping.items():
            lot = lots_by_id.get(str(lot_id), {})
            enriched.append({
                "lot_id": lot_id,
                "lot_title": lot.get("title", "(лот удалён?)"),
                "lot_price": lot.get("price"),
                "service_id": m.get("service_id"),
                "service_name": m.get("service_name"),
                "quantity": m.get("quantity"),
                "auto": m.get("auto", False),
                "manual": m.get("manual", False),
                "match_score": m.get("match_score"),
                "profile": m.get("profile"),
            })
        return {"ok": True, "count": len(enriched), "mappings": enriched}

    # ====================================================================
    # ДОБАВЛЕННЫЕ МЕТОДЫ ДЛЯ ДЕАКТИВАЦИИ И ГЕНЕРАЦИИ
    # ====================================================================

    def _check_balance_and_deactivate(self):
        """Проверяет баланс Twiboost, при низком балансе деактивирует лоты и шлёт уведомление."""
        api_key = self.config.get("api_key", "").strip()
        if not api_key:
            return
        try:
            url = self.config.get("api_url", DEFAULT_CONFIG["api_url"])
            j = self.http_client.get(url, params={"action": "balance", "key": api_key}, timeout=15)
            balance = float(j.get("balance", 0))
            threshold = float(self.config.get("min_balance_alert", 50))
            if balance < threshold:
                self._deactivate_as_lots()
                try:
                    self._emit_event("low_balance", {"balance": balance, "threshold": threshold})
                except Exception:
                    pass
                self._log(f"⚠️ Низкий баланс Twiboost: {balance} (порог {threshold}). Лоты деактивированы.")
        except Exception as e:
            self._log(f"Ошибка проверки баланса для деактивации: {e}", level="warn")

    def _deactivate_as_lots(self):
        """Деактивирует все лоты с маркером AS#."""
        try:
            from runtime.seller_service import seller_service_singleton as svc
            lots_data = svc.get_my_lots(force_refresh=True)
            if not lots_data.get("available"):
                return
            for lot in lots_data.get("lots", []):
                title = lot.get("title", "")
                if "[AS#" in title:
                    lot_id = lot.get("id")
                    if lot_id:
                        svc.toggle_lot_active(lot_id, False, dry_run=False)
                        self._log(f"Деактивирован лот {lot_id} ({title[:30]})")
        except Exception as e:
            self._log(f"Ошибка деактивации лотов: {e}", level="error")

    def action_generate_lots_from_niches(self, payload):
        """Генерирует лоты для выбранных ниш (по 15 вариаций)."""
        niches = payload.get("niches", [])
        if not niches:
            return {"ok": False, "error": "Ниши не выбраны"}
        results = []
        total_generated = 0
        for niche in niches:
            service_id = niche.get("service_id")
            quantity = niche.get("quantity", 1000)
            price = niche.get("price", 40)
            variations = niche.get("variations", 15)
            try:
                data = self.http_client.post(self.hub_url + "/api/dev/lots/generate", json={
                    "service_id": service_id,
                    "quantity": quantity,
                    "price": price,
                    "variations": variations
                }, timeout=30)
                if data.get("ok"):
                    results.append({
                        "service_id": service_id,
                        "generated": data.get("lots_generated", 0),
                        "lots": data.get("lots", [])
                    })
                    total_generated += data.get("lots_generated", 0)
                else:
                    results.append({"service_id": service_id, "error": "Ошибка генерации"})
            except Exception as e:
                results.append({"service_id": service_id, "error": str(e)})
        return {
            "ok": True,
            "total_generated": total_generated,
            "results": results,
            "message": f"Сгенерировано {total_generated} лотов"
        }

    def get_logs(self):
        return list(self._log_buffer)[-30:]

    def get_stats(self):
        return {
            **self._stats,
            "active_orders": len(self._active),
            "pending_dialogs": len(self._dialogs),
            "worker_alive": bool(self._worker and self._worker.is_alive()),
        }
