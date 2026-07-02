"""Next Move AI tests: intent detection, fallback, suggested pipeline update."""

import pytest

from app.services import llm_client, next_move


@pytest.fixture(autouse=True)
def force_fallback(monkeypatch):
    """Run the deterministic path for every test — no network calls."""
    monkeypatch.setattr(llm_client, "llm_available", lambda: False)


# ----- Intent detection -----

@pytest.mark.parametrize(
    "text,expected",
    [
        ("Are you free for a quick call this week to chat?", "interview_related"),
        ("Happy to refer you internally and pass your info along.", "referral_possible"),
        ("Could you send me your resume so I can take a look?", "asks_for_resume"),
        ("Will you require visa sponsorship now or in the future?",
         "asks_for_work_authorization"),
        ("Unfortunately the role has been filled, we are not moving forward.",
         "negative"),
        ("Things are busy right now, can you circle back in a few weeks?",
         "needs_follow_up"),
        ("Great to hear from you, sounds good — excited!", "positive"),
        ("Got it, thanks.", "neutral"),
    ],
)
def test_intent_detection(text, expected):
    intent, _signals = next_move.primary_intent(text)
    assert intent == expected


def test_negative_tone_overrides_specific_signals():
    # A rejection that mentions a call should still read as negative.
    intent, _ = next_move.primary_intent(
        "Unfortunately we won't be moving forward, but happy to chat another time."
    )
    assert intent == "negative"


# ----- Fallback drafting -----

def test_analyze_fallback_produces_complete_drafts():
    r = next_move.analyze_reply(
        reply_text="Sounds good, excited to chat about the role!",
        context={"company": "Acme", "role": "Backend Engineer",
                 "contact_name": "Jordan Smith", "contact_title": None},
    )
    assert r["llm_used"] is False
    assert r["drafted_email"]["subject"] and r["drafted_email"]["body"]
    assert r["drafted_short_message"]
    assert r["quality_checklist"]["total"] > 0
    assert r["safety_checklist"]["total"] > 0
    assert r["intent"] in next_move.INTENTS
    assert r["urgency"] in next_move.URGENCIES


def test_work_authorization_adds_safety_item_and_risk_note():
    r = next_move.analyze_reply(
        reply_text="Quick question — will you need visa sponsorship?",
        context={},
    )
    keys = {i["key"] for i in r["safety_checklist"]["items"]}
    assert "truthful_authorization" in keys
    assert "truthful" in r["risk_notes"].lower()


# ----- Suggested pipeline update + momentum preview -----

@pytest.mark.parametrize(
    "text,outcome",
    [
        ("Are you free for a call this week?", "interview_received"),
        ("Happy to refer you internally.", "referral_received"),
        ("Unfortunately the position is filled.", "rejected"),
        ("Sounds good, thanks for the note!", "replied"),
    ],
)
def test_suggested_pipeline_update(text, outcome):
    r = next_move.analyze_reply(reply_text=text, context={})
    assert r["suggested_pipeline_update"] == outcome


# ----- API endpoint integration -----

def _profile(client):
    client.post("/profile/resume-text", json={
        "resume_text": "New grad. Skills: Python, FastAPI, React, SQL, Docker."
    })


def _seed_message(client, db_session):
    _profile(client)
    saved = client.post("/outreach/save-draft", json={
        "body": "Hi — I'd love to connect about the Backend Engineer role at Acme.",
        "company": "Acme", "role": "Backend Engineer",
        "channel": "email", "language": "en",
    }).json()
    return saved["id"]


def test_analyze_endpoint_rejects_empty(client):
    r = client.post("/next-move/analyze", json={"reply_text": "   "})
    assert r.status_code == 400


def test_analyze_endpoint_links_pipeline_target(client, db_session):
    mid = _seed_message(client, db_session)
    a = client.post(
        "/next-move/analyze",
        json={"reply_text": "Are you free for a call this week?", "message_id": mid},
    ).json()
    assert a["pipeline_target"] == {"type": "message", "id": mid}
    assert a["suggested_pipeline_update"] == "interview_received"
    assert a["drafted_email"]["body"]  # context flows into the draft


def test_outcome_confirmation_updates_pipeline(client, db_session):
    mid = _seed_message(client, db_session)
    client.post(
        "/next-move/analyze",
        json={"reply_text": "Are you free for a call this week?", "message_id": mid},
    )
    # Confirming the suggested outcome reuses the existing messages endpoint.
    res = client.post(
        f"/messages/{mid}/outcome", json={"outcome": "interview_received"}
    ).json()
    assert res["outcome"] == "interview_received"
