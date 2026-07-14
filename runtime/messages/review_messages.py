from __future__ import annotations

from typing import Any, Dict, Optional
from .message_manager import MessageManager


class ReviewMessages:
    def __init__(self, message_manager: MessageManager, db_provider: Any = None) -> None:
        self._mm = message_manager
        self._db = db_provider

    def on_positive_review(self, order_id: str, chat_id: str, order: Optional[Dict[str, Any]] = None) -> bool:
        title = self._mm.formatter.build_order_title(order or {})
        context = {"order_id": order_id, "order_title": title}
        return self._mm.send(order_id, chat_id, "review", "positive", context)

    def on_negative_review(self, order_id: str, chat_id: str) -> bool:
        return self._mm.send(order_id, chat_id, "review", "negative", {"order_id": order_id})

    def on_neutral_review(self, order_id: str, chat_id: str) -> bool:
        return self._mm.send(order_id, chat_id, "review", "neutral", {"order_id": order_id})
