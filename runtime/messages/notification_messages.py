from __future__ import annotations

from typing import Any, Dict, Optional
from .message_manager import MessageManager


class NotificationMessages:
    def __init__(self, message_manager: MessageManager, db_provider: Any = None) -> None:
        self._mm = message_manager
        self._db = db_provider

    def admin_new_order(self, order: Dict[str, Any]) -> bool:
        context = {
            "order_id": order.get("funpay_order_id", ""),
            "price": order.get("price", 0),
            "buyer": order.get("buyer", ""),
            "order_title": self._mm.formatter.build_order_title(order),
        }
        return self._mm.send_admin("notification", "admin_new_order", context)

    def admin_supplier_down(self, order_id: str, supplier: str, price: float) -> bool:
        context = {
            "order_id": order_id,
            "supplier": supplier,
            "price": price,
            "need": price * 2,
        }
        return self._mm.send_admin("notification", "admin_supplier_down", context)

    def admin_refund(self, order_id: str, buyer: str, price: float) -> bool:
        context = {
            "order_id": order_id,
            "buyer": buyer,
            "price": price,
        }
        return self._mm.send_admin("notification", "admin_refund", context)

    def admin_plugin_error(self, plugin_name: str, error: str) -> bool:
        context = {
            "plugin_name": plugin_name,
            "error": error,
        }
        return self._mm.send_admin("notification", "admin_plugin_error", context)

    def admin_funpay_unavailable(self) -> bool:
        return self._mm.send_admin("notification", "admin_funpay_unavailable", {})

    def admin_order_timeout(self, order_id: str, stage: str, chat_id: str, price: float) -> bool:
        context = {
            "order_id": order_id,
            "stage": stage,
            "chat_id": chat_id,
            "price": price,
        }
        return self._mm.send_admin("notification", "admin_order_timeout", context)
