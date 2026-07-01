"""Opportunities → Outreach → Pipeline loop.

Covers saving a reviewed outreach draft as a tracked Message (pipeline item),
whether it came from an opportunity or from pasted job text, listing it, updating
its status/outcome/follow-up manually, and linking it in Next Move AI. Nothing is
ever sent — these only persist and track drafts the user copies and sends by hand.
"""


def _save_payload(**overrides):
    payload = {
        "body": "Hi Jordan, I came across the backend role at Acme Cloud and would love to connect.",
        "subject": "Backend engineer — quick hello",
        "company": "Acme Cloud",
        "role": "Backend Engineer",
        "channel": "email",
        "language": "en",
        "contact_name": "Jordan Smith",
        "contact_title": "Engineering Manager",
        "status": "copied",
    }
    payload.update(overrides)
    return payload


# ----- 1. Saving a draft to the pipeline -----

def test_save_draft_persists_pipeline_item(client):
    res = client.post("/outreach/save-draft", json=_save_payload())
    assert res.status_code == 200
    item = res.json()
    assert item["id"]
    assert item["company"] == "Acme Cloud"
    assert item["title"] == "Backend Engineer"
    assert item["channel"] == "email"
    assert item["language"] == "en"
    assert item["subject"] == "Backend engineer — quick hello"
    assert item["contact_name"] == "Jordan Smith"
    assert item["status"] == "copied"
    assert item["draft_text"].startswith("Hi Jordan")
    # It reuses the Message shape, so the pipeline gets a checklist for free.
    assert "checklist" in item


def test_save_draft_rejects_empty_body(client):
    res = client.post("/outreach/save-draft", json=_save_payload(body="   "))
    assert res.status_code == 400


def test_linkedin_draft_drops_subject(client):
    res = client.post(
        "/outreach/save-draft",
        json=_save_payload(channel="linkedin", subject="ignored for notes"),
    )
    item = res.json()
    assert item["channel"] == "linkedin"
    assert item["subject"] is None


# ----- 2. Saved from an opportunity (context preserved) -----

def test_save_draft_from_opportunity_links_source(client):
    # The seeded sample feed gives us a real opportunity id + prefill.
    opps = client.get("/opportunities").json()["items"]
    assert opps, "expected the sample feed to be seeded in tests"
    opp = opps[0]
    prefill = opp["outreach_prefill"]
    assert prefill["id"] == opp["id"]  # id now flows through the prefill

    res = client.post(
        "/outreach/save-draft",
        json=_save_payload(
            company=prefill["company"] or "Sample Co",
            role=prefill["role"] or "Engineer",
            opportunity_id=prefill["id"],
            job_url=prefill.get("url") or None,
        ),
    )
    assert res.status_code == 200
    assert res.json()["opportunity_id"] == opp["id"]


# ----- 3. Saved from pasted job text (no opportunity) -----

def test_save_draft_from_pasted_job_has_no_opportunity(client):
    res = client.post("/outreach/save-draft", json=_save_payload(opportunity_id=None))
    assert res.status_code == 200
    assert res.json()["opportunity_id"] is None


# ----- 4. Pipeline listing -----

def test_saved_drafts_appear_in_pipeline_listing(client):
    client.post("/outreach/save-draft", json=_save_payload(company="Alpha"))
    client.post("/outreach/save-draft", json=_save_payload(company="Beta"))
    listed = client.get("/messages").json()
    companies = {m["company"] for m in listed}
    assert {"Alpha", "Beta"} <= companies


# ----- 5. Manual status / outcome / follow-up updates -----

def test_saved_draft_status_and_outcome_updates(client):
    mid = client.post("/outreach/save-draft", json=_save_payload()).json()["id"]

    sent = client.post(f"/messages/{mid}/mark-sent-manually").json()
    assert sent["status"] == "sent_manually"

    replied = client.post(f"/messages/{mid}/outcome", json={"outcome": "replied"}).json()
    assert replied["outcome"] == "replied"

    follow = client.post(
        f"/messages/{mid}/follow-up", json={"status": "follow_up_needed"}
    ).json()
    assert follow["follow_up_status"] == "follow_up_needed"


# ----- 6. Next Move AI can link to a saved pipeline item -----

def test_next_move_can_link_saved_pipeline_item(client):
    mid = client.post("/outreach/save-draft", json=_save_payload()).json()["id"]
    res = client.post(
        "/next-move/analyze",
        json={
            "reply_text": "Thanks for reaching out — are you free for a quick call this week?",
            "message_id": mid,
        },
    )
    assert res.status_code == 200
    target = res.json()["pipeline_target"]
    assert target["type"] == "message"
    assert target["id"] == mid


# ----- 7. Existing outreach drafting is unaffected -----

def test_existing_draft_from_paste_still_works(client):
    res = client.post(
        "/outreach/draft-from-paste",
        json={
            "jd_text": "Backend Engineer (Remote, EU). Build APIs in Python.",
            "contact": {"name": "Jordan", "title": "EM", "company": "Acme"},
            "language": "en",
            "channel": "email",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["body"] and "llm_used" in body
