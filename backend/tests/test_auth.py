"""Auth lifecycle: signup, login, logout, sessions, and the public surface."""

from datetime import datetime, timedelta

from app.models import AuditEvent, AuthSession
from tests.conftest import TEST_PASSWORD


# ----- Signup -----

def test_signup_sets_cookie_and_me_roundtrip(anon_client):
    r = anon_client.post(
        "/auth/signup", json={"email": "New@Example.com", "password": TEST_PASSWORD}
    )
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "new@example.com"  # normalized/lowercased
    assert body["plan"] == "free"
    assert "password" not in str(body)

    me = anon_client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == body["id"]


def test_signup_duplicate_email_is_409(anon_client):
    payload = {"email": "dup@example.com", "password": TEST_PASSWORD}
    assert anon_client.post("/auth/signup", json=payload).status_code == 201
    assert anon_client.post("/auth/signup", json=payload).status_code == 409


def test_signup_rejects_short_password(anon_client):
    r = anon_client.post(
        "/auth/signup", json={"email": "short@example.com", "password": "short"}
    )
    assert r.status_code == 422  # pydantic min_length=8


def test_signup_rejects_invalid_email(anon_client):
    r = anon_client.post(
        "/auth/signup", json={"email": "not-an-email", "password": TEST_PASSWORD}
    )
    assert r.status_code == 400


# ----- Login / logout -----

def test_login_wrong_password_is_uniform_401(anon_client):
    anon_client.post(
        "/auth/signup", json={"email": "l@example.com", "password": TEST_PASSWORD}
    )
    anon_client.post("/auth/logout")

    wrong_pw = anon_client.post(
        "/auth/login", json={"email": "l@example.com", "password": "wrong-password"}
    )
    unknown = anon_client.post(
        "/auth/login", json={"email": "ghost@example.com", "password": "whatever1"}
    )
    assert wrong_pw.status_code == unknown.status_code == 401
    # Uniform message — never reveal whether the email exists.
    assert wrong_pw.json()["detail"] == unknown.json()["detail"]


def test_login_then_me(anon_client):
    anon_client.post(
        "/auth/signup", json={"email": "in@example.com", "password": TEST_PASSWORD}
    )
    anon_client.post("/auth/logout")
    r = anon_client.post(
        "/auth/login", json={"email": "in@example.com", "password": TEST_PASSWORD}
    )
    assert r.status_code == 200
    assert anon_client.get("/auth/me").status_code == 200


def test_logout_revokes_server_side(client, db_session):
    assert client.get("/auth/me").status_code == 200
    # Capture the cookie before logout deletes it from the jar.
    cookie = client.cookies.get("na_session")
    assert cookie
    client.post("/auth/logout")
    assert client.get("/auth/me").status_code == 401
    # Even re-presenting the old cookie manually fails — revoked in the DB.
    assert client.get("/auth/me", cookies={"na_session": cookie}).status_code == 401


def test_expired_session_is_rejected(client, db_session):
    session = db_session.query(AuthSession).first()
    session.expires_at = datetime.utcnow() - timedelta(days=1)
    db_session.commit()
    assert client.get("/auth/me").status_code == 401


# ----- Public vs private surface -----

def test_anon_cannot_access_private_endpoints(anon_client):
    assert anon_client.get("/profile").status_code == 401
    assert anon_client.get("/messages").status_code == 401
    assert anon_client.get("/goals").status_code == 401
    assert anon_client.get("/emails").status_code == 401
    assert anon_client.post("/opportunities/refresh-all").status_code == 401


def test_anon_can_browse_public_opportunities(anon_client):
    r = anon_client.get("/opportunities")
    assert r.status_code == 200
    assert r.json()["count"] >= 1  # seeded sample feed
    assert anon_client.get("/opportunities/sources").status_code == 200
    assert anon_client.get("/health").status_code == 200


# ----- Audit -----

def test_auth_events_are_audited_without_secrets(anon_client, db_session):
    anon_client.post(
        "/auth/signup", json={"email": "audit@example.com", "password": TEST_PASSWORD}
    )
    anon_client.post(
        "/auth/login", json={"email": "audit@example.com", "password": "wrong-pass!"}
    )
    events = {e.event for e in db_session.query(AuditEvent).all()}
    assert "signup" in events
    assert "login_failed" in events
    # No audit row ever contains a password.
    for e in db_session.query(AuditEvent).all():
        assert TEST_PASSWORD not in (e.note or "")
        assert "wrong-pass" not in (e.note or "")
