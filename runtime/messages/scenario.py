from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("FunPayHUB.Messages.Scenario")

from .message_manager import MessageManager
from .order_messages import OrderMessages
from .delivery_messages import DeliveryMessages
from .error_messages import ErrorMessages
from .review_messages import ReviewMessages
from .notification_messages import NotificationMessages
from .recovery_messages import RecoveryMessages
from .stage_detector import (
    OrderStageDetector,
    ORDER_STAGE_NEW,
    ORDER_STAGE_GREETING,
    ORDER_STAGE_LINK_REQUEST,
    ORDER_STAGE_LINK_RECEIVED,
    ORDER_STAGE_CONFIRM,
    ORDER_STAGE_TO_SUPPLIER,
    ORDER_STAGE_PROCESSING,
    ORDER_STAGE_COMPLETED,
    ORDER_STAGE_REMINDER,
    ORDER_STAGE_THANKS,
    ORDER_STAGE_REVIEW,
    ORDER_STAGE_CLOSED,
)


class ConversationScenario:
    """Defines a full conversation scenario for an order stage."""

    def __init__(
        self,
        stage: int,
        name: str,
        template_keys: List[str],
        context_builder: Optional[Any] = None,
        guard: Optional[Any] = None,
    ):
        self.stage = stage
        self.name = name
        self.template_keys = template_keys
        self.context_builder = context_builder
        self.guard = guard

    def should_run(self, order: Dict[str, Any]) -> bool:
        if self.guard is None:
            return True
        try:
            return bool(self.guard(order))
        except Exception:
            return False

    def build_context(self, order: Dict[str, Any]) -> Dict[str, Any]:
        if self.context_builder is None:
            return {"order_id": order.get("funpay_order_id", "")}
        try:
            return dict(self.context_builder(order))
        except Exception:
            return {"order_id": order.get("funpay_order_id", "")}


class ScenarioEngine:
    """Maps order stages to conversation scenarios and executes them."""

    def __init__(self, message_manager: MessageManager, db_provider: Any = None, api_provider: Any = None):
        self._mm = message_manager
        self._order_msgs = OrderMessages(message_manager, db_provider, api_provider)
        self._delivery_msgs = DeliveryMessages(message_manager)
        self._error_msgs = ErrorMessages(message_manager)
        self._review_msgs = ReviewMessages(message_manager)
        self._notif_msgs = NotificationMessages(message_manager)
        self._recovery_msgs = RecoveryMessages(message_manager)
        self._detector = OrderStageDetector(db_provider, api_provider)

        self._scenarios: Dict[int, ConversationScenario] = {}
        self._register_scenarios()

    def _register_scenarios(self):
        self._scenarios[ORDER_STAGE_NEW] = ConversationScenario(
            stage=ORDER_STAGE_NEW,
            name="new_order",
            template_keys=["order.new_order"],
        )
        self._scenarios[ORDER_STAGE_GREETING] = ConversationScenario(
            stage=ORDER_STAGE_GREETING,
            name="greeting",
            template_keys=["order.greeting"],
        )
        self._scenarios[ORDER_STAGE_LINK_REQUEST] = ConversationScenario(
            stage=ORDER_STAGE_LINK_REQUEST,
            name="link_request",
            template_keys=["order.link_request"],
        )
        self._scenarios[ORDER_STAGE_LINK_RECEIVED] = ConversationScenario(
            stage=ORDER_STAGE_LINK_RECEIVED,
            name="link_received",
            template_keys=["order.link_received"],
        )
        self._scenarios[ORDER_STAGE_CONFIRM] = ConversationScenario(
            stage=ORDER_STAGE_CONFIRM,
            name="confirm",
            template_keys=["order.confirm"],
        )
        self._scenarios[ORDER_STAGE_TO_SUPPLIER] = ConversationScenario(
            stage=ORDER_STAGE_TO_SUPPLIER,
            name="sent_to_supplier",
            template_keys=["order.sent_to_supplier"],
        )
        self._scenarios[ORDER_STAGE_PROCESSING] = ConversationScenario(
            stage=ORDER_STAGE_PROCESSING,
            name="processing",
            template_keys=["order.processing"],
        )
        self._scenarios[ORDER_STAGE_COMPLETED] = ConversationScenario(
            stage=ORDER_STAGE_COMPLETED,
            name="completed",
            template_keys=["order.completed"],
        )
        self._scenarios[ORDER_STAGE_REMINDER] = ConversationScenario(
            stage=ORDER_STAGE_REMINDER,
            name="completed_reminder",
            template_keys=["order.completed_reminder"],
        )
        self._scenarios[ORDER_STAGE_THANKS] = ConversationScenario(
            stage=ORDER_STAGE_THANKS,
            name="thanks",
            template_keys=["order.thanks"],
        )
        self._scenarios[ORDER_STAGE_REVIEW] = ConversationScenario(
            stage=ORDER_STAGE_REVIEW,
            name="review_prompt",
            template_keys=["order.review_prompt"],
        )

    def get_stage(self, order_id: str, order: Dict[str, Any]) -> int:
        return self._detector.detect(order_id, order)

    def execute_for_stage(self, order_id: str, chat_id: str, order: Dict[str, Any]) -> bool:
        stage = self.get_stage(order_id, order)
        scenario = self._scenarios.get(stage)
        if not scenario:
            return False
        if not scenario.should_run(order):
            return False

        context = scenario.build_context(order)
        category, key = scenario.template_keys[0].split(".", 1)
        sent = self._mm.send(order_id, chat_id, category, key, context)
        if sent:
            logger.info(f"[Scenario] Sent '{scenario.name}' for order={order_id} stage={stage}")
        return sent

    def execute_delivery(self, order_id: str, chat_id: str, delivery: Dict[str, Any], delivery_type: str = "digital_account") -> bool:
        if delivery_type == "digital_account":
            return self._delivery_msgs.send_digital_account(order_id, chat_id, delivery)
        if delivery_type == "link":
            return self._order_msgs.on_link_request(order_id, chat_id)
        return False

    def execute_review_response(self, order_id: str, chat_id: str, rating: int, order: Optional[Dict[str, Any]] = None) -> bool:
        if rating >= 4:
            return self._review_msgs.on_positive_review(order_id, chat_id, order)
        return self._review_msgs.on_negative_review(order_id, chat_id)

    def execute_error(self, order_id: str, chat_id: str, error_type: str) -> bool:
        handlers = {
            "supplier_balance_zero": self._error_msgs.supplier_balance_zero,
            "supplier_error": self._error_msgs.supplier_error,
            "site_unavailable": self._error_msgs.site_unavailable,
            "api_unavailable": self._error_msgs.api_unavailable,
            "limit_exceeded": self._error_msgs.limit_exceeded,
            "out_of_stock": self._error_msgs.out_of_stock,
        }
        handler = handlers.get(error_type)
        if handler:
            return handler(order_id, chat_id)
        return False

    def execute_recovery(self, order_id: str, chat_id: str, recovery_type: str) -> bool:
        handlers = {
            "supplier_error": self._recovery_msgs.supplier_error,
            "balance_zero": self._recovery_msgs.balance_zero,
            "site_unavailable": self._recovery_msgs.site_unavailable,
            "api_unavailable": self._recovery_msgs.api_unavailable,
            "out_of_stock": self._recovery_msgs.out_of_stock,
        }
        handler = handlers.get(recovery_type)
        if handler:
            return handler(order_id, chat_id)
        return False

    def execute_notification(self, notif_type: str, context: Dict[str, Any]) -> bool:
        handlers = {
            "admin_new_order": self._notif_msgs.admin_new_order,
            "admin_supplier_down": lambda ctx: self._notif_msgs.admin_supplier_down(
                ctx.get("order_id", ""), ctx.get("supplier", ""), ctx.get("price", 0)
            ),
            "admin_refund": lambda ctx: self._notif_msgs.admin_refund(
                ctx.get("order_id", ""), ctx.get("buyer", ""), ctx.get("price", 0)
            ),
            "admin_plugin_error": lambda ctx: self._notif_msgs.admin_plugin_error(
                ctx.get("plugin_name", ""), ctx.get("error", "")
            ),
            "admin_funpay_unavailable": self._notif_msgs.admin_funpay_unavailable,
        }
        handler = handlers.get(notif_type)
        if handler:
            return handler(context)
        return False

    def get_stage_name(self, stage: int) -> str:
        return self._detector.get_stage_name(stage)
