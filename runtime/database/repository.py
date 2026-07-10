"""
Repository — high-level database operations for FunPayHub.

Provides convenience methods used by order_tracker, plugins, and reports.
"""

import time
from typing import Optional, List, Dict, Any
from sqlalchemy import func

from runtime.database.base import get_session
from runtime.database.models import (
    User, Order, Product, Lot, Provider,
    Transaction, Review, Log, ProviderBalance,
    OrderStatus,
)


class Repository:
    """High-level DB operations."""

    # ── Users ───────────────────────────────────────────────────────

    @staticmethod
    def get_or_create_user(
        funpay_id: Optional[str] = None,
        username: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> User:
        session = get_session()
        try:
            user = None
            if funpay_id:
                user = session.query(User).filter(
                    User.funpay_id == funpay_id
                ).first()
            if not user and chat_id:
                user = session.query(User).filter(
                    User.chat_id == chat_id
                ).first()
            if not user:
                user = User(
                    funpay_id=funpay_id,
                    username=username,
                    chat_id=chat_id,
                )
                session.add(user)
                session.commit()
            else:
                # update
                if username:
                    user.username = username
                if chat_id:
                    user.chat_id = chat_id
                user.updated_at = time.time()
                session.commit()
            return user
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ── Orders ──────────────────────────────────────────────────────

    @staticmethod
    def create_order(
        funpay_order_id: str,
        price: float,
        buyer_name: Optional[str] = None,
        chat_id: Optional[str] = None,
        service_tag: Optional[str] = None,
        product_id: Optional[int] = None,
        lot_id: Optional[int] = None,
    ) -> Order:
        session = get_session()
        try:
            order = Order(
                funpay_order_id=funpay_order_id,
                price=price,
                buyer_name=buyer_name,
                chat_id=chat_id,
                service_tag=service_tag,
                product_id=product_id,
                lot_id=lot_id,
                status="pending",
                started_at=time.time(),
            )
            session.add(order)
            session.commit()
            return order
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def get_order(funpay_order_id: str) -> Optional[Order]:
        session = get_session()
        try:
            return session.query(Order).filter(
                Order.funpay_order_id == funpay_order_id
            ).first()
        finally:
            session.close()

    @staticmethod
    def get_order_by_id(order_id: int) -> Optional[Order]:
        session = get_session()
        try:
            return session.query(Order).get(order_id)
        finally:
            session.close()

    @staticmethod
    def update_order_status(
        funpay_order_id: str,
        status: str,
        **extra,
    ) -> Optional[Order]:
        session = get_session()
        try:
            order = session.query(Order).filter(
                Order.funpay_order_id == funpay_order_id
            ).first()
            if order:
                order.status = status
                if status == "completed":
                    order.completed_at = time.time()
                for k, v in extra.items():
                    if hasattr(order, k):
                        setattr(order, k, v)
                session.commit()
            return order
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def get_active_orders() -> List[Order]:
        """Get orders that are pending or in progress."""
        session = get_session()
        try:
            return (
                session.query(Order)
                .filter(Order.status.in_(["pending", "in_progress"]))
                .order_by(Order.started_at)
                .all()
            )
        finally:
            session.close()

    @staticmethod
    def get_orders_by_status(status: str, limit: int = 100) -> List[Order]:
        session = get_session()
        try:
            return (
                session.query(Order)
                .filter(Order.status == status)
                .order_by(Order.started_at.desc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()

    @staticmethod
    def count_orders(since: float = 0) -> int:
        session = get_session()
        try:
            return (
                session.query(func.count(Order.id))
                .filter(Order.started_at >= since)
                .scalar()
            )
        finally:
            session.close()

    # ── Lots ────────────────────────────────────────────────────────

    @staticmethod
    def create_lot(
        funpay_lot_id: str,
        title: str,
        price: float,
        service_tag: Optional[str] = None,
        product_id: Optional[int] = None,
        markup: float = 1.3,
    ) -> Lot:
        session = get_session()
        try:
            lot = Lot(
                funpay_lot_id=funpay_lot_id,
                title=title,
                price=price,
                service_tag=service_tag,
                product_id=product_id,
                markup=markup,
                status="active",
            )
            session.add(lot)
            session.commit()
            return lot
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def get_lot(funpay_lot_id: str) -> Optional[Lot]:
        session = get_session()
        try:
            return session.query(Lot).filter(
                Lot.funpay_lot_id == funpay_lot_id
            ).first()
        finally:
            session.close()

    @staticmethod
    def get_lots_by_tag(service_tag: str) -> List[Lot]:
        session = get_session()
        try:
            return (
                session.query(Lot)
                .filter(Lot.service_tag == service_tag)
                .all()
            )
        finally:
            session.close()

    # ── Providers ───────────────────────────────────────────────────

    @staticmethod
    def get_or_create_provider(name: str, base_url: Optional[str] = None) -> Provider:
        session = get_session()
        try:
            prov = session.query(Provider).filter(
                Provider.name == name
            ).first()
            if not prov:
                prov = Provider(
                    name=name,
                    base_url=base_url or "",
                    balance=0.0,
                    status="active",
                )
                session.add(prov)
                session.commit()
            return prov
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def update_provider_balance(
        provider_name: str,
        balance: float,
    ) -> Optional[Provider]:
        session = get_session()
        try:
            prov = session.query(Provider).filter(
                Provider.name == provider_name
            ).first()
            if prov:
                prov.balance = balance
                # Also record snapshot
                snap = ProviderBalance(
                    provider_id=prov.id,
                    balance=balance,
                    checked_at=time.time(),
                )
                session.add(snap)
                session.commit()
            return prov
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ── Reviews ─────────────────────────────────────────────────────

    @staticmethod
    def create_review(
        order_id: int,
        rating: int,
        text: Optional[str] = None,
        funpay_review_id: Optional[str] = None,
    ) -> Review:
        session = get_session()
        try:
            review = Review(
                order_id=order_id,
                funpay_review_id=funpay_review_id,
                rating=rating,
                text=text,
                responded=False,
            )
            session.add(review)
            session.commit()
            return review
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ── Logs ────────────────────────────────────────────────────────

    @staticmethod
    def log(
        level: str,
        source: str,
        message: str,
        order_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        session = get_session()
        try:
            entry = Log(
                level=level.upper(),
                source=source,
                message=message,
                order_id=order_id,
                metadata=metadata,
            )
            session.add(entry)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    # ── Dashboard / Stats ──────────────────────────────────────────

    @staticmethod
    def get_dashboard_stats() -> Dict[str, Any]:
        """Quick stats for the Telegram Control Panel."""
        session = get_session()
        try:
            now = time.time()
            today_start = now - (now % 86400)  # start of current UTC day

            total_orders = session.query(func.count(Order.id)).scalar() or 0
            active_orders = (
                session.query(func.count(Order.id))
                .filter(Order.status.in_(["pending", "in_progress"]))
                .scalar() or 0
            )
            today_orders = (
                session.query(func.count(Order.id))
                .filter(Order.started_at >= today_start)
                .scalar() or 0
            )

            total_income = (
                session.query(func.sum(Transaction.amount))
                .filter(Transaction.type == "funpay_income")
                .scalar() or 0.0
            )

            total_profit = (
                session.query(func.sum(Transaction.amount))
                .filter(Transaction.type == "profit")
                .scalar() or 0.0
            )

            return {
                "total_orders": total_orders,
                "active_orders": active_orders,
                "today_orders": today_orders,
                "total_income": float(total_income),
                "total_profit": float(total_profit),
            }
        finally:
            session.close()
