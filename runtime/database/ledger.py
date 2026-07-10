"""
Ledger — денежный журнал.

Каждое движение денег записывается в таблицу transactions с типом:
  funpay_income      — поступление от покупателя (на баланс FunPay)
  provider_payment   — оплата поставщику
  commission         — комиссия площадки (FunPay)
  refund             — возврат покупателю
  deposit            — пополнение кошелька
  profit             — расчётная прибыль (доход - расходы)
  withdrawal         — вывод средств

Пример для заказа 100₽:
  +100 funpay_income
   -30 provider_payment
   -10 commission
   +60 profit
"""

import time
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy import func

from runtime.database.base import get_session
from runtime.database.models import Transaction, Order, Provider


class Ledger:
    """Ledger — денежный журнал."""

    # ── Запись операций ─────────────────────────────────────────────

    @staticmethod
    def record(
        tx_type: str,
        amount: float,
        order_id: Optional[int] = None,
        funpay_order_id: Optional[str] = None,
        provider_id: Optional[int] = None,
        provider_name: Optional[str] = None,
        description: Optional[str] = None,
        currency: str = "RUB",
    ) -> Transaction:
        """Record a transaction in the ledger.

        If order_id is None but funpay_order_id is given, resolves the order.
        """
        session = get_session()
        try:
            # Resolve order by funpay_id if needed
            resolved_order_id = order_id
            if resolved_order_id is None and funpay_order_id:
                ord_obj = session.query(Order).filter(
                    Order.funpay_order_id == funpay_order_id
                ).first()
                if ord_obj:
                    resolved_order_id = ord_obj.id

            # Resolve provider by name if needed
            resolved_provider_id = provider_id
            if resolved_provider_id is None and provider_name:
                prov = session.query(Provider).filter(
                    Provider.name == provider_name
                ).first()
                if prov:
                    resolved_provider_id = prov.id

            tx = Transaction(
                order_id=resolved_order_id,
                type=tx_type,
                amount=amount,
                currency=currency,
                description=description or "",
                provider_id=resolved_provider_id,
                created_at=time.time(),
            )
            session.add(tx)
            session.commit()
            return tx
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def record_order_income(
        order_id: int,
        amount: float,
        description: Optional[str] = None,
    ) -> Transaction:
        """Record income from a buyer (funpay_income)."""
        return Ledger.record(
            tx_type="funpay_income",
            amount=abs(amount),
            order_id=order_id,
            description=description or "Поступление от покупателя",
        )

    @staticmethod
    def record_provider_payment(
        order_id: int,
        amount: float,
        provider_name: str,
        description: Optional[str] = None,
    ) -> Transaction:
        """Record payment to a supplier (provider_payment, negative)."""
        return Ledger.record(
            tx_type="provider_payment",
            amount=-abs(amount),
            order_id=order_id,
            provider_name=provider_name,
            description=description or f"Оплата поставщику {provider_name}",
        )

    @staticmethod
    def record_commission(
        order_id: int,
        amount: float,
        description: Optional[str] = None,
    ) -> Transaction:
        """Record FunPay commission (commission, negative)."""
        return Ledger.record(
            tx_type="commission",
            amount=-abs(amount),
            order_id=order_id,
            description=description or "Комиссия FunPay",
        )

    @staticmethod
    def record_refund(
        order_id: int,
        amount: float,
        description: Optional[str] = None,
    ) -> Transaction:
        """Record a refund to buyer (refund, negative)."""
        return Ledger.record(
            tx_type="refund",
            amount=-abs(amount),
            order_id=order_id,
            description=description or "Возврат покупателю",
        )

    @staticmethod
    def record_profit(
        order_id: int,
        amount: float,
        description: Optional[str] = None,
    ) -> Transaction:
        """Record calculated profit."""
        return Ledger.record(
            tx_type="profit",
            amount=amount,
            order_id=order_id,
            description=description or "Прибыль по заказу",
        )

    @staticmethod
    def record_deposit(
        amount: float,
        description: Optional[str] = None,
    ) -> Transaction:
        """Record a manual deposit."""
        return Ledger.record(
            tx_type="deposit",
            amount=abs(amount),
            description=description or "Пополнение кошелька",
        )

    # ── Запросы ─────────────────────────────────────────────────────

    @staticmethod
    def get_order_transactions(order_id: int) -> List[Transaction]:
        """Get all ledger entries for a specific order."""
        session = get_session()
        try:
            return (
                session.query(Transaction)
                .filter(Transaction.order_id == order_id)
                .order_by(Transaction.created_at)
                .all()
            )
        finally:
            session.close()

    @staticmethod
    def get_order_profit(order_id: int) -> float:
        """Calculate net profit for an order from ledger entries."""
        session = get_session()
        try:
            result = (
                session.query(func.sum(Transaction.amount))
                .filter(Transaction.order_id == order_id)
                .scalar()
            )
            return float(result or 0.0)
        finally:
            session.close()

    @staticmethod
    def get_balance_snapshot(
        since: Optional[float] = None,
        until: Optional[float] = None,
    ) -> Dict[str, float]:
        """Get aggregated totals by transaction type.

        Returns:
            {"funpay_income": 1000.0, "provider_payment": -300.0, ...}
        """
        session = get_session()
        try:
            query = session.query(
                Transaction.type,
                func.sum(Transaction.amount),
            )
            if since:
                query = query.filter(Transaction.created_at >= since)
            if until:
                query = query.filter(Transaction.created_at <= until)

            rows = query.group_by(Transaction.type).all()
            result: Dict[str, float] = {}
            for tx_type, total in rows:
                result[tx_type] = float(total or 0.0)
            return result
        finally:
            session.close()

    @staticmethod
    def get_daily_report(
        day_start: float,
        day_end: float,
    ) -> Dict[str, Any]:
        """Generate a daily report summary for the given period.

        Returns:
            {
                "total_income": 1000.0,
                "total_expenses": -300.0,
                "total_profit": 700.0,
                "order_count": 10,
                "by_type": { ... }
            }
        """
        snapshot = Ledger.get_balance_snapshot(since=day_start, until=day_end)

        session = get_session()
        try:
            order_count = (
                session.query(func.count(Order.id))
                .filter(Order.started_at >= day_start,
                        Order.started_at <= day_end)
                .scalar()
            )
        finally:
            session.close()

        income = snapshot.get("funpay_income", 0.0)
        expenses = (
            snapshot.get("provider_payment", 0.0)
            + snapshot.get("commission", 0.0)
            + snapshot.get("refund", 0.0)
        )
        profit = snapshot.get("profit", income + expenses)

        return {
            "total_income": income,
            "total_expenses": expenses,
            "total_profit": profit,
            "order_count": order_count or 0,
            "by_type": snapshot,
        }

    @staticmethod
    def get_provider_spending(
        provider_name: str,
        since: Optional[float] = None,
        until: Optional[float] = None,
    ) -> float:
        """Get total spending at a specific provider."""
        session = get_session()
        try:
            query = (
                session.query(func.sum(Transaction.amount))
                .join(Provider, Transaction.provider_id == Provider.id)
                .filter(Provider.name == provider_name,
                        Transaction.type == "provider_payment")
            )
            if since:
                query = query.filter(Transaction.created_at >= since)
            if until:
                query = query.filter(Transaction.created_at <= until)
            result = query.scalar()
            return float(result or 0.0)
        finally:
            session.close()
