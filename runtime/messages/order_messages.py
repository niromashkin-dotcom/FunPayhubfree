from __future__ import annotations

from typing import Any, Dict, Optional
from .message_manager import MessageManager
from .formatter import MessageFormatter
from .stage_detector import (
    ORDER_STAGE_GREETING,
    ORDER_STAGE_LINK_REQUEST,
    ORDER_STAGE_CONFIRM,
    ORDER_STAGE_TO_SUPPLIER,
    ORDER_STAGE_COMPLETED,
    ORDER_STAGE_REMINDER,
    ORDER_STAGE_THANKS,
    ORDER_STAGE_CLOSED,
)


class OrderMessages:
    def __init__(self, message_manager: MessageManager, db_provider: Any = None, api_provider: Any = None) -> None:
        self._mm = message_manager
        self._db = db_provider
        self._api = api_provider
        self._fmt = message_manager.formatter

    def on_new_order(self, order_id: str, chat_id: str, order: Dict[str, Any]) -> bool:
        title = self._fmt.build_order_title(order)
        eta = self._resolve_eta(order)
        ctx = {"order_id": order_id, "order_title": title, "eta": eta}
        if "price" not in ctx:
            try:
                ctx["price"] = f"{float(order.get('price', 0)):.0f}"
            except Exception:
                ctx["price"] = "0"
        return self._mm.send(order_id, chat_id, "order", "new_order", ctx)

    def on_greeting(self, order_id: str, chat_id: str, order: Dict[str, Any]) -> bool:
        title = self._fmt.build_order_title(order)
        eta = self._resolve_eta(order)
        ctx = {"order_id": order_id, "order_title": title, "eta": eta}
        try:
            ctx["price"] = f"{float(order.get('price', 0)):.0f}"
        except Exception:
            ctx["price"] = "0"
        return self._mm.send(order_id, chat_id, "order", "greeting", ctx)

    def on_link_request(self, order_id: str, chat_id: str) -> bool:
        return self._mm.send(order_id, chat_id, "order", "link_request", {"order_id": order_id})

    def on_link_received(self, order_id: str, chat_id: str, link: str) -> bool:
        return self._mm.send(order_id, chat_id, "order", "link_received", {"order_id": order_id, "link": link})

    def on_confirm_request(self, order_id: str, chat_id: str, link: str) -> bool:
        return self._mm.send(order_id, chat_id, "order", "link_received", {"order_id": order_id, "link": link})

    def on_confirm(self, order_id: str, chat_id: str, eta: Optional[int] = None) -> bool:
        eta_text = self._fmt.build_eta_text(eta)
        return self._mm.send(order_id, chat_id, "order", "confirm", {"order_id": order_id, "eta": eta_text})

    def on_sent_to_supplier(self, order_id: str, chat_id: str) -> bool:
        return self._mm.send(order_id, chat_id, "order", "sent_to_supplier", {"order_id": order_id})

    def on_processing(self, order_id: str, chat_id: str) -> bool:
        return self._mm.send(order_id, chat_id, "order", "processing", {"order_id": order_id})

    def on_completed(self, order_id: str, chat_id: str, order: Optional[Dict[str, Any]] = None) -> bool:
        title = self._fmt.build_order_title(order or {})
        return self._mm.send(order_id, chat_id, "order", "completed", {"order_id": order_id, "order_title": title})

    def on_completed_reminder(self, order_id: str, chat_id: str, order: Optional[Dict[str, Any]] = None) -> bool:
        title = self._fmt.build_order_title(order or {})
        return self._mm.send(order_id, chat_id, "order", "completed_reminder", {"order_id": order_id, "order_title": title})

    def on_thanks(self, order_id: str, chat_id: str) -> bool:
        return self._mm.send(order_id, chat_id, "order", "thanks", {"order_id": order_id})

    def on_review_prompt(self, order_id: str, chat_id: str) -> bool:
        return self._mm.send(order_id, chat_id, "order", "review_prompt", {"order_id": order_id})

    def on_cancelled(self, order_id: str, chat_id: str, order: Optional[Dict[str, Any]] = None) -> bool:
        return self._mm.send(order_id, chat_id, "order", "cancelled", {"order_id": order_id})

    def on_refund(self, order_id: str, chat_id: str, order: Optional[Dict[str, Any]] = None) -> bool:
        title = self._fmt.build_order_title(order or {})
        return self._mm.send(order_id, chat_id, "order", "refund", {"order_id": order_id, "order_title": title})

    def _resolve_eta(self, order: Dict[str, Any]) -> str:
        service_tag = order.get("service_tag", "")
        if not service_tag:
            return "4"
        tag = service_tag.lower()
        if "premium" in tag or "tg" in tag:
            return "10"
        if "boost" in tag or "discord" in tag:
            return "5"
        if "stars" in tag:
            return "15"
        return "4"
