"""Append-only audit logging for security-relevant events.

Rules:
- NEVER log resume text, message bodies, passwords, session tokens, API keys,
  or payment details. `note` is for short context like an email address or a
  plan name — nothing else.
- Audit must never break the request it's attached to: failures are swallowed
  (and reported to the server log only).
"""

import logging

from sqlalchemy.orm import Session

from ..models import AuditEvent

logger = logging.getLogger("app.audit")


def log(
    db: Session,
    event: str,
    *,
    user_id: str | None = None,
    ip: str | None = None,
    note: str | None = None,
) -> None:
    """Record an audit event; swallow any failure so requests never break."""
    try:
        db.add(AuditEvent(user_id=user_id, event=event, ip=ip, note=note))
        db.commit()
    except Exception:  # pragma: no cover - defensive; audit must not raise
        logger.exception("Failed to write audit event %r", event)
        try:
            db.rollback()
        except Exception:
            pass
