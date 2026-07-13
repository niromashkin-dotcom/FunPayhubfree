"""
SQLAlchemy ORM models for FunPayHub.

Tables:
  - users          (funpay buyers / system users)
  - orders         (funpay orders)
  - products       (service definitions, e.g. "100 Discord Boost")
  - lots           (funpay lot clones)
  - providers      (external suppliers: Twiboost, LookSMM, etc.)
  - transactions   (ledger — every money movement)
  - reviews        (funpay reviews left by buyers)
  - logs           (structured application logs)
  - provider_balance (balance snapshots for each provider)
"""

import time
from sqlalchemy import (
    Column, Integer, String, Float, BigInteger, Text,
    DateTime, ForeignKey, Enum, JSON, Boolean,
    Index,
)
from sqlalchemy.orm import relationship
from runtime.database.base import Base

import enum


# ── Enums ──────────────────────────────────────────────────────────────

class OrderStatus(str, enum.Enum):
    PENDING       = "pending"        # just purchased, awaiting fulfillment
    IN_PROGRESS   = "in_progress"    # sent to supplier
    COMPLETED     = "completed"      # done
    REFUNDED      = "refunded"       # money returned
    CANCELLED     = "cancelled"      # manually cancelled
    FAILED        = "failed"         # supplier error, no refund yet


class TransactionType(str, enum.Enum):
    FUNPAY_INCOME      = "funpay_income"       # money from buyer → funpay balance
    PROVIDER_PAYMENT   = "provider_payment"    # money spent at supplier
    COMMISSION         = "commission"          # funpay/platform commission
    REFUND             = "refund"              # money returned to buyer
    DEPOSIT            = "deposit"             # manual top-up (crypto)
    PROFIT             = "profit"              # calculated: income - costs
    WITHDRAWAL         = "withdrawal"          # money taken out


class ProviderStatus(str, enum.Enum):
    ACTIVE   = "active"
    PAUSED   = "paused"     # supplier-level issue
    OFFLINE  = "offline"    # API unreachable
    DISABLED = "disabled"   # manually turned off


class LotStatus(str, enum.Enum):
    ACTIVE   = "active"
    SOLD_OUT = "sold_out"
    PAUSED   = "paused"
    DELETED  = "deleted"


# ── Models ─────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    funpay_id     = Column(String(64), unique=True, nullable=True, index=True)
    username      = Column(String(128), nullable=True)
    chat_id       = Column(String(64), nullable=True)  # telegram chat id
    created_at    = Column(Float, default=time.time, nullable=False)
    updated_at    = Column(Float, default=time.time, onupdate=time.time)

    orders = relationship("Order", back_populates="buyer")

    def __repr__(self):
        return f"<User {self.id} funpay={self.funpay_id}>"


class Product(Base):
    """A service type — e.g. '100 Discord Boost' or '500 Telegram Stars'."""
    __tablename__ = "products"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    name          = Column(String(256), nullable=False, index=True)
    category      = Column(String(128), nullable=True)   # smm, discord, stars
    provider_name = Column(String(64), nullable=True)    # default provider
    markup        = Column(Float, default=1.3)           # multiplier
    cost_price    = Column(Float, nullable=True)          # base cost
    market_price  = Column(Float, nullable=True)          # price after analysis
    is_active     = Column(Boolean, default=True)
    created_at    = Column(Float, default=time.time)

    lots    = relationship("Lot", back_populates="product")
    orders  = relationship("Order", back_populates="product")

    def __repr__(self):
        return f"<Product {self.id} {self.name}>"


class Lot(Base):
    """A single funpay lot (potentially a clone of a product)."""
    __tablename__ = "lots"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    product_id    = Column(Integer, ForeignKey("products.id"), nullable=True)
    funpay_lot_id = Column(String(64), unique=True, nullable=True, index=True)
    title         = Column(String(512), nullable=False)
    price         = Column(Float, nullable=False)
    markup        = Column(Float, default=1.3)
    service_tag   = Column(String(32), nullable=True, index=True)  # e.g. [AS#123]
    copies        = Column(Integer, default=1)       # how many clones exist
    status        = Column(String(32), default="active")
    created_at    = Column(Float, default=time.time)

    product = relationship("Product", back_populates="lots")

    def __repr__(self):
        return f"<Lot {self.id} price={self.price} tag={self.service_tag}>"


class Provider(Base):
    """External supplier — Twiboost, LookSMM, etc."""
    __tablename__ = "providers"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    name           = Column(String(128), unique=True, nullable=False)
    base_url       = Column(String(512), nullable=True)
    balance        = Column(Float, default=0.0)
    currency       = Column(String(8), default="RUB")
    status         = Column(String(32), default="active")
    min_balance    = Column(Float, default=0.0)   # warn threshold
    created_at     = Column(Float, default=time.time)

    orders      = relationship("Order", back_populates="provider")
    balances    = relationship("ProviderBalance", back_populates="provider")

    def __repr__(self):
        return f"<Provider {self.name} balance={self.balance}>"


class Order(Base):
    """A funpay order placed by a buyer."""
    __tablename__ = "orders"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    funpay_order_id = Column(String(64), unique=True, nullable=False, index=True)
    product_id      = Column(Integer, ForeignKey("products.id"), nullable=True)
    provider_id     = Column(Integer, ForeignKey("providers.id"), nullable=True)
    buyer_id        = Column(Integer, ForeignKey("users.id"), nullable=True)
    lot_id          = Column(Integer, ForeignKey("lots.id"), nullable=True)

    buyer_name       = Column(String(128), nullable=True)
    chat_id          = Column(String(64), nullable=True)
    price            = Column(Float, nullable=False)
    service_tag      = Column(String(32), nullable=True)
    status           = Column(String(32), default="pending")
    supplier_order_id = Column(String(128), nullable=True)
    supplier_name    = Column(String(64), nullable=True)
    link             = Column(String(1024), nullable=True)
    pings_sent       = Column(Integer, default=0)
    started_at       = Column(Float, default=time.time)
    completed_at     = Column(Float, nullable=True)
    timeout_refunded = Column(Boolean, default=False)
    source           = Column(String(32), default="real", nullable=False, index=True)

    buyer     = relationship("User", back_populates="orders")
    product   = relationship("Product", back_populates="orders")
    provider  = relationship("Provider", back_populates="orders")
    lot       = relationship("Lot")
    transactions = relationship("Transaction", back_populates="order")
    reviews     = relationship("Review", back_populates="order")

    def __repr__(self):
        return f"<Order {self.funpay_order_id} status={self.status}>"

    __table_args__ = (
        Index("ix_orders_status_created", "status", "started_at"),
    )


class Transaction(Base):
    """Ledger entry — every money movement is recorded here."""
    __tablename__ = "transactions"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    order_id      = Column(Integer, ForeignKey("orders.id"), nullable=True,
                           index=True)
    type          = Column(String(32), nullable=False, index=True)
    amount        = Column(Float, nullable=False)
    currency      = Column(String(8), default="RUB")
    description   = Column(String(512), nullable=True)
    provider_id   = Column(Integer, ForeignKey("providers.id"), nullable=True)
    balance_after = Column(Float, nullable=True)   # running balance
    created_at    = Column(Float, default=time.time)

    order    = relationship("Order", back_populates="transactions")
    provider = relationship("Provider")

    def __repr__(self):
        return f"<Transaction {self.type} {self.amount:.2f} order={self.order_id}>"

    __table_args__ = (
        Index("ix_tx_created_type", "created_at", "type"),
    )


class Review(Base):
    """A review left on FunPay after order completion."""
    __tablename__ = "reviews"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    order_id      = Column(Integer, ForeignKey("orders.id"), nullable=True,
                           index=True)
    funpay_review_id = Column(String(64), unique=True, nullable=True)
    rating        = Column(Integer, nullable=False)  # 1-5 stars
    text          = Column(Text, nullable=True)
    responded     = Column(Boolean, default=False)
    response_text = Column(Text, nullable=True)
    created_at    = Column(Float, default=time.time)

    order = relationship("Order", back_populates="reviews")

    def __repr__(self):
        return f"<Review {self.rating}* order={self.order_id}>"


class Log(Base):
    """Structured application log entry."""
    __tablename__ = "logs"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    level      = Column(String(16), nullable=False, index=True)
    source     = Column(String(128), nullable=True, index=True)
    message    = Column(Text, nullable=False)
    order_id   = Column(String(64), nullable=True, index=True)
    log_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(Float, default=time.time)

    __table_args__ = (
        Index("ix_logs_created_level", "created_at", "level"),
    )


class ProviderBalance(Base):
    """Snapshot of provider balance over time."""
    __tablename__ = "provider_balance"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    balance     = Column(Float, nullable=False)
    currency    = Column(String(8), default="RUB")
    checked_at  = Column(Float, default=time.time)

    provider = relationship("Provider", back_populates="balances")


class Notification(Base):
    """Outgoing notification log — tracks every message sent to buyer."""
    __tablename__ = "notifications"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    order_id     = Column(Integer, ForeignKey("orders.id"), nullable=True, index=True)
    chat_id      = Column(String(64), nullable=False, index=True)
    category     = Column(String(32), nullable=False)   # order, error, delivery, review, notification
    key          = Column(String(64), nullable=False)   # template key
    text         = Column(Text, nullable=False)
    context      = Column(JSON, nullable=True)
    sent_at      = Column(Float, default=time.time, nullable=False)
    delivery_status = Column(String(16), default="sent")  # sent, failed, pending
    error        = Column(Text, nullable=True)

    order = relationship("Order")

    __table_args__ = (
        Index("ix_notif_order_sent", "order_id", "sent_at"),
    )


class CacheEntry(Base):
    """Persistent cache for API responses, templates, etc."""
    __tablename__ = "cache"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    key        = Column(String(256), unique=True, nullable=False, index=True)
    value      = Column(Text, nullable=True)
    ttl        = Column(Float, nullable=True)       # expiration timestamp
    category    = Column(String(64), nullable=True)  # api, template, config
    created_at = Column(Float, default=time.time)

    __table_args__ = (
        Index("ix_cache_ttl", "ttl"),
    )


class PluginState(Base):
    """Persistent plugin state (overrides plugin_state.py FSM)."""
    __tablename__ = "plugin_states"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    plugin_name = Column(String(128), unique=True, nullable=False, index=True)
    state       = Column(String(32), nullable=False)   # init, loaded, active, disabled, error, unloaded
    config      = Column(JSON, nullable=True)
    last_error  = Column(Text, nullable=True)
    updated_at  = Column(Float, default=time.time, onupdate=time.time)


class AnalyticsEvent(Base):
    """Analytics event log for orders, messages, errors."""
    __tablename__ = "analytics_events"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    event_type  = Column(String(64), nullable=False, index=True)  # order_created, message_sent, error, refund
    order_id    = Column(String(64), nullable=True, index=True)
    payload     = Column(JSON, nullable=True)
    created_at  = Column(Float, default=time.time, nullable=False)

    __table_args__ = (
        Index("ix_analytics_type_created", "event_type", "created_at"),
    )
