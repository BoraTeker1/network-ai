"""Message endpoints.

Draft generation + the Cursor-style approval workflow: AI proposes drafts,
the user reviews / edits / approves / rejects / copies / marks-sent manually.
Nothing is ever auto-sent.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_user
from ..models import (
    FOLLOW_UP_STATUSES,
    OUTCOMES,
    Job,
    Message,
    OutreachEvent,
    Profile,
    User,
)
from ..schemas import FollowUpIn, MessageGenerateIn, MessagePatch, OutcomeIn
from ..services import message_generator, momentum, plans
from ..services.rate_limit import rate_limit
from ..services.matcher import get_profile

router = APIRouter(prefix="/messages", tags=["messages"])

# Allowed message statuses for the approval workflow.
VALID_STATUSES = {"draft", "approved", "rejected", "copied", "sent_manually"}


def _user_skills(db: Session, user_id: str) -> list[str]:
    """Profile skills for the user (used by the quality checklist)."""
    profile = get_profile(db, user_id)
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
    # Prefer the outreach-copilot context stored on the message itself; fall back
    # to the linked legacy Job (older US-flow drafts have no stored company/title).
    company = msg.company or (job.company if job else None)
    role = msg.title or (job.title if job else None)
    checklist = message_generator.quality_checklist(
        text=text,
        message_type=msg.message_type,
        company=company,
        role=role,
        profile_skills=profile_skills or [],
    )
    return {
        "id": msg.id,
        "job_id": msg.job_id,
        "opportunity_id": msg.opportunity_id,
        "company": company,
        "title": role,
        "subject": msg.subject,
        "channel": msg.channel,
        "language": msg.language,
        "job_url": msg.job_url,
        "contact_name": msg.contact_name,
        "contact_title": msg.contact_title,
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


def _get_or_404(db: Session, message_id: int, user_id: str) -> Message:
    msg = (
        db.query(Message)
        .filter(Message.id == message_id, Message.user_id == user_id)
        .first()
    )
    if msg is None:
        raise HTTPException(status_code=404, detail=f"Message {message_id} not found")
    return msg


def _log_event(db: Session, message_id: int, event_type: str) -> None:
    db.add(OutreachEvent(message_id=message_id, event_type=event_type))


def _set_status(db: Session, message_id: int, status: str, event_type: str,
                user_id: str) -> dict:
    msg = _get_or_404(db, message_id, user_id)
    msg.status = status
    _log_event(db, message_id, event_type)
    db.commit()
    db.refresh(msg)
    # Award Momentum for real progress (approve/copy/manual-send). Reject earns
    # nothing — STATUS_EVENT has no mapping for it, so award() returns None.
    award = momentum.award(db, user_id, "message", message_id, momentum.STATUS_EVENT.get(status))
    res = _serialize(msg, _user_skills(db, user_id))
    res["momentum"] = award
    return res


# ----- Generation -----

@router.post("/generate")
def generate_messages(
    payload: MessageGenerateIn,
    db: Session = Depends(get_db),
    _rl: None = Depends(rate_limit("message_generate")),
    user: User = Depends(plans.enforce_limit("message_generate")),
):
    """Generate and store the 4 draft variants for a job (status='draft')."""
    profile: Profile | None = get_profile(db, user.id)
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
            user_id=user.id,
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
def list_messages(db: Session = Depends(get_db), user: User = Depends(require_user)):
    """List the user's message drafts (newest first)."""
    skills = _user_skills(db, user.id)
    msgs = (
        db.query(Message)
        .filter(Message.user_id == user.id)
        .order_by(Message.id.desc())
        .all()
    )
    return [_serialize(msg, skills) for msg in msgs]


@router.get("/{message_id}")
def get_message(message_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    """Return a single message by id (404 unless it belongs to the user)."""
    return _serialize(_get_or_404(db, message_id, user.id), _user_skills(db, user.id))


# ----- Edit -----

@router.patch("/{message_id}")
def patch_message(message_id: int, payload: MessagePatch, db: Session = Depends(get_db), user: User = Depends(require_user)):
    """Edit the draft text of a message."""
    msg = _get_or_404(db, message_id, user.id)
    msg.content = payload.draft_text
    _log_event(db, message_id, "edited")
    db.commit()
    db.refresh(msg)
    return _serialize(msg, _user_skills(db, user.id))


# ----- Approval workflow -----

@router.post("/{message_id}/approve")
def approve_message(message_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    return _set_status(db, message_id, "approved", "approved", user.id)


@router.post("/{message_id}/reject")
def reject_message(message_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    return _set_status(db, message_id, "rejected", "rejected", user.id)


@router.post("/{message_id}/mark-copied")
def mark_copied(message_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    return _set_status(db, message_id, "copied", "copied", user.id)


@router.post("/{message_id}/mark-sent-manually")
def mark_sent_manually(message_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    return _set_status(db, message_id, "sent_manually", "marked_sent", user.id)


# ----- Outcome tracking -----

@router.post("/{message_id}/outcome")
def set_outcome(message_id: int, payload: OutcomeIn, db: Session = Depends(get_db), user: User = Depends(require_user)):
    """Record the real-world result of a (manually sent) message.

    This is the CRM signal — it never sends anything, it just logs what
    happened after the user reached out on their own.
    """
    if payload.outcome not in OUTCOMES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported outcome. Must be one of: {', '.join(OUTCOMES)}",
        )
    msg = _get_or_404(db, message_id, user.id)
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
        db, user.id, "message", message_id, momentum.OUTCOME_EVENT.get(payload.outcome)
    )
    res = _serialize(msg, _user_skills(db, user.id))
    res["momentum"] = award
    return res


# ----- Follow-up tracking -----

@router.post("/{message_id}/follow-up")
def set_follow_up(message_id: int, payload: FollowUpIn, db: Session = Depends(get_db), user: User = Depends(require_user)):
    """Set/clear the follow-up state for a message (CRM nudge, never sends).

    status "none" clears follow-up tracking. A due date is optional and stored
    as a plain ISO date string.
    """
    if payload.status not in FOLLOW_UP_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported status. Must be one of: {', '.join(FOLLOW_UP_STATUSES)}",
        )
    msg = _get_or_404(db, message_id, user.id)
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
        db, user.id, "message", message_id, momentum.FOLLOW_UP_EVENT.get(payload.status)
    )
    res = _serialize(msg, _user_skills(db, user.id))
    res["momentum"] = award
    return res
