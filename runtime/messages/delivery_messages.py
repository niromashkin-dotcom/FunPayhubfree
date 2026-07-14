from __future__ import annotations

from typing import Any, Dict, Optional
from .message_manager import MessageManager


class DeliveryMessages:
    def __init__(self, message_manager: MessageManager, db_provider: Any = None) -> None:
        self._mm = message_manager
        self._db = db_provider

    def send_digital_account(self, order_id: str, chat_id: str, delivery: Dict[str, Any]) -> bool:
        context = self._mm.formatter.build_delivery_data(delivery)
        context["order_id"] = order_id
        return self._mm.send(order_id, chat_id, "delivery", "digital_account", context)

    def send_link(self, order_id: str, chat_id: str, link: str) -> bool:
        return self._mm.send(order_id, chat_id, "delivery", "link_delivery", {"order_id": order_id, "link": link})
