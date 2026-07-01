"""Plan gates: free limits (402), pro/admin unlimited, admin set-plan, usage."""

from app.models import UsageEvent, User


def _analyze(c):
    return c.post("/next-move/analyze", json={"reply_text": "Sounds great, thanks!"})


def _promote(db_session, client, plan: str):
    """Directly set the client's user plan (test bootstrap only)."""
    u = db_session.query(User).filter(User.id == client.user["id"]).first()
    u.plan = plan
    db_session.commit()


def test_free_limit_returns_402_with_upgrade_payload(client, monkeypatch):
    monkeypatch.setenv("PLAN_LIMIT_FREE_NEXT_MOVE", "2")
    assert _analyze(client).status_code == 200
    assert _analyze(client).status_code == 200
    r = _analyze(client)
    assert r.status_code == 402
    detail = r.json()["detail"]
    assert detail["code"] == "plan_limit"
    assert detail["action"] == "next_move"
    assert detail["limit"] == 2
    assert detail["upgrade_url"] == "/pricing"


def test_pro_user_is_unlimited(client, db_session, monkeypatch):
    monkeypatch.setenv("PLAN_LIMIT_FREE_NEXT_MOVE", "1")
    _promote(db_session, client, "pro")
    for _ in range(3):
        assert _analyze(client).status_code == 200


def test_usage_events_are_recorded(client, db_session):
    _analyze(client)
    rows = (
        db_session.query(UsageEvent)
        .filter(UsageEvent.user_id == client.user["id"], UsageEvent.action == "next_move")
        .all()
    )
    assert len(rows) == 1


def test_pipeline_save_total_cap(client, monkeypatch):
    monkeypatch.setenv("PLAN_LIMIT_FREE_PIPELINE_SAVE", "2")
    payload = {"body": "Hi there — quick note.", "company": "Acme", "channel": "email"}
    assert client.post("/outreach/save-draft", json=payload).status_code == 200
    assert client.post("/outreach/save-draft", json=payload).status_code == 200
    r = client.post("/outreach/save-draft", json=payload)
    assert r.status_code == 402
    assert r.json()["detail"]["period"] == "total"


def test_billing_plan_overview(client):
    r = client.get("/billing/plan")
    assert r.status_code == 200
    body = r.json()
    assert body["plan"] == "free"
    assert body["limits"]["outreach_draft"] == 5
    assert body["usage"]["outreach_draft"] == 0


def test_billing_plans_catalog_is_public(anon_client):
    r = anon_client.get("/billing/plans")
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()["plans"]]
    assert ids == ["free", "pro"]


def test_checkout_never_fakes_success(client):
    r = client.post("/billing/checkout")
    assert r.status_code == 200
    assert r.json()["status"] == "unavailable"


def test_set_plan_requires_admin(client, client_b, db_session):
    # Free user B cannot change plans.
    r = client_b.post(
        "/billing/set-plan", json={"email": client.user["email"], "plan": "pro"}
    )
    assert r.status_code == 403

    # Promote A to admin (bootstrap), then A upgrades B — and it sticks.
    _promote(db_session, client, "admin")
    r = client.post(
        "/billing/set-plan", json={"email": client_b.user["email"], "plan": "pro"}
    )
    assert r.status_code == 200
    assert client_b.get("/auth/me").json()["plan"] == "pro"

    # Unknown email / bad plan are rejected.
    assert (
        client.post(
            "/billing/set-plan", json={"email": "ghost@example.com", "plan": "pro"}
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/billing/set-plan",
            json={"email": client_b.user["email"], "plan": "platinum"},
        ).status_code
        == 422
    )
