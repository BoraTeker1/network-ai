"""Dashboard insights endpoints.

Read-only aggregates that power the homepage dashboard and the pipeline /
outcome views. No LLM, no external calls — just counts over local data.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import OUTCOMES, Job, JobMatch, Message
from ..services import matcher
from .messages import VALID_STATUSES, _demo_skills, _serialize

router = APIRouter(tags=["insights"])


@router.get("/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    """Everything the homepage dashboard needs in a single call."""
    skills = _demo_skills(db)

    total_jobs = db.query(Job).count()
    total_matches = db.query(JobMatch).count()
    # Strong targets are the high-confidence matches (score >= 75) the funnel
    # and dashboard headline both key off of.
    strong_targets = db.query(JobMatch).filter(JobMatch.score >= 75).count()
    messages = db.query(Message).order_by(Message.id.desc()).all()

    status_counts = {status: 0 for status in VALID_STATUSES}
    outcome_counts = {outcome: 0 for outcome in OUTCOMES}
    follow_ups_due = 0
    for msg in messages:
        if msg.status in status_counts:
            status_counts[msg.status] += 1
        if msg.outcome in outcome_counts:
            outcome_counts[msg.outcome] += 1
        if msg.follow_up_status == "follow_up_needed":
            follow_ups_due += 1

    # Investor-friendly funnel — every number comes straight from local data.
    sent = status_counts.get("sent_manually", 0)
    funnel = [
        {"label": "Jobs found", "value": total_jobs},
        {"label": "Strong matches", "value": strong_targets},
        {"label": "Drafts", "value": len(messages)},
        {"label": "Sent", "value": sent},
        {"label": "Replies", "value": outcome_counts.get("replied", 0)},
        {"label": "Interviews", "value": outcome_counts.get("interview_received", 0)},
    ]

    top_matches = matcher.ranked_matches(db, limit=5)
    recent_messages = [_serialize(msg, skills) for msg in messages[:5]]

    return {
        "total_jobs": total_jobs,
        "total_matches": total_matches,
        "strong_targets": strong_targets,
        "total_messages": len(messages),
        "status_counts": status_counts,
        "outcome_counts": outcome_counts,
        "follow_ups_due": follow_ups_due,
        "funnel": funnel,
        "top_matches": top_matches,
        "recent_messages": recent_messages,
    }


@router.get("/outcomes")
def list_outcomes(db: Session = Depends(get_db)):
    """Supported outcome vocabulary, per-outcome counts, and reported messages."""
    skills = _demo_skills(db)
    msgs = (
        db.query(Message)
        .filter(Message.outcome.isnot(None))
        .order_by(Message.id.desc())
        .all()
    )
    counts = {outcome: 0 for outcome in OUTCOMES}
    for msg in msgs:
        if msg.outcome in counts:
            counts[msg.outcome] += 1
    return {
        "supported": list(OUTCOMES),
        "counts": counts,
        "messages": [_serialize(msg, skills) for msg in msgs],
    }
