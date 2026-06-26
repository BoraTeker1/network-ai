"""LinkedIn outreach drafting — OpenAI Responses API with deterministic fallback.

The honest sibling of :mod:`email_generator`. Two draft kinds:

  - "connection": a connection-request note, hard-capped at LinkedIn's 300-char
    limit. Warm, advice-first, no fake "we met".
  - "dm": a short post-accept message / InMail with a single low-pressure ask.

Why no auto-send? "Draft it, copy it, paste it yourself" is the ONLY ToS-safe
way to do LinkedIn outreach — automation violates LinkedIn's terms — so the
manual-send ethos isn't a limitation here, it's the only honest path.

Guardrails mirror the email copilot: never invent facts/personalization, never
claim the user applied, keep a single low-pressure ask, and ALWAYS recompute the
quality + risk checklists locally on the final body.
"""

import json

from . import email_generator, llm_client
# Reuse the shared honesty/tone vocabularies so both copilots judge text the
# same way — one source of truth.
from .email_generator import (
    _AGGRESSIVE_TERMS,
    _FAKE_CLAIM_TERMS,
    _SOFT_ASK_TERMS,
    _skill_phrase,
)

# LinkedIn's hard caps. The connection note is the strict one (300 chars); the
# DM/InMail is kept short by convention rather than a platform wall.
CONNECTION_CHAR_LIMIT = 300
DM_CHAR_LIMIT = 600

KIND_CONNECTION = "connection"
KIND_DM = "dm"
VALID_KINDS = (KIND_CONNECTION, KIND_DM)

# Stored on EmailDraft.message_type so the row is recognizable as a LinkedIn draft.
MESSAGE_TYPES = {
    KIND_CONNECTION: "linkedin_connection",
    KIND_DM: "linkedin_dm",
}


def _char_limit(kind: str) -> int:
    return CONNECTION_CHAR_LIMIT if kind == KIND_CONNECTION else DM_CHAR_LIMIT


# ----- Prompt -----

def build_prompt(
    *, kind, profile_skills, experience_summary, goal, job, contact, tone
) -> str:
    """Compose the strict-JSON prompt. Only includes facts we actually have."""
    skills = ", ".join(profile_skills) if profile_skills else "(none listed)"
    limit = _char_limit(kind)
    if kind == KIND_CONNECTION:
        intro = (
            "Write a short, honest LinkedIn CONNECTION REQUEST note for a job "
            "seeker. This is the tiny note attached to a connection invite."
        )
        format_rule = (
            f"- HARD LIMIT: the note MUST be at most {limit} characters "
            "(LinkedIn rejects longer). Aim for 2-3 short sentences."
        )
    else:
        intro = (
            "Write a short, honest LinkedIn MESSAGE (sent after they accept the "
            "connection, or as an InMail) for a job seeker."
        )
        format_rule = (
            f"- Keep it under {limit} characters and skimmable on mobile."
        )
    lines = [
        intro,
        "",
        "RESUME / PROFILE (facts you may use — do NOT add anything not here):",
        f"- Skills: {skills}",
        f"- Summary: {experience_summary or '(none)'}",
        "",
        "JOB-SEARCH GOAL:",
        f"- Target role: {goal.get('target_role') or '(unspecified)'}",
        f"- Outreach goal: {goal.get('outreach_goal') or 'advice'}",
        f"- Tone preference: {tone or goal.get('tone_preference') or 'warm_low_pressure'}",
        "",
        "SELECTED JOB:",
        f"- Company: {job.get('company') or '(unknown)'}",
        f"- Role: {job.get('title') or '(unknown)'}",
        "",
        "SELECTED CONTACT:",
        f"- Name: {contact.get('name') or '(unknown)'}",
        f"- Title: {contact.get('title') or '(unknown)'}",
        f"- Type: {contact.get('contact_type') or '(unknown)'}",
        "",
        "RULES:",
        "- Never invent facts, shared history, or personalization.",
        "- Do NOT claim the user already applied or that you have met before.",
        "- Use at most one relevant skill from the resume, naturally.",
        "- Keep a single, low-pressure ask (advice or a brief chat), never a",
        "  demanding referral ask.",
        format_rule,
        "- No spammy phrasing, no exclamation spam, no false urgency, no links.",
        "",
        "Return STRICT JSON only with exactly these keys:",
        '{"body": str, "personalization_notes": str}',
    ]
    return "\n".join(lines)


# ----- Deterministic fallback -----

def _deterministic_linkedin(*, kind, profile_skills, goal, job, contact) -> dict:
    company = job.get("company") or "your team"
    role = job.get("title") or "the role"
    first = (contact.get("name") or "").strip().split()[0] if contact.get("name") else ""
    phrase = _skill_phrase(profile_skills, n=1)

    if kind == KIND_CONNECTION:
        # Compose conservatively, then fall back to shorter variants if the
        # 300-char cap is exceeded (long company/role names).
        greeting = f"Hi {first} — " if first else "Hi — "
        candidates = [
            (
                f"{greeting}I'm a new-grad engineer focused on {phrase}, and I'm "
                f"genuinely interested in the {role} role at {company}. Would you "
                "be open to connecting? I'd value any quick advice — no pressure."
            ),
            (
                f"{greeting}new-grad engineer keen on the {role} role at {company}. "
                "Would you be open to connecting for a little advice? No pressure."
            ),
            (
                f"{greeting}new-grad engineer interested in {company}. Would you be "
                "open to connecting for some quick advice? No pressure either way."
            ),
        ]
        body = next(
            (c for c in candidates if len(c) <= CONNECTION_CHAR_LIMIT),
            candidates[-1][:CONNECTION_CHAR_LIMIT],
        )
        notes = (
            "Deterministic template (no LLM). Connection note kept under "
            f"{CONNECTION_CHAR_LIMIT} chars; mentions the company/role and a single "
            "low-pressure ask; no invented personalization."
        )
        return {"body": body, "personalization_notes": notes}

    # Post-accept DM.
    greeting = f"Hi {first}," if first else "Hi,"
    outreach_goal = goal.get("outreach_goal") or "advice"
    if outreach_goal == "referral":
        ask = (
            "If it feels right, I'd be grateful for any pointers on the best way to "
            "apply — but no pressure at all."
        )
    else:
        ask = (
            "Would you be open to a few minutes to share what the team is like? "
            "No pressure either way."
        )
    body = (
        f"{greeting} thanks for connecting! I'm a new-grad engineer working mostly "
        f"with {phrase}, and I'm genuinely interested in the {role} role at "
        f"{company}. I'm trying to learn from people doing the work rather than "
        f"applying into the void. {ask}"
    )
    notes = (
        "Deterministic template (no LLM). Short post-accept message with a single "
        "low-pressure ask; mentions company, role, and a resume skill; no invented "
        "personalization."
    )
    return {"body": body, "personalization_notes": notes}


# ----- Checklist (computed locally on the final body) -----

def quality_checklist(*, kind, body, company, role, profile_skills) -> dict:
    text = (body or "").lower()
    char_count = len(body or "")
    limit = _char_limit(kind)
    matched = [s for s in (profile_skills or []) if s and s.lower() in text]
    exclamations = (body or "").count("!")

    items = [
        {"key": "mentions_company", "label": "Mentions the company",
         "passed": bool(company) and company.lower() in text},
        {"key": "within_char_limit", "label": f"Within {limit} characters",
         "passed": 0 < char_count <= limit},
        {"key": "clear_ask", "label": "Has a clear, single ask",
         "passed": ("?" in (body or "")) or any(t in text for t in _SOFT_ASK_TERMS)},
        {"key": "no_fake_claim", "label": "No fake/over-personalized claim",
         "passed": not any(t in text for t in _FAKE_CLAIM_TERMS)},
        {"key": "low_pressure", "label": "Low-pressure tone",
         "passed": any(t in text for t in _SOFT_ASK_TERMS)
         and not any(t in text for t in _AGGRESSIVE_TERMS)},
        {"key": "not_spammy", "label": "Not spammy (no links/urgency)",
         "passed": exclamations <= 1
         and "http" not in text
         and not any(t in text for t in _AGGRESSIVE_TERMS)},
    ]
    # The DM has room to reference the specific role; the 300-char note may not.
    if kind == KIND_DM:
        items.insert(
            1,
            {"key": "mentions_role", "label": "Mentions the role",
             "passed": bool(role) and role.lower() in text},
        )
    if matched:
        items.append(
            {"key": "mentions_skill", "label": "Mentions a relevant skill",
             "passed": True}
        )
    passed = sum(1 for i in items if i["passed"])
    return {"items": items, "passed": passed, "total": len(items)}


# ----- Public entry point -----

def generate_linkedin(
    *, kind, profile_skills, experience_summary, goal, job, contact, tone
) -> dict:
    """Return a full LinkedIn draft dict (subject is always None). Uses the LLM
    when available, else a deterministic template. Checklists computed locally."""
    if kind not in VALID_KINDS:
        kind = KIND_CONNECTION
    body = personalization_notes = None
    llm_used = False

    if llm_client.llm_available():
        prompt = build_prompt(
            kind=kind,
            profile_skills=profile_skills,
            experience_summary=experience_summary,
            goal=goal,
            job=job,
            contact=contact,
            tone=tone,
        )
        try:
            data = llm_client.generate_json(prompt)
            body = str(data.get("body") or "").strip()
            personalization_notes = str(data.get("personalization_notes") or "").strip()
            if not body:
                raise ValueError("missing body")
            # Enforce the platform cap even on LLM output — fall back if it blew
            # past the connection-note limit rather than ship a note LinkedIn rejects.
            if kind == KIND_CONNECTION and len(body) > CONNECTION_CHAR_LIMIT:
                raise ValueError("connection note over char limit")
            llm_used = True
        except Exception:
            body = personalization_notes = None
            llm_used = False

    if not body:
        fb = _deterministic_linkedin(
            kind=kind, profile_skills=profile_skills, goal=goal, job=job, contact=contact
        )
        body, personalization_notes = fb["body"], fb["personalization_notes"]

    quality = quality_checklist(
        kind=kind,
        body=body,
        company=job.get("company"),
        role=job.get("title"),
        profile_skills=profile_skills,
    )
    # Risk checks are platform-agnostic — reuse the email copilot's logic.
    risk = email_generator.risk_checklist(contact_source=contact.get("source"))

    return {
        "subject": None,
        "body": body,
        "message_type": MESSAGE_TYPES[kind],
        "tone": tone or goal.get("tone_preference") or "warm_low_pressure",
        "personalization_notes": personalization_notes,
        "quality_checklist": quality,
        "risk_checklist": risk,
        "status": "draft",
        "llm_used": llm_used,
    }
