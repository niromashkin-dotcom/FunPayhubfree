from __future__ import annotations

from typing import Any, Dict, Optional
from .message_manager import MessageManager


class ErrorMessages:
    def __init__(self, message_manager: MessageManager, db_provider: Any = None) -> None:
        self._mm = message_manager
        self._db = db_provider

    def supplier_balance_zero(self, order_id: str, chat_id: str) -> bool:
        return self._mm.send(order_id, chat_id, "error", "supplier_balance_zero", {"order_id": order_id})

    def supplier_error(self, order_id: str, chat_id: str) -> bool:
        return self._mm.send(order_id, chat_id, "error", "supplier_error", {"order_id": order_id})

    def site_unavailable(self, order_id: str, chat_id: str) -> bool:
        return self._mm.send(order_id, chat_id, "error", "site_unavailable", {"order_id": order_id})

    def api_unavailable(self, order_id: str, chat_id: str) -> bool:
        return self._mm.send(order_id, chat_id, "error", "api_unavailable", {"order_id": order_id})

    def limit_exceeded(self, order_id: str, chat_id: str) -> bool:
        return self._mm.send(order_id, chat_id, "error", "limit_exceeded", {"order_id": order_id})

    def out_of_stock(self, order_id: str, chat_id: str) -> bool:
        return self._mm.send(order_id, chat_id, "error", "out_of_stock", {"order_id": order_id})
