from __future__ import annotations

from typing import Any, Dict, Optional
from .message_manager import MessageManager


class RecoveryMessages:
    def __init__(self, message_manager: MessageManager, db_provider: Any = None) -> None:
        self._mm = message_manager
        self._db = db_provider

    def supplier_error(self, order_id: str, chat_id: str) -> bool:
        return self._mm.send(order_id, chat_id, "recovery", "supplier_error", {"order_id": order_id})

    def balance_zero(self, order_id: str, chat_id: str) -> bool:
        return self._mm.send(order_id, chat_id, "recovery", "balance_zero", {"order_id": order_id})

    def site_unavailable(self, order_id: str, chat_id: str) -> bool:
        return self._mm.send(order_id, chat_id, "recovery", "site_unavailable", {"order_id": order_id})

    def api_unavailable(self, order_id: str, chat_id: str) -> bool:
        return self._mm.send(order_id, chat_id, "recovery", "api_unavailable", {"order_id": order_id})

    def out_of_stock(self, order_id: str, chat_id: str) -> bool:
        return self._mm.send(order_id, chat_id, "recovery", "out_of_stock", {"order_id": order_id})
