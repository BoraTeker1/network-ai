"""Job endpoints (skeleton).

Ingestion/dedup/ranking logic lives in services/ and is wired in later.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/")
def list_jobs(db: Session = Depends(get_db)):
    """List ingested jobs. Placeholder until ingestion is implemented."""
    count = db.query(Job).count()
    return {"jobs": count}
