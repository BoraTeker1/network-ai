"""Event recommendation endpoint.

GET /events/recommendations — upcoming networking events for the user's
strongest job match of the day. Read-only: reuses the matcher + goal, calls
configured provider APIs (no scraping), and always returns manual search links
as a safe fallback. Never invents events, never registers the user, never
emails anyone.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_user
from ..models import User
from ..services import events

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/recommendations")
def event_recommendations(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    location: str | None = Query(None, description="Override city/area to search near."),
    radius_miles: int = Query(50, ge=1, le=500),
    days_ahead: int = Query(30, ge=1, le=180),
    include_online: bool = Query(True),
    max_results: int = Query(12, ge=1, le=50),
):
    """Networking events for the strongest match + always-on manual search links."""
    resp = events.recommend_events(
        db,
        user.id,
        location=location,
        radius_miles=radius_miles,
        days_ahead=days_ahead,
        include_online=include_online,
        max_results=max_results,
    )
    return events.response_to_dict(resp)
