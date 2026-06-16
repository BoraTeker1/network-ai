"""Momentum endpoints (Vibe Mode gamification).

Read-only summary for the dashboard. Points are *awarded* inside the existing
message/email action endpoints when the user confirms real progress — there is
no endpoint to mint points directly, and nothing is ever automated.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..services import momentum

router = APIRouter(prefix="/momentum", tags=["momentum"])


@router.get("/summary")
def momentum_summary(db: Session = Depends(get_db)):
    """Points earned today, total points, current streak, and recent wins."""
    return momentum.summary(db)
