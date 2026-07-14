from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum
from sqlalchemy.sql import func
import enum
from runtime.database.database import Base

class OrderStatus(str, enum.Enum):
    NEW = "NEW"
    PAID = "PAID"
    PROCESSING = "PROCESSING"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    funpay_order_id = Column(String, unique=True, index=True, nullable=False)
    buyer_id = Column(String, index=True, nullable=False)
    lot_id = Column(String, index=True)
    lot_name = Column(String)
    
    status = Column(String, default=OrderStatus.NEW.value, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    delivery_status = Column(String, nullable=True)

class EventJournalStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"

class EventJournal(Base):
    __tablename__ = "event_journal"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, index=True, nullable=False)
    payload = Column(Text, nullable=False) # JSON encoded
    status = Column(String, default=EventJournalStatus.PENDING.value, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

class TransactionType(str, enum.Enum):
    SALE = "SALE"
    PROVIDER_COST = "PROVIDER_COST"
    COMMISSION = "COMMISSION"
    PROFIT = "PROFIT"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, index=True, nullable=False)
    tx_type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
