"""Message endpoints (skeleton).

Drafting lives in services/message_generator.py. Approval workflow
(approve/reject/edit/copy/mark-sent) is wired in later via outreach_events.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Message

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("/")
def list_messages(db: Session = Depends(get_db)):
    """List message drafts. Placeholder until generation is implemented."""
    count = db.query(Message).count()
    return {"messages": count}
