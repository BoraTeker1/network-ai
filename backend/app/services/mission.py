"""Today's Networking Mission — deterministic dashboard aggregation.

Turns everything the app already knows (profile, goal, best match, drafts,
follow-ups, pipeline, momentum) into one clean, action-oriented object so the
user opens the app and immediately knows *what to do today*.

This is a pure aggregation over local data:
- No LLM calls, no external APIs, no scraping, no auto-send.
- Reuses the existing matcher / strategy / momentum / contact-discovery
  services — it never re-implements matching, strategy, or momentum logic.

Everything degrades gracefully: with no profile/jobs/contacts it still returns
a fully-populated object whose `setup_steps` tell the user exactly what to do
next, so the dashboard is never blank.
"""

import json

from sqlalchemy.orm import Session

from ..models import (
    CONTACT_TYPES,
    DEMO_USER_ID,
    Contact,
    EmailDraft,
    Goal,
    Job,
    JobMatch,
    Meeting,
    Message,
    Profile,
)
from . import contact_discovery, matcher, momentum, strategy

# Humanized labels for the controlled contact-type vocabulary.
CONTACT_TYPE_LABELS = {
    "recruiter": "Recruiter",
    "technical_recruiter": "Technical recruiter",
    "hiring_manager": "Hiring manager",
    "engineer": "Team engineer",
    "alumni": "Alumni",
    "founder": "Founder",
}

# Deterministic default contact ordering per match label (used when the user
# hasn't set preferred contact types on their goal). Advice-first by design.
_LABEL_CONTACT_TYPES = {
    "Strong Target": ["recruiter", "hiring_manager", "engineer"],
    "Worth Networking": ["engineer", "alumni", "recruiter"],
    "Low Priority": ["engineer"],
    "Poor Fit": [],
}


def _goal_dict(goal: Goal | None) -> dict | None:
    if goal is None:
        return None
    return {
        "id": goal.id,
        "target_role": goal.target_role,
        "target_location": goal.target_location,
        "target_company_type": goal.target_company_type,
        "outreach_goal": goal.outreach_goal,
        "tone_preference": goal.tone_preference,
        "preferred_contact_types": json.loads(goal.preferred_contact_types)
        if goal.preferred_contact_types
        else [],
    }


def _recommended_contact_types(label: str, goal: Goal | None, company: str | None,
                               goal_dict: dict | None) -> list[dict]:
    """Who to look for, ordered. Honors the user's goal preferences, else uses a
    deterministic per-label default. Reuses contact_discovery for the rationale."""
    preferred = (goal_dict or {}).get("preferred_contact_types") or []
    types = [t for t in preferred if t in CONTACT_TYPES] or _LABEL_CONTACT_TYPES.get(
        label, []
    )
    goal_for_why = {"outreach_goal": goal.outreach_goal if goal else None}
    return [
        {
            "contact_type": t,
            "label": CONTACT_TYPE_LABELS.get(t, t.replace("_", " ").title()),
            "why": contact_discovery._why_relevant(t, goal_for_why, company),
        }
        for t in types
    ]


def _best_match(db: Session) -> tuple[dict | None, Job | None]:
    """Highest-ranked match for the demo profile (reuses the matcher)."""
    ranked = matcher.ranked_matches(db, limit=1)
    if not ranked:
        return None, None
    best = ranked[0]
    job = db.query(Job).filter(Job.id == best["job_id"]).first()
    return best, job


def _drafts_summary(db: Session) -> dict:
    """Counts of drafts awaiting the user across both workflows.

    `pending_review` is the headline number: drafts still sitting at status
    'draft' that the user should approve or reject. `ready_to_send` are approved
    drafts the user has not yet copied / marked sent.
    """
    messages = db.query(Message).filter(Message.user_id == DEMO_USER_ID).all()
    emails = db.query(EmailDraft).filter(EmailDraft.user_id == DEMO_USER_ID).all()

    message_drafts = sum(1 for m in messages if m.status == "draft")
    email_drafts = sum(1 for e in emails if e.status == "draft")
    ready_to_send = sum(1 for m in messages if m.status == "approved") + sum(
        1 for e in emails if e.status == "approved"
    )
    return {
        "message_drafts": message_drafts,
        "email_drafts": email_drafts,
        "pending_review": message_drafts + email_drafts,
        "ready_to_send": ready_to_send,
    }


def _follow_ups_summary(db: Session) -> dict:
    """Follow-ups the user has flagged as needed across both workflows."""
    msg_due = (
        db.query(Message)
        .filter(
            Message.user_id == DEMO_USER_ID,
            Message.follow_up_status == "follow_up_needed",
        )
        .all()
    )
    email_due = (
        db.query(EmailDraft)
        .filter(
            EmailDraft.user_id == DEMO_USER_ID,
            EmailDraft.follow_up_status == "follow_up_needed",
        )
        .all()
    )
    items = [
        {
            "kind": "message",
            "id": m.id,
            "company": m.job.company if m.job else None,
            "role": m.job.title if m.job else None,
            "due_date": m.follow_up_due_date,
        }
        for m in msg_due
    ] + [
        {
            "kind": "email",
            "id": e.id,
            "company": e.job.company if e.job else None,
            "role": e.job.title if e.job else None,
            "due_date": e.follow_up_due_date,
        }
        for e in email_due
    ]
    return {"due": len(items), "items": items[:8]}


def _pipeline_summary(db: Session) -> dict:
    """A funnel over local data (messages + emails). Mirrors the /stats funnel
    but spans both outreach workflows. Deterministic counts, no estimates."""
    total_jobs = db.query(Job).count()
    strong_matches = db.query(JobMatch).filter(JobMatch.score >= strategy.STRONG_MIN).count()
    people_met = db.query(Meeting).filter(Meeting.user_id == DEMO_USER_ID).count()

    messages = db.query(Message).filter(Message.user_id == DEMO_USER_ID).all()
    emails = db.query(EmailDraft).filter(EmailDraft.user_id == DEMO_USER_ID).all()

    drafts = len(messages) + len(emails)
    sent = sum(1 for m in messages if m.status == "sent_manually") + sum(
        1 for e in emails if e.status in ("sent_manual", "sent_via_gmail")
    )

    def _outcome(value: str) -> int:
        return sum(1 for m in messages if m.outcome == value) + sum(
            1 for e in emails if e.outcome == value
        )

    return {
        "jobs_found": total_jobs,
        "strong_matches": strong_matches,
        "people_met": people_met,
        "drafts": drafts,
        "sent": sent,
        "replies": _outcome("replied"),
        "interviews": _outcome("interview_received"),
        "funnel": [
            {"label": "Jobs found", "value": total_jobs},
            {"label": "Strong matches", "value": strong_matches},
            {"label": "Drafts", "value": drafts},
            {"label": "Sent", "value": sent},
            {"label": "Replies", "value": _outcome("replied")},
            {"label": "Interviews", "value": _outcome("interview_received")},
        ],
    }


def _setup_steps(
    *,
    has_profile: bool,
    has_goal: bool,
    total_jobs: int,
    has_matches: bool,
    has_contacts: bool,
    best: dict | None,
    pending_review: int,
) -> list[dict]:
    """Ordered, actionable empty-state checklist so the dashboard is never blank.

    Each step is `done` once satisfied; the frontend can show the first unmet
    step prominently and the rest as a checklist.
    """
    steps = [
        {
            "key": "profile",
            "title": "Upload your resume",
            "description": "Add your resume so jobs can be ranked against your real skills.",
            "cta_href": "/profile",
            "cta_label": "Go to Profile",
            "done": has_profile,
        },
        {
            "key": "goal",
            "title": "Set your job-search goal",
            "description": "Tell the copilot the role, location, and outreach goal so drafts are honest and personalized.",
            "cta_href": "/goals",
            "cta_label": "Set a goal",
            "done": has_goal,
        },
        {
            "key": "jobs",
            "title": "Ingest new-grad jobs",
            "description": "Pull the latest new-grad roles so you have something to target.",
            "cta_href": "/jobs",
            "cta_label": "Ingest jobs",
            "done": total_jobs > 0,
        },
        {
            "key": "matches",
            "title": "Rank jobs against your profile",
            "description": "Score every posting so the best target rises to the top.",
            "cta_href": "/matches",
            "cta_label": "Match jobs",
            "done": has_matches,
        },
        {
            "key": "contacts",
            "title": "Add a contact to reach out to",
            "description": "Find people yourself (no scraping) and add them manually for your top company.",
            "cta_href": "/contacts",
            "cta_label": "Add contacts",
            "done": has_contacts,
        },
        {
            "key": "drafts",
            "title": "Draft your first outreach",
            "description": (
                f"Generate permission-based drafts for {best['company']}."
                if best and best.get("company")
                else "Generate permission-based drafts for your best job."
            ),
            "cta_href": f"/jobs/{best['job_id']}" if best else "/matches",
            "cta_label": "Network for this job",
            "done": pending_review > 0,
        },
    ]
    return steps


def build_mission(db: Session) -> dict:
    """Aggregate everything the dashboard needs into one deterministic object."""
    profile = db.query(Profile).filter(Profile.user_id == DEMO_USER_ID).first()
    has_profile = profile is not None
    skills = matcher._profile_skills(profile) if profile else []

    goal = (
        db.query(Goal)
        .filter(Goal.user_id == DEMO_USER_ID)
        .order_by(Goal.id.desc())
        .first()
    )
    goal_dict = _goal_dict(goal)

    best, best_job = _best_match(db)
    total_jobs = db.query(Job).count()
    total_matches = db.query(JobMatch).count()
    has_contacts = (
        db.query(Contact).filter(Contact.user_id == DEMO_USER_ID).count() > 0
    )

    # Build the contact plan + strategy for the best job (reuses strategy.py).
    contact_plan = None
    label = None
    if best and best_job is not None:
        label = best.get("recommendation") or strategy.label_for_score(
            best["match_score"]
        )
        strat = strategy.outreach_strategy(
            best["match_score"], best_job, len(best.get("matched_skills") or [])
        )
        contact_plan = {
            "who_first": strat["who_first"],
            "contact_count": strat["contact_count"],
            "tone": strat["tone"],
            "ask_type": strat["ask_type"],
            "sequence": strat["sequence"],
            "recommended_contact_types": _recommended_contact_types(
                label, goal, best.get("company"), goal_dict
            ),
        }

    drafts = _drafts_summary(db)
    follow_ups = _follow_ups_summary(db)
    pipeline = _pipeline_summary(db)
    momentum_summary = momentum.summary(db)

    setup_steps = _setup_steps(
        has_profile=has_profile,
        has_goal=goal is not None,
        total_jobs=total_jobs,
        has_matches=total_matches > 0,
        has_contacts=has_contacts,
        best=best,
        pending_review=drafts["pending_review"],
    )
    # The mission is "ready" once there's a best job to act on. Otherwise the
    # first unmet setup step is the user's real next action.
    ready = best is not None
    next_setup = next((s for s in setup_steps if not s["done"]), None)

    if ready:
        headline = f"Network for {best['company']}"
        focus = best.get("next_best_action")
    elif next_setup is not None:
        headline = next_setup["title"]
        focus = next_setup["description"]
    else:
        headline = "You're all set for today"
        focus = "Review your drafts and update outcomes to keep momentum going."

    return {
        "ready": ready,
        "headline": headline,
        "focus": focus,
        "profile": {
            "exists": has_profile,
            "skills_count": len(skills),
            "skills": skills[:12],
        },
        "goal": goal_dict,
        "best_job": best,  # full ranked-match shape (or None)
        "match_label": label,
        "match_explanation": best.get("explanation") if best else None,
        "recommended_next_action": best.get("next_best_action") if best else None,
        "contact_plan": contact_plan,
        "drafts": drafts,
        "follow_ups": follow_ups,
        "pipeline": pipeline,
        "momentum": momentum_summary,
        "setup_steps": setup_steps,
        "next_setup_step": next_setup,
    }
