"""Momentum gamification tests: correct points, no double-counting, summary."""

import pytest

from app.models import Job
from app.services import momentum


@pytest.fixture
def job(db_session):
    j = Job(source="test", external_id="m1", company="Acme",
            title="Software Engineer, New Grad", location="Remote",
            url="https://example.com/apply")
    db_session.add(j)
    db_session.commit()
    db_session.refresh(j)
    return j


def _profile(client):
    client.post("/profile/resume-text", json={
        "resume_text": "New grad. Skills: Python, FastAPI, React, SQL, Docker."
    })


def test_award_is_idempotent(db_session):
    first = momentum.award(db_session, "message", 1, "draft_approved")
    second = momentum.award(db_session, "message", 1, "draft_approved")
    assert first is not None and first["points"] == 5
    assert second is None  # same milestone never re-awards


def test_unknown_event_awards_nothing(db_session):
    assert momentum.award(db_session, "message", 1, None) is None
    assert momentum.award(db_session, "message", 1, "not_a_real_event") is None


def test_tracked_no_points_is_logged_without_points(db_session):
    award = momentum.award(db_session, "message", 9, "tracked_no_points")
    assert award is not None
    assert award["points"] == 0
    assert award["celebration"] == "none"


def test_summary_totals_and_recent_wins(db_session):
    momentum.award(db_session, "message", 1, "draft_approved")   # +5
    momentum.award(db_session, "message", 1, "sent_manual")      # +10
    momentum.award(db_session, "message", 2, "interview_received")  # +100
    momentum.award(db_session, "message", 3, "tracked_no_points")   # +0
    s = momentum.summary(db_session)
    assert s["total_points"] == 115
    assert s["points_today"] == 115
    assert s["streak"] == 1
    # Zero-point events are not "wins".
    assert all(w["points"] > 0 for w in s["recent_wins"])
    assert s["recent_wins"][0]["event_type"] == "interview_received"  # newest first


def test_message_outcome_awards_via_api(client, job):
    _profile(client)
    drafts = client.post("/messages/generate", json={"job_id": job.id}).json()
    mid = drafts[0]["id"]

    approved = client.post(f"/messages/{mid}/approve").json()
    assert approved["momentum"]["points"] == 5

    # Reject earns no momentum (workflow action, not progress).
    other = drafts[1]["id"]
    rejected = client.post(f"/messages/{other}/reject").json()
    assert rejected["momentum"] is None

    interview = client.post(
        f"/messages/{mid}/outcome", json={"outcome": "interview_received"}
    ).json()
    assert interview["momentum"]["points"] == 100
    assert interview["momentum"]["celebration"] == "big"

    # Re-clicking the same outcome must not double-count.
    again = client.post(
        f"/messages/{mid}/outcome", json={"outcome": "interview_received"}
    ).json()
    assert again["momentum"] is None

    summary = client.get("/momentum/summary").json()
    assert summary["total_points"] == 105  # 5 (approve) + 100 (interview)
