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
    tables = set(inspector.get_table_names())

    # (table -> {column name -> ADD COLUMN statement}) for every additive column.
    additive_by_table = {
        "messages": {
            "outcome": "ALTER TABLE messages ADD COLUMN outcome VARCHAR",
            "follow_up_status": "ALTER TABLE messages ADD COLUMN follow_up_status VARCHAR",
            "follow_up_due_date": "ALTER TABLE messages ADD COLUMN follow_up_due_date VARCHAR",
        },
        # Richer normalized job fields introduced with the newgrad-jobs.com adapter.
        "jobs": {
            "employment_type": "ALTER TABLE jobs ADD COLUMN employment_type VARCHAR",
            "work_mode": "ALTER TABLE jobs ADD COLUMN work_mode VARCHAR",
            "salary_range": "ALTER TABLE jobs ADD COLUMN salary_range VARCHAR",
            "level": "ALTER TABLE jobs ADD COLUMN level VARCHAR",
            "description": "ALTER TABLE jobs ADD COLUMN description TEXT",
            "responsibilities": "ALTER TABLE jobs ADD COLUMN responsibilities TEXT",
            "qualifications": "ALTER TABLE jobs ADD COLUMN qualifications TEXT",
            "benefits": "ALTER TABLE jobs ADD COLUMN benefits TEXT",
            "source_url": "ALTER TABLE jobs ADD COLUMN source_url VARCHAR",
            "external_apply_url": "ALTER TABLE jobs ADD COLUMN external_apply_url VARCHAR",
            "is_closed": "ALTER TABLE jobs ADD COLUMN is_closed BOOLEAN DEFAULT 0",
            "discovered_at": "ALTER TABLE jobs ADD COLUMN discovered_at DATETIME",
        },
        # Source provenance for the curated opportunity feed.
        "opportunities": {
            "source_provider": "ALTER TABLE opportunities ADD COLUMN source_provider VARCHAR",
            "source_confidence": "ALTER TABLE opportunities ADD COLUMN source_confidence VARCHAR",
            "job_function": "ALTER TABLE opportunities ADD COLUMN job_function VARCHAR",
        },
    }

    statements: list[str] = []
    for table, additive in additive_by_table.items():
        if table not in tables:
            continue  # create_all() builds it fresh with the columns present.
        existing = {col["name"] for col in inspector.get_columns(table)}
        statements.extend(sql for name, sql in additive.items() if name not in existing)

    if statements:
        with engine.begin() as conn:
            for sql in statements:
                conn.execute(text(sql))
