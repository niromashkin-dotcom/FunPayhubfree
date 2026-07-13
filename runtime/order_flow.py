"""
Order Flow Manager — полный цикл заказа через Customer Communication Engine.

Все сообщения покупателю отправляются ТОЛЬКО через MessageManager + ScenarioEngine.
Никаких сырых строк в коде.
"""

import time
import threading
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from runtime.messages.message_manager import MessageManager
from runtime.messages.scenario import ScenarioEngine
from runtime.messages.order_messages import OrderMessages
from runtime.messages.error_messages import ErrorMessages
from runtime.messages.review_messages import ReviewMessages
from runtime.messages.notification_messages import NotificationMessages
from runtime.messages.recovery_messages import RecoveryMessages

logger = logging.getLogger("FunPayHUB.OrderFlow")


class OrderFlowManager:
    """Управляет полным жизненным циклом заказа через CCE."""

    def __init__(self, seller_service, event_bus, telegram_bot_url: str = "", admin_chat_id: str = ""):
        self._svc = seller_service
        self._eb = event_bus
        self._tg_bot_url = telegram_bot_url
        self._admin_chat_id = admin_chat_id
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._worker = None
        self._stop = threading.Event()

        self._msg_manager = MessageManager(sender=seller_service, admin_chat_id=admin_chat_id)
        self._scenario = ScenarioEngine(self._msg_manager)
        self._error_msgs = ErrorMessages(self._msg_manager)
        self._review_msgs = ReviewMessages(self._msg_manager)
        self._notif_msgs = NotificationMessages(self._msg_manager)
        self._recovery_msgs = RecoveryMessages(self._msg_manager)

        self.TIMEOUT_MINUTES = 25
        self.CHECK_INTERVAL = 5
        self.BONUS_TEXT = "При следующем заказе — 2 накрутки по цене одной ✨"

    def start(self):
        self._eb.subscribe("new_order", self._on_new_order, priority=80)
        self._eb.subscribe("new_message", self._on_new_message, priority=80)
        self._eb.subscribe("review_received", self._on_review, priority=80)
        self._eb.subscribe("order_cancelled", self._on_order_cancelled, priority=80)
        self._start_worker()
        logger.info("[OrderFlow] Manager started")

    def stop(self):
        self._stop.set()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=5)

    def _on_new_order(self, event):
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
                    "status": "pending",
                }

            self._db_create_order(order_id, price, buyer, chat_id, service_tag)

            balance_ok = self._check_supplier_balance(service_tag)
            if not balance_ok:
                self._handle_low_balance(order_id, service_tag)
            else:
                order = self._orders[order_id]
                self._scenario.execute_for_stage(order_id, chat_id, order)
                self._update_step(order_id, 4)

            logger.info(f"[OrderFlow] New order {order_id} tag={service_tag} balance_ok={balance_ok}")

        except Exception as e:
            logger.error(f"[OrderFlow] _on_new_order error: {e}")

    def _on_order_cancelled(self, event, event_type=None):
        try:
            if isinstance(event, str):
                event_type, event = event, event_type
            order_id = event.get("order_id") if isinstance(event, dict) else getattr(event, "order_id", None)
            if not order_id:
                return
            order = self._orders.get(order_id)
            if not order:
                return
            order["status"] = "cancelled"
            self._update_step(order_id, 9)
            self._db_update_order(order_id, status="cancelled")
            OrderMessages(self._msg_manager).on_cancelled(order_id, order["chat_id"], order)
            logger.info(f"[OrderFlow] Order {order_id} cancelled by buyer")
        except Exception as e:
            logger.error(f"[OrderFlow] _on_order_cancelled error: {e}")

    def _handle_low_balance(self, order_id: str, service_tag: str):
        order = self._orders.get(order_id)
        if not order:
            return
        supplier = self._tag_to_supplier(service_tag)
        price = order.get("price", 0)
        caps_msg = (
            f"🚨 НЕХВАТАЕТ СРЕДСТВ НА {supplier.upper()} 🚨\n"
            f"Заказ #{order_id}\n"
            f"Сумма: {price}₽\n\n"
            f"📌 ПОПОЛНИТЕ {supplier} НА {price * 2}₽\n"
            f"Лоты {supplier} сняты с продажи до пополнения."
        )
        self._send_admin(caps_msg)
        self._deactivate_supplier_lots(supplier)
        self._update_step(order_id, 2)
        self._error_msgs.supplier_balance_zero(order_id, order["chat_id"])
        logger.warning(f"[OrderFlow] Low balance for {supplier} order {order_id}")

    def _check_supplier_balance(self, service_tag: str) -> bool:
        try:
            if not service_tag:
                return True
            supplier = self._tag_to_supplier(service_tag)
            if not supplier:
                return True
            from runtime.http_client import HTTPClient
            from bot.config import get_hub_url
            hc = HTTPClient()
            data = hc.get(f"{get_hub_url()}/api/seller/balance/suppliers", timeout=5)
            if data and isinstance(data, dict):
                entry = data.get(supplier)
                if isinstance(entry, dict) and isinstance(entry.get("balance"), (int, float)):
                    return float(entry["balance"]) > 0
            return True
        except Exception:
            return True

    def _deactivate_supplier_lots(self, supplier: str):
        try:
            from runtime.http_client import HTTPClient
            from bot.config import get_hub_url
            hc = HTTPClient()
            hc.post(f"{get_hub_url()}/api/seller/lots/deactivate", json={"supplier": supplier}, timeout=10)
        except Exception:
            pass

    def _on_new_message(self, event):
        try:
            chat_id = event.get("chat_id") if isinstance(event, dict) else getattr(event, "chat_id", None)
            text = (event.get("text") or "").strip()
            from_me = event.get("from_me", False)
            if from_me or not chat_id or not text:
                return

            order = self._find_order_by_chat(chat_id)
            if not order:
                return
            order_id = order["funpay_order_id"]

            if order["step"] == 4 and not order["confirmed"]:
                if self._looks_like_link(text):
                    order["link"] = text
                    self._db_update_order(order_id, link=text)
                    order_messages = OrderMessages(self._msg_manager)
                    order_messages.on_link_received(order_id, chat_id, text)
                    self._update_step(order_id, 5)
                return

            if order["step"] == 5 and not order["confirmed"]:
                if text.lower() in ("да", "yes", "ага", "ок", "✅"):
                    order["confirmed"] = True
                    order_messages = OrderMessages(self._msg_manager)
                    order_messages.on_confirm(order_id, chat_id)
                    self._send_order_to_supplier(order_id)
                else:
                    OrderMessages(self._msg_manager).on_link_request(order_id, chat_id)
                return

        except Exception as e:
            logger.error(f"[OrderFlow] _on_new_message error: {e}")

    def _send_order_to_supplier(self, order_id: str):
        order = self._orders.get(order_id)
        if not order:
            return
        service_tag = order.get("service_tag", "")
        link = order.get("link", "")
        chat_id = order["chat_id"]

        try:
            self._eb.publish("order_ready_for_supplier", {
                "order_id": order_id,
                "chat_id": chat_id,
                "link": link,
                "service_tag": service_tag,
                "price": order["price"],
            })
            OrderMessages(self._msg_manager).on_sent_to_supplier(order_id, chat_id)
            self._update_step(order_id, 6)
            logger.info(f"[OrderFlow] Order {order_id} sent to supplier")
        except Exception as e:
            logger.error(f"[OrderFlow] Failed to send order {order_id}: {e}")
            self._error_msgs.supplier_error(order_id, chat_id)
            self._update_step(order_id, 6)

    def _process_timeouts(self):
        now = time.time()
        to_refund = []
        with self._lock:
            for oid, order in self._orders.items():
                if order.get("timeout_refunded"):
                    continue
                if order["step"] < 6:
                    continue
                elapsed = now - order.get("last_action", order["started_at"])
                if elapsed >= self.TIMEOUT_MINUTES * 60:
                    to_refund.append(oid)

        for oid in to_refund:
            self._do_auto_refund(oid)

    def _do_auto_refund(self, order_id: str):
        order = self._orders.get(order_id)
        if not order:
            return
        chat_id = order["chat_id"]
        price = order["price"]

        try:
            self._svc.refund_order(order_id, dry_run=False)
        except Exception as e:
            logger.error(f"[OrderFlow] Refund failed for {order_id}: {e}")

        refund_msg = (
            f"🙏 Простите за долгое ожидание!\n\n"
            f"К сожалению, выполнение заказа заняло больше времени, "
            f"чем обычно. Я оформил возврат — средства вернутся в "
            f"течение 24 часов.\n\n"
            f"🎁 {self.BONUS_TEXT}"
        )
        self._send_to_chat(chat_id, refund_msg, order_id)

        admin_msg = (
            f"❌ АВТОВОЗВРАТ #{order_id}\n"
            f"Причина: превышен лимит {self.TIMEOUT_MINUTES} мин\n"
            f"Сумма: {price}₽\n"
            f"{'🎁 Бонус: ' + self.BONUS_TEXT if not order.get('bonus_given') else ''}"
        )
        self._send_admin(admin_msg)

        order["timeout_refunded"] = True
        order["bonus_given"] = True
        self._update_step(order_id, 7)
        self._db_update_order(order_id, status="refunded", timeout_refunded=True)
        logger.info(f"[OrderFlow] Auto-refund for {order_id}")

    def on_order_completed(self, order_id: str, details: Optional[str] = None):
        order = self._orders.get(order_id)
        if not order:
            return
        chat_id = order["chat_id"]
        OrderMessages(self._msg_manager).on_completed(order_id, chat_id, order)
        self._update_step(order_id, 8)
        self._db_update_order(order_id, status="completed")
        logger.info(f"[OrderFlow] Order {order_id} completed")

    def on_order_confirmed(self, order_id: str):
        order = self._orders.get(order_id)
        if not order:
            return
        chat_id = order["chat_id"]
        OrderMessages(self._msg_manager).on_thanks(order_id, chat_id)
        self._update_step(order_id, 9)
        logger.info(f"[OrderFlow] Order {order_id} confirmed by buyer")

    def _on_review(self, event):
        try:
            order_id = event.get("order_id") if isinstance(event, dict) else getattr(event, "order_id", None)
            rating = int(event.get("rating", 0) if isinstance(event, dict) else getattr(event, "rating", 0))
            text = event.get("text", "") if isinstance(event, dict) else getattr(event, "text", "")
            chat_id = event.get("chat_id") if isinstance(event, dict) else getattr(event, "chat_id", None)

            if not order_id or not rating:
                return

            order = self._orders.get(order_id)
            title = order.get("title", "Заказ") if order else "Заказ"

            self._db_create_review(order_id, rating, text)

            if rating >= 4:
                self._review_msgs.on_positive_review(order_id, chat_id, order)
            elif rating == 3:
                self._review_msgs.on_neutral_review(order_id, chat_id)
            else:
                if text and self._has_valid_complaint(text):
                    self._review_msgs.on_negative_review(order_id, chat_id)
                else:
                    self._file_unfair_review_complaint(order_id, rating, text)

            self._update_step(order_id, 10)
            logger.info(f"[OrderFlow] Review {rating}⭐ for {order_id}")

        except Exception as e:
            logger.error(f"[OrderFlow] _on_review error: {e}")

    def _has_valid_complaint(self, text: str) -> bool:
        reasons = ["долго", "не работает", "не пришло", "обман", "кидалово",
                    "не зачли", "плохо", "ужасно", "верните"]
        return any(r in text.lower() for r in reasons)

    def _file_unfair_review_complaint(self, order_id: str, rating: int, text: str):
        msg = (
            f"⚠️ ЖАЛОБА НА НЕОБОСНОВАННЫЙ ОТЗЫВ\n"
            f"Заказ #{order_id}\n"
            f"Оценка: {rating}⭐\n"
            f"Текст: {text[:200]}\n\n"
            f"Рекомендуется подать жалобу в администрацию FunPay."
        )
        self._send_admin(msg)

    def _extract_tag(self, title: str) -> str:
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
        text = text.lower().strip()
        return any(text.startswith(p) for p in ["http", "t.me", "@", "https"])

    def _find_order_by_chat(self, chat_id: str) -> Optional[Dict]:
        with self._lock:
            for oid, order in self._orders.items():
                if order.get("chat_id") == chat_id and order["step"] < 10:
                    return order
        return None

    def _update_step(self, order_id: str, step: int):
        with self._lock:
            order = self._orders.get(order_id)
            if order:
                order["step"] = step
                order["last_action"] = time.time()

    def _send_to_chat(self, chat_id: str, text: str, order_id: str = ""):
        try:
            self._msg_manager.send(order_id, chat_id, "order", "raw", {"text": text}, force=True)
        except Exception as e:
            logger.error(f"[OrderFlow] Send to chat {chat_id} failed: {e}")

    def _send_admin(self, text: str):
        if not text or not self._admin_chat_id:
            return
        try:
            self._msg_manager.send_admin("notification", "admin_system", {"text": text})
        except Exception:
            pass

    def _db_create_order(self, funpay_order_id: str, price: float, buyer: str, chat_id: str, service_tag: str):
        try:
            from runtime.database.repository import Repository
            import os
            source = "simulation" if os.environ.get("FUNPAYHUB_SIMULATION") == "1" else "real"
            Repository.create_order(
                funpay_order_id=funpay_order_id,
                price=price,
                buyer_name=buyer,
                chat_id=chat_id,
                service_tag=service_tag,
                source=source,
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
            from runtime.database.base import get_session
            from runtime.database.models import Order
            session = get_session()
            try:
                order = session.query(Order).filter(Order.funpay_order_id == order_id).first()
                if order:
                    Repository.create_review(order_id=order.id, rating=rating, text=text or "")
            finally:
                session.close()
        except Exception:
            pass

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
