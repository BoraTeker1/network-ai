"""Momentum — tasteful gamification for Vibe Mode.

Rewards *quality* networking progress (milestones the user manually confirms),
never volume, bulk, or anything automated. No scraping, no auto-send, no
auto-detection of replies — the user reports every outcome by hand.

Each event is awarded at most once per (subject_type, subject_id, event_type),
so clicking the same outcome twice never double-counts.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..models import DEMO_USER_ID, MomentumEvent

# Points per event type. Kept deliberately weighted toward real outcomes
# (replies, referrals, interviews) over mechanical workflow steps.
POINTS = {
    "draft_approved": 5,
    "copied": 5,
    "sent_manual": 10,
    "follow_up_completed": 10,
    "reply_received": 25,
    "referral_received": 50,
    "interview_received": 100,
    "tracked_no_points": 0,
}

# Celebration intensity the frontend uses to size the toast / chime.
CELEBRATION = {
    "interview_received": "big",
    "referral_received": "big",
    "reply_received": "medium",
    "sent_manual": "small",
    "follow_up_completed": "small",
    "draft_approved": "small",
    "copied": "small",
    "tracked_no_points": "none",
}

# Professional, non-arcade labels.
LABELS = {
    "draft_approved": "Draft approved",
    "copied": "Ready to send",
    "sent_manual": "Sent manually",
    "follow_up_completed": "Follow-up completed",
    "reply_received": "Reply received",
    "referral_received": "Referral received",
    "interview_received": "Interview received",
    "tracked_no_points": "Outcome logged",
}

# Map a reported outcome -> the momentum event it earns. Neutral outcomes are
# tracked with zero points (no negative shame).
OUTCOME_EVENT = {
    "replied": "reply_received",
    "referral_received": "referral_received",
    "interview_received": "interview_received",
    "connected": "tracked_no_points",
    "ignored": "tracked_no_points",
    "rejected": "tracked_no_points",
}

# Map a follow-up status -> momentum event (only "followed_up" earns points).
FOLLOW_UP_EVENT = {"followed_up": "follow_up_completed"}

# Map a workflow status -> momentum event (for approve/copy/manual-send).
STATUS_EVENT = {
    "approved": "draft_approved",
    "copied": "copied",
    "sent_manually": "sent_manual",   # messages workflow
    "sent_manual": "sent_manual",     # emails workflow
}


def _serialize_award(ev: MomentumEvent) -> dict:
    points = ev.points or 0
    if points > 0:
        message = f"Momentum +{points} · {LABELS.get(ev.event_type, ev.event_type)}"
    else:
        message = f"Logged · {LABELS.get(ev.event_type, ev.event_type)} — no points, no pressure"
    return {
        "event_type": ev.event_type,
        "points": points,
        "label": LABELS.get(ev.event_type, ev.event_type),
        "celebration": CELEBRATION.get(ev.event_type, "small"),
        "message": message,
    }


def award(db: Session, subject_type: str, subject_id: int | None, event_type: str | None):
    """Award a momentum event once. Returns the award dict, or None if the event
    type is unknown or this exact event was already awarded (no double-count)."""
    if not event_type or event_type not in POINTS:
        return None

    existing = (
        db.query(MomentumEvent)
        .filter(
            MomentumEvent.subject_type == subject_type,
            MomentumEvent.subject_id == subject_id,
            MomentumEvent.event_type == event_type,
        )
        .first()
    )
    if existing is not None:
        return None  # already counted — clicking again never re-awards

    ev = MomentumEvent(
        user_id=DEMO_USER_ID,
        subject_type=subject_type,
        subject_id=subject_id,
        event_type=event_type,
        points=POINTS[event_type],
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return _serialize_award(ev)


def summary(db: Session) -> dict:
    """Dashboard summary: points today, total, streak, and recent wins."""
    events = (
        db.query(MomentumEvent)
        .filter(MomentumEvent.user_id == DEMO_USER_ID)
        .order_by(MomentumEvent.id.desc())
        .all()
    )

    total_points = sum(e.points or 0 for e in events)
    today = datetime.utcnow().date()
    points_today = sum(
        (e.points or 0) for e in events if e.created_at and e.created_at.date() == today
    )

    # Streak: consecutive days (ending today or yesterday) with any activity.
    active_days = {e.created_at.date() for e in events if e.created_at}
    streak = 0
    if today in active_days:
        cursor = today
    elif (today - timedelta(days=1)) in active_days:
        cursor = today - timedelta(days=1)
    else:
        cursor = None
    while cursor in active_days:
        streak += 1
        cursor = cursor - timedelta(days=1)

    recent_wins = [
        {
            "event_type": e.event_type,
            "label": LABELS.get(e.event_type, e.event_type),
            "points": e.points or 0,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
        if (e.points or 0) > 0
    ][:6]

    return {
        "points_today": points_today,
        "total_points": total_points,
        "streak": streak,
        "recent_wins": recent_wins,
    }
