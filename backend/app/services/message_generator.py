"""Deterministic quality checklist + tone labels for outreach drafts.

Pure functions, no LLM: the messages router uses these to score every draft
in the pipeline against a transparent, explainable checklist.
"""

CONNECTION_LIMIT = 280

# Deterministic tone label per draft type (shown as a chip in the UI). Tones:
# concise | warm | direct | low-pressure.
TONE_BY_TYPE = {
    "connection_request": "concise",
    "recruiter_follow_up": "direct",
    "engineer_advice_request": "low-pressure",
    "alumni_style_message": "warm",
}


def tone_for(message_type: str) -> str:
    """Tone label for a message type (defaults to low-pressure)."""
    return TONE_BY_TYPE.get(message_type, "low-pressure")


# ----- Quality checklist (deterministic) -----

# Words/claims we never want to appear — they imply fake familiarity or
# overstate the relationship.
_FAKE_CLAIM_TERMS = (
    "we met",
    "as we discussed",
    "great to see you again",
    "longtime fan",
    "your biggest fan",
    "we connected at",
    "as a fellow alum",  # only honest if the user really is one; keep it out of templates
)


def _mentions(text: str, value: str | None) -> bool:
    return bool(value) and value.strip().lower() in text.lower()


def quality_checklist(
    text: str,
    message_type: str,
    company: str | None,
    role: str | None,
    profile_skills: list[str],
) -> dict:
    """Score a draft against a transparent, deterministic checklist.

    Returns {"items": [{"key","label","passed"}...], "passed": int, "total": int}.
    Nothing here calls an LLM — every check is explainable.
    """
    text = text or ""
    lower = text.lower()
    is_connection = message_type == "connection_request"
    char_limit = CONNECTION_LIMIT

    matched_skills = [s for s in (profile_skills or []) if s and s.lower() in lower]
    has_fake_claim = any(term in lower for term in _FAKE_CLAIM_TERMS)
    # A low-pressure ask: invites a conversation without demanding anything.
    soft_ask_terms = ("would love", "would you be open", "no pressure", "happy to",
                      "any advice", "is this a good time", "connect")
    has_soft_ask = any(term in lower for term in soft_ask_terms)

    items = [
        {
            "key": "char_limit",
            "label": (
                f"Under {char_limit} characters"
                if is_connection
                else "Reasonable length"
            ),
            "passed": len(text) <= (char_limit if is_connection else 600),
        },
        {
            "key": "mentions_company",
            "label": "Mentions the company",
            "passed": _mentions(text, company),
        },
        {
            "key": "mentions_role",
            "label": "Mentions the role",
            "passed": _mentions(text, role),
        },
        {
            "key": "mentions_skills",
            "label": "Mentions 1–3 relevant skills",
            "passed": 1 <= len(matched_skills) <= 3,
        },
        {
            "key": "no_fake_claims",
            "label": "Avoids fake/over-personalized claims",
            "passed": not has_fake_claim,
        },
        {
            "key": "soft_ask",
            "label": "Has a clear but low-pressure ask",
            "passed": has_soft_ask,
        },
    ]
    passed = sum(1 for i in items if i["passed"])
    return {"items": items, "passed": passed, "total": len(items)}
