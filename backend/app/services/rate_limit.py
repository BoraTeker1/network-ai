"""In-process fixed-window rate limiting.

Keyed by authenticated user id when available, else client IP. Limits are
env-configurable per action (RATE_LIMIT_<ACTION>, requests/minute, read at
request time) and RATE_LIMIT_DISABLED=1 turns everything off (tests, dev).

HONEST LIMITATION: the counters live in this process's memory. They do NOT
survive restarts and are NOT shared across uvicorn workers — run a single
worker in the beta, move to Redis before scaling out. Documented in
PRODUCTION_CHECKLIST.md.
"""

import os
import threading
import time

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import client_ip, optional_user
from ..models import User
from . import audit

# Requests/minute defaults per action. Auth endpoints are per-IP (anonymous).
DEFAULT_LIMITS: dict[str, int] = {
    "login": 10,
    "signup": 5,
    "outreach_draft": 10,
    "next_move": 10,
    "resume_upload": 6,
    "opps_refresh": 2,
    "email_draft": 10,
    "message_generate": 10,
}

# (action, key) -> [window_minute, count, audit_logged_this_window]
_buckets: dict[tuple[str, str], list] = {}
_lock = threading.Lock()
_MAX_BUCKETS = 10_000


def reset() -> None:
    """Clear all counters (tests)."""
    with _lock:
        _buckets.clear()


def _disabled() -> bool:
    return os.getenv("RATE_LIMIT_DISABLED", "").strip().lower() in ("1", "true", "yes")


def _limit_for(action: str) -> int:
    raw = os.getenv(f"RATE_LIMIT_{action.upper()}", "").strip()
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return DEFAULT_LIMITS.get(action, 30)


def rate_limit(action: str, by: str = "auto"):
    """Dependency factory. Order it BEFORE plan gates in endpoint signatures so
    cheap rejection happens first. Returns None — it only gates.

    by="auto": key by user id when authenticated, else client IP.
    by="ip":   always key by client IP — required for auth endpoints, where a
               freshly-set session cookie must not grant a fresh bucket.
    """

    def dep(
        request: Request,
        db: Session = Depends(get_db),
        user: User | None = Depends(optional_user),
    ) -> None:
        if _disabled():
            return

        if by == "ip" or user is None:
            key = client_ip(request)
        else:
            key = user.id
        limit = _limit_for(action)
        window = int(time.time() // 60)

        with _lock:
            if len(_buckets) > _MAX_BUCKETS:  # crude pruning; windows are short
                _buckets.clear()
            bucket = _buckets.get((action, key))
            if bucket is None or bucket[0] != window:
                _buckets[(action, key)] = [window, 1, False]
                return
            bucket[1] += 1
            over = bucket[1] > limit
            should_audit = over and not bucket[2]
            if should_audit:
                bucket[2] = True  # one audit row per window per key, not per hit

        if over:
            if should_audit:
                audit.log(
                    db, "rate_limited",
                    user_id=user.id if user else None,
                    ip=client_ip(request),
                    note=f"{action} > {limit}/min",
                )
            retry_after = 60 - int(time.time() % 60)
            raise HTTPException(
                status_code=429,
                detail="Too many requests — slow down and try again shortly.",
                headers={"Retry-After": str(max(1, retry_after))},
            )

    return dep
