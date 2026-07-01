"""Plan limits + feature gates.

Free users get real, reasonable daily limits; pro/admin are unlimited. Limits
are enforced SERVER-SIDE via the `enforce_limit(action)` dependency — UI hints
alone are never trusted. Limits are env-overridable per action:

    PLAN_LIMIT_FREE_OUTREACH_DRAFT=5   (etc. — read at request time)

Design notes (deliberate, documented):
- Usage is recorded at admission, so a request that later fails still counts
  toward the day's quota. Simple and abuse-safe for a beta.
- `pipeline_save` is a TOTAL cap counted from the user's stored Message rows,
  not a daily rate.
- 402 Payment Required with a structured detail so the frontend can show an
  upgrade callout instead of a generic error.
"""

import os
from datetime import datetime, time

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_user
from ..models import Message, UsageEvent, User

# Daily free-tier defaults (None = unlimited). Keep generous enough for a real
# job hunt, tight enough that heavy use has a reason to pay.
FREE_DAILY_LIMITS: dict[str, int] = {
    "outreach_draft": 5,
    "next_move": 5,
    "email_draft": 10,
    "message_generate": 10,
    "resume_upload": 10,
}
# Total (not daily) free-tier caps.
FREE_TOTAL_LIMITS: dict[str, int] = {
    "pipeline_save": 15,
}

UNLIMITED_PLANS = ("pro", "admin")


def get_limit(plan: str, action: str) -> int | None:
    """The applicable limit for a plan+action, or None for unlimited.
    Env override: PLAN_LIMIT_FREE_<ACTION> (read per call so tests can patch)."""
    if plan in UNLIMITED_PLANS:
        return None
    default = FREE_DAILY_LIMITS.get(action, FREE_TOTAL_LIMITS.get(action))
    if default is None:
        return None
    raw = os.getenv(f"PLAN_LIMIT_FREE_{action.upper()}", "").strip()
    if raw:
        try:
            return max(0, int(raw))
        except ValueError:
            pass
    return default


def usage_today(db: Session, user_id: str, action: str) -> int:
    start = datetime.combine(datetime.utcnow().date(), time.min)
    return (
        db.query(UsageEvent)
        .filter(
            UsageEvent.user_id == user_id,
            UsageEvent.action == action,
            UsageEvent.created_at >= start,
        )
        .count()
    )


def usage_total(db: Session, user_id: str, action: str) -> int:
    if action == "pipeline_save":
        # The real total that matters: stored pipeline items.
        return db.query(Message).filter(Message.user_id == user_id).count()
    return (
        db.query(UsageEvent)
        .filter(UsageEvent.user_id == user_id, UsageEvent.action == action)
        .count()
    )


def record(db: Session, user_id: str, action: str) -> None:
    db.add(UsageEvent(user_id=user_id, action=action))
    db.commit()


def _current_usage(db: Session, user_id: str, action: str) -> int:
    if action in FREE_TOTAL_LIMITS:
        return usage_total(db, user_id, action)
    return usage_today(db, user_id, action)


def enforce_limit(action: str):
    """Dependency factory: authenticates, checks the plan limit for `action`,
    records the usage event, and returns the User. Raises 402 when over limit."""

    def dep(
        user: User = Depends(require_user), db: Session = Depends(get_db)
    ) -> User:
        limit = get_limit(user.plan, action)
        if limit is not None and _current_usage(db, user.id, action) >= limit:
            period = "total" if action in FREE_TOTAL_LIMITS else "today"
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "plan_limit",
                    "action": action,
                    "limit": limit,
                    "period": period,
                    "message": (
                        f"Free plan limit reached ({limit} {action.replace('_', ' ')}"
                        f" {period}). Upgrade to Pro for unlimited use."
                    ),
                    "upgrade_url": "/pricing",
                },
            )
        record(db, user.id, action)
        return user

    return dep


def plan_overview(db: Session, user: User) -> dict:
    """Current plan + limits + usage, for GET /billing/plan."""
    actions = list(FREE_DAILY_LIMITS) + list(FREE_TOTAL_LIMITS)
    return {
        "plan": user.plan,
        "limits": {a: get_limit(user.plan, a) for a in actions},
        "usage": {a: _current_usage(db, user.id, a) for a in actions},
    }
