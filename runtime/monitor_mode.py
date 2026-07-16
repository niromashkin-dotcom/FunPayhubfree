"""
Real Order Monitor Mode — безопасный dry-run для реальных заказов.

Режим: REAL_ORDER_MONITOR_MODE=true

Что делает:
- видит реальные заказы (source='real')
- НЕ отправляет лишние действия
- только логирует:
  FOUND ORDER
  CLASSIFIED
  MESSAGE SCENARIO
  DELIVERY PLAN

Использование:
    export REAL_ORDER_MONITOR_MODE=true
    python funpayhub_main.py
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger("FunPayHUB.Monitor")


class RealOrderMonitor:
    """Monitor mode for real orders — log only, no side effects."""

    def __init__(self, event_bus=None) -> None:
        self._event_bus = event_bus
        self._enabled = os.environ.get("REAL_ORDER_MONITOR_MODE", "false").lower() == "true"
        self._orders: Dict[str, Dict[str, Any]] = {}

    def is_enabled(self) -> bool:
        return self._enabled

    def start(self) -> None:
        if not self._enabled:
            return
        if not self._event_bus:
            logger.warning("[Monitor] REAL_ORDER_MONITOR_MODE=true but no event_bus provided")
            return
        self._event_bus.subscribe("new_order", self._on_new_order, priority=10)
        self._event_bus.subscribe("order_completed", self._on_order_completed, priority=10)
        self._event_bus.subscribe("order_failed", self._on_order_failed, priority=10)
        logger.info("[Monitor] Real order monitor started (dry-run mode)")

    def stop(self) -> None:
        if not self._event_bus:
            return
        try:
            self._event_bus.unsubscribe("new_order", self._on_new_order)
            self._event_bus.unsubscribe("order_completed", self._on_order_completed)
            self._event_bus.unsubscribe("order_failed", self._on_order_failed)
        except Exception:
            pass
        logger.info("[Monitor] Real order monitor stopped")

    def _on_new_order(self, event: Dict[str, Any]) -> None:
        order_id = event.get("order_id") if isinstance(event, dict) else getattr(event, "order_id", None)
        if not order_id:
            return
        self._orders[order_id] = {
            "event": event,
            "classified": False,
            "scenario": None,
            "delivery_plan": None,
        }
        logger.info("[Monitor] FOUND ORDER: %s", order_id)
        self._classify(order_id, event)

    def _on_order_completed(self, event: Dict[str, Any]) -> None:
        order_id = event.get("order_id") if isinstance(event, dict) else getattr(event, "order_id", None)
        if not order_id:
            return
        logger.info("[Monitor] ORDER COMPLETED: %s", order_id)
        self._orders.pop(order_id, None)

    def _on_order_failed(self, event: Dict[str, Any]) -> None:
        order_id = event.get("order_id") if isinstance(event, dict) else getattr(event, "order_id", None)
        if not order_id:
            return
        logger.info("[Monitor] ORDER FAILED: %s", order_id)
        self._orders.pop(order_id, None)

    def _classify(self, order_id: str, event: Dict[str, Any]) -> None:
        title = event.get("title", "") or ""
        price = event.get("price", 0)
        service_tag = event.get("service_tag", "") or ""

        category = "unknown"
        if any(k in title.lower() for k in ["premium", "tg", "телеграм"]):
            category = "telegram"
        elif any(k in title.lower() for k in ["boost", "discord", "буст"]):
            category = "boost"
        elif any(k in title.lower() for k in ["stars", "звёзд", "звезд"]):
            category = "stars"
        elif any(k in title.lower() for k in ["донат", "donate"]):
            category = "donate"

        entry = self._orders.get(order_id)
        if entry:
            entry["classified"] = True
            entry["category"] = category

        logger.info("[Monitor] CLASSIFIED: %s -> %s (price=%.2f, tag=%s)", order_id, category, price, service_tag)
        self._plan_scenario(order_id, category, price)

    def _plan_scenario(self, order_id: str, category: str, price: float) -> None:
        if category == "telegram":
            scenario = "premium_order"
            delivery_plan = "member/admins invite"
        elif category == "boost":
            scenario = "boost_order"
            delivery_plan = "server invite / friend request"
        elif category == "stars":
            scenario = "stars_order"
            delivery_plan = "send stars to username"
        elif category == "donate":
            scenario = "donate_order"
            delivery_plan = "transfer to wallet"
        else:
            scenario = "default_order"
            delivery_plan = "manual review required"

        entry = self._orders.get(order_id)
        if entry:
            entry["scenario"] = scenario
            entry["delivery_plan"] = delivery_plan

        logger.info("[Monitor] MESSAGE SCENARIO: %s -> %s", order_id, scenario)
        logger.info("[Monitor] DELIVERY PLAN: %s -> %s", order_id, delivery_plan)

    def get_active_orders(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._orders)
