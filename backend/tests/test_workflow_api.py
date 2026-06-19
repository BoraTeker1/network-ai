"""End-to-end API tests: profile → match → message approval → outcome → stats,
plus the email draft/approve queue and the disabled Gmail send.

The LLM is forced unavailable so email drafting uses the deterministic template
(no network calls in the test suite).
"""

import pytest

from app.models import Job
from app.services import llm_client


@pytest.fixture
def seeded_job(db_session):
    job = Job(
        source="test", external_id="t1",
        company="Acme", title="Software Engineer, New Grad", location="Remote",
        url="https://example.com/apply",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def _save_profile(client):
    r = client.post("/profile/resume-text", json={
        "resume_text": "New grad. Skills: Python, FastAPI, React, TypeScript, SQL, Docker."
    })
    assert r.status_code == 200
    return r.json()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_save_profile_parses_skills(client):
    profile = _save_profile(client)
    assert "Python" in profile["skills"]
    assert "Docker" in profile["skills"]


def test_match_endpoint_returns_breakdown(client, seeded_job):
    _save_profile(client)
    r = client.post(f"/jobs/{seeded_job.id}/match")
    assert r.status_code == 200
    data = r.json()
    assert data["match_score"] >= 75
    assert data["recommendation"] == "Strong Target"
    assert len(data["breakdown"]) == 4
    assert data["matched_skills"]


def test_match_without_profile_is_400(client, seeded_job):
    r = client.post(f"/jobs/{seeded_job.id}/match")
    assert r.status_code == 400


def test_message_approval_and_outcome_flow(client, seeded_job):
    _save_profile(client)
    drafts = client.post("/messages/generate", json={"job_id": seeded_job.id}).json()
    assert len(drafts) == 4
    mid = drafts[0]["id"]

    assert client.post(f"/messages/{mid}/approve").json()["status"] == "approved"
    assert client.post(f"/messages/{mid}/reject").json()["status"] == "rejected"
    assert client.post(f"/messages/{mid}/mark-sent-manually").json()["status"] == "sent_manually"

    out = client.post(f"/messages/{mid}/outcome", json={"outcome": "replied"}).json()
    assert out["outcome"] == "replied"

    bad = client.post(f"/messages/{mid}/outcome", json={"outcome": "nonsense"})
    assert bad.status_code == 400


def test_stats_counts_update(client, seeded_job):
    _save_profile(client)
    client.post(f"/jobs/{seeded_job.id}/match")
    drafts = client.post("/messages/generate", json={"job_id": seeded_job.id}).json()
    client.post(f"/messages/{drafts[0]['id']}/mark-sent-manually")
    client.post(f"/messages/{drafts[0]['id']}/outcome", json={"outcome": "replied"})

    stats = client.get("/stats").json()
    assert stats["total_jobs"] == 1
    assert stats["strong_targets"] >= 1
    assert stats["total_messages"] == 4
    assert stats["status_counts"]["sent_manually"] == 1
    assert stats["outcome_counts"]["replied"] == 1


def test_email_draft_fallback_and_disabled_gmail(client, seeded_job, monkeypatch):
    monkeypatch.setattr(llm_client, "llm_available", lambda: False)
    _save_profile(client)
    contact = client.post("/contacts/manual", json={
        "name": "Jordan Smith", "title": "Engineer", "contact_type": "engineer",
        "job_id": seeded_job.id,
    }).json()

    draft = client.post("/emails/draft", json={
        "job_id": seeded_job.id, "contact_id": contact["id"],
    }).json()
    assert draft["llm_used"] is False
    assert draft["body"]
    assert draft["why_safe"]
    assert "Approve" in draft["suggested_next_step"]

    approved = client.post(f"/emails/{draft['id']}/approve").json()
    assert approved["status"] == "approved"
    assert "Copy" in approved["suggested_next_step"]

    # Gmail must stay disabled — friendly response, never an actual send.
    gmail = client.post(f"/emails/{draft['id']}/send-gmail", json={"confirm_send": True}).json()
    assert gmail["sent"] is False
    assert "disabled" in gmail["message"].lower()


def test_linkedin_draft_flow(client, seeded_job, monkeypatch):
    monkeypatch.setattr(llm_client, "llm_available", lambda: False)
    _save_profile(client)
    contact = client.post("/contacts/manual", json={
        "name": "Jordan Smith", "title": "Engineer", "contact_type": "engineer",
        "job_id": seeded_job.id,
    }).json()

    # Connection note: no subject, capped at 300 chars, stored as a LinkedIn draft.
    note = client.post("/linkedin/draft", json={
        "job_id": seeded_job.id, "contact_id": contact["id"], "kind": "connection",
    }).json()
    assert note["llm_used"] is False
    assert note["subject"] is None
    assert note["message_type"] == "linkedin_connection"
    assert 0 < len(note["body"]) <= 300

    # DM is a separate kind.
    dm = client.post("/linkedin/draft", json={
        "job_id": seeded_job.id, "contact_id": contact["id"], "kind": "dm",
    }).json()
    assert dm["message_type"] == "linkedin_dm"

    # LinkedIn drafts reuse the /emails approval workflow + appear in the queue.
    approved = client.post(f"/emails/{note['id']}/approve").json()
    assert approved["status"] == "approved"
    assert note["id"] in [e["id"] for e in client.get("/emails").json()]

    bad = client.post("/linkedin/draft", json={
        "job_id": seeded_job.id, "contact_id": contact["id"], "kind": "bogus",
    })
    assert bad.status_code == 400
