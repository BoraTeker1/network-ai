"""Profile endpoints (skeleton).

Real resume parsing lives in services/resume_parser.py and is wired in later.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Profile

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/")
def list_profiles(db: Session = Depends(get_db)):
    """List stored profiles. Placeholder until create/parse is implemented."""
    count = db.query(Profile).count()
    return {"profiles": count}
