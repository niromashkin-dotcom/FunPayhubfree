"""FunPayHub Database Layer — SQLite + SQLAlchemy.

Provides:
  - Session / engine / Base (SQLAlchemy declarative)
  - All ORM models (users, orders, products, lots, providers,
    transactions/ledger, reviews, logs)
  - High-level repository methods
  - Ledger journal with double-entry-style tracking
"""

from runtime.database.base import (
    get_engine,
    get_session,
    init_db,
    shutdown_db,
    Base,
)
from runtime.database.models import (
    User,
    Order,
    Product,
    Lot,
    Provider,
    Transaction,
    Review,
    Log,
    ProviderBalance,
)
from runtime.database.ledger import Ledger
from runtime.database.repository import Repository

__all__ = [
    "get_engine",
    "get_session",
    "init_db",
    "shutdown_db",
    "Base",
    "User",
    "Order",
    "Product",
    "Lot",
    "Provider",
    "Transaction",
    "Review",
    "Log",
    "ProviderBalance",
    "Ledger",
    "Repository",
]
