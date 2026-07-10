"""
Order Flow Manager — полный цикл заказа (Этап C, 11 шагов).

Шаги:
  1. Покупка → проверка баланса поставщика
  2. Баланс 0 → CAPS-алерт в Telegram + снять лоты поставщика
  3. Ожидание пополнения (проверка каждую минуту)
  4. Баланс есть → приветствие + запрос ссылки + повторная проверка
  5. Ссылка получена → финальное подтверждение "напишите 'да'"
  6. Заказ поставщику → ошибка → вежливое уведомление клиента
  7. 25+ мин нет ответа → автовозврат + бонус
  8. Заказ выполнен → уведомление + просьба подтвердить и оставить отзыв
  9. Подтверждение заказа → благодарность
  10. Отзыв: 4-5⭐ → автоответ; 3⭐ → извинение; 2⭐ без причины → жалоба
  11. Все шаги → в БД
"""

import time
import threading
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger("FunPayHUB.OrderFlow")


class OrderFlowManager:
    """Управляет полным жизненным циклом заказа."""

    def __init__(self, seller_service, event_bus, telegram_bot_url: str = "",
                 admin_chat_id: str = ""):
        self._svc = seller_service
        self._eb = event_bus
        self._tg_bot_url = telegram_bot_url
        self._admin_chat_id = admin_chat_id
        self._orders: Dict[str, Dict[str, Any]] = {}  # funpay_order_id -> state
        self._lock = threading.RLock()
        self._worker = None
        self._stop = threading.Event()

        # Настройки
        self.TIMEOUT_MINUTES = 25
        self.CHECK_INTERVAL = 60      # проверка каждую минуту
        self.BONUS_TEXT = "При следующем заказе — 2 накрутки по цене одной ✨"

    # ── Публичный API ──────────────────────────────────────────────

    def start(self):
        """Запустить фоновый воркер."""
        self._eb.subscribe("new_order", self._on_new_order, priority=80)
        self._eb.subscribe("new_message", self._on_new_message, priority=80)
        self._eb.subscribe("review_received", self._on_review, priority=80)
        self._start_worker()
        logger.info("[OrderFlow] Manager started")

    def stop(self):
        self._stop.set()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=5)

    # ── Шаг 1: Покупка → проверка баланса ─────────────────────────

    def _on_new_order(self, event):
        """Шаг 1. Покупка лота — проверка баланса поставщика."""
        try:
            order_id = event.get("order_id") if isinstance(event, dict) else getattr(event, "order_id", None)
            chat_id = event.get("chat_id") if isinstance(event, dict) else getattr(event, "chat_id", None)
            price = event.get("price", 0) if isinstance(event, dict) else getattr(event, "price", 0)
            title = event.get("title", "") if isinstance(event, dict) else getattr(event, "title", "")
            buyer = event.get("buyer", "") if isinstance(event, dict) else getattr(event, "buyer", "")
            service_tag = self._extract_tag(title)

            if not order_id or not chat_id:
                return

            with self._lock:
                if order_id in self._orders:
                    return
                self._orders[order_id] = {
                    "funpay_order_id": order_id,
                    "chat_id": chat_id,
                    "price": price,
                    "title": title,
                    "buyer": buyer,
                    "service_tag": service_tag or "",
                    "step": 1,
                    "link": "",
                    "confirmed": False,
                    "supplier_order_id": "",
                    "supplier_name": "",
                    "started_at": time.time(),
                    "last_action": time.time(),
                    "timeout_refunded": False,
                    "bonus_given": False,
                }

            # Запись в БД
            self._db_create_order(order_id, price, buyer, chat_id, service_tag)

            # Шаг 2: проверка баланса поставщика
            balance_ok = self._check_supplier_balance(service_tag)
            if not balance_ok:
                self._handle_low_balance(order_id, service_tag)
            else:
                # Шаг 4: приветствие
                self._send_greeting(order_id)
                self._update_step(order_id, 4)

            logger.info(f"[OrderFlow] New order {order_id} tag={service_tag} balance_ok={balance_ok}")

        except Exception as e:
            logger.error(f"[OrderFlow] _on_new_order error: {e}")

    # ── Шаг 2: Баланс 0 → алерт + снять лоты ─────────────────────

    def _handle_low_balance(self, order_id: str, service_tag: str):
        """Баланса нет — капс-алерт и снятие лотов поставщика."""
        order = self._orders.get(order_id)
        if not order:
            return

        supplier = self._tag_to_supplier(service_tag)
        caps_msg = (
            f"🚨🚨🚨 НЕХВАТАЕТ СРЕДСТВ НА {supplier.upper()} 🚨🚨🚨\n"
            f"Заказ #{order_id} — {order.get('title', '')}\n"
            f"Сумма: {order.get('price', 0)}₽\n\n"
            f"📌 ПОПОЛНИТЕ {supplier} НА {order.get('price', 0) * 2}₽\n"
            f"Лоты {supplier} сняты с продажи до пополнения."
        )
        self._send_admin(caps_msg)
        self._deactivate_supplier_lots(supplier)
        self._update_step(order_id, 2)
        logger.warning(f"[OrderFlow] Low balance for {supplier} order {order_id}")

    # ── Шаг 3: Ожидание пополнения (воркер) ───────────────────────

    def _check_supplier_balance(self, service_tag: str) -> bool:
        """Проверить, хватает ли баланса поставщика для услуги."""
        try:
            if not service_tag:
                return True  # нет тега — пропускаем проверку
            supplier = self._tag_to_supplier(service_tag)
            if not supplier:
                return True
            # Баланс поставщика получаем из health-check или seller_service
            from runtime.http_client import HTTPClient
            hc = HTTPClient()
            data = hc.get(f"http://127.0.0.1:5000/api/seller/balance/suppliers", timeout=5)
            if data and isinstance(data, dict):
                sup_balance = float(data.get(supplier, {}).get("balance", 0))
                return sup_balance > 0
            return True
        except Exception:
            return True  # если не можем проверить — пропускаем

    def _deactivate_supplier_lots(self, supplier: str):
        """Снять с продажи лоты конкретного поставщика."""
        try:
            from runtime.http_client import HTTPClient
            hc = HTTPClient()
            hc.post("http://127.0.0.1:5000/api/seller/lots/deactivate",
                     json={"supplier": supplier}, timeout=10)
        except Exception:
            pass

    # ── Шаг 4: Приветствие + запрос ссылки ────────────────────────

    def _send_greeting(self, order_id: str):
        """Отправить приветственное сообщение клиенту."""
        order = self._orders.get(order_id)
        if not order:
            return
        chat_id = order["chat_id"]
        price = order["price"]
        title = order["title"]

        greeting = (
            f"👋 Привет! Спасибо за заказ!\n\n"
            f"📦 {title}\n"
            f"💰 {price}₽\n\n"
            f"Для выполнения укажите, пожалуйста, ссылку на профиль/канал:"
        )
        self._send_to_chat(chat_id, greeting)

    # ── Шаг 5: Подтверждение перед отправкой ──────────────────────

    def _on_new_message(self, event):
        """Обработка входящих сообщений от клиента."""
        try:
            chat_id = event.get("chat_id") if isinstance(event, dict) else getattr(event, "chat_id", None)
            text = (event.get("text") or "").strip()
            from_me = event.get("from_me", False)
            if from_me or not chat_id or not text:
                return

            # Ищем заказ по chat_id
            order = self._find_order_by_chat(chat_id)
            if not order:
                return

            order_id = order["funpay_order_id"]

            # Шаг 5: получили ссылку → финальное подтверждение
            if order["step"] == 4 and not order["confirmed"]:
                if self._looks_like_link(text):
                    order["link"] = text
                    self._db_update_order(order_id, link=text)
                    confirm_msg = (
                        f"🔍 Проверьте ссылку в последний раз:\n{text}\n\n"
                        f"⚠️ В случае ошибки возврат не делается.\n"
                        f"Уверены? Напишите 'да'"
                    )
                    self._send_to_chat(chat_id, confirm_msg)
                    self._update_step(order_id, 5)
                return

            # Подтверждение получено
            if order["step"] == 5 and not order["confirmed"]:
                if text.lower() in ("да", "yes", "ага", "ok", "го", "✅"):
                    order["confirmed"] = True
                    self._send_to_chat(chat_id, "✅ Принято! Отправляю заказ...")
                    self._send_order_to_supplier(order_id)
                else:
                    self._send_to_chat(chat_id, "Напишите 'да', если всё верно.")
                return

        except Exception as e:
            logger.error(f"[OrderFlow] _on_new_message error: {e}")

    # ── Шаг 6: Отправка поставщику ────────────────────────────────

    def _send_order_to_supplier(self, order_id: str):
        """Отправить заказ поставщику. Если ошибка — уведомить клиента."""
        order = self._orders.get(order_id)
        if not order:
            return

        service_tag = order.get("service_tag", "")
        link = order.get("link", "")
        chat_id = order["chat_id"]

        # Здесь плагин (AutoSMM/AutoDonate) обработает отправку через event_bus
        # Публикуем событие для плагина
        try:
            self._eb.publish("order_ready_for_supplier", {
                "order_id": order_id,
                "chat_id": chat_id,
                "link": link,
                "service_tag": service_tag,
                "price": order["price"],
            })
            self._update_step(order_id, 6)
            logger.info(f"[OrderFlow] Order {order_id} sent to supplier")
        except Exception as e:
            logger.error(f"[OrderFlow] Failed to send order {order_id}: {e}")
            self._send_to_chat(chat_id,
                "🙏 Возникла небольшая задержка при обработке заказа. "
                "Мы уже решаем вопрос, ожидайте, пожалуйста.")
            self._update_step(order_id, 6)

    # ── Шаг 7: 25+ минут → автовозврат ────────────────────────────

    def _process_timeouts(self):
        """Проверить заказы, которые висят дольше TIMEOUT_MINUTES."""
        now = time.time()
        to_refund = []

        with self._lock:
            for oid, order in self._orders.items():
                if order.get("timeout_refunded"):
                    continue
                if order["step"] < 6:
                    continue  # ещё не отправили поставщику
                elapsed = now - order.get("last_action", order["started_at"])
                if elapsed >= self.TIMEOUT_MINUTES * 60:
                    to_refund.append(oid)

        for oid in to_refund:
            self._do_auto_refund(oid)

    def _do_auto_refund(self, order_id: str):
        """Автовозврат + бонус."""
        order = self._orders.get(order_id)
        if not order:
            return

        chat_id = order["chat_id"]
        price = order["price"]

        # Возврат через seller_service
        try:
            self._svc.refund_order(order_id, dry_run=False)
        except Exception as e:
            logger.error(f"[OrderFlow] Refund failed for {order_id}: {e}")

        # Сообщение клиенту
        refund_msg = (
            f"🙏 Простите за долгое ожидание!\n\n"
            f"К сожалению, выполнение заказа заняло больше времени, "
            f"чем обычно. Я оформил возврат — средства вернутся в "
            f"течение 24 часов.\n\n"
            f"🎁 {self.BONUS_TEXT}"
        )
        self._send_to_chat(chat_id, refund_msg)

        # Админ-уведомление
        admin_msg = (
            f"❌ АВТОВОЗВРАТ #{order_id}\n"
            f"Причина: превышен лимит {self.TIMEOUT_MINUTES} мин\n"
            f"Сумма: {price}₽\n"
            f"{f'🎁 Бонус: {self.BONUS_TEXT}' if not order.get('bonus_given') else ''}"
        )
        self._send_admin(admin_msg)

        order["timeout_refunded"] = True
        order["bonus_given"] = True
        self._update_step(order_id, 7)
        self._db_update_order(order_id, status="refunded", timeout_refunded=True)
        logger.info(f"[OrderFlow] Auto-refund for {order_id}")

    # ── Шаг 8: Заказ выполнен → уведомление ───────────────────────

    def on_order_completed(self, order_id: str, details: Optional[str] = None):
        """Вызывается плагином когда поставщик подтвердил выполнение."""
        order = self._orders.get(order_id)
        if not order:
            return

        chat_id = order["chat_id"]
        title = order["title"]

        completed_msg = (
            f"✅ Заказ выполнен!\n\n"
            f"📦 {title}\n"
            f"📋 {details or ''}\n\n"
            f"Пожалуйста, подтвердите получение и оставьте отзыв 🙏"
        )
        self._send_to_chat(chat_id, completed_msg)
        self._update_step(order_id, 8)
        self._db_update_order(order_id, status="completed")
        logger.info(f"[OrderFlow] Order {order_id} completed")

    # ── Шаг 9: Подтверждение заказа → благодарность ───────────────

    def on_order_confirmed(self, order_id: str):
        """Клиент подтвердил заказ (деньги ушли на баланс FunPay)."""
        order = self._orders.get(order_id)
        if not order:
            return

        chat_id = order["chat_id"]
        thank_you = (
            f"🎉 Спасибо за заказ! Рады, что всё понравилось.\n"
            f"Будем рады видеть вас снова 😊"
        )
        self._send_to_chat(chat_id, thank_you)
        self._update_step(order_id, 9)
        logger.info(f"[OrderFlow] Order {order_id} confirmed by buyer")

    # ── Шаг 10: Отзыв → реакция по рейтингу ───────────────────────

    def _on_review(self, event):
        """Обработка отзыва."""
        try:
            order_id = event.get("order_id") if isinstance(event, dict) else getattr(event, "order_id", None)
            rating = int(event.get("rating", 0) if isinstance(event, dict) else getattr(event, "rating", 0))
            text = event.get("text", "") if isinstance(event, dict) else getattr(event, "text", "")
            chat_id = event.get("chat_id") if isinstance(event, dict) else getattr(event, "chat_id", None)

            if not order_id or not rating:
                return

            order = self._orders.get(order_id)
            title = order.get("title", "Заказ") if order else "Заказ"

            # Запись в БД
            self._db_create_review(order_id, rating, text)

            if rating >= 4:
                reply = (
                    f"🙏 Спасибо за {rating}⭐, {title}!\n"
                    f"Рады, что вам понравилось. Обращайтесь ещё 😊"
                )
            elif rating == 3:
                reply = (
                    f"Спасибо за отзыв! Нам важно ваше мнение. "
                    f"Если были какие-то проблемы — напишите, всё исправим 🤝"
                )
            else:
                # 1-2 звезды
                if text and self._has_valid_complaint(text):
                    reply = (
                        f"Извините за доставленные неудобства. "
                        f"Мы обязательно учтём ваш опыт и станем лучше 🙏"
                    )
                else:
                    # Без объективной причины — подать жалобу в админку FunPay
                    reply = ""
                    self._file_unfair_review_complaint(order_id, rating, text)

            if reply and chat_id:
                try:
                    self._svc.send_chat_message(chat_id, reply, dry_run=False)
                except Exception as e:
                    logger.error(f"[OrderFlow] Review reply failed: {e}")

            self._update_step(order_id, 10)
            logger.info(f"[OrderFlow] Review {rating}⭐ for {order_id}")

        except Exception as e:
            logger.error(f"[OrderFlow] _on_review error: {e}")

    def _has_valid_complaint(self, text: str) -> bool:
        """Проверяет, есть ли в отзыве объективная причина."""
        reasons = ["долго", "не работает", "не пришло", "обман", "кидалово",
                    "не зачли", "плохо", "ужасно", "верните"]
        return any(r in text.lower() for r in reasons)

    def _file_unfair_review_complaint(self, order_id: str, rating: int, text: str):
        """Подать жалобу на необоснованный низкий отзыв."""
        msg = (
            f"⚠️ ЖАЛОБА НА НЕОБОСНОВАННЫЙ ОТЗЫВ\n"
            f"Заказ #{order_id}\n"
            f"Оценка: {rating}⭐\n"
            f"Текст: {text[:200]}\n\n"
            f"Рекомендуется подать жалобу в администрацию FunPay."
        )
        self._send_admin(msg)

    # ── Вспомогательные методы ─────────────────────────────────────

    def _extract_tag(self, title: str) -> str:
        """Извлечь маркер услуги из названия лота: [AS#123]."""
        try:
            from runtime.plugin_markers import parse_marker
            result = parse_marker(title)
            if result:
                code, srv_id = result
                return f"{code}#{srv_id}"
            return ""
        except Exception:
            return ""

    def _tag_to_supplier(self, tag: str) -> str:
        """Определить поставщика по маркеру."""
        tag_up = tag.upper()
        if tag_up.startswith("AS#"):
            return "twiboost"
        elif tag_up.startswith("GB#"):
            return "gorgonaboosts"
        elif tag_up.startswith("HB#"):
            return "holdboost"
        elif tag_up.startswith("KS#"):
            return "kosell"
        elif tag_up.startswith("SC#"):
            return "shopclaude"
        elif tag_up.startswith("ST#"):
            return "fragment"
        return ""

    def _looks_like_link(self, text: str) -> bool:
        """Проверить, похож ли текст на ссылку."""
        text = text.lower().strip()
        return any(text.startswith(p) for p in ["http", "t.me", "@", "https"])

    def _find_order_by_chat(self, chat_id: str) -> Optional[Dict]:
        """Найти активный заказ по chat_id."""
        with self._lock:
            for oid, order in self._orders.items():
                if order.get("chat_id") == chat_id and order["step"] < 10:
                    return order
        return None

    def _update_step(self, order_id: str, step: int):
        """Обновить шаг заказа."""
        with self._lock:
            order = self._orders.get(order_id)
            if order:
                order["step"] = step
                order["last_action"] = time.time()

    def _send_to_chat(self, chat_id: str, text: str):
        """Отправить сообщение клиенту на FunPay."""
        try:
            self._svc.send_chat_message(chat_id, text, dry_run=False)
        except Exception as e:
            logger.error(f"[OrderFlow] Send to chat {chat_id} failed: {e}")

    def _send_admin(self, text: str):
        """Отправить админ-сообщение в Telegram."""
        if not text or not self._admin_chat_id:
            return
        try:
            from runtime.http_client import HTTPClient
            hc = HTTPClient()
            hc.post(
                f"{self._tg_bot_url}/sendMessage",
                json={"chat_id": self._admin_chat_id, "text": text,
                       "parse_mode": "HTML"},
                timeout=10,
            )
        except Exception:
            pass

    # ── Работа с БД ───────────────────────────────────────────────

    def _db_create_order(self, funpay_order_id: str, price: float,
                          buyer: str, chat_id: str, service_tag: str):
        try:
            from runtime.database.repository import Repository
            Repository.create_order(
                funpay_order_id=funpay_order_id,
                price=price,
                buyer_name=buyer,
                chat_id=chat_id,
                service_tag=service_tag,
            )
        except Exception:
            pass

    def _db_update_order(self, order_id: str, **kw):
        try:
            from runtime.database.repository import Repository
            Repository.update_order_status(order_id, **kw)
        except Exception:
            pass

    def _db_create_review(self, order_id: str, rating: int, text: str):
        try:
            from runtime.database.repository import Repository
            # Найти order_id в PO
            from runtime.database.base import get_session
            from runtime.database.models import Order
            session = get_session()
            try:
                order = session.query(Order).filter(
                    Order.funpay_order_id == order_id).first()
                if order:
                    Repository.create_review(
                        order_id=order.id,
                        rating=rating,
                        text=text or "",
                    )
            finally:
                session.close()
        except Exception:
            pass

    # ── Фоновый воркер ─────────────────────────────────────────────

    def _start_worker(self):
        def _loop():
            while not self._stop.is_set():
                try:
                    self._process_timeouts()
                except Exception as e:
                    logger.error(f"[OrderFlow] Worker error: {e}")
                time.sleep(self.CHECK_INTERVAL)
        self._worker = threading.Thread(target=_loop, name="OrderFlow", daemon=True)
        self._worker.start()
