"""SQLAlchemy database setup for Network AI.

Uses a local SQLite file (network_ai.db) for the MVP.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# SQLite file lives next to the backend/ folder when you run from backend/.
SQLALCHEMY_DATABASE_URL = "sqlite:///./network_ai.db"

# check_same_thread is required for SQLite + FastAPI's threaded request handling.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
