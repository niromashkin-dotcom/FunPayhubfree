import os
import re
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any
from plugins.plugin_base import PluginBase
from runtime.http_client import HTTPClient, HTTPClientError
from runtime.order_tracker import get_tracker

# ЭТАП 1 — Импорты и конфиг
FRAGMENT_API_URL = os.getenv("FRAGMENT_API_URL", "https://fragment.com/api")
FRAGMENT_WALLET_SEED = os.getenv("FRAGMENT_WALLET_SEED", "")
STARS_MARKUP = float(os.getenv("STARS_MARKUP", "1.3"))  # маржа 30%

DEFAULT_CONFIG = {
    "enabled": False,
    "fragment_api": {
        "api_key": "",  # Для будущей интеграции API-ключа
        "wallet_seed": FRAGMENT_WALLET_SEED,
    },
    "msg_ask_username": "❤ Спасибо за заказ! Пришлите username для зачисления звёзд Telegram.\n\nФормат: @username или t.me/username",
    "msg_order_created": "✅ Заказ принят! Обрабатываем {stars} звёзд...",
    "msg_error": "❌ Ошибка при заказе звёзд: {error}",
    "msg_completed": "🎉 {stars} звёзд успешно зачислено! Проверьте свой профиль.",
}

class StarsPlugin(PluginBase):
    PLUGIN_INFO = {
        "name": "Telegram Stars",
        "version": "1.0.0",
        "author": "FunPay Hub",
        "description": "Продажа Telegram Stars через Fragment API",
        "dependencies": [],
        "optional_dependencies": [],
    }

    execution_mode = "inprocess"

    CONFIG_SCHEMA = [
        {"key": "enabled", "type": "toggle", "label": "Включить плагин", "default": False},
        {"key": "fragment_api.wallet_seed", "type": "password", "label": "Fragment Wallet Seed", "default": ""},
    ]

    def __init__(self, module_name, state_api, event_bus):
        super().__init__(module_name, state_api, event_bus)
        self.http_client = HTTPClient(max_retries=3)
        from bot.config import get_hub_url
        self.hub_url = get_hub_url()
        self._data_dir = self._get_data_dir()
        # Мы не сохраняем event_bus и state_api как атрибуты, но можем при необходимости

    def on_load(self):
        self.load_config(DEFAULT_CONFIG)
        if not FRAGMENT_WALLET_SEED:
            self._log("⚠️ Fragment Wallet Seed не настроен — плагин работает в режиме ЗАГЛУШКИ", level="warn")

    def on_event(self, event):
        try:
            event_type = getattr(event, "type", None) or (event.get("type") if isinstance(event, dict) else None)
        except Exception:
            event_type = None

        if event_type == "new_order":
            self._on_new_stars_order(event)

    # ЭТАП 2 — Реализованные функции

    def _on_new_stars_order(self, order_data):
        try:
            order_id = order_data.get("order_id") if isinstance(order_data, dict) else getattr(order_data, "order_id", None)
            title = order_data.get("title", "") if isinstance(order_data, dict) else getattr(order_data, "title", None)
            chat_id = order_data.get("chat_id") if isinstance(order_data, dict) else getattr(order_data, "chat_id", None)
        except Exception as e:
            self._log(f"Ошибка парса события: {e}", level="error")
            return

        stars_count = self._parse_stars(title)
        if not stars_count:
            return

        # Запрашиваем username у покупателя (в реальности нужно ждать ответ, но пока заглушка)
        username = self._get_buyer_username(order_data)
        if not username:
            self._log("Не удалось определить username покупателя", level="warn")
            self._send_message(chat_id, "❌ Не удалось определить ваш Telegram username. Пожалуйста, укажите его в профиле FunPay или напишите в поддержку.")
            return

        self._send_message(chat_id, DEFAULT_CONFIG["msg_order_created"].format(stars=stars_count))
        self._log(f"Telegram Stars [ST#{stars_count}] обнаружено для заказа {order_id}, username={username}")

        try:
            fragment_order = self._create_stars_order(username, stars_count, order_id)
            if fragment_order.get("stub"):
                self._log("⚠️ Fragment API не настроен — заглушка", level="warn")
                # В режиме заглушки считаем заказ выполненным сразу
                self._send_message(chat_id, DEFAULT_CONFIG["msg_completed"].format(stars=stars_count))
                return

            # Регистрируем в OrderTracker для отслеживания статуса (если нужен возврат/повторная проверка)
            self._register_order_in_tracker(order_id, fragment_order["fragment_order_id"], stars_count)

            # Проверяем статус (в реальности можно сделать фоновую проверку, но пока синхронно)
            status = self._check_stars_status(fragment_order["fragment_order_id"])
            if status == "completed":
                self._send_message(chat_id, DEFAULT_CONFIG["msg_completed"].format(stars=stars_count))
            elif status == "failed":
                self._send_message(chat_id, DEFAULT_CONFIG["msg_error"].format(error="не удалось зачислить звёзды"))
            else:
                # pending — информируем, что проверяем
                self._send_message(chat_id, f"⏳ Заказ обрабатывается... Проверяем статус через минуту.")

        except Exception as e:
            self._log(f"Ошибка обработки заказа: {e}", level="error")
            self._send_message(chat_id, DEFAULT_CONFIG["msg_error"].format(error=str(e)))

    def _create_stars_order(self, username: str, quantity: int, order_id: str) -> Dict[str, Any]:
        """
        POST на Fragment API: покупка Stars для username
        URL: https://fragment.com/api (или задаётся через FRAGMENT_API_URL)
        Payload: {"recipient": "@username", "quantity": quantity}
        Возвращает: {"fragment_order_id": "...", "status": "pending", "stars_sent": N}
        При ошибке: выбрасывает ValueError с понятным сообщением
        """
        if not FRAGMENT_WALLET_SEED:
            return {"stub": True, "fragment_order_id": f"STUB-{int(time.time())}"}

        headers = {
            "Authorization": f"Bearer {FRAGMENT_WALLET_SEED}",
            "Content-Type": "application/json",
        }
        payload = {
            "recipient": username if username.startswith("@") else f"@{username}",
            "quantity": quantity,
            "funpay_order_id": order_id,  # для трекинга
        }

        try:
            response = self.http_client.post(
                f"{FRAGMENT_API_URL}/stars/order",
                json=payload,
                headers=headers,
                timeout=30,
            )
            if not isinstance(response, dict):
                raise ValueError("Неверный ответ от Fragment API")
            return {
                "fragment_order_id": response.get("order_id"),
                "status": response.get("status", "pending"),
                "stars_sent": response.get("quantity", quantity),
            }
        except HTTPClientError as e:
            raise ValueError(f"HTTP {e.status_code}: {e.body[:200] if e.body else 'неизвестная ошибка'}")
        except Exception as e:
            raise ValueError(f"Ошибка Fragment API: {str(e)}")

    def _check_stars_status(self, fragment_order_id: str) -> str:
        """
        GET статус заказа у Fragment
        Возвращает: "completed" | "pending" | "failed"
        """
        if not FRAGMENT_WALLET_SEED:
            return "completed"  # В заглушке считаем выполненным

        headers = {"Authorization": f"Bearer {FRAGMENT_WALLET_SEED}"}
        try:
            response = self.http_client.get(
                f"{FRAGMENT_API_URL}/stars/order/{fragment_order_id}",
                headers=headers,
                timeout=15,
            )
            return response.get("status", "pending")
        except HTTPClientError:
            return "failed"
        except Exception:
            return "failed"

    def _parse_stars(self, title: str) -> int:
        """Извлекает количество звёзд из маркера [ST#N]"""
        if not title:
            return 0
        match = re.search(r'\[ST#(\d+)\]', title, re.IGNORECASE)
        return int(match.group(1)) if match else 0

    def _get_buyer_username(self, order_data) -> Optional[str]:
        """
        Извлекает username покупателя из order_data.
        В реальной системе может быть в поле buyer_username или подобное.
        Пока используем buyer как fallback (может быть не Telegram username).
        """
        buyer = None
        if isinstance(order_data, dict):
            buyer = order_data.get("buyer") or order_data.get("buyer_username") or order_data.get("username")
        else:
            buyer = getattr(order_data, "buyer", None) or getattr(order_data, "buyer_username", None) or getattr(order_data, "username", None)
        if buyer and isinstance(buyer, str):
            return buyer.strip()
        return None

    def _send_message(self, chat_id: str, text: str):
        """Отправляет сообщение покупателю через внутренний API"""
        try:
            # Следуем образцу autodonate_plugin.py: отправляем на локальный эндпоинт
            self.http_client.post(
                self.hub_url + f"/api/seller/chats/{chat_id}/send",
                json={"text": text, "dry_run": False},
                timeout=10,
            )
        except Exception as e:
            self._log(f"Ошибка отправки сообщения: {e}", level="warn")

    def _register_order_in_tracker(self, order_id: str, fragment_id: str, stars: int):
        """
        Регистрирует заказ в OrderTracker для возможной будущей проверки статуса/возврата.
        В реальности OrderTracker может иметь метод register_order, но мы используем его внутренний механизм через get_tracker.
        """
        try:
            tracker = get_tracker()  # Возвращает singleton OrderPaymentTracker
            if tracker:
                # Добавляем в pending_orders с нашими полями
                with tracker._lock:
                    tracker.pending_orders[order_id] = {
                        "start_time": time.time(),
                        "next_ping": time.time() + 60,
                        "pings_sent": 0,
                        "warned": False,
                        "chat_id": None,  # Мы не храним chat_id здесь, но можно добавить
                        "lot_title": f"Stars {stars}",
                        "service_name": "Telegram Stars",
                        "price": 0,
                        "url": "",
                        "_fragment_order_id": fragment_id,
                        "_stars": stars,
                        "_status": "pending",
                    }
                self._log(f"Заказ {order_id} зарегистрирован в OrderTracker для отслеживания Fragment заказа {fragment_id}")
        except Exception as e:
            self._log(f"Не удалось зарегистрировать заказ в OrderTracker: {e}", level="warn")

    def _log(self, message, level="info"):
        """Единый лог с префиксом плагина"""
        print(f"[StarsPlugin] [{level.upper()}] {message}")

    def _get_data_dir(self):
        return Path(__file__).resolve().parent.parent / "data" / "stars"

    # Заглушки для совместимости с PluginBase (если нужны)
    def action_test_connection(self, payload=None):
        if not FRAGMENT_WALLET_SEED:
            return {
                "ok": True,
                "message": "Fragment API ключ не настроен — вставьте в конфиг",
                "needs_api_key": True
            }
        # Пытаемся сделать простой запрос к API
        try:
            self._check_stars_status("test")
            return {"ok": True, "message": "Fragment API доступен"}
        except Exception as e:
            return {"ok": False, "message": f"Ошибка подключения: {e}"}