"""Meetings — log people you actually MET (presence tracking).

The core signal of the "presence" wedge: turn showing up into tracked
relationships. Everything is logged MANUALLY by the user — never scraped, never
auto-detected. Logging a person earns Momentum; deleting a meeting removes its
Momentum so points and the presence funnel stay honest.

Static-free router: only /{meeting_id} is dynamic, so no ordering hazards.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CONTACT_TYPES, DEMO_USER_ID, Job, Meeting, MomentumEvent
from ..schemas import MeetingIn, MeetingPatch
from ..services import momentum

router = APIRouter(prefix="/meetings", tags=["meetings"])


def _serialize(m: Meeting) -> dict:
    return {
        "id": m.id,
        "job_id": m.job_id,
        "name": m.name,
        "title": m.title,
        "company": m.company,
        "where_met": m.where_met,
        "met_on": m.met_on,
        "contact_type": m.contact_type,
        "linkedin_url": m.linkedin_url,
        "note": m.note,
        "followed_up": bool(m.followed_up),
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


@router.post("")
def log_meeting(payload: MeetingIn, db: Session = Depends(get_db)):
    """Log a person you met. Awards Momentum ('Person met') exactly once."""
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name must not be empty")
    if payload.contact_type and payload.contact_type not in CONTACT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"contact_type must be one of: {', '.join(CONTACT_TYPES)}",
        )

    # Inherit the company from the linked opportunity when not provided.
    company = (payload.company or "").strip() or None
    if payload.job_id and not company:
        job = db.query(Job).filter(Job.id == payload.job_id).first()
        company = job.company if job else None

    meeting = Meeting(
        user_id=DEMO_USER_ID,
        job_id=payload.job_id,
        name=name,
        title=(payload.title or "").strip() or None,
        company=company,
        where_met=(payload.where_met or "").strip() or None,
        met_on=(payload.met_on or "").strip() or date.today().isoformat(),
        contact_type=payload.contact_type,
        linkedin_url=(payload.linkedin_url or "").strip() or None,
        note=(payload.note or "").strip() or None,
        followed_up=False,
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    award = momentum.award(db, "meeting", meeting.id, "person_met")
    result = _serialize(meeting)
    result["momentum"] = award
    return result


@router.get("")
def list_meetings(job_id: int | None = None, db: Session = Depends(get_db)):
    """All logged meetings (newest first), optionally filtered to one opportunity."""
    q = db.query(Meeting).filter(Meeting.user_id == DEMO_USER_ID)
    if job_id is not None:
        q = q.filter(Meeting.job_id == job_id)
    return [_serialize(m) for m in q.order_by(Meeting.id.desc()).all()]


@router.patch("/{meeting_id}")
def patch_meeting(meeting_id: int, payload: MeetingPatch, db: Session = Depends(get_db)):
    """Update a meeting (mark followed-up, edit the note)."""
    m = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if m is None:
        raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")
    if payload.followed_up is not None:
        m.followed_up = payload.followed_up
    if payload.note is not None:
        m.note = payload.note.strip() or None
    db.commit()
    db.refresh(m)
    return _serialize(m)


@router.delete("/{meeting_id}")
def delete_meeting(meeting_id: int, db: Session = Depends(get_db)):
    """Delete a meeting and remove its Momentum so points/funnel stay honest."""
    m = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if m is None:
        raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")
    db.query(MomentumEvent).filter(
        MomentumEvent.subject_type == "meeting",
        MomentumEvent.subject_id == meeting_id,
    ).delete()
    db.delete(m)
    db.commit()
    return {"status": "deleted", "id": meeting_id}
