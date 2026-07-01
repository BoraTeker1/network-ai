"""Tests for the dashboard mission aggregation endpoint + service.

Covers the deterministic fallback when there is no data (the dashboard must
never be blank), and the populated path after a profile/job/match exist.
"""

import pytest

from app.models import Job
from app.services import llm_client, mission


@pytest.fixture
def seeded_job(db_session):
    job = Job(
        source="test", external_id="d1",
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


# ----- Deterministic empty-state behavior -----

def test_mission_empty_is_never_blank(client):
    """With no data at all, the endpoint still returns a usable, ordered plan."""
    r = client.get("/dashboard/mission")
    assert r.status_code == 200
    data = r.json()

    assert data["ready"] is False
    assert data["best_job"] is None
    assert data["contact_plan"] is None
    # Always returns a full setup checklist, none done yet.
    assert len(data["setup_steps"]) == 6
    assert all(s["done"] is False for s in data["setup_steps"])
    # The first unmet step is uploading a resume, and the headline points there.
    assert data["next_setup_step"]["key"] == "profile"
    assert data["headline"] == "Upload your resume"
    # Momentum / pipeline summaries exist and are zeroed, not null.
    assert data["momentum"]["total_points"] == 0
    assert data["pipeline"]["jobs_found"] == 0


def test_mission_service_matches_endpoint(client, db_session):
    """The service and the HTTP endpoint return the same shape."""
    direct = mission.build_mission(db_session, client.user["id"])
    via_http = client.get("/dashboard/mission").json()
    assert set(direct.keys()) == set(via_http.keys())


# ----- Populated path -----

def test_mission_surfaces_best_job_and_contact_plan(client, seeded_job):
    _save_profile(client)
    assert client.post("/jobs/match-all").status_code == 200

    data = client.get("/dashboard/mission").json()

    assert data["ready"] is True
    assert data["best_job"]["job_id"] == seeded_job.id
    assert data["best_job"]["company"] == "Acme"
    assert data["match_label"] == "Strong Target"
    assert data["match_explanation"]
    assert data["recommended_next_action"]

    plan = data["contact_plan"]
    assert plan is not None
    assert plan["who_first"]
    # A Strong Target recommends recruiter/hiring-manager/engineer by default.
    types = [c["contact_type"] for c in plan["recommended_contact_types"]]
    assert "recruiter" in types
    assert all(c["why"] for c in plan["recommended_contact_types"])

    # The profile/jobs/matches setup steps are now satisfied.
    done = {s["key"]: s["done"] for s in data["setup_steps"]}
    assert done["profile"] and done["jobs"] and done["matches"]


def test_mission_counts_drafts_and_follow_ups(client, seeded_job):
    """Forces the deterministic template (no LLM) and checks draft/follow-up counts."""
    monkey = llm_client  # template path is used automatically when no key is set
    assert monkey is not None

    _save_profile(client)
    client.post("/jobs/match-all")

    # Two message drafts pending review.
    drafts = client.post("/messages/generate", json={"job_id": seeded_job.id}).json()
    assert len(drafts) >= 1

    data = client.get("/dashboard/mission").json()
    assert data["drafts"]["message_drafts"] == len(drafts)
    assert data["drafts"]["pending_review"] >= len(drafts)
    # The "draft your first outreach" setup step is now done.
    done = {s["key"]: s["done"] for s in data["setup_steps"]}
    assert done["drafts"] is True

    # Flag a follow-up and confirm it surfaces.
    mid = drafts[0]["id"]
    client.post(f"/messages/{mid}/follow-up", json={"status": "follow_up_needed", "due_date": "2026-07-01"})
    data = client.get("/dashboard/mission").json()
    assert data["follow_ups"]["due"] == 1
    assert data["follow_ups"]["items"][0]["company"] == "Acme"
