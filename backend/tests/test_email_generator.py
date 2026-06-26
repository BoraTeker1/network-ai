"""Email generation tests: deterministic fallback + explainability helpers."""

from app.services import email_generator, llm_client

GOAL = {"target_role": "Backend Engineer", "outreach_goal": "advice"}
JOB = {"company": "Acme", "title": "Backend Engineer", "location": "Remote"}
CONTACT = {"name": "Jordan Smith", "title": "Engineer", "contact_type": "engineer",
           "source": "manual"}


def test_fallback_used_when_llm_unavailable(monkeypatch):
    monkeypatch.setattr(llm_client, "llm_available", lambda: False)
    result = email_generator.generate_email(
        profile_skills=["Python", "FastAPI"],
        experience_summary="New grad engineer",
        goal=GOAL, job=JOB, contact=CONTACT, tone="warm_low_pressure",
    )
    assert result["llm_used"] is False
    assert result["body"]  # deterministic template still produces a body
    assert result["subject"]
    assert "Acme" in result["body"]


def test_fallback_when_llm_raises(monkeypatch):
    monkeypatch.setattr(llm_client, "llm_available", lambda: True)

    def _boom(_prompt):
        raise llm_client.LLMError("simulated failure")

    monkeypatch.setattr(llm_client, "generate_json", _boom)
    result = email_generator.generate_email(
        profile_skills=["Python"], experience_summary="x",
        goal=GOAL, job=JOB, contact=CONTACT, tone=None,
    )
    assert result["llm_used"] is False
    assert result["body"]


def test_quality_and_risk_checklists_present(monkeypatch):
    monkeypatch.setattr(llm_client, "llm_available", lambda: False)
    result = email_generator.generate_email(
        profile_skills=["Python"], experience_summary="x",
        goal=GOAL, job=JOB, contact=CONTACT, tone=None,
    )
    q = result["quality_checklist"]
    assert q["passed"] == q["total"]  # template passes its own checklist
    assert result["risk_checklist"]["passed"] == result["risk_checklist"]["total"]


def test_quality_checklist_flags_missing_company():
    q = email_generator.quality_checklist(
        subject="Hello", body="No company named here.",
        company="Acme", role="Backend Engineer", profile_skills=["Python"],
    )
    company_item = next(i for i in q["items"] if i["key"] == "mentions_company")
    assert company_item["passed"] is False


def test_safety_summary_mentions_low_pressure():
    quality = {"items": [{"key": "low_pressure", "passed": True}], "passed": 8, "total": 8}
    risk = {"passed": 4, "total": 4}
    summary = email_generator.safety_summary(risk=risk, quality=quality)
    assert "low-pressure" in summary.lower()
    assert "approval" in summary.lower()


def test_suggested_next_step_transitions():
    assert "Approve" in email_generator.suggested_next_step(status="draft", outcome=None)
    assert "Copy" in email_generator.suggested_next_step(status="approved", outcome=None)
    assert "log the outcome" in email_generator.suggested_next_step(
        status="sent_manual", outcome=None
    ).lower()
    # Once an outcome exists, the step pivots to follow-up.
    assert "follow-up" in email_generator.suggested_next_step(
        status="sent_manual", outcome="replied"
    ).lower()
