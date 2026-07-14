"""
Auto Donate Plugin for FunPay Hub
Universal administrator for external suppliers: GorgonaBoosts, HoldBoost, ShopClaude, Kosell
"""
import time
import re
import threading
from pathlib import Path
from plugins.plugin_base import PluginBase
from runtime.http_client import HTTPClient, HTTPClientError
from runtime.order_tracker import get_supplier_order_registry

DEFAULT_CONFIG = {
    "enabled": True,
    "priority": 10,
    "dry_run": False,
    "suppliers": {
        "gorgonaboosts": {
            "name": "GorgonaBoosts",
            "type": "discord_boosts",
            "api_key": "",
            "api_url": "https://api.gorgonaboost.xyz",
            "auth_header": "Authorization: Bearer",
            "marker": "[GB#",
            "endpoints": {
                "create_order": "POST /boost",
                "check_stock": "GET /stock",
                "get_prices": "GET /price"
            },
            "auto_deactivate_on_error": True,
            "enabled": True
        },
        "holdboost": {
            "name": "HoldBoost",
            "type": "discord_boosts",
            "api_key": "",
            "api_url": "https://api.holdboost.store",
            "auth_header": "X-API-Key",
            "marker": "[HB#",
            "endpoints": {
                "create_order": "POST /v1/external/orders",
                "check_stock": "GET /v1/external/stock",
                "get_prices": "GET /v1/boosts/prices",
                "get_profile": "GET /v1/external/profile",
                "order_status": "GET /v1/external/orders/{order_id}"
            },
            "auto_deactivate_on_error": True,
            "enabled": True
        },
        "shopclaude": {
            "name": "ShopClaude",
            "type": "ai_subscriptions",
            "api_key": "",
            "auth_header": "Authorization: Bearer",
            "marker": "[SC#",
            "auto_deactivate_on_error": True,
            "enabled": True
        },
        "kosell": {
            "name": "Kosell",
            "type": "game_rentals",
            "api_key": "",
            "api_url": "https://api.kosell.store",
            "marker": "[KS#",
            "auto_deactivate_on_error": True,
            "enabled": True
        }
    },
    "return_policy": "При проблемах с услугой — возврат в течение 24 часов. Заблокированные аккаунты возврату не подлежат. Подробнее в описании лота.",
    "auto_responses": {
        "order_received": "Спасибо за заказ! Обрабатываем...",
        "order_completed": "Заказ выполнен! Проверьте результат.",
        "order_failed": "К сожалению, произошла ошибка. Возврат будет произведён автоматически.",
        "refund_trigger_words": ["возврат", "вернуть", "рефанд", "refund", "отмена"],
        "refund_response": "Запрос на возврат принят. Обработка в течение 24 часов.",
        "discord_boost_received": "🎮 Заказ на Discord Boost принят!\n\n🔗 Сервер: {invite}\n💎 Бустов: {amount}\n⏱ Применение: 5-30 минут\n\nОставайтесь на связи! 💙",
        "discord_boost_completed": "🎉 Бусты успешно применены! 💎\n\nПроверьте ваш сервер и подтвердите заказ! ⭐",
        "discord_boost_failed": "😔 Не удалось применить бусты. Возврат автоматически. 🙏",
        "ai_subscription_received": "🤖 Заказ на AI подписку принят!\n\n📧 Ключ активации будет отправлен shortly.\n⏱ Обработка: до 1 часа\n\nСпасибо за заказ! 💙",
        "ai_subscription_completed": "🎉 Ключ активации отправлен! ✅\n\nИспользуйте его на сайте сервиса.\nЕсли не сработает — напишите нам! 💙",
        "ai_subscription_failed": "😔 Ошибка при активации подписки. Возврат автоматически. 🙏",
        "game_rental_received": "🎮 Аренда игры оформлена!\n\n📋 Данные для входа:\n👤 Логин: {login}\n🔑 Пароль: {password}\n⏱ Срок: {hours} часов\n\nПриятной игры! 🎯",
        "game_rental_completed": "🎉 Аренда активирована! ✅\n\nДанные для входа отправлены.\nЕсли проблемы — пишите! 💙",
        "game_rental_failed": "😔 Не удалось активировать аренду. Возврат автоматически. 🙏"
    }
}


class AutoDonatePlugin(PluginBase):
    PLUGIN_INFO = {
        "name": "Auto Donate",
        "version": "2.0.0",
        "author": "FunPay Hub",
        "description": "Универсальный администратор донат-заказов: GorgonaBoosts, HoldBoost, ShopClaude, Kosell",
        "dependencies": [],
        "optional_dependencies": [],
    }

    execution_mode = "inprocess"

    CONFIG_SCHEMA = [
        {"key": "enabled", "type": "toggle", "label": "Включить плагин", "default": True},
        {"key": "suppliers.gorgonaboosts.enabled", "type": "toggle", "label": "GorgonaBoosts: включён", "default": True},
        {"key": "suppliers.gorgonaboosts.api_key", "type": "password", "label": "GorgonaBoosts: API ключ", "default": ""},
        {"key": "suppliers.gorgonaboosts.auto_deactivate_on_error", "type": "toggle", "label": "GorgonaBoosts: авто-deactivate при ошибке", "default": True},
        {"key": "suppliers.holdboost.enabled", "type": "toggle", "label": "HoldBoost: включён", "default": True},
        {"key": "suppliers.holdboost.api_key", "type": "password", "label": "HoldBoost: API ключ", "default": ""},
        {"key": "suppliers.holdboost.auto_deactivate_on_error", "type": "toggle", "label": "HoldBoost: авто-deactivate при ошибке", "default": True},
        {"key": "suppliers.shopclaude.enabled", "type": "toggle", "label": "ShopClaude: включён", "default": True},
        {"key": "suppliers.shopclaude.api_key", "type": "password", "label": "ShopClaude: API ключ", "default": ""},
        {"key": "suppliers.kosell.enabled", "type": "toggle", "label": "Kosell: включён", "default": True},
        {"key": "suppliers.kosell.api_key", "type": "password", "label": "Kosell: API ключ", "default": ""},
        {"key": "return_policy", "type": "textarea", "rows": 3,
         "label": "Политика возврата", "default": DEFAULT_CONFIG["return_policy"]},
        {"key": "auto_responses.order_received", "type": "textarea", "rows": 2,
         "label": "Автоответ: заказ получен", "default": DEFAULT_CONFIG["auto_responses"]["order_received"]},
        {"key": "auto_responses.order_completed", "type": "textarea", "rows": 2,
         "label": "Автоответ: заказ выполнен", "default": DEFAULT_CONFIG["auto_responses"]["order_completed"]},
        {"key": "auto_responses.order_failed", "type": "textarea", "rows": 2,
         "label": "Автоответ: ошибка", "default": DEFAULT_CONFIG["auto_responses"]["order_failed"]},
        {"key": "auto_responses.refund_response", "type": "textarea", "rows": 2,
         "label": "Автоответ: возврат", "default": DEFAULT_CONFIG["auto_responses"]["refund_response"]},
    ]

    def __init__(self, module_name, state_api, event_bus):
        super().__init__(module_name, state_api, event_bus)
        self.http_client = HTTPClient()
        from bot.config import get_hub_url
        self.hub_url = get_hub_url()
        self._data_dir = self._get_data_dir()
        self._orders_file = self._data_dir / "donate_orders.json"
        self._throttle = {}
        self._throttle_lock = threading.Lock()
        self._last_telegram_notify = 0
        self._pending_orders = {}  # order_id -> {supplier, cfg, title, event, created_at, ping_count}
        self._pending_lock = threading.Lock()
        self._replenish_thread = None
        self._replenish_stop = threading.Event()

    def on_enable(self):
        self._start_replenish_timer()

    def on_disable(self):
        self._stop_replenish_timer()

    def on_unload(self):
        self._stop_replenish_timer()

    def on_load(self):
        self.load_config(DEFAULT_CONFIG)
        env_mapping = {
            "gorgonaboosts": "GORGONABOOSTS_API_KEY",
            "holdboost": "HOLDBOOST_API_KEY",
            "shopclaude": "SHOPCLAUDE_API_KEY",
            "kosell": "KOSELL_API_KEY",
        }
        for supplier, env_name in env_mapping.items():
            supplier_cfg = self.config.get("suppliers", {}).get(supplier, {})
            if not supplier_cfg.get("api_key"):
                secret = self.get_secret(env_name, "")
                if secret:
                    supplier_cfg["api_key"] = secret

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

    # ====================================================================
    # NEW ORDER
    # ====================================================================

    def _on_new_order(self, event):
        try:
            order_id = event.get("order_id") if isinstance(event, dict) else getattr(event, "order_id", None)
            chat_id = event.get("chat_id") if isinstance(event, dict) else getattr(event, "chat_id", None)
            title = event.get("title", "") if isinstance(event, dict) else getattr(event, "title", "")
            buyer = event.get("buyer", "") if isinstance(event, dict) else getattr(event, "buyer", "")
        except Exception:
            return

        supplier, marker = self._detect_supplier(title)
        if not supplier:
            return

        cfg = self._get_supplier_config(supplier)
        if not cfg or not cfg.get("enabled", False):
            return

        auto_resp = self.config.get("auto_responses", DEFAULT_CONFIG["auto_responses"])
        if supplier in ("gorgonaboosts", "holdboost"):
            invite = self._extract_invite_from_title(title) or ""
            amount = self._extract_quantity_from_title(title) or 1
            msg = auto_resp.get("discord_boost_received", DEFAULT_CONFIG["auto_responses"]["discord_boost_received"]).format(invite=invite, amount=amount)
        elif supplier == "shopclaude":
            msg = auto_resp.get("ai_subscription_received", DEFAULT_CONFIG["auto_responses"]["ai_subscription_received"])
        elif supplier == "kosell":
            hours = self._parse_kosell_hours(title)
            msg = auto_resp.get("game_rental_received", DEFAULT_CONFIG["auto_responses"]["game_rental_received"]).format(hours=hours or "?", login="---", password="---")
        else:
            msg = auto_resp.get("order_received", DEFAULT_CONFIG["auto_responses"]["order_received"])
        self._send_message(chat_id, msg)
        self._log(f"🆕 Новый заказ #{order_id} -> {supplier} (маркер {marker})")

        balance = self.check_balance(supplier)
        if not balance.get("ok") or not self._is_balance_sufficient(supplier, balance):
            self._log(f"⚠️ Низкий баланс {supplier} для заказа #{order_id}: {balance}")
            self._send_telegram_notification(f"⚠️ Нужно пополнить {supplier} на сумму для заказа #{order_id} ({title[:50]}). Баланс: {balance.get('balance', '?')}")
            self._send_message(chat_id, "⏳ Обработка заказа... Пожалуйста, подождите.")
            self._add_pending_order(supplier, cfg, title, event)
            return

        # Idempotency check: skip if order already sent to this supplier
        registry = get_supplier_order_registry()
        if registry.is_registered(str(order_id), supplier):
            self._log(f"⚠️ Заказ #{order_id} уже создан у {supplier} (idempotency), пропускаю")
            existing_supplier_id = registry.get_supplier_order_id(str(order_id))
            self._send_message(chat_id, "✅ Заказ уже обрабатывается. Ожидайте выполнения.")
            return

        if self.config.get("dry_run", DEFAULT_CONFIG.get("dry_run", False)):
            self._log(f"[DRY-RUN] Создал бы заказ у {supplier} для лота {title[:50]}")
            self._send_message(chat_id, "✅ Заказ принят (DRY-RUN режим).")
            return

        result = self._create_supplier_order(supplier, cfg, title, event)
        if result.get("ok"):
            registry.register(str(order_id), supplier, result.get("order_id", "?"))
        if not result.get("ok"):
            err = result.get("error", "Unknown error")
            self._log(f"❌ Ошибка создания заказа у {supplier}: {err}", level="error")
            if cfg.get("auto_deactivate_on_error"):
                self._deactivate_supplier_lots(supplier)
            fail_msg = self.config.get("auto_responses", {}).get("order_failed", DEFAULT_CONFIG["auto_responses"]["order_failed"])
            self._send_message(chat_id, fail_msg)

    def _on_new_message(self, event):
        try:
            chat_id = event.get("chat_id") if isinstance(event, dict) else getattr(event, "chat_id", None)
            text = event.get("text") if isinstance(event, dict) else getattr(event, "text", "")
            from_me = event.get("from_me") if isinstance(event, dict) else getattr(event, "from_me", False)
        except Exception:
            return

        if from_me or not chat_id or not text:
            return

        lower = text.lower().strip()
        auto_resp = self.config.get("auto_responses", DEFAULT_CONFIG["auto_responses"])
        refund_words = auto_resp.get("refund_trigger_words", DEFAULT_CONFIG["auto_responses"]["refund_trigger_words"])
        if any(lower.startswith(w) for w in refund_words):
            msg = auto_resp.get("refund_response", DEFAULT_CONFIG["auto_responses"]["refund_response"])
            self._send_message(chat_id, msg)
            return

    def _on_order_completed(self, event):
        try:
            chat_id = event.get("chat_id") if isinstance(event, dict) else getattr(event, "chat_id", None)
            order_id = event.get("order_id") if isinstance(event, dict) else getattr(event, "order_id", None)
            title = event.get("title") if isinstance(event, dict) else getattr(event, "title", "")
            if not chat_id:
                return
            supplier, _ = self._detect_supplier(title)
            auto_resp = self.config.get("auto_responses", DEFAULT_CONFIG["auto_responses"])
            if supplier in ("gorgonaboosts", "holdboost"):
                msg = auto_resp.get("discord_boost_completed", "🎉 Бусты успешно применены! 💎\n\nПроверьте ваш сервер и подтвердите заказ! ⭐")
            elif supplier == "shopclaude":
                msg = auto_resp.get("ai_subscription_completed", "🎉 Ключ активации отправлен! ✅\n\nИспользуйте его на сайте сервиса.\nЕсли не сработает — напишите нам! 💙")
            elif supplier == "kosell":
                msg = auto_resp.get("game_rental_completed", "🎉 Аренда активирована! ✅\n\nДанные для входа отправлены.\nЕсли проблемы — пишите! 💙")
            else:
                msg = auto_resp.get("order_completed", DEFAULT_CONFIG["auto_responses"]["order_completed"])
            self._send_message(chat_id, msg)
        except Exception as e:
            self._log(f"on_order_completed err: {e}", level="warn")

    def _on_review_received(self, event):
        try:
            chat_id = event.get("chat_id") if isinstance(event, dict) else getattr(event, "chat_id", None)
            order_id = event.get("order_id") if isinstance(event, dict) else getattr(event, "order_id", None)
            stars = int(event.get("stars") or event.get("rating") or 0)
            if not chat_id or not order_id:
                return
            if stars >= 5:
                msg = "Спасибо за отличный отзыв! Ждём вас снова!"
            elif stars == 4:
                msg = "Спасибо! Будем стараться ещё лучше."
            else:
                msg = "Извините за неудобства. Напишите нам — разберёмся."
            self._send_message(chat_id, msg)
            self._log(f"⭐ Ответ на отзыв {stars}* на заказе {order_id}")
        except Exception as e:
            self._log(f"on_review_received err: {e}", level="warn")

    # ====================================================================
    # SUPPLIER DETECTION
    # ====================================================================

    def _detect_supplier(self, title):
        if not title:
            return None, None
        title_lower = title.lower()
        suppliers = self.config.get("suppliers", {})
        for name, cfg in suppliers.items():
            marker = cfg.get("marker", "")
            if marker and marker.lower() in title_lower:
                return name, marker
        return None, None

    def _get_supplier_config(self, name):
        return self.config.get("suppliers", {}).get(name)

    def _parse_kosell_hours(self, title):
        m = re.search(r'\[KS#\d+:(\d+)\]', title, re.I)
        return int(m.group(1)) if m else None

    # ====================================================================
    # SUPPLIER API
    # ====================================================================

    def _create_supplier_order(self, supplier, cfg, title, event):
        if supplier == "gorgonaboosts":
            return self._create_gorgonaboosts_order(cfg, title, event)
        elif supplier == "holdboost":
            return self._create_holdboost_order(cfg, title, event)
        elif supplier == "shopclaude":
            return self._create_shopclaude_order(cfg, title, event)
        elif supplier == "kosell":
            return self._create_kosell_order(cfg, title, event)
        return {"ok": False, "error": f"Неизвестный поставщик {supplier}"}

    def _create_gorgonaboosts_order(self, cfg, title, event):
        api_key = cfg.get("api_key", "").strip()
        api_url = cfg.get("api_url", "https://api.gorgonaboost.xyz").rstrip("/")
        if not api_key:
            return {"ok": False, "error": "API ключ не задан"}

        invite = self._extract_invite_from_title(title) or ""
        boosts = self._extract_quantity_from_title(title) or 1
        try:
            j = self.http_client.post(
                f"{api_url}/boost",
                json={"invite": invite, "boosts": int(boosts), "plan": "1m"},
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                timeout=30,
            )
            order_id = j.get("order_id") or j.get("id") or j.get("order")
            if not order_id:
                return {"ok": False, "error": j.get("error", str(j))}
            return {"ok": True, "order_id": order_id, "supplier": "gorgonaboosts"}
        except HTTPClientError as e:
            return {"ok": False, "error": f"HTTP {e.status_code}: {e.body[:200] if e.body else e.last_error}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _create_holdboost_order(self, cfg, title, event):
        api_key = cfg.get("api_key", "").strip()
        api_url = cfg.get("api_url", "https://api.holdboost.store").rstrip("/")
        if not api_key:
            return {"ok": False, "error": "API ключ не задан"}

        invite = self._extract_invite_from_title(title) or ""
        amount = self._extract_quantity_from_title(title) or 1
        try:
            j = self.http_client.post(
                f"{api_url}/v1/external/orders",
                json={"guild_invite": invite, "amount": int(amount), "boost_months": 1},
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                timeout=30,
            )
            order_id = j.get("order_id") or j.get("id") or j.get("order")
            if not order_id:
                return {"ok": False, "error": j.get("error", str(j))}
            return {"ok": True, "order_id": order_id, "supplier": "holdboost"}
        except HTTPClientError as e:
            return {"ok": False, "error": f"HTTP {e.status_code}: {e.body[:200] if e.body else e.last_error}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _create_shopclaude_order(self, cfg, title, event):
        # TODO: ShopClaude API требования:
        # 1. URL: https://shopclaude.provider/api/
        # 2. Auth: API_KEY в SHOPCLAUDE_API_KEY
        # 3. POST /order: {"product_id": "...", "quantity": 1} → {"order_id": "...", "status": "pending"}
        # 4. GET /order/{order_id}: {"status": "completed" | "pending" | "failed"}
        # 5. Товары: ChatGPT Plus, Claude Pro, GPT-4, Midjourney (маржин ↑ 30% от цены)
        # 6. Маркер: [SC#order_id]
        self._log("[ShopClaude] Заглушка: заказ создан в логах")
        return {"ok": True, "order_id": f"SC-{int(time.time())}", "supplier": "shopclaude", "stub": True}

    def _create_kosell_order(self, cfg, title, event):
        api_key = cfg.get("api_key", "").strip()
        api_url = cfg.get("api_url", "https://api.kosell.store").rstrip("/")
        if not api_key:
            return {"ok": False, "error": "API ключ не задан"}

        product_id, hours = self._parse_kosell_product(title)
        if not product_id:
            return {"ok": False, "error": "Не найден product_id в маркере [KS#product_id:hours]"}

        # Check stock
        try:
            products = self.http_client.get(f"{api_url}/products", headers={"Authorization": f"Bearer {api_key}"}, timeout=15)
            if isinstance(products, list):
                available = any(str(p.get("id")) == str(product_id) and p.get("stock", 0) > 0 for p in products)
                if not available:
                    return {"ok": False, "error": "Товар закончился"}
        except HTTPClientError:
            pass
        except Exception:
            pass

        try:
            self.http_client.post(
                f"{api_url}/calculate_price",
                json={"product_id": int(product_id), "hours": int(hours or 24)},
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                timeout=15,
            )
        except HTTPClientError as e:
            return {"ok": False, "error": f"HTTP {e.status_code}: {e.body[:200] if e.body else e.last_error}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

        try:
            j = self.http_client.post(
                f"{api_url}/rent",
                json={"product_id": int(product_id), "hours": int(hours or 24)},
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                timeout=30,
            )
            uid = j.get("uid") or j.get("id")
            if not uid:
                return {"ok": False, "error": j.get("error", str(j))}
            creds = self.http_client.get(
                f"{api_url}/credentials/{uid}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=15,
            )
            login = creds.get("login", "") if isinstance(creds, dict) else ""
            password = creds.get("password", "") if isinstance(creds, dict) else ""
            self._send_credentials(event, login, password, hours)
            return {"ok": True, "order_id": uid, "supplier": "kosell"}
        except HTTPClientError as e:
            return {"ok": False, "error": f"HTTP {e.status_code}: {e.body[:200] if e.body else e.last_error}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _extract_invite_from_title(self, title):
        m = re.search(r'(https?://(?:discord\.gg|discord\.com/invite)/[A-Za-z0-9_-]+)', title)
        return m.group(1) if m else ""

    def _extract_quantity_from_title(self, title):
        m = re.search(r'\[GB#(\d+)\]|\[HB#(\d+)\]', title, re.I)
        if m:
            q = m.group(1) or m.group(2)
            return int(q) if q else 1
        m = re.search(r'(\d{1,5})\s*(буст|boost|месяц|month)', title, re.I)
        if m:
            return int(m.group(1))
        return 1

    def _parse_kosell_product(self, title):
        m = re.search(r'\[KS#(\d+)(?::(\d+))?\]', title, re.I)
        if m:
            return m.group(1), m.group(2)
        return None, None

    def _send_credentials(self, event, login, password, hours):
        try:
            chat_id = event.get("chat_id") if isinstance(event, dict) else getattr(event, "chat_id", None)
            if not chat_id:
                return
            msg = f"🔐 Данные для входа:\n👤 Логин: {login}\n🔑 Пароль: {password}\n⏰ Срок аренды: {hours or '?'} часов"
            self._send_message(chat_id, msg)
        except Exception as e:
            self._log(f"send_credentials err: {e}", level="warn")

    # ====================================================================
    # DEACTIVATE LOTS
    # ====================================================================

    def _deactivate_supplier_lots(self, supplier):
        cfg = self._get_supplier_config(supplier)
        if not cfg or not cfg.get("auto_deactivate_on_error"):
            return
        marker = cfg.get("marker", "")
        try:
            from runtime.seller_service import seller_service_singleton as svc
            lots_data = svc.get_my_lots(force_refresh=True)
            if not lots_data.get("available"):
                return
            for lot in lots_data.get("lots", []):
                title = lot.get("title", "")
                if marker and marker.lower() in title.lower():
                    lot_id = lot.get("id")
                    if lot_id:
                        svc.toggle_lot_active(lot_id, False, dry_run=False)
                        self._log(f"Деактивирован лот {lot_id} ({title[:30]})")
        except Exception as e:
            self._log(f"Ошибка деактивации лотов {supplier}: {e}", level="error")

    # ====================================================================
    # CHECK BALANCE / STOCK
    # ====================================================================

    def check_balance(self, supplier):
        cfg = self._get_supplier_config(supplier)
        if not cfg:
            return {"ok": False, "error": "Поставщик не найден"}
        api_key = cfg.get("api_key", "").strip()
        api_url = cfg.get("api_url", "").rstrip("/")
        if not api_key or not api_url:
            return {"ok": False, "error": "API не настроен"}

        try:
            if supplier == "gorgonaboosts":
                result = self.http_client.get(f"{api_url}/stock", headers={"Authorization": f"Bearer {api_key}"}, timeout=15)
            elif supplier == "holdboost":
                result = self.http_client.get(f"{api_url}/v1/external/stock", headers={"X-API-Key": api_key}, timeout=15)
            elif supplier == "kosell":
                result = self.http_client.get(f"{api_url}/balance", headers={"Authorization": f"Bearer {api_key}"}, timeout=15)
            else:
                return {"ok": True, "balance": "N/A", "message": "Баланс не поддерживается"}
            return {"ok": True, "balance": str(result)[:200], "message": "OK"}
        except HTTPClientError as e:
            return {"ok": False, "error": f"HTTP {e.status_code}: {e.body[:100] if e.body else e.last_error}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _is_balance_sufficient(self, supplier, balance_info):
        if not balance_info.get("ok"):
            return False
        bal = balance_info.get("balance")
        if isinstance(bal, dict):
            stock = bal.get("stock", {})
            if stock:
                return any(v > 0 for v in stock.values())
            return True
        if isinstance(bal, (int, float)):
            return bal > 0
        return True

    def check_stock(self, supplier):
        cfg = self._get_supplier_config(supplier)
        if not cfg:
            return {"ok": False, "error": "Поставщик не найден"}
        api_key = cfg.get("api_key", "").strip()
        api_url = cfg.get("api_url", "").rstrip("/")
        if not api_key or not api_url:
            return {"ok": False, "error": "API не настроен"}

        try:
            if supplier == "gorgonaboosts":
                result = self.http_client.get(f"{api_url}/stock", headers={"Authorization": f"Bearer {api_key}"}, timeout=15)
            elif supplier == "holdboost":
                result = self.http_client.get(f"{api_url}/v1/external/stock", headers={"X-API-Key": api_key}, timeout=15)
            elif supplier == "kosell":
                result = self.http_client.get(f"{api_url}/products", headers={"Authorization": f"Bearer {api_key}"}, timeout=15)
            else:
                return {"ok": True, "stock": "N/A", "message": "Остатки не поддерживаются"}
            return {"ok": True, "stock": result, "message": "OK"}
        except HTTPClientError as e:
            return {"ok": False, "error": f"HTTP {e.status_code}: {e.body[:100] if e.body else e.last_error}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ====================================================================
    # HELPERS
    # ====================================================================

    def _send_message(self, chat_id, text):
        if getattr(self, "_msg_manager", None) is not None:
            try:
                self._msg_manager.send("", str(chat_id), "plugin", "donate_message", {"text": text}, force=True)
                return
            except Exception:
                pass
        self._log(f"[MessageManager] Not available, cannot send message to {chat_id}", level="warn")

    def _log(self, message, level="info"):
        print(f"[AutoDonatePlugin] {message}")

    def _get_data_dir(self):
        return Path(__file__).resolve().parent.parent / "data" / "autodonate"

    # ====================================================================
    # AUTO-REPLENISHMENT TIMER
    # ====================================================================

    def _start_replenish_timer(self):
        if self._replenish_thread and self._replenish_thread.is_alive():
            return
        self._replenish_stop.clear()
        self._replenish_thread = threading.Thread(target=self._replenish_loop, daemon=True, name="DonateReplenish")
        self._replenish_thread.start()

    def _stop_replenish_timer(self):
        self._replenish_stop.set()
        if self._replenish_thread and self._replenish_thread.is_alive():
            self._replenish_thread.join(timeout=3)

    def _replenish_loop(self):
        while not self._replenish_stop.is_set():
            try:
                self._check_pending_orders()
            except Exception as e:
                self._log(f"replenish loop err: {e}", level="warn")
            for _ in range(60):
                if self._replenish_stop.is_set():
                    return
                time.sleep(1)

    def _check_pending_orders(self):
        with self._pending_lock:
            now = time.time()
            to_process = []
            to_remove = []
            for order_id, info in self._pending_orders.items():
                age = now - info.get("created_at", 0)
                if age > 25 * 60:
                    to_remove.append(order_id)
                    to_process.append((order_id, info, "expired"))
                elif age > 2 * 60 and info.get("ping_count", 0) < 4:
                    to_process.append((order_id, info, "ping"))
            for order_id in to_remove:
                self._pending_orders.pop(order_id, None)

        for order_id, info, action in to_process:
            supplier = info.get("supplier")
            cfg = info.get("cfg")
            title = info.get("title", "")
            event = info.get("event", {})
            chat_id = event.get("chat_id") if isinstance(event, dict) else getattr(event, "chat_id", None)
            if action == "ping":
                balance = self.check_balance(supplier)
                if not balance.get("ok"):
                    self._send_telegram_notification(f"⚠️ Нужно пополнить {supplier} для заказа {order_id}!\nОшибка проверки баланса: {balance.get('error')}")
                else:
                    bal_text = str(balance.get("balance", "?"))
                    self._send_telegram_notification(f"⚠️ Нужно пополнить {supplier} для заказа {order_id}!\nБаланс: {bal_text}")
                with self._pending_lock:
                    if order_id in self._pending_orders:
                        self._pending_orders[order_id]["ping_count"] = self._pending_orders[order_id].get("ping_count", 0) + 1
                        self._pending_orders[order_id]["last_ping"] = now
            elif action == "expired":
                self._log(f"⏰ Заказ {order_id} отменён: не пополнен баланс {supplier} за 25 минут")
                self._send_telegram_notification(f"❌ Заказ {order_id} отменён. Лоты {supplier} сняты.")
                self._send_message(chat_id, "😔 Извините, временные технические сложности. Возврат средств произведён.")
                self._deactivate_supplier_lots(supplier)
                fp_order_id = event.get("order_id") if isinstance(event, dict) else getattr(event, "order_id", None)
                if fp_order_id:
                    self._refund_order(fp_order_id, f"Balance not replenished for {supplier}")

    def _send_telegram_notification(self, text):
        token = self.config.get("telegram_bot_token", "").strip() or self.config.get("bot_token", "").strip()
        chat = self.config.get("telegram_chat_id", "").strip() or self.config.get("chat_id", "").strip()
        if not token or not chat:
            return
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            self.http_client.post(url, json={"chat_id": chat, "text": text, "parse_mode": "HTML"}, timeout=10)
        except Exception:
            pass

    def _add_pending_order(self, supplier, cfg, title, event):
        order_id = event.get("order_id") if isinstance(event, dict) else getattr(event, "order_id", None)
        if not order_id:
            return
        with self._pending_lock:
            self._pending_orders[str(order_id)] = {
                "supplier": supplier,
                "cfg": cfg,
                "title": title,
                "event": event,
                "created_at": time.time(),
                "ping_count": 0,
                "last_ping": 0,
            }
        self._log(f"⏳ Заказ {order_id} добавлен в отслеживание пополнения {supplier}")

    # ====================================================================
    # ACTIONS
    # ====================================================================

    def action_test_connection(self, payload=None):
        results = {}
        for name, cfg in self.config.get("suppliers", {}).items():
            results[name] = self.check_balance(name)
        return {
            "ok": True,
            "suppliers": results,
            "message": "Проверка завершена"
        }

    def action_check_stock(self, payload=None):
        supplier = payload.get("supplier") if isinstance(payload, dict) else None
        if supplier:
            return self.check_stock(supplier)
        results = {}
        for name in self.config.get("suppliers", {}):
            results[name] = self.check_stock(name)
        return {"ok": True, "suppliers": results}
