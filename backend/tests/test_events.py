"""Validation-sprint layer: product events, label feedback, sample hiding."""

from app.models import LabelFeedback, ProductEvent


def _events(db, event: str) -> list[ProductEvent]:
    return db.query(ProductEvent).filter(ProductEvent.event == event).all()


# ----- Server-side funnel events -----


def test_signup_records_event(client, db_session):
    rows = _events(db_session, "signup_completed")
    assert len(rows) == 1
    assert rows[0].user_id == client.user["id"]


def test_resume_upload_records_event(client, db_session):
    r = client.post("/profile/resume-text", json={"resume_text": "Python, SQL"})
    assert r.status_code == 200
    rows = _events(db_session, "resume_uploaded")
    assert len(rows) == 1 and rows[0].user_id == client.user["id"]


def test_feed_view_records_event_for_user_only(client, anon_client, db_session):
    assert anon_client.get("/opportunities").status_code == 200
    assert _events(db_session, "opportunity_viewed") == []
    assert client.get("/opportunities").status_code == 200
    rows = _events(db_session, "opportunity_viewed")
    assert len(rows) == 1 and rows[0].user_id == client.user["id"]


def test_draft_and_pipeline_save_record_events(client, db_session):
    r = client.post("/outreach/draft-from-paste",
                    json={"jd_text": "Backend Engineer\nPython role at Acme"})
    assert r.status_code == 200
    assert len(_events(db_session, "draft_created")) == 1

    r = client.post("/outreach/save-draft",
                    json={"body": "Hi there", "company": "Acme"})
    assert r.status_code == 200
    assert len(_events(db_session, "pipeline_saved")) == 1


def test_mock_checkout_records_event(client, db_session):
    r = client.post("/billing/checkout")
    assert r.status_code == 200
    assert r.json()["status"] == "unavailable"  # still honest, never fakes success
    rows = _events(db_session, "mock_checkout_viewed")
    assert len(rows) == 1 and rows[0].user_id == client.user["id"]


# ----- Client-fired events (POST /events) -----


def test_post_event_logged_in(client, db_session):
    r = client.post("/events", json={"event": "pro_button_clicked"})
    assert r.status_code == 201
    rows = _events(db_session, "pro_button_clicked")
    assert len(rows) == 1 and rows[0].user_id == client.user["id"]


def test_post_event_anonymous_allowed(anon_client, db_session):
    r = anon_client.post("/events", json={"event": "pro_button_clicked"})
    assert r.status_code == 201
    assert _events(db_session, "pro_button_clicked")[0].user_id is None


def test_post_event_rejects_unknown_name(client, db_session):
    r = client.post("/events", json={"event": "made_up_event"})
    assert r.status_code == 422
    assert db_session.query(ProductEvent).filter_by(event="made_up_event").count() == 0


# ----- Label feedback -----


def test_label_feedback_right(client, db_session):
    opp = client.get("/opportunities").json()["items"][0]
    r = client.post(f"/opportunities/{opp['id']}/label-feedback",
                    json={"verdict": "right"})
    assert r.status_code == 201
    fb = db_session.query(LabelFeedback).one()
    assert fb.verdict == "right"
    assert fb.user_id == client.user["id"]
    assert fb.label == opp["turkey_applicability_label"]


def test_label_feedback_wrong_with_reason(client, db_session):
    opp = client.get("/opportunities").json()["items"][0]
    r = client.post(f"/opportunities/{opp['id']}/label-feedback",
                    json={"verdict": "wrong", "reason": "Role is US-only"})
    assert r.status_code == 201
    fb = db_session.query(LabelFeedback).one()
    assert fb.verdict == "wrong" and fb.reason == "Role is US-only"


def test_label_feedback_validation(client, anon_client):
    opp_id = client.get("/opportunities").json()["items"][0]["id"]
    assert client.post(f"/opportunities/{opp_id}/label-feedback",
                       json={"verdict": "maybe"}).status_code == 422
    assert client.post("/opportunities/999999/label-feedback",
                       json={"verdict": "right"}).status_code == 404
    assert anon_client.post(f"/opportunities/{opp_id}/label-feedback",
                            json={"verdict": "right"}).status_code == 401


# ----- Sample rows hidden once real listings exist -----

REAL_JOB = {
    "external_id": "real-1",
    "company": "RealCo",
    "title": "Junior Backend Engineer",
    "location": "Istanbul, Turkey",
    "description": "Python and SQL role in Istanbul.",
    "url": "https://realco.example/jobs/1",
}


def test_samples_shown_when_only_samples_exist(client):
    items = client.get("/opportunities").json()["items"]
    assert items and all(i["is_sample"] for i in items)


def test_samples_hidden_once_real_listings_exist(client):
    r = client.post("/opportunities/import",
                    json={"jobs": [REAL_JOB], "source": "manual-import"})
    assert r.status_code == 200

    items = client.get("/opportunities").json()["items"]
    assert items and all(not i["is_sample"] for i in items)

    # Explicitly asking for the demo feed still works.
    sample_items = client.get(
        "/opportunities", params={"confidence": "sample_demo"}
    ).json()["items"]
    assert sample_items and all(i["is_sample"] for i in sample_items)


# ----- Admin scoreboard -----


def test_events_summary_admin_only(client, db_session):
    assert client.get("/events/summary").status_code == 403

    opp_id = client.get("/opportunities").json()["items"][0]["id"]
    client.post(f"/opportunities/{opp_id}/label-feedback",
                json={"verdict": "wrong", "reason": "seniority off"})

    from app.models import User

    db_session.query(User).filter_by(id=client.user["id"]).update({"plan": "admin"})
    db_session.commit()

    r = client.get("/events/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["events"]["signup_completed"]["total"] == 1
    assert data["events"]["opportunity_viewed"]["total"] >= 1
    assert data["label_feedback"]["wrong"] == 1
    assert data["label_feedback"]["recent_wrong"][0]["reason"] == "seniority off"
