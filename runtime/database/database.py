from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool
import os

Base = declarative_base()

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "funpayhub.db")
# Enable WAL mode for high concurrency
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    import runtime.database.models  # load models
    Base.metadata.create_all(bind=engine)
    
    from sqlalchemy import text
    # Execute PRAGMA statements to enable WAL mode
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL;"))
        conn.execute(text("PRAGMA synchronous=NORMAL;"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
