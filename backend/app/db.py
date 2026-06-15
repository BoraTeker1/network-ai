"""SQLAlchemy database setup for Network AI.

Uses a local SQLite file (network_ai.db) for the MVP.
"""

from sqlalchemy import create_engine, inspect, text
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


def run_lightweight_migrations() -> None:
    """Add new additive columns to existing tables without dropping data.

    create_all() only creates missing tables — it never alters existing ones.
    For a local SQLite MVP we don't want full Alembic migrations, so we do a
    tiny, idempotent "ADD COLUMN if missing" pass for the few additive columns
    introduced after the first release. Safe to run on every startup.
    """
    inspector = inspect(engine)
    if "messages" not in inspector.get_table_names():
        return  # create_all() will build it fresh with the column already present.

    columns = {col["name"] for col in inspector.get_columns("messages")}
    # (column name -> ADD COLUMN statement) for every additive column.
    additive = {
        "outcome": "ALTER TABLE messages ADD COLUMN outcome VARCHAR",
        "follow_up_status": "ALTER TABLE messages ADD COLUMN follow_up_status VARCHAR",
        "follow_up_due_date": "ALTER TABLE messages ADD COLUMN follow_up_due_date VARCHAR",
    }
    missing = [sql for name, sql in additive.items() if name not in columns]
    if missing:
        with engine.begin() as conn:
            for sql in missing:
                conn.execute(text(sql))
