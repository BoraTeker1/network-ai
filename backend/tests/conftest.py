"""Shared pytest fixtures.

Each test gets an isolated in-memory SQLite database (StaticPool keeps a single
shared connection) so nothing touches the real network_ai.db. The FastAPI
get_db dependency is overridden to use that session.

Auth: the standard `client` fixture is a TestClient that has already signed up
and logged in as user-a (its cookie jar carries the session automatically), so
pre-auth tests keep working unchanged. `anon_client` has no session; `client_b`
is an independent second account for cross-user isolation tests. All clients
share the SAME app override / in-memory DB but hold separate cookie jars.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.services import opportunities, rate_limit

TEST_PASSWORD = "test-pass-1234"


@pytest.fixture(autouse=True)
def _no_rate_limit(monkeypatch):
    """Rate limiting is off by default in tests; test_rate_limit.py re-enables
    it explicitly per test."""
    monkeypatch.setenv("RATE_LIMIT_DISABLED", "1")
    rate_limit.reset()


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture
def app_ctx(db_session):
    """Install the get_db override exactly once per test + seed the sample feed.

    dependency_overrides live on the app object, so every TestClient created in
    the same test shares this override (and therefore the same in-memory DB).
    """
    opportunities.ensure_seeded(db_session)

    def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    yield app
    app.dependency_overrides.clear()


def signup(c: TestClient, email: str) -> dict:
    """Sign a fresh client up (cookie is kept in the client's own jar)."""
    r = c.post("/auth/signup", json={"email": email, "password": TEST_PASSWORD})
    assert r.status_code == 201, r.text
    return r.json()  # {"id", "email", "plan", "created_at"}


@pytest.fixture
def client(app_ctx):
    """Authenticated primary client (user-a) — what almost every test uses."""
    with TestClient(app_ctx) as c:
        c.user = signup(c, "user-a@example.com")
        yield c


@pytest.fixture
def anon_client(app_ctx):
    """A client with no session cookie."""
    with TestClient(app_ctx) as c:
        yield c


@pytest.fixture
def client_b(app_ctx):
    """A second, independent authenticated account (user-b)."""
    with TestClient(app_ctx) as c:
        c.user = signup(c, "user-b@example.com")
        yield c
