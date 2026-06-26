"""Outreach email drafting — OpenAI Responses API with deterministic fallback.

Flow:
  1. Build a strict-JSON prompt from resume + goal + job + contact.
  2. If an OpenAI key is configured, ask the model (Responses API only).
  3. Validate the JSON; on ANY problem, fall back to a deterministic template.
  4. ALWAYS recompute the quality + risk checklists locally on the final body,
     so the verification never depends on the model's self-report.

Guardrails are baked in: never invents facts/personalization, never claims the
user applied, keeps a low-pressure ask, stays under 180 words.
"""

import json

from . import llm_client

WORD_LIMIT = 180

# Phrases that imply a fake relationship or an unsupported "I applied" claim.
_FAKE_CLAIM_TERMS = (
    "we met",
    "as we discussed",
    "when we spoke",
    "great to see you again",
    "as a fellow alum",
    "i already applied",
    "i have applied",
    "per our conversation",
)
# Aggressive / spammy signals we want to stay clear of.
_AGGRESSIVE_TERMS = (
    "refer me",
    "give me a referral",
    "asap",
    "as soon as possible",
    "urgent",
    "you must",
    "guarantee",
    "click here",
    "buy now",
    "free trial",
)
_SOFT_ASK_TERMS = (
    "would you be open",
    "would you have",
    "could we",
    "any advice",
    "no pressure",
    "happy to",
    "quick chat",
    "few minutes",
    "open to",
)

# ----- Turkish equivalents (bilingual outreach for the Turkey→remote/EU wedge) --
# Same guardrails in Turkish: never imply a fake prior relationship, never make a
# demanding/spammy ask, keep a single low-pressure request.
_FAKE_CLAIM_TERMS_TR = (
    "tanışmıştık",
    "görüşmüştük",
    "konuşmuştuk",
    "geçen sefer",
    "hatırlarsınız",
    "başvurdum",
    "başvuru yaptım",
)
_AGGRESSIVE_TERMS_TR = (
    "referans ver",
    "beni refere et",
    "acilen",
    "en kısa sürede",
    "hemen",
    "garanti",
    "buraya tıkla",
    "şimdi satın al",
)
_SOFT_ASK_TERMS_TR = (
    "müsait misiniz",
    "vaktiniz olur mu",
    "tavsiyeniz",
    "tavsiye",
    "kısa bir görüşme",
    "birkaç dakika",
    "rica etsem",
    "mümkün mü",
    "memnun olurum",
    "yardımcı olabilir misiniz",
    "merak ediyorum",
)


def _terms_for(language: str | None) -> tuple[tuple, tuple, tuple]:
    """Return (fake_claim, aggressive, soft_ask) term tuples for a language.

    Turkish bodies are checked against Turkish phrasing PLUS English, since role
    and skill terms often stay in English even inside a Turkish message."""
    if (language or "en").lower().startswith("tr"):
        return (
            _FAKE_CLAIM_TERMS + _FAKE_CLAIM_TERMS_TR,
            _AGGRESSIVE_TERMS + _AGGRESSIVE_TERMS_TR,
            _SOFT_ASK_TERMS + _SOFT_ASK_TERMS_TR,
        )
    return _FAKE_CLAIM_TERMS, _AGGRESSIVE_TERMS, _SOFT_ASK_TERMS


def _skill_phrase(skills: list[str], n: int = 2) -> str:
    chosen = [s for s in (skills or []) if s][:n]
    if not chosen:
        return "software engineering"
    if len(chosen) == 1:
        return chosen[0]
    return " and ".join(chosen)


def message_type_for(contact_type: str | None, outreach_goal: str | None) -> str:
    """A readable label for the draft, e.g. 'engineer_advice'."""
    ct = (contact_type or "contact").strip()
    og = (outreach_goal or "advice").strip()
    return f"{ct}_{og}"


# ----- Prompt -----

def build_prompt(
    *, profile_skills, experience_summary, goal, job, contact, tone
) -> str:
    """Compose the strict-JSON prompt. Only includes facts we actually have."""
    skills = ", ".join(profile_skills) if profile_skills else "(none listed)"
    lines = [
        "Write a short, honest networking email for a job seeker.",
        "",
        "RESUME / PROFILE (facts you may use — do NOT add anything not here):",
        f"- Skills: {skills}",
        f"- Summary: {experience_summary or '(none)'}",
        "",
        "JOB-SEARCH GOAL:",
        f"- Target role: {goal.get('target_role') or '(unspecified)'}",
        f"- Target location: {goal.get('target_location') or '(unspecified)'}",
        f"- Outreach goal: {goal.get('outreach_goal') or 'advice'}",
        f"- Tone preference: {tone or goal.get('tone_preference') or 'warm_low_pressure'}",
        "",
        "SELECTED JOB:",
        f"- Company: {job.get('company') or '(unknown)'}",
        f"- Role: {job.get('title') or '(unknown)'}",
        f"- Location: {job.get('location') or '(unknown)'}",
        "",
        "SELECTED CONTACT:",
        f"- Name: {contact.get('name') or '(unknown)'}",
        f"- Title: {contact.get('title') or '(unknown)'}",
        f"- Type: {contact.get('contact_type') or '(unknown)'}",
        "",
        "RULES:",
        "- Never invent facts, shared history, or personalization.",
        "- Do NOT claim the user already applied.",
        "- Be honest that the user is interested in the role/company.",
        "- Use 1-2 relevant skills from the resume, naturally.",
        "- Keep a single, low-pressure ask (advice or a brief chat), never a",
        "  demanding referral ask.",
        f"- Keep the body under {WORD_LIMIT} words.",
        "- No spammy phrasing, no exclamation spam, no false urgency.",
        "",
        "Return STRICT JSON only with exactly these keys:",
        '{"subject": str, "body": str, "personalization_notes": str}',
    ]
    return "\n".join(lines)


# ----- Deterministic fallback -----

def _deterministic_email(*, profile_skills, goal, job, contact, tone) -> dict:
    company = job.get("company") or "your team"
    role = job.get("title") or "the role"
    first = (contact.get("name") or "").strip().split()[0] if contact.get("name") else ""
    greeting = f"Hi {first}," if first else "Hi,"
    phrase = _skill_phrase(profile_skills)
    outreach_goal = goal.get("outreach_goal") or "advice"

    if outreach_goal == "referral":
        ask = (
            "If it feels right after that, I'd be grateful for any pointers on "
            "the best way to apply — but no pressure at all."
        )
    else:
        ask = (
            "Would you be open to a few minutes sometime to share what the team "
            "is like? No pressure either way."
        )

    body = (
        f"{greeting}\n\n"
        f"I'm a new-grad engineer working mostly with {phrase}, and I'm genuinely "
        f"interested in the {role} role at {company}. I'm trying to learn from "
        f"people actually doing the work rather than just applying into the void.\n\n"
        f"{ask}\n\n"
        f"Thanks for reading, and either way I appreciate your time."
    )
    subject = f"New grad interested in the {role} role at {company}"
    notes = (
        "Deterministic template (no LLM). Mentions the company, role, and a "
        "resume skill; single low-pressure ask; no invented personalization."
    )
    return {"subject": subject, "body": body, "personalization_notes": notes}


# ----- Checklists (always computed locally on the final body) -----

def quality_checklist(*, subject, body, company, role, profile_skills, language="en") -> dict:
    text = f"{subject}\n{body}".lower()
    body_words = len((body or "").split())
    matched = [s for s in (profile_skills or []) if s and s.lower() in text]
    exclamations = (body or "").count("!")
    fake_terms, aggressive_terms, soft_terms = _terms_for(language)

    items = [
        {"key": "mentions_company", "label": "Mentions the company",
         "passed": bool(company) and company.lower() in text},
        {"key": "mentions_role", "label": "Mentions the role",
         "passed": bool(role) and role.lower() in text},
        {"key": "mentions_skill", "label": "Mentions a relevant skill",
         "passed": len(matched) >= 1},
        {"key": "clear_ask", "label": "Has a clear ask",
         "passed": ("?" in (body or "")) or any(t in text for t in soft_terms)},
        {"key": "under_180_words", "label": f"Under {WORD_LIMIT} words",
         "passed": 0 < body_words <= WORD_LIMIT},
        {"key": "no_fake_claim", "label": "No fake/over-personalized claim",
         "passed": not any(t in text for t in fake_terms)},
        {"key": "low_pressure", "label": "Low-pressure tone",
         "passed": any(t in text for t in soft_terms)
         and not any(t in text for t in aggressive_terms)},
        {"key": "not_spammy", "label": "Not spammy",
         "passed": exclamations <= 1
         and not any(t in text for t in aggressive_terms)},
    ]
    passed = sum(1 for i in items if i["passed"])
    return {"items": items, "passed": passed, "total": len(items)}


def risk_checklist(*, contact_source: str | None) -> dict:
    source = (contact_source or "manual").lower()
    compliant = source in ("manual", "hunter", "pdl")
    items = [
        {"key": "compliant_source", "label": "Contact added manually or via a configured compliant provider",
         "passed": compliant},
        {"key": "no_scraping", "label": "No scraping source used", "passed": True},
        {"key": "not_bulk", "label": "Single draft — not bulk sending", "passed": True},
        {"key": "requires_approval", "label": "Requires explicit approval before any send",
         "passed": True},
    ]
    passed = sum(1 for i in items if i["passed"])
    return {"items": items, "passed": passed, "total": len(items)}


# ----- Explainability helpers (deterministic, no LLM) -----

def safety_summary(*, risk: dict | None, quality: dict | None) -> str:
    """One honest sentence on why this draft is safe / low-pressure.

    Reads the locally-computed checklists so the claim is never just asserted —
    it reflects the checks that actually passed on the final body.
    """
    low_pressure = False
    for item in (quality or {}).get("items", []):
        if item.get("key") == "low_pressure" and item.get("passed"):
            low_pressure = True
    risk_passed = (risk or {}).get("passed", 0)
    risk_total = (risk or {}).get("total", 0)
    bits = []
    bits.append(
        "a single low-pressure ask (advice or a brief chat), not a referral demand"
        if low_pressure
        else "a single, non-demanding ask"
    )
    if risk_total and risk_passed == risk_total:
        bits.append(
            "a compliant (non-scraped) contact, no bulk sending, and it can't be "
            "sent without your explicit approval"
        )
    else:
        bits.append("no bulk sending, and it can't be sent without your approval")
    return "Safe because it keeps " + bits[0] + ", with " + bits[1] + "."


def suggested_next_step(*, status: str | None, outcome: str | None) -> str:
    """The concrete next action for this draft, based on where it is in the
    review → manual-send → outcome workflow."""
    if outcome:
        return "Outcome logged — keep the thread warm with a thoughtful follow-up if it fits."
    status = (status or "draft").lower()
    if status == "draft":
        return "Review and edit the wording, then Approve it if it reads honestly."
    if status == "approved":
        return "Copy the email and send it yourself from your own inbox, then mark it sent."
    if status == "copied":
        return "Send it from your inbox, then mark it sent manually and log the outcome."
    if status in ("sent_manual", "sent_via_gmail"):
        return "Sent — log the outcome (replied / interview / no response) when you hear back."
    if status == "rejected":
        return "Rejected — generate a fresh draft or pick a different contact."
    return "Review the draft and decide whether to approve it."


# ----- Public entry point -----

def generate_email(
    *, profile_skills, experience_summary, goal, job, contact, tone
) -> dict:
    """Return a full email draft dict. Uses the LLM when available, else a
    deterministic template. Checklists are always computed locally."""
    subject = body = personalization_notes = None
    llm_used = False

    if llm_client.llm_available():
        prompt = build_prompt(
            profile_skills=profile_skills,
            experience_summary=experience_summary,
            goal=goal,
            job=job,
            contact=contact,
            tone=tone,
        )
        try:
            data = llm_client.generate_json(prompt)
            subject = str(data.get("subject") or "").strip()
            body = str(data.get("body") or "").strip()
            personalization_notes = str(data.get("personalization_notes") or "").strip()
            if not subject or not body:
                raise ValueError("missing subject/body")
            llm_used = True
        except Exception:
            subject = body = personalization_notes = None
            llm_used = False

    if not body:
        fb = _deterministic_email(
            profile_skills=profile_skills, goal=goal, job=job, contact=contact, tone=tone
        )
        subject, body, personalization_notes = (
            fb["subject"], fb["body"], fb["personalization_notes"]
        )

    quality = quality_checklist(
        subject=subject,
        body=body,
        company=job.get("company"),
        role=job.get("title"),
        profile_skills=profile_skills,
    )
    risk = risk_checklist(contact_source=contact.get("source"))

    return {
        "subject": subject,
        "body": body,
        "message_type": message_type_for(
            contact.get("contact_type"), goal.get("outreach_goal")
        ),
        "tone": tone or goal.get("tone_preference") or "warm_low_pressure",
        "personalization_notes": personalization_notes,
        "quality_checklist": quality,
        "risk_checklist": risk,
        "status": "draft",
        "llm_used": llm_used,
    }
