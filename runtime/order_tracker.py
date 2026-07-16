"""
Order Payment Tracker for FunPay Hub.

Tracks pending orders, sends Telegram pings every 60 seconds,
and handles refunds after timeout (25 minutes).
Uses MessageManager for all buyer-facing messages.
"""
import json
import time
import threading
from runtime.http_client import HTTPClient
from pathlib import Path
from typing import Optional, Dict, Any
from runtime.messages.message_manager import MessageManager
from runtime.messages.order_messages import OrderMessages
from runtime.messages.error_messages import ErrorMessages
from runtime.messages.notification_messages import NotificationMessages

_http_client = HTTPClient(max_retries=3)


def _project_root() -> Path:
    import sys, os
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _tg_config() -> Dict[str, str]:
    try:
        cfg_path = _project_root() / "configs" / "plugins" / "telegram_notifier_plugin.json"
        if cfg_path.exists():
            return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


class OrderPaymentTracker:
    def __init__(self, event_bus, seller_service, telegram_bot_url: str = "", admin_chat_id: str = "", message_manager: Optional[MessageManager] = None):
        self.event_bus = event_bus
        self.svc = seller_service
        self.tg_bot_url = telegram_bot_url
        self.admin_chat_id = admin_chat_id or _tg_config().get("chat_id", "")
        self._path = _project_root() / "data" / "state" / "pending_orders.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.pending_orders: Dict[str, Dict[str, Any]] = {}
        self._load_pending()
        self._lock = threading.RLock()
        self._worker = None
        self._stop = threading.Event()
        self._msg_manager = message_manager
        self._order_msgs = OrderMessages(message_manager) if message_manager else None
        self._error_msgs = ErrorMessages(message_manager) if message_manager else None
        self._notif_msgs = NotificationMessages(message_manager) if message_manager else None

    def set_message_manager(self, mm: MessageManager):
        self._msg_manager = mm
        self._order_msgs = OrderMessages(mm)
        self._error_msgs = ErrorMessages(mm)
        self._error_msgs = ErrorMessages(mm)
        self._notif_msgs = NotificationMessages(mm)

    def _load_pending(self):
        try:
            if self._path.exists():
                raw = self._path.read_text(encoding="utf-8")
                self.pending_orders = json.loads(raw) if raw.strip() else {}
            else:
                self.pending_orders = {}
        except Exception:
            self.pending_orders = {}

    def _save_pending(self):
        try:
            self._path.write_text(
                json.dumps(self.pending_orders, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def start(self):
        if not self.event_bus:
            return
        self.event_bus.subscribe("new_order", self._on_new_order, priority=90)
        self._start_worker()

    def stop(self):
        self._stop.set()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=5)

    def _start_worker(self):
        def _loop():
            while not self._stop.is_set():
                time.sleep(60)
                with self._lock:
                    now = time.time()
                    to_process = []
                    to_remove = []
                    for oid, data in self.pending_orders.items():
                        elapsed = now - data["start_time"]
                        if elapsed >= 25 * 60:
                            to_process.append(("refund", oid))
                            to_remove.append(oid)
                        elif elapsed >= data["next_ping"] and data["pings_sent"] < 3:
                            to_process.append(("ping", oid))
                        elif elapsed >= 3 * 60 and data["pings_sent"] >= 3:
                            to_process.append(("warning", oid))
                    for action, oid in to_process:
                        try:
                            self._process_action(action, oid)
                        except Exception as e:
                            print(f"[OrderTracker] {action} error for {oid}: {e}")
                    for oid in to_remove:
                        self.pending_orders.pop(oid, None)
                    if to_remove:
                        self._save_pending()

        self._worker = threading.Thread(target=_loop, name="OrderTracker", daemon=True)
        self._worker.start()

    def _process_action(self, action: str, order_id: str):
        data = self.pending_orders.get(order_id)
        if not data:
            return
        chat_id = data.get("chat_id")
        lot_title = data.get("lot_title", "")
        service_name = data.get("service_name", "")
        price = data.get("price", 0)
        order_url = data.get("url", f"https://funpay.com/orders/{order_id}/")

        if action == "ping":
            ping_num = data["pings_sent"] + 1
            data["pings_sent"] = ping_num
            data["pings_sent"] = ping_num
            data["next_ping"] = data["start_time"] + 60 * ping_num
            self._save_pending()
            text = (
                f"🛒 НОВАЯ ПОКУПКА!\n\n"
                f"📦 Лот: \"{lot_title}\"\n"
                f"🔧 Сервис: {service_name}\n"
                f"💰 Сумма: {price} ₽\n"
                f"🔗 Ссылка: {order_url}\n\n"
                f"⏱ Ожидание пополнения... ({ping_num}/3)"
            )
            self._send_tg(text)
            self._send_timeout_warning(chat_id, order_id, lot_title)

        elif action == "warning":
            data["warned"] = True
            self._save_pending()
            text = (
                f"🚨 ПОСЛЕДНЕЕ ПРЕДУПРЕЖДЕНИЕ ({data['pings_sent']}/3)\n\n"
                f"📦 Лот: \"{lot_title}\"\n"
                f"🔧 Сервис: {service_name}\n"
                f"⏱ Через 1 минуту будет оформлен возврат"
            )
            self._send_tg(text)

        elif action == "refund":
            self._do_refund(order_id, data)

    def _send_timeout_warning(self, chat_id: str, order_id: str, lot_title: str):
        if not chat_id:
            return
        text = f"⏱ Уважаемый покупатель, платеж за заказ #{order_id} пока не поступил. Если возникли проблемы — напишите."
        if self._msg_manager:
            self._msg_manager.send(order_id, chat_id, "order", "link_request", {"order_id": order_id})
        else:
            try:
                self.svc.send_chat_message(chat_id, text, dry_run=False)
            except Exception:
                pass

    def _do_refund(self, order_id: str, data: Dict[str, Any]):
        chat_id = data.get("chat_id")
        lot_title = data.get("lot_title", "")
        try:
            self.svc.refund_order(order_id, dry_run=False)
        except Exception as e:
            print(f"[OrderTracker] refund failed for {order_id}: {e}")
        admin_text = (
            f"❌ Заказ #{order_id} — возврат оформлен.\n"
            f"Причина: баланс не пополнен за 25 мин\n\n"
            f"📦 Лот: \"{lot_title}\""
        )
        self._send_tg(admin_text)
        buyer_text = (
            f"🙏 Простите за ожидание!\n\n"
            f"К сожалению, платеж не поступил. Оформляю возврат — средства вернутся в течение 24 часов."
        )
        if chat_id:
            if self._msg_manager:
                self._msg_manager.send(order_id, chat_id, "order", "refund", {"order_id": order_id})
            else:
                try:
                    self.svc.send_chat_message(chat_id, buyer_text, dry_run=False)
                except Exception:
                    pass

    def _send_tg(self, text: str):
        if not text or not self.admin_chat_id:
            return
        try:
            tg = _tg_config()
            token = tg.get("bot_token", "")
            if token:
                _http_client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": self.admin_chat_id, "text": text, "parse_mode": "HTML"},
                    timeout=10,
                )
        except Exception:
            pass

    def _on_new_order(self, event):
        try:
            order_id = event.get("order_id") if isinstance(event, dict) else getattr(event, "order_id", None)
            chat_id = event.get("chat_id") if isinstance(event, dict) else getattr(event, "chat_id", None)
            price = event.get("price", 0) if isinstance(event, dict) else getattr(event, "price", 0)
            title = event.get("title", "") if isinstance(event, dict) else getattr(event, "title", "")
            url = event.get("url", "") if isinstance(event, dict) else getattr(event, "url", "")
            buyer = event.get("buyer", "") if isinstance(event, dict) else getattr(event, "buyer", "")
            if not order_id or not chat_id:
                return
            with self._lock:
                if order_id in self.pending_orders:
                    return
                self.pending_orders[order_id] = {
                    "start_time": time.time(),
                    "next_ping": time.time() + 60,
                    "pings_sent": 0,
                    "warned": False,
                    "chat_id": chat_id,
                    "lot_title": title,
                    "service_name": "",
                    "price": price,
                    "price": price,
                    "url": url or f"https://funpay.com/orders/{order_id}/",
                }
                self._save_pending()
            print(f"[OrderTracker] Tracking order {order_id}")
            try:
                from runtime.database.repository import Repository
                import os
                source = "simulation" if os.environ.get("FUNPAYHUB_SIMULATION") == "1" else "real"
                Repository.create_order(
                    funpay_order_id=order_id,
                    price=price,
                    buyer_name=buyer,
                    chat_id=chat_id,
                    source=source,
                )
            except Exception as db_e:
                print(f"[OrderTracker] DB persist error: {db_e}")
        except Exception as e:
            print(f"[OrderTracker] _on_new_order error: {e}")

    def check_balance_filled(self, order_id: str) -> bool:
        try:
            bal = self.svc.get_balance()
            if bal.get("available"):
                return float(bal.get("available_rub") or bal.get("total_rub") or 0) > 0
        except Exception:
            pass
        return False

    def send_refund(self, order_id: str):
        data = self.pending_orders.get(order_id)
        if data:
            self._do_refund(order_id, data)


_tracker_singleton = None


def get_tracker(event_bus=None, seller_service=None, message_manager=None) -> Optional[OrderPaymentTracker]:
    global _tracker_singleton
    if _tracker_singleton is None and event_bus and seller_service:
        _tracker_singleton = OrderPaymentTracker(event_bus, seller_service, message_manager=message_manager)
        _tracker_singleton.start()
    return _tracker_singleton


# ====================================================================
# Supplier Order Registry — idempotency guard
#
# Prevents creating duplicate orders at an external supplier for the
# same FunPay order.  Stores a simple JSON mapping:
#   funpay_order_id -> {supplier, supplier_order_id, created_at}
# ====================================================================

class SupplierOrderRegistry:
    """
    Lightweight, file-backed registry that answers "have we already
    created a supplier order for this FunPay order_id *from this
    supplier*?"  Used by AutoSMM and AutoDonate plugins to guarantee
    idempotency.
    """

    def __init__(self, storage_path: Optional[str] = None):
        if storage_path:
            self._path = Path(storage_path)
        else:
            self._path = _project_root() / "data" / "state" / "supplier_orders.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._data: Dict[str, dict] = {}
        self._load()

    def is_registered(self, funpay_order_id: str, supplier: str) -> bool:
        with self._lock:
            entry = self._data.get(str(funpay_order_id))
            if entry and entry.get("supplier") == supplier:
                return True
            return False

    def get_supplier_order_id(self, funpay_order_id: str) -> Optional[str]:
        with self._lock:
            entry = self._data.get(str(funpay_order_id))
            if entry:
                return entry.get("supplier_order_id")
            return None

    def register(self, funpay_order_id: str, supplier: str,
                 supplier_order_id: str):
        with self._lock:
            self._data[str(funpay_order_id)] = {
                "supplier": supplier,
                "supplier_order_id": str(supplier_order_id),
                "created_at": time.time(),
            }
        self._save()

    def remove(self, funpay_order_id: str):
        with self._lock:
            self._data.pop(str(funpay_order_id), None)
        self._save()

    def _load(self):
        try:
            if self._path.exists():
                raw = self._path.read_text(encoding="utf-8")
                self._data = json.loads(raw) if raw.strip() else {}
            else:
                self._data = {}
        except Exception:
            self._data = {}

    def _save(self):
        try:
            self._path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass


_supplier_order_registry: Optional[SupplierOrderRegistry] = None


def get_supplier_order_registry() -> SupplierOrderRegistry:
    global _supplier_order_registry
    if _supplier_order_registry is None:
        _supplier_order_registry = SupplierOrderRegistry()
    return _supplier_order_registry
