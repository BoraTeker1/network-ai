"""LinkedIn generation tests: deterministic fallback + 300-char cap enforcement."""

from app.services import linkedin_generator, llm_client

GOAL = {"target_role": "Backend Engineer", "outreach_goal": "advice"}
JOB = {"company": "Acme", "title": "Backend Engineer", "location": "Remote"}
CONTACT = {"name": "Jordan Smith", "title": "Engineer", "contact_type": "engineer",
           "source": "manual"}


def _gen(kind, monkeypatch, **over):
    monkeypatch.setattr(llm_client, "llm_available", lambda: False)
    return linkedin_generator.generate_linkedin(
        kind=kind,
        profile_skills=over.get("skills", ["Python", "FastAPI"]),
        experience_summary="New grad engineer",
        goal=over.get("goal", GOAL),
        job=over.get("job", JOB),
        contact=CONTACT,
        tone="warm_low_pressure",
    )


def test_connection_note_fallback_within_char_limit(monkeypatch):
    result = _gen("connection", monkeypatch)
    assert result["llm_used"] is False
    assert result["subject"] is None  # LinkedIn has no subject
    assert result["message_type"] == "linkedin_connection"
    assert 0 < len(result["body"]) <= linkedin_generator.CONNECTION_CHAR_LIMIT
    item = next(
        i for i in result["quality_checklist"]["items"]
        if i["key"] == "within_char_limit"
    )
    assert item["passed"] is True


def test_connection_note_stays_under_cap_with_long_names(monkeypatch):
    long_job = {
        "company": "A Very Long Enterprise Company Name Incorporated Worldwide",
        "title": "Senior Distributed Systems Backend Platform Engineer II",
        "location": "Remote",
    }
    result = _gen("connection", monkeypatch, job=long_job)
    assert len(result["body"]) <= linkedin_generator.CONNECTION_CHAR_LIMIT


def test_dm_mentions_role_and_company(monkeypatch):
    result = _gen("dm", monkeypatch)
    assert result["message_type"] == "linkedin_dm"
    text = result["body"].lower()
    assert "acme" in text
    assert "backend engineer" in text


def test_llm_connection_over_limit_falls_back(monkeypatch):
    monkeypatch.setattr(llm_client, "llm_available", lambda: True)
    too_long = "x" * (linkedin_generator.CONNECTION_CHAR_LIMIT + 50)
    monkeypatch.setattr(
        llm_client,
        "generate_json",
        lambda _p: {"body": too_long, "personalization_notes": "n"},
    )
    result = linkedin_generator.generate_linkedin(
        kind="connection",
        profile_skills=["Python"],
        experience_summary="x",
        goal=GOAL, job=JOB, contact=CONTACT, tone=None,
    )
    # Over-cap LLM output is rejected → deterministic fallback (under cap).
    assert result["llm_used"] is False
    assert len(result["body"]) <= linkedin_generator.CONNECTION_CHAR_LIMIT


def test_template_passes_its_own_checklist(monkeypatch):
    for kind in ("connection", "dm"):
        result = _gen(kind, monkeypatch)
        q = result["quality_checklist"]
        assert q["passed"] == q["total"], f"{kind} failed: {q}"
        assert result["risk_checklist"]["passed"] == result["risk_checklist"]["total"]
