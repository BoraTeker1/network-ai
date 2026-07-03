"""First-party product-event tracking (validation sprint).

Mirrors services/audit.py: tracking must NEVER break the request it rides on,
and never stores content — only an allowlisted event name, an optional user id,
and a short non-sensitive note. No third-party analytics provider.
"""

import logging

from sqlalchemy.orm import Session

from ..models import PRODUCT_EVENTS, ProductEvent

logger = logging.getLogger("app.events")


def track(
    db: Session,
    event: str,
    *,
    user_id: str | None = None,
    note: str | None = None,
) -> None:
    """Record a product event; unknown names and failures are swallowed."""
    if event not in PRODUCT_EVENTS:
        logger.warning("Dropped unknown product event %r", event)
        return
    try:
        db.add(ProductEvent(user_id=user_id, event=event, note=(note or None)))
        db.commit()
    except Exception:  # pragma: no cover - defensive; tracking must not raise
        logger.exception("Failed to write product event %r", event)
        try:
            db.rollback()
        except Exception:
            pass
