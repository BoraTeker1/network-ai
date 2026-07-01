"""Rate limiting: 429 + Retry-After, per-user key independence, disable flag."""

from app.models import AuditEvent
from app.services import rate_limit
from tests.conftest import TEST_PASSWORD


def _enable(monkeypatch, **limits):
    """Re-enable rate limiting for this test with tiny limits."""
    monkeypatch.delenv("RATE_LIMIT_DISABLED", raising=False)
    for action, value in limits.items():
        monkeypatch.setenv(f"RATE_LIMIT_{action.upper()}", str(value))
    rate_limit.reset()


def test_login_rate_limited_by_ip(anon_client, monkeypatch):
    _enable(monkeypatch, login=2)
    payload = {"email": "ghost@example.com", "password": "whatever-123"}
    assert anon_client.post("/auth/login", json=payload).status_code == 401
    assert anon_client.post("/auth/login", json=payload).status_code == 401
    r = anon_client.post("/auth/login", json=payload)
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) >= 1


def test_authed_action_rate_limited_per_user(client, client_b, monkeypatch):
    _enable(monkeypatch, next_move=2)
    body = {"reply_text": "Thanks for reaching out!"}
    assert client.post("/next-move/analyze", json=body).status_code == 200
    assert client.post("/next-move/analyze", json=body).status_code == 200
    assert client.post("/next-move/analyze", json=body).status_code == 429
    # Independent bucket: user B is unaffected by A's burst.
    assert client_b.post("/next-move/analyze", json=body).status_code == 200


def test_rate_limit_hits_are_audited_once_per_window(anon_client, db_session, monkeypatch):
    _enable(monkeypatch, login=1)
    payload = {"email": "ghost@example.com", "password": "whatever-123"}
    anon_client.post("/auth/login", json=payload)
    for _ in range(3):  # several over-limit hits, one audit row
        anon_client.post("/auth/login", json=payload)
    rows = db_session.query(AuditEvent).filter(AuditEvent.event == "rate_limited").all()
    assert len(rows) == 1
    assert "login" in rows[0].note


def test_disable_flag_bypasses_limits(anon_client, monkeypatch):
    # conftest sets RATE_LIMIT_DISABLED=1; even a limit of 1 must not fire.
    monkeypatch.setenv("RATE_LIMIT_LOGIN", "1")
    payload = {"email": "ghost@example.com", "password": "whatever-123"}
    for _ in range(4):
        assert anon_client.post("/auth/login", json=payload).status_code == 401


def test_signup_rate_limited(anon_client, monkeypatch):
    _enable(monkeypatch, signup=1)
    assert (
        anon_client.post(
            "/auth/signup", json={"email": "rl1@example.com", "password": TEST_PASSWORD}
        ).status_code
        == 201
    )
    r = anon_client.post(
        "/auth/signup", json={"email": "rl2@example.com", "password": TEST_PASSWORD}
    )
    assert r.status_code == 429
