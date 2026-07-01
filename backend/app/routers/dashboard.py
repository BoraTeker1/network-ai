"""Dashboard aggregation endpoint.

Powers the "Today's Networking Mission" command center. Read-only: it aggregates
existing local data (profile, goal, best match, drafts, follow-ups, pipeline,
momentum) into one deterministic JSON object. No LLM, no external calls, no
scraping, no auto-send.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_user
from ..models import User
from ..services import mission

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/mission")
def todays_mission(db: Session = Depends(get_db), user: User = Depends(require_user)):
    """Everything the dashboard needs to answer 'what should I do today?'."""
    return mission.build_mission(db, user.id)
