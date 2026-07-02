"""Cross-user isolation: user B must never see or touch user A's data.

Every check uses two independent authenticated clients (separate cookie jars,
same in-memory DB). Foreign IDs must return 404 — never 403 (don't leak
existence), never 200.
"""

from app.models import Job


def _save_outreach(c, company="Acme Cloud"):
    r = c.post(
        "/outreach/save-draft",
        json={
            "body": f"Hi — I'd love to connect about the role at {company}.",
            "company": company,
            "role": "Backend Engineer",
            "channel": "email",
            "language": "en",
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_profile_is_private(client, client_b):
    client.post(
        "/profile/resume-text",
        json={"resume_text": "Ayşe Yılmaz. Skills: Python, FastAPI, SQL."},
    )
    assert client.get("/profile").status_code == 200
    assert client_b.get("/profile").status_code == 404  # B has no profile


def test_pipeline_messages_are_isolated(client, client_b):
    a_msg = _save_outreach(client)
    # B's list is empty; A's message id 404s for B on read AND mutation.
    assert client_b.get("/messages").json() == []
    assert client_b.get(f"/messages/{a_msg['id']}").status_code == 404
    assert (
        client_b.post(f"/messages/{a_msg['id']}/mark-sent-manually").status_code == 404
    )
    assert (
        client_b.post(
            f"/messages/{a_msg['id']}/outcome", json={"outcome": "replied"}
        ).status_code
        == 404
    )
    # A still sees exactly its own.
    assert [m["id"] for m in client.get("/messages").json()] == [a_msg["id"]]


def test_goals_are_isolated(client, client_b):
    goal = client.post("/goals", json={"target_role": "Backend Engineer"}).json()
    assert client_b.get("/goals").json() == []
    assert (
        client_b.patch(f"/goals/{goal['id']}", json={"target_role": "Hijack"}).status_code
        == 404
    )
    assert client_b.delete(f"/goals/{goal['id']}").status_code == 404


def test_contacts_are_isolated(client, client_b):
    contact = client.post(
        "/contacts/manual", json={"name": "Jordan Smith", "company": "Acme"}
    ).json()
    assert client_b.get("/contacts").json() == []
    assert client_b.get(f"/contacts/{contact['id']}").status_code == 404


def test_next_move_cannot_link_foreign_message(client, client_b):
    a_msg = _save_outreach(client)
    r = client_b.post(
        "/next-move/analyze",
        json={"reply_text": "Thanks, let's talk!", "message_id": a_msg["id"]},
    )
    assert r.status_code == 404
    # A can link its own message fine.
    r = client.post(
        "/next-move/analyze",
        json={"reply_text": "Thanks, let's talk!", "message_id": a_msg["id"]},
    )
    assert r.status_code == 200
    assert r.json()["pipeline_target"] == {"type": "message", "id": a_msg["id"]}


def test_emails_are_isolated(client, client_b, db_session):
    # Seed A a job + contact, then draft an email as A.
    job = Job(source="test", external_id="iso1", company="Acme",
              title="Backend Engineer", location="Remote")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    job_id = job.id
    contact = client.post(
        "/contacts/manual", json={"name": "Sam Lee", "job_id": job_id}
    ).json()
    email = client.post(
        "/emails/draft", json={"job_id": job_id, "contact_id": contact["id"]}
    ).json()

    assert client_b.get("/emails").json() == []
    assert client_b.get(f"/emails/{email['id']}").status_code == 404
    assert client_b.post(f"/emails/{email['id']}/approve").status_code == 404
    # B also can't draft against A's contact (ownership check on contact).
    r = client_b.post(
        "/emails/draft", json={"job_id": job_id, "contact_id": contact["id"]}
    )
    assert r.status_code == 404
