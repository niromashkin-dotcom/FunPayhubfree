"""
SQLAlchemy engine, session factory, and Base.
Uses DATABASE_URL from environment (default: sqlite:///data/funpayhub.db).
"""

import os
import threading
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

Base = declarative_base()

_engine = None
_session_factory = None
_db_lock = threading.RLock()


def _resolve_db_path(url: str) -> str:
    """If URL is sqlite relative path, make it absolute relative to project root."""
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        rel = url[len("sqlite:///"):]
        # Try to find project root
        root = Path(__file__).resolve().parent.parent.parent
        abs_path = root / rel
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{abs_path.as_posix()}"
    return url


def get_engine():
    """Return the shared engine (lazily created)."""
    global _engine
    if _engine is None:
        with _db_lock:
            if _engine is None:
                db_url = os.environ.get(
                    "DATABASE_URL",
                    "sqlite:///data/funpayhub.db",
                )
                db_url = _resolve_db_path(db_url)
                connect_args = {}
                if db_url.startswith("sqlite"):
                    connect_args["check_same_thread"] = False
                _engine = create_engine(
                    db_url,
                    echo=False,
                    connect_args=connect_args,
                    pool_pre_ping=True,
                )
                # Enable WAL mode for SQLite — better concurrent reads
                @event.listens_for(_engine, "connect")
                def _set_sqlite_pragma(dbapi_connection, connection_record):
                    if db_url.startswith("sqlite"):
                        cursor = dbapi_connection.cursor()
                        cursor.execute("PRAGMA journal_mode=WAL")
                        cursor.execute("PRAGMA busy_timeout=5000")
                        cursor.close()
    return _engine


def get_session():
    """Return a new session (or scoped session for thread safety)."""
    global _session_factory, _engine
    if _session_factory is None:
        with _db_lock:
            if _session_factory is None:
                engine = get_engine()
                _session_factory = scoped_session(
                    sessionmaker(bind=engine, expire_on_commit=False)
                )
    return _session_factory()


def init_db():
    """Create all tables if they don't exist. Safe to call multiple times."""
    engine = get_engine()
    from runtime.database.models import (
        User, Order, Product, Lot, Provider,
        Transaction, Review, Log, ProviderBalance,
        Notification, CacheEntry, PluginState, AnalyticsEvent,
    )
    Base.metadata.create_all(engine)

    _migrate_add_order_source(engine)

    return engine


def _migrate_add_order_source(engine):
    """Add source column to orders table if it doesn't exist (SQLite migration)."""
    import sqlalchemy as sa
    from sqlalchemy import inspect
    try:
        insp = inspect(engine)
        if not insp.has_table("orders"):
            return
        cols = [c["name"] for c in insp.get_columns("orders")]
        if "source" not in cols:
            with engine.connect() as conn:
                conn.execute(sa.text("ALTER TABLE orders ADD COLUMN source VARCHAR(32) DEFAULT 'real' NOT NULL"))
                conn.commit()
                _mark_existing_test_orders(conn)
    except Exception:
        pass


def _mark_existing_test_orders(conn):
    """Mark existing test/simulation orders by ID pattern."""
    import sqlalchemy as sa
    patterns = [
        "sim_test_%", "sim_load_%", "sim_%",
        "ORD%", "db_stress_%",
    ]
    for pattern in patterns:
        try:
            conn.execute(sa.text(
                "UPDATE orders SET source='simulation' WHERE funpay_order_id LIKE :p AND source='real'"
            ), {"p": pattern})
            conn.commit()
        except Exception:
            pass


def shutdown_db():
    """Dispose engine and clear session factory (e.g., on shutdown)."""
    global _engine, _session_factory
    with _db_lock:
        if _session_factory is not None:
            _session_factory.remove()
            _session_factory = None
        if _engine is not None:
            _engine.dispose()
            _engine = None
