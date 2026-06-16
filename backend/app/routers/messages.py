"""Message endpoints.

Draft generation + the Cursor-style approval workflow: AI proposes drafts,
the user reviews / edits / approves / rejects / copies / marks-sent manually.
Nothing is ever auto-sent.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    DEMO_USER_ID,
    FOLLOW_UP_STATUSES,
    OUTCOMES,
    Job,
    Message,
    OutreachEvent,
    Profile,
)
from ..schemas import FollowUpIn, MessageGenerateIn, MessagePatch, OutcomeIn
from ..services import message_generator, momentum
from ..services.matcher import get_demo_profile

router = APIRouter(prefix="/messages", tags=["messages"])

# Allowed message statuses for the approval workflow.
VALID_STATUSES = {"draft", "approved", "rejected", "copied", "sent_manually"}


def _demo_skills(db: Session) -> list[str]:
    """Profile skills for the demo user (used by the quality checklist)."""
    profile = get_demo_profile(db)
    if profile is None or not profile.skills:
        return []
    try:
        return json.loads(profile.skills)
    except (ValueError, TypeError):
        return []


def _serialize(msg: Message, profile_skills: list[str] | None = None) -> dict:
    """Convert a Message row into clean, frontend-friendly JSON.

    Includes a deterministic quality checklist so the UI can show the user
    exactly why a draft is (or isn't) ready to send.
    """
    job = msg.job
    text = msg.content or ""
    checklist = message_generator.quality_checklist(
        text=text,
        message_type=msg.message_type,
        company=job.company if job else None,
        role=job.title if job else None,
        profile_skills=profile_skills or [],
    )
    return {
        "id": msg.id,
        "job_id": msg.job_id,
        "company": job.company if job else None,
        "title": job.title if job else None,
        "message_type": msg.message_type,
        "tone": message_generator.tone_for(msg.message_type),
        "draft_text": msg.content,
        "status": msg.status,
        "outcome": msg.outcome,
        "follow_up_status": msg.follow_up_status,
        "follow_up_due_date": msg.follow_up_due_date,
        "char_count": len(text),
        "checklist": checklist,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
        "updated_at": msg.updated_at.isoformat() if msg.updated_at else None,
    }


def _get_or_404(db: Session, message_id: int) -> Message:
    msg = db.query(Message).filter(Message.id == message_id).first()
    if msg is None:
        raise HTTPException(status_code=404, detail=f"Message {message_id} not found")
    return msg


def _log_event(db: Session, message_id: int, event_type: str) -> None:
    db.add(OutreachEvent(message_id=message_id, event_type=event_type))


def _set_status(db: Session, message_id: int, status: str, event_type: str) -> dict:
    msg = _get_or_404(db, message_id)
    msg.status = status
    _log_event(db, message_id, event_type)
    db.commit()
    db.refresh(msg)
    # Award Momentum for real progress (approve/copy/manual-send). Reject earns
    # nothing — STATUS_EVENT has no mapping for it, so award() returns None.
    award = momentum.award(db, "message", message_id, momentum.STATUS_EVENT.get(status))
    res = _serialize(msg, _demo_skills(db))
    res["momentum"] = award
    return res


# ----- Generation -----

@router.post("/generate")
def generate_messages(payload: MessageGenerateIn, db: Session = Depends(get_db)):
    """Generate and store the 4 draft variants for a job (status='draft')."""
    profile: Profile | None = get_demo_profile(db)
    if profile is None:
        raise HTTPException(
            status_code=400, detail="No profile saved yet — paste a resume first."
        )

    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {payload.job_id} not found")

    skills = json.loads(profile.skills) if profile.skills else []
    drafts = message_generator.build_drafts(
        profile_skills=skills,
        company=job.company or "the company",
        role=job.title or "this role",
        contact_name=payload.contact_name,
        contact_title=payload.contact_title,
    )

    created: list[Message] = []
    for message_type, text in drafts:
        msg = Message(
            user_id=DEMO_USER_ID,
            job_id=job.id,
            message_type=message_type,
            content=text,
            status="draft",
        )
        db.add(msg)
        created.append(msg)

    db.commit()
    for msg in created:
        db.refresh(msg)
    return [_serialize(msg, skills) for msg in created]


# ----- Reads -----

@router.get("")
def list_messages(db: Session = Depends(get_db)):
    """List all message drafts (newest first)."""
    skills = _demo_skills(db)
    msgs = db.query(Message).order_by(Message.id.desc()).all()
    return [_serialize(msg, skills) for msg in msgs]


@router.get("/{message_id}")
def get_message(message_id: int, db: Session = Depends(get_db)):
    """Return a single message by id."""
    return _serialize(_get_or_404(db, message_id), _demo_skills(db))


# ----- Edit -----

@router.patch("/{message_id}")
def patch_message(message_id: int, payload: MessagePatch, db: Session = Depends(get_db)):
    """Edit the draft text of a message."""
    msg = _get_or_404(db, message_id)
    msg.content = payload.draft_text
    _log_event(db, message_id, "edited")
    db.commit()
    db.refresh(msg)
    return _serialize(msg, _demo_skills(db))


# ----- Approval workflow -----

@router.post("/{message_id}/approve")
def approve_message(message_id: int, db: Session = Depends(get_db)):
    return _set_status(db, message_id, "approved", "approved")


@router.post("/{message_id}/reject")
def reject_message(message_id: int, db: Session = Depends(get_db)):
    return _set_status(db, message_id, "rejected", "rejected")


@router.post("/{message_id}/mark-copied")
def mark_copied(message_id: int, db: Session = Depends(get_db)):
    return _set_status(db, message_id, "copied", "copied")


@router.post("/{message_id}/mark-sent-manually")
def mark_sent_manually(message_id: int, db: Session = Depends(get_db)):
    return _set_status(db, message_id, "sent_manually", "marked_sent")


# ----- Outcome tracking -----

@router.post("/{message_id}/outcome")
def set_outcome(message_id: int, payload: OutcomeIn, db: Session = Depends(get_db)):
    """Record the real-world result of a (manually sent) message.

    This is the CRM signal — it never sends anything, it just logs what
    happened after the user reached out on their own.
    """
    if payload.outcome not in OUTCOMES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported outcome. Must be one of: {', '.join(OUTCOMES)}",
        )
    msg = _get_or_404(db, message_id)
    msg.outcome = payload.outcome
    db.add(
        OutreachEvent(
            message_id=message_id,
            event_type=f"outcome:{payload.outcome}",
            note=payload.note,
        )
    )
    db.commit()
    db.refresh(msg)
    award = momentum.award(
        db, "message", message_id, momentum.OUTCOME_EVENT.get(payload.outcome)
    )
    res = _serialize(msg, _demo_skills(db))
    res["momentum"] = award
    return res


# ----- Follow-up tracking -----

@router.post("/{message_id}/follow-up")
def set_follow_up(message_id: int, payload: FollowUpIn, db: Session = Depends(get_db)):
    """Set/clear the follow-up state for a message (CRM nudge, never sends).

    status "none" clears follow-up tracking. A due date is optional and stored
    as a plain ISO date string.
    """
    if payload.status not in FOLLOW_UP_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported status. Must be one of: {', '.join(FOLLOW_UP_STATUSES)}",
        )
    msg = _get_or_404(db, message_id)
    if payload.status == "none":
        msg.follow_up_status = None
        msg.follow_up_due_date = None
    else:
        msg.follow_up_status = payload.status
        msg.follow_up_due_date = payload.due_date
    _log_event(db, message_id, f"follow_up:{payload.status}")
    db.commit()
    db.refresh(msg)
    award = momentum.award(
        db, "message", message_id, momentum.FOLLOW_UP_EVENT.get(payload.status)
    )
    res = _serialize(msg, _demo_skills(db))
    res["momentum"] = award
    return res
