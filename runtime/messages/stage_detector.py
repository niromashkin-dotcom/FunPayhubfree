from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("FunPayHUB.Messages.StageDetector")

ORDER_STAGE_NEW          = 0
ORDER_STAGE_GREETING     = 1
ORDER_STAGE_LINK_REQUEST = 2
ORDER_STAGE_LINK_RECEIVED= 3
ORDER_STAGE_CONFIRM      = 4
ORDER_STAGE_TO_SUPPLIER  = 5
ORDER_STAGE_PROCESSING   = 6
ORDER_STAGE_COMPLETED    = 7
ORDER_STAGE_REMINDER     = 8
ORDER_STAGE_THANKS       = 9
ORDER_STAGE_REVIEW       = 10
ORDER_STAGE_CLOSED       = 11


class OrderStageDetector:
    """Detects the current communication stage of an order from DB + API state."""

    def __init__(self, db_provider: Any = None, api_provider: Any = None) -> None:
        self._db = db_provider
        self._api = api_provider

    def detect(self, order_id: str, order: Dict[str, Any]) -> int:
        try:
            db_status = (order.get("status") or "").lower()
            step = int(order.get("step") or 0)
            confirmed = bool(order.get("confirmed"))
            has_link = bool(order.get("link"))
            timeout_refunded = bool(order.get("timeout_refunded"))
            completed_at = order.get("completed_at")
            supplier_order_id = order.get("supplier_order_id")

            api_status = self._get_api_status(order_id) if self._api else None

            if db_status == "cancelled" or db_status == "refunded":
                return ORDER_STAGE_CLOSED
            if timeout_refunded:
                return ORDER_STAGE_CLOSED

            if api_status == "completed" or db_status == "completed":
                if step < 9:
                    return ORDER_STAGE_COMPLETED
                if step < 10:
                    return ORDER_STAGE_REVIEW
                return ORDER_STAGE_CLOSED

            if completed_at:
                return ORDER_STAGE_REMINDER if step < 8 else ORDER_STAGE_REVIEW

            if supplier_order_id or step >= 6:
                return ORDER_STAGE_PROCESSING

            if confirmed:
                return ORDER_STAGE_TO_SUPPLIER

            if has_link and not confirmed and step >= 3:
                return ORDER_STAGE_CONFIRM

            if has_link and step >= 3:
                return ORDER_STAGE_LINK_RECEIVED

            if step >= 2:
                return ORDER_STAGE_LINK_REQUEST

            if step >= 1:
                return ORDER_STAGE_GREETING

            return ORDER_STAGE_NEW
        except Exception as exc:
            logger.debug(f"[StageDetector] detect error order={order_id}: {exc}")
            return ORDER_STAGE_NEW

    def get_stage_name(self, stage: int) -> str:
        names = {
            ORDER_STAGE_NEW: "new",
            ORDER_STAGE_GREETING: "greeting",
            ORDER_STAGE_LINK_REQUEST: "link_request",
            ORDER_STAGE_LINK_RECEIVED: "link_received",
            ORDER_STAGE_CONFIRM: "confirm",
            ORDER_STAGE_TO_SUPPLIER: "to_supplier",
            ORDER_STAGE_PROCESSING: "processing",
            ORDER_STAGE_COMPLETED: "completed",
            ORDER_STAGE_REMINDER: "reminder",
            ORDER_STAGE_THANKS: "thanks",
            ORDER_STAGE_REVIEW: "review",
            ORDER_STAGE_CLOSED: "closed",
        }
        return names.get(stage, "unknown")

    def _get_api_status(self, order_id: str) -> Optional[str]:
        try:
            if not self._api:
                return None
            result = self._api.get_order(order_id)
            if isinstance(result, dict):
                status = result.get("status")
                if isinstance(status, str):
                    return status.lower()
            return None
        except Exception:
            return None
