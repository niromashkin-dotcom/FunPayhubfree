from __future__ import annotations
import os
import time
import uuid
import tempfile
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from runtime.database import database
from runtime.database.models import Base, Order, Transaction, OrderStatus, EventJournal, EventJournalStatus, TransactionType
from runtime.services.order_service import OrderService
from runtime.services.delivery_service import DeliveryService
from runtime.services.finance_service import FinanceService
from runtime.database.repositories import EventJournalRepository

# Mocks
class MockEventBus:
    def __init__(self):
        self.events = []
    def emit(self, event_name, data):
        self.events.append({"name": event_name, "data": data})

class MockChatService:
    def __init__(self, fail_send=False):
        self.messages = []
        self.fail_send = fail_send
    def send_message(self, user_id, text):
        if self.fail_send:
            raise Exception("CCE Unavailable")
        self.messages.append({"user_id": user_id, "text": text})

@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    fd, db_path = tempfile.mkstemp(suffix=".db", prefix="funpayhub_e2e_")
    os.close(fd)
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = scoped_session(sessionmaker(bind=engine, expire_on_commit=False))
    
    # Patch all modules that imported SessionLocal directly
    monkeypatch.setattr("runtime.services.order_service.SessionLocal", session_factory)
    monkeypatch.setattr("runtime.services.delivery_service.SessionLocal", session_factory)
    monkeypatch.setattr("runtime.services.finance_service.SessionLocal", session_factory)
    database.SessionLocal = session_factory
    
    yield

    session_factory.remove()
    engine.dispose()
    try:
        os.unlink(db_path)
    except Exception:
        pass

def setup_services(fail_chat=False):
    event_bus = MockEventBus()
    chat_service = MockChatService(fail_send=fail_chat)
    delivery_service = DeliveryService(event_bus, chat_service)
    finance_service = FinanceService(event_bus)
    order_service = OrderService(event_bus, delivery_service, finance_service, chat_service)
    return order_service, delivery_service, finance_service, event_bus, chat_service

def get_db():
    return database.SessionLocal()

def test_scenario_1_success():
    order_svc, del_svc, fin_svc, bus, chat = setup_services()
    order_id = "ORD_SUCCESS"
    order_svc.create_order(order_id, "Buyer1", "Lot1")
    
    # 1. Simulate payment
    order_svc.process_payment(order_id, 150.0)
    
    # 2. Check Order Status
    db = get_db()
    order = db.query(Order).filter_by(funpay_order_id=order_id).first()
    assert order.status == OrderStatus.DELIVERED.value
    
    # 3. Check CCE Chat
    assert len(chat.messages) == 1
    assert "Ваш товар" in chat.messages[0]["text"]
    
    # 4. Check Finance (Ledger)
    fin_svc.calculate_and_record_profit(order_id, 150.0, 50.0)
    
    # Check transactions
    sale_tx = db.query(Transaction).filter_by(order_id=order_id, tx_type=TransactionType.SALE.value).first()
    assert sale_tx.amount == 150.0
    profit_tx = db.query(Transaction).filter_by(order_id=order_id, tx_type=TransactionType.PROFIT.value).first()
    assert profit_tx.amount == 100.0
    db.close()

def test_scenario_2_provider_timeout():
    order_svc, del_svc, fin_svc, bus, chat = setup_services()
    order_id = "FAIL_DELIVERY_1"
    order_svc.create_order(order_id, "Buyer1", "Lot1")
    
    order_svc.process_payment(order_id, 150.0)
    
    db = get_db()
    order = db.query(Order).filter_by(funpay_order_id=order_id).first()
    assert order.status == OrderStatus.FAILED.value
    
    # Ledger should NOT have profit
    profit_tx = db.query(Transaction).filter_by(order_id=order_id, tx_type=TransactionType.PROFIT.value).first()
    assert profit_tx is None
    db.close()

def test_scenario_3_crash_recovery():
    # Write event to EventJournal simulating a crash mid-processing
    db = get_db()
    repo = EventJournalRepository(db)
    repo.log_event("order_paid", {"order_id": "ORD_CRASH", "amount": 150.0})
    db.close()

    order_svc, del_svc, fin_svc, bus, chat = setup_services()
    order_svc.create_order("ORD_CRASH", "Buyer1", "Lot1")
    
    db = get_db()
    unprocessed = EventJournalRepository(db).get_unprocessed_events()
    assert len(unprocessed) == 1
    event = unprocessed[0]
    payload = json.loads(event.payload)
    
    # "Restart" and process from journal
    order_svc.process_payment(payload["order_id"], payload["amount"])
    
    order = db.query(Order).filter_by(funpay_order_id="ORD_CRASH").first()
    assert order.status == OrderStatus.DELIVERED.value
    db.close()

def test_scenario_4_double_payment():
    order_svc, del_svc, fin_svc, bus, chat = setup_services()
    order_id = "ORD_DOUBLE"
    order_svc.create_order(order_id, "Buyer1", "Lot1")
    
    order_svc.process_payment(order_id, 150.0)
    order_svc.process_payment(order_id, 150.0)
    order_svc.process_payment(order_id, 150.0)
    
    db = get_db()
    # Check idempotency: multiple calls should only produce one SALE transaction
    tx_count = db.query(Transaction).filter_by(order_id=order_id, tx_type=TransactionType.SALE.value).count()
    assert tx_count == 1, "Idempotency failed: multiple sales recorded"
    db.close()

def test_scenario_5_cce_unavailable():
    order_svc, del_svc, fin_svc, bus, chat = setup_services(fail_chat=True)
    order_id = "ORD_CCE_FAIL"
    order_svc.create_order(order_id, "Buyer1", "Lot1")
    
    # Process payment will hit CCE failure
    order_svc.process_payment(order_id, 150.0)
        
    db = get_db()
    order = db.query(Order).filter_by(funpay_order_id=order_id).first()
    # As per patched delivery_service, should fall back to PROCESSING
    assert order.status == OrderStatus.PROCESSING.value
    
    # EventBus should have emitted "message_send_failed"
    emitted = [e["name"] for e in bus.events]
    assert "message_send_failed" in emitted
    db.close()
