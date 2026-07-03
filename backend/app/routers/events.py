"""Product-event ingestion + validation-sprint scoreboard.

POST /events lets the frontend report UI-side funnel events (e.g. the fake-door
"pro_button_clicked"). Server-side events (signup, drafts, saves…) are recorded
directly in their own routers — the client can't fake those. GET /events/summary
is the founder's (admin-only) scoreboard: event counts plus label-feedback tallies.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import optional_user, require_admin
from ..models import (
    LABEL_FEEDBACK_VERDICTS,
    PRODUCT_EVENTS,
    LabelFeedback,
    ProductEvent,
    User,
)
from ..schemas import EventIn
from ..services import events
from ..services.rate_limit import rate_limit

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", status_code=201)
def record_event(
    payload: EventIn,
    db: Session = Depends(get_db),
    user: User | None = Depends(optional_user),
    _rl: None = Depends(rate_limit("events")),
):
    """Record one allowlisted UI event, user-scoped when a session exists."""
    if payload.event not in PRODUCT_EVENTS:
        raise HTTPException(
            status_code=422,
            detail=f"event must be one of: {', '.join(PRODUCT_EVENTS)}",
        )
    events.track(db, payload.event, user_id=user.id if user else None,
                 note=payload.note)
    return {"status": "recorded", "event": payload.event}


@router.get("/summary")
def summary(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Admin scoreboard: per-event totals + unique users, and label-feedback
    verdict counts with the most recent 'wrong' reasons."""
    rows = (
        db.query(
            ProductEvent.event,
            func.count(ProductEvent.id),
            func.count(func.distinct(ProductEvent.user_id)),
        )
        .group_by(ProductEvent.event)
        .all()
    )
    counts = {e: {"total": 0, "unique_users": 0} for e in PRODUCT_EVENTS}
    for event, total, uniq in rows:
        counts[event] = {"total": total, "unique_users": uniq}

    verdicts = dict(
        db.query(LabelFeedback.verdict, func.count(LabelFeedback.id))
        .group_by(LabelFeedback.verdict)
        .all()
    )
    recent_wrong = (
        db.query(LabelFeedback)
        .filter(LabelFeedback.verdict == "wrong")
        .order_by(LabelFeedback.created_at.desc())
        .limit(20)
        .all()
    )
    return {
        "events": counts,
        "label_feedback": {
            **{v: verdicts.get(v, 0) for v in LABEL_FEEDBACK_VERDICTS},
            "recent_wrong": [
                {
                    "opportunity_id": f.opportunity_id,
                    "label": f.label,
                    "reason": f.reason,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in recent_wrong
            ],
        },
    }
