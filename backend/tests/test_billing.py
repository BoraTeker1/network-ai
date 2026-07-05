"""Billing checkout: hosted payment link when configured, honest fake-door
otherwise. Neither path ever fakes a successful payment."""

from app.models import ProductEvent


def test_checkout_fake_door_when_no_link(client, db_session, monkeypatch):
    monkeypatch.delenv("PAYMENT_LINK_URL", raising=False)
    r = client.post("/billing/checkout")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "unavailable"
    assert "url" not in body
    events = [e.event for e in db_session.query(ProductEvent).all()]
    assert "mock_checkout_viewed" in events
    assert "checkout_link_opened" not in events


def test_checkout_returns_payment_link_when_configured(client, db_session, monkeypatch):
    monkeypatch.setenv("PAYMENT_LINK_URL", "https://buy.example.com/pro")
    r = client.post("/billing/checkout")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "payment_link"
    assert body["url"] == "https://buy.example.com/pro"
    # The link never flips the plan by itself.
    assert body["plan"] == "free"
    events = [e.event for e in db_session.query(ProductEvent).all()]
    assert "checkout_link_opened" in events
    assert "mock_checkout_viewed" not in events


def test_checkout_requires_auth(anon_client, monkeypatch):
    monkeypatch.setenv("PAYMENT_LINK_URL", "https://buy.example.com/pro")
    assert anon_client.post("/billing/checkout").status_code == 401


def test_plans_reports_payments_live(anon_client, monkeypatch):
    monkeypatch.delenv("PAYMENT_LINK_URL", raising=False)
    assert anon_client.get("/billing/plans").json()["payments_live"] is False
    monkeypatch.setenv("PAYMENT_LINK_URL", "https://buy.example.com/pro")
    assert anon_client.get("/billing/plans").json()["payments_live"] is True
