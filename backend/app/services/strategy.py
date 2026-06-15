"""Deterministic networking strategy service.

Turns a numeric match into *decisions*: a 4-tier label, a single "next best
action", and a full outreach strategy (who to contact, how many, what tone,
advice-vs-referral, and a step sequence).

Everything here is a pure function of the match score + a few job signals — no
LLM, no randomness — so the demo is reproducible and explainable.
"""

from ..models import Job

# Score tiers (aligned to the labels shown in the UI).
STRONG_MIN = 75
NETWORK_MIN = 50
LOW_MIN = 25


def label_for_score(score: float) -> str:
    """4-tier, decision-oriented label for a 0-100 score."""
    if score >= STRONG_MIN:
        return "Strong Target"
    if score >= NETWORK_MIN:
        return "Worth Networking"
    if score >= LOW_MIN:
        return "Low Priority"
    return "Poor Fit"


def _is_recruiter_friendly(job: Job) -> bool:
    """Big, well-known employers tend to route new grads through recruiters."""
    title = (job.title or "").lower()
    return "new grad" in title or "university" in title or "early career" in title


def next_best_action(score: float, job: Job, matched_skills: int = 0) -> str:
    """One concrete recommended action for this match (deterministic)."""
    label = label_for_score(score)

    if label == "Strong Target":
        return (
            "Strong target — generate outreach drafts now. Aim to reach 1 recruiter "
            "and 2 engineers before you apply."
        )
    if label == "Worth Networking":
        if matched_skills >= 1:
            return (
                "Worth networking — start with an engineer advice request (not a "
                "referral ask) to learn about the team, then apply."
            )
        return (
            "Worth networking — connect with a recruiter first to confirm the role "
            "is open to new grads before investing more effort."
        )
    if label == "Low Priority":
        return (
            "Low priority — save it, but don't spend outreach effort yet. Revisit if "
            "a warm contact appears."
        )
    return "Poor fit — skip unless you have a personal connection at the company."


def _sequence(score: float) -> list[dict]:
    """Ordered outreach sequence for the job-detail strategy panel."""
    strong = score >= NETWORK_MIN
    return [
        {
            "step": 1,
            "title": "Connect with a recruiter",
            "detail": (
                "Send a short, low-pressure connection note confirming the role is "
                "open to new grads."
            ),
        },
        {
            "step": 2,
            "title": "Ask an engineer for advice",
            "detail": (
                "Request a few minutes on what the team does and how they ramped up — "
                "advice first, never a referral ask."
            ),
        },
        {
            "step": 3,
            "title": "Follow up after connecting",
            "detail": (
                "Once someone replies, share your interest in the role and ask what "
                "they'd suggest you highlight."
                if strong
                else "Only follow up if you get a reply — quality over volume."
            ),
        },
        {
            "step": 4,
            "title": "Log the outcome",
            "detail": "Record what happened (replied, interview, no response) to keep your pipeline honest.",
        },
    ]


def outreach_strategy(score: float, job: Job, matched_skills: int = 0) -> dict:
    """A deterministic outreach plan for a job-detail strategy panel."""
    label = label_for_score(score)
    recruiter_first = _is_recruiter_friendly(job) or label == "Strong Target"

    if label == "Strong Target":
        contact_count = "Reach out to ~3 people: 1 recruiter and 2 engineers."
        tone = "warm"
        ask = "advice"
        who_first = (
            "Start with a recruiter to confirm timing, then engineers on the team."
            if recruiter_first
            else "Start with an engineer on the team for an advice conversation."
        )
    elif label == "Worth Networking":
        contact_count = "Reach out to 1–2 people to learn more before applying."
        tone = "low-pressure"
        ask = "advice"
        who_first = "Start with one engineer for an advice request, not a referral ask."
    elif label == "Low Priority":
        contact_count = "Hold off — save the role and don't spend outreach effort yet."
        tone = "low-pressure"
        ask = "advice"
        who_first = "No outreach recommended right now."
    else:
        contact_count = "Skip outreach unless you already know someone here."
        tone = "low-pressure"
        ask = "advice"
        who_first = "No outreach recommended."

    return {
        "label": label,
        "score": int(round(score)),
        "who_first": who_first,
        "contact_count": contact_count,
        "tone": tone,
        "ask_type": ask,  # always advice-first by design (never referral as the opener)
        "sequence": _sequence(score),
        "next_best_action": next_best_action(score, job, matched_skills),
    }
