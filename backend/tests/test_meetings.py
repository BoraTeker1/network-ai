"""Meetings (presence tracking) tests.

Covers: logging a person awards 'person_met' Momentum once, today's date is
defaulted, listing/filtering, follow-up patching, deletion removes Momentum,
the presence funnel ('people_met') reflects logged meetings, and validation.
"""

from datetime import date

import pytest

from app.models import DEMO_USER_ID, Job, Meeting, MomentumEvent


@pytest.fixture
def seeded_job(db_session):
    job = Job(source="test", external_id="m1", company="Notion",
              title="Backend Engineer", location="Remote",
              url="https://example.com/apply")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def test_log_meeting_awards_momentum_and_defaults_date(client):
    r = client.post("/meetings", json={"name": "Priya Patel",
                                       "where_met": "JS Conf NY",
                                       "title": "Staff Engineer"})
    assert r.status_code == 200
    m = r.json()
    assert m["name"] == "Priya Patel"
    assert m["where_met"] == "JS Conf NY"
    assert m["met_on"] == date.today().isoformat()  # defaulted to today
    assert m["followed_up"] is False
    # Momentum awarded: 'Person met' = 15 points.
    assert m["momentum"]["event_type"] == "person_met"
    assert m["momentum"]["points"] == 15


def test_meeting_inherits_company_from_job(client, seeded_job):
    r = client.post("/meetings", json={"name": "Alex Kim", "job_id": seeded_job.id})
    assert r.status_code == 200
    assert r.json()["company"] == "Notion"


def test_momentum_awarded_once_per_meeting(client, db_session):
    client.post("/meetings", json={"name": "Sam"})
    client.post("/meetings", json={"name": "Sam"})  # a different meeting row
    # Two distinct meetings -> two awards (one each), never double per row.
    events = (
        db_session.query(MomentumEvent)
        .filter(MomentumEvent.event_type == "person_met")
        .all()
    )
    assert len(events) == 2
    # Each is tied to a unique meeting id.
    assert len({e.subject_id for e in events}) == 2


def test_list_and_filter_by_job(client, seeded_job):
    client.post("/meetings", json={"name": "At Event", "where_met": "Conf"})
    client.post("/meetings", json={"name": "At Job", "job_id": seeded_job.id})
    assert len(client.get("/meetings").json()) == 2
    filtered = client.get(f"/meetings?job_id={seeded_job.id}").json()
    assert len(filtered) == 1
    assert filtered[0]["name"] == "At Job"


def test_patch_followed_up(client):
    mid = client.post("/meetings", json={"name": "Jordan"}).json()["id"]
    r = client.patch(f"/meetings/{mid}", json={"followed_up": True,
                                               "note": "Sent a thank-you note"})
    assert r.status_code == 200
    assert r.json()["followed_up"] is True
    assert r.json()["note"] == "Sent a thank-you note"


def test_delete_removes_meeting_and_momentum(client, db_session):
    mid = client.post("/meetings", json={"name": "Casey"}).json()["id"]
    assert db_session.query(MomentumEvent).filter(
        MomentumEvent.subject_type == "meeting", MomentumEvent.subject_id == mid
    ).count() == 1

    r = client.delete(f"/meetings/{mid}")
    assert r.status_code == 200
    assert db_session.query(Meeting).filter(Meeting.id == mid).first() is None
    # Momentum for that meeting is gone too — points/funnel stay honest.
    assert db_session.query(MomentumEvent).filter(
        MomentumEvent.subject_type == "meeting", MomentumEvent.subject_id == mid
    ).count() == 0


def test_empty_name_rejected(client):
    assert client.post("/meetings", json={"name": "   "}).status_code == 400


def test_bad_contact_type_rejected(client):
    r = client.post("/meetings", json={"name": "X", "contact_type": "wizard"})
    assert r.status_code == 400


def test_presence_funnel_counts_people_met(client):
    assert client.get("/dashboard/mission").json()["pipeline"]["people_met"] == 0
    client.post("/meetings", json={"name": "One"})
    client.post("/meetings", json={"name": "Two"})
    assert client.get("/dashboard/mission").json()["pipeline"]["people_met"] == 2
