"""Outreach message draft generator + deterministic quality checklist.

Template-based drafts — no LLM. Pure functions: the router supplies the
profile skills + job details, this builds natural-sounding message texts and
can score each draft against a transparent quality checklist.

Guardrails baked into the templates:
  - Never invents shared background, schools, or specific people.
  - Never claims the user already applied (only "interested in").
  - Never fakes personalization — if no contact name is given, the greeting
    stays generic instead of pretending familiarity.
  - Keeps a low-pressure ask; never demands a referral.
  - connection_request stays under 280 characters (LinkedIn's limit).

The four draft types:
  - connection_request    short LinkedIn connection note (<280 chars)
  - recruiter_follow_up    a note to a recruiter about next steps
  - engineer_advice_request a peer-level request for advice from an engineer
  - alumni_style_message    a warm note framed around shared early-career path
"""

CONNECTION_LIMIT = 280

# Message types we always produce, in display order.
MESSAGE_TYPES = (
    "connection_request",
    "recruiter_follow_up",
    "engineer_advice_request",
    "alumni_style_message",
)

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


def _greeting(contact_name: str | None) -> str:
    """First-name greeting when we have a name, otherwise a generic one.

    We never guess a name — a generic greeting is more honest than a fake
    personalization.
    """
    if contact_name and contact_name.strip():
        first = contact_name.strip().split()[0]
        return f"Hi {first},"
    return "Hi,"


def _skill_phrase(skills: list[str], n: int = 2) -> str:
    """Short, human phrase from the user's strongest (first-listed) skills."""
    chosen = [s for s in (skills or []) if s][:n]
    if not chosen:
        return "software engineering"
    if len(chosen) == 1:
        return chosen[0]
    return " and ".join(chosen)


def _connection_request(company: str, role: str, skills: list[str], g: str) -> str:
    """A short, natural connection note that stays under the 280 char limit.

    Trims the skill phrase before falling back to a skill-free version so the
    note always fits.
    """
    for n in (2, 1):
        phrase = _skill_phrase(skills, n)
        text = (
            f"{g} I'm a new grad working with {phrase}, and I'm interested in the "
            f"{role} role at {company}. Would love to connect and follow your team's work."
        )
        if len(text) <= CONNECTION_LIMIT:
            return text
    text = (
        f"{g} New-grad engineer interested in the {role} role at {company}. "
        f"Would love to connect and follow your team's work."
    )
    return text if len(text) <= CONNECTION_LIMIT else text[: CONNECTION_LIMIT - 1]


def _recruiter_follow_up(company: str, role: str, skills: list[str], g: str) -> str:
    phrase = _skill_phrase(skills)
    return (
        f"{g} thanks for connecting. I'm a new grad focused on {phrase} and I'm "
        f"interested in the {role} role at {company}. Is this a good time to apply, "
        f"and is there anything you'd suggest I highlight? Happy to share my resume."
    )


def _engineer_advice_request(company: str, role: str, skills: list[str], g: str) -> str:
    phrase = _skill_phrase(skills)
    return (
        f"{g} I'm a new grad who works mostly with {phrase}, and I've been looking at "
        f"the {role} role at {company}. Would you be open to a few minutes on what the "
        f"team is like and what helped you ramp up? No pressure either way — thanks."
    )


def _alumni_style_message(company: str, role: str, skills: list[str], g: str) -> str:
    phrase = _skill_phrase(skills)
    return (
        f"{g} I'm early in my career working with {phrase}, and I'm hoping to break "
        f"into a role like the {role} position at {company}. I'd really value any "
        f"advice you have for someone making that jump. Thanks for reading."
    )


_BUILDERS = {
    "connection_request": _connection_request,
    "recruiter_follow_up": _recruiter_follow_up,
    "engineer_advice_request": _engineer_advice_request,
    "alumni_style_message": _alumni_style_message,
}


def build_drafts(
    profile_skills: list[str],
    company: str,
    role: str,
    contact_name: str | None = None,
    contact_title: str | None = None,
) -> list[tuple[str, str]]:
    """Return [(message_type, text), ...] for the 4 draft variants."""
    g = _greeting(contact_name)
    return [
        (mtype, _BUILDERS[mtype](company, role, profile_skills, g))
        for mtype in MESSAGE_TYPES
    ]


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
