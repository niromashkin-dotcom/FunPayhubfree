"""
Real Mode Constraints — ограничения для первого боевого сценария.

Режим: REAL_MODE=true

Ограничения:
- max_orders_per_day=5
- max_price=500
- manual_delivery=true (требует ручного подтверждения доставки)

Использование:
    export REAL_MODE=true
    export REAL_MODE_MAX_ORDERS_PER_DAY=5
    export REAL_MODE_MAX_PRICE=500
    export REAL_MODE_MANUAL_DELIVERY=true
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger("FunPayHUB.RealMode")


class RealModeConstraints:
    """Ограничения для реального режима."""

    def __init__(self) -> None:
        self._enabled = os.environ.get("REAL_MODE", "false").lower() == "true"
        self._max_orders_per_day = int(os.environ.get("REAL_MODE_MAX_ORDERS_PER_DAY", "5"))
        self._max_price = float(os.environ.get("REAL_MODE_MAX_PRICE", "500"))
        self._manual_delivery = os.environ.get("REAL_MODE_MANUAL_DELIVERY", "true").lower() == "true"
        self._orders_today: Dict[str, float] = {}

    def is_enabled(self) -> bool:
        return self._enabled

    def check_order(self, order_id: str, price: float, chat_id: str = "") -> Dict[str, Any]:
        """Проверяет ограничения для нового заказа. Возвращает {allowed, reason}."""
        if not self._enabled:
            return {"allowed": True, "reason": ""}

        if price > self._max_price:
            msg = f"REAL_MODE: заказ {order_id} отклонён: цена {price}₽ > лимит {self._max_price}₽"
            logger.warning(msg)
            return {"allowed": False, "reason": msg}

        today_orders = sum(1 for oid, p in self._orders_today.items() if p > 0)
        if today_orders >= self._max_orders_per_day:
            msg = f"REAL_MODE: заказ {order_id} отклонён: лимит {self._max_orders_per_day} заказов/день исчерпан"
            logger.warning(msg)
            return {"allowed": False, "reason": msg}

        self._orders_today[order_id] = price
        logger.info("REAL_MODE: заказ %s разрешён (цена=%.2f, сегодня=%d/%d)", order_id, price, today_orders + 1, self._max_orders_per_day)
        return {"allowed": True, "reason": ""}

    def require_manual_delivery(self, order_id: str) -> bool:
        """Требует ручного подтверждения доставки."""
        if not self._enabled:
            return False
        if not self._manual_delivery:
            return False
        logger.info("REAL_MODE: заказ %s требует ручной доставки", order_id)
        return True

    def get_stats(self) -> Dict[str, Any]:
        today_orders = sum(1 for oid, p in self._orders_today.items() if p > 0)
        return {
            "enabled": self._enabled,
            "max_orders_per_day": self._max_orders_per_day,
            "max_price": self._max_price,
            "manual_delivery": self._manual_delivery,
            "orders_today": today_orders,
        }
