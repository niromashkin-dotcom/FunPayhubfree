"""Order Flow E2E test — полный жизненный цикл заказа.

Сценарий:
1. Создаём заказ(source="simulation")
2. Эмулируем сообщение покупателю (CCE)
3. Эмулируем обработку поставщиком
4. Эмулируем доставку
5. Эмулируем завершение
6. Эмулируем запрос отзыва
7. Проверяем Ledger: transactions + profit

Запуск:
    pytest tests/test_order_lifecycle.py -v
"""
from __future__ import annotations

import os
import time
import uuid
import tempfile

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

from runtime.database import base
from runtime.database.models import (
    Base, Order, Transaction, Notification, Review
)
from runtime.database.repository import Repository
from runtime.database.ledger import Ledger
from sqlalchemy import func


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Каждый тест получает чистую временную БД с полным контролем над engine."""
    fd, db_path = tempfile.mkstemp(suffix=".db", prefix="funpayhub_e2e_")
    os.close(fd)
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = scoped_session(sessionmaker(bind=engine, expire_on_commit=False))

    base._engine = engine
    base._session_factory = session_factory

    yield

    session_factory.remove()
    engine.dispose()
    try:
        os.unlink(db_path)
    except Exception:
        pass


def _create_order(price: float = 150.0) -> Order:
    funpay_order_id = f"E2E_{uuid.uuid4().hex[:8]}"
    order = Repository.create_order(
        funpay_order_id=funpay_order_id,
        price=price,
        buyer_name="E2E Buyer",
        chat_id="e2e_chat_001",
        service_tag="AS#TEST",
        source="simulation",
    )
    return order


def test_full_order_lifecycle():
    order = _create_order()
    assert order.status == "pending"

    session = base.get_session()
    try:
        order.started_at = time.time()
        session.add(order)
        session.commit()
        session.refresh(order)
    finally:
        session.close()

    Repository.log_notification(
        order_id=order.id,
        chat_id="e2e_chat_001",
        category="order",
        key="new_order",
        text="🎉 Спасибо за покупку! Заказ принят.",
        delivery_status="sent",
    )
    Repository.log_notification(
        order_id=order.id,
        chat_id="e2e_chat_001",
        category="order",
        key="processing",
        text="⏳ Заказ выполняется.",
        delivery_status="sent",
    )
    Repository.log_notification(
        order_id=order.id,
        chat_id="e2e_chat_001",
        category="delivery",
        key="delivery_message",
        text="🎁 Ваша ссылка готова.",
        delivery_status="sent",
    )
    Repository.log_notification(
        order_id=order.id,
        chat_id="e2e_chat_001",
        category="review",
        key="review_prompt",
        text="Если вам понравилось — будем благодарны за отзыв.",
        delivery_status="sent",
    )

    Ledger.record_order_income(order.id, order.price, "Тестовый доход")
    Ledger.record_provider_payment(order.id, 45.0, "twiboost", "Оплата поставщику")
    Ledger.record_commission(order.id, 15.0, "Комиссия FunPay")
    Ledger.record_profit(order.id, 90.0, "Прибыль по заказу")

    session = base.get_session()
    try:
        order.status = "completed"
        order.completed_at = time.time()
        session.add(order)
        session.commit()
        session.refresh(order)
    finally:
        session.close()

    review = Review(
        order_id=order.id,
        funpay_review_id="E2E_REV_001",
        rating=5,
        text="Супер!",
        responded=False,
        created_at=time.time(),
    )
    session = base.get_session()
    try:
        session.add(review)
        session.commit()
        session.refresh(review)
    finally:
        session.close()

    session = base.get_session()
    try:
        notifications = session.query(Notification).filter(Notification.order_id == order.id).all()
        assert len(notifications) == 4, f"Expected 4 notifications, got {len(notifications)}"
        categories = {(n.category, n.key) for n in notifications}
        assert ("order", "new_order") in categories
        assert ("order", "processing") in categories
        assert ("delivery", "delivery_message") in categories
        assert ("review", "review_prompt") in categories
    finally:
        session.close()

    report = Ledger.get_daily_report(0, time.time(), real_only=False)
    assert report["order_count"] == 1, f"Expected 1 order, got {report['order_count']}"
    assert report["total_income"] == 150.0
    assert report["total_expenses"] == -60.0
    assert report["total_profit"] == 90.0

    session = base.get_session()
    try:
        tx_count = session.query(Transaction).filter(Transaction.order_id == order.id).count()
        assert tx_count == 4, f"Expected 4 transactions, got {tx_count}"
        income = session.query(func.sum(Transaction.amount)).filter(
            Transaction.order_id == order.id, Transaction.type == "funpay_income"
        ).scalar() or 0.0
        assert income == 150.0
        provider = session.query(func.sum(Transaction.amount)).filter(
            Transaction.order_id == order.id, Transaction.type == "provider_payment"
        ).scalar() or 0.0
        assert provider == -45.0
        commission = session.query(func.sum(Transaction.amount)).filter(
            Transaction.order_id == order.id, Transaction.type == "commission"
        ).scalar() or 0.0
        assert commission == -15.0
        profit = session.query(func.sum(Transaction.amount)).filter(
            Transaction.order_id == order.id, Transaction.type == "profit"
        ).scalar() or 0.0
        assert profit == 90.0
    finally:
        session.close()

    session = base.get_session()
    try:
        stored_review = session.query(Review).filter(Review.order_id == order.id).first()
        assert stored_review is not None
        assert stored_review.rating == 5
        assert stored_review.text == "Супер!"
    finally:
        session.close()
