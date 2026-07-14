from sqlalchemy.orm import Session
from runtime.database.models import Order, EventJournal, Transaction, OrderStatus, EventJournalStatus
from datetime import datetime
import json

class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_order(self, order_id: str, buyer: str, lot_name: str, lot_id: str = None):
        order = Order(
            funpay_order_id=order_id,
            buyer_id=buyer,
            lot_name=lot_name,
            lot_id=lot_id,
            status=OrderStatus.NEW.value
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def get_order(self, order_id: str):
        return self.db.query(Order).filter(Order.funpay_order_id == order_id).first()

    def update_status(self, order_id: str, status: OrderStatus):
        order = self.get_order(order_id)
        if order:
            order.status = status.value
            if status == OrderStatus.PAID:
                order.paid_at = datetime.utcnow()
            elif status == OrderStatus.COMPLETED:
                order.completed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(order)
        return order

class EventJournalRepository:
    def __init__(self, db: Session):
        self.db = db

    def log_event(self, event_type: str, payload: dict):
        event = EventJournal(
            event_type=event_type,
            payload=json.dumps(payload, ensure_ascii=False)
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_unprocessed_events(self):
        return self.db.query(EventJournal).filter(EventJournal.status == EventJournalStatus.PENDING.value).all()

    def mark_processing(self, event_id: int):
        event = self.db.query(EventJournal).filter(EventJournal.id == event_id).first()
        if event:
            event.status = EventJournalStatus.PROCESSING.value
            self.db.commit()

    def mark_processed(self, event_id: int):
        event = self.db.query(EventJournal).filter(EventJournal.id == event_id).first()
        if event:
            event.status = EventJournalStatus.PROCESSED.value
            event.processed_at = datetime.utcnow()
            self.db.commit()
            
    def mark_failed(self, event_id: int):
        event = self.db.query(EventJournal).filter(EventJournal.id == event_id).first()
        if event:
            event.status = EventJournalStatus.FAILED.value
            self.db.commit()

class LedgerRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_transaction(self, order_id: str, tx_type: str, amount: float):
        tx = Transaction(
            order_id=order_id,
            tx_type=tx_type,
            amount=amount
        )
        self.db.add(tx)
        self.db.commit()
        self.db.refresh(tx)
        return tx
