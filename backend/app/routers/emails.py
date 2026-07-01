"""Email draft generation + approval queue.

AI (or a deterministic template) PROPOSES an email; the user reviews, edits,
approves, copies, and sends manually. Nothing is ever auto-sent. Gmail sending
is a disabled placeholder.

Static path /emails/draft is declared before /{email_id}.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_user
from ..models import (
    EMAIL_STATUSES,
    FOLLOW_UP_STATUSES,
    OUTCOMES,
    Contact,
    EmailDraft,
    Goal,
    Job,
    User,
)
from ..schemas import EmailDraftIn, EmailPatchIn, GmailSendIn
from ..services import email_generator, gmail_sender, matcher, momentum, plans
from ..services.rate_limit import rate_limit

router = APIRouter(prefix="/emails", tags=["emails"])


def _loads(blob: str | None) -> dict:
    try:
        return json.loads(blob) if blob else {}
    except (ValueError, TypeError):
        return {}


def _serialize(e: EmailDraft, db: Session) -> dict:
    contact = e.contact
    job = e.job
    quality = _loads(e.quality_checklist)
    risk = _loads(e.risk_checklist)
    return {
        "id": e.id,
        "job_id": e.job_id,
        "contact_id": e.contact_id,
        "goal_id": e.goal_id,
        "company": job.company if job else None,
        "role": job.title if job else None,
        "contact_name": contact.name if contact else None,
        "contact_title": contact.title if contact else None,
        "contact_email": contact.email if contact else None,
        "contact_why_relevant": contact.why_relevant if contact else None,
        "subject": e.subject,
        "body": e.body,
        "message_type": e.message_type,
        "tone": e.tone,
        "personalization_notes": e.personalization_notes,
        "quality_checklist": quality,
        "risk_checklist": risk,
        "why_safe": email_generator.safety_summary(risk=risk, quality=quality),
        "suggested_next_step": email_generator.suggested_next_step(
            status=e.status, outcome=e.outcome
        ),
        "llm_used": bool(e.llm_used),
        "status": e.status,
        "outcome": e.outcome,
        "follow_up_status": e.follow_up_status,
        "follow_up_due_date": e.follow_up_due_date,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
    }


def _get_or_404(db: Session, email_id: int, user_id: str) -> EmailDraft:
    e = (
        db.query(EmailDraft)
        .filter(EmailDraft.id == email_id, EmailDraft.user_id == user_id)
        .first()
    )
    if e is None:
        raise HTTPException(status_code=404, detail=f"Email {email_id} not found")
    return e


# ----- Generation -----

@router.post("/draft")
def draft_email(
    payload: EmailDraftIn,
    db: Session = Depends(get_db),
    _rl: None = Depends(rate_limit("email_draft")),
    user: User = Depends(plans.enforce_limit("email_draft")),
):
    """Generate and store an email draft (LLM when configured, else template)."""
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {payload.job_id} not found")
    contact = (
        db.query(Contact)
        .filter(Contact.id == payload.contact_id, Contact.user_id == user.id)
        .first()
    )
    if contact is None:
        raise HTTPException(
            status_code=404, detail=f"Contact {payload.contact_id} not found"
        )
    goal = (
        db.query(Goal)
        .filter(Goal.id == payload.goal_id, Goal.user_id == user.id)
        .first()
        if payload.goal_id
        else None
    )

    profile = matcher.get_profile(db, user.id)
    skills = matcher._profile_skills(profile) if profile else []
    summary = profile.experience_summary if profile else None

    goal_dict = {
        "target_role": goal.target_role if goal else None,
        "target_location": goal.target_location if goal else None,
        "outreach_goal": goal.outreach_goal if goal else None,
        "tone_preference": goal.tone_preference if goal else None,
    }
    job_dict = {"company": job.company, "title": job.title, "location": job.location}
    contact_dict = {
        "name": contact.name,
        "title": contact.title,
        "company": contact.company,
        "contact_type": contact.contact_type,
        "source": contact.source,
    }

    result = email_generator.generate_email(
        profile_skills=skills,
        experience_summary=summary,
        goal=goal_dict,
        job=job_dict,
        contact=contact_dict,
        tone=payload.tone,
    )

    draft = EmailDraft(
        user_id=user.id,
        job_id=job.id,
        contact_id=contact.id,
        goal_id=goal.id if goal else None,
        subject=result["subject"],
        body=result["body"],
        message_type=result["message_type"],
        tone=result["tone"],
        personalization_notes=result["personalization_notes"],
        quality_checklist=json.dumps(result["quality_checklist"]),
        risk_checklist=json.dumps(result["risk_checklist"]),
        llm_used=result["llm_used"],
        status="draft",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return _serialize(draft, db)


# ----- Reads -----

@router.get("")
def list_emails(db: Session = Depends(get_db), user: User = Depends(require_user)):
    emails = (
        db.query(EmailDraft)
        .filter(EmailDraft.user_id == user.id)
        .order_by(EmailDraft.id.desc())
        .all()
    )
    return [_serialize(e, db) for e in emails]


@router.get("/{email_id}")
def get_email(email_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    return _serialize(_get_or_404(db, email_id, user.id), db)


# ----- Edit -----

@router.patch("/{email_id}")
def patch_email(email_id: int, payload: EmailPatchIn, db: Session = Depends(get_db), user: User = Depends(require_user)):
    """Edit subject/body (recomputes quality checklist) or set outcome/follow-up."""
    e = _get_or_404(db, email_id, user.id)

    if payload.subject is not None:
        e.subject = payload.subject
    if payload.body is not None:
        e.body = payload.body
    if payload.subject is not None or payload.body is not None:
        profile = matcher.get_profile(db, user.id)
        skills = matcher._profile_skills(profile) if profile else []
        quality = email_generator.quality_checklist(
            subject=e.subject,
            body=e.body,
            company=e.job.company if e.job else None,
            role=e.job.title if e.job else None,
            profile_skills=skills,
        )
        e.quality_checklist = json.dumps(quality)

    if payload.outcome is not None:
        if payload.outcome not in OUTCOMES:
            raise HTTPException(
                status_code=400,
                detail=f"outcome must be one of: {', '.join(OUTCOMES)}",
            )
        e.outcome = payload.outcome
    if payload.follow_up_status is not None:
        if payload.follow_up_status not in FOLLOW_UP_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"follow_up_status must be one of: {', '.join(FOLLOW_UP_STATUSES)}",
            )
        e.follow_up_status = (
            None if payload.follow_up_status == "none" else payload.follow_up_status
        )
        e.follow_up_due_date = (
            None if payload.follow_up_status == "none" else payload.follow_up_due_date
        )

    db.commit()
    db.refresh(e)
    # Award Momentum for a reported outcome or a completed follow-up (once each).
    event_type = None
    if payload.outcome is not None:
        event_type = momentum.OUTCOME_EVENT.get(payload.outcome)
    elif payload.follow_up_status is not None:
        event_type = momentum.FOLLOW_UP_EVENT.get(payload.follow_up_status)
    award = momentum.award(db, user.id, "email", email_id, event_type)
    res = _serialize(e, db)
    res["momentum"] = award
    return res


# ----- Approval workflow (explicit, manual) -----

def _set_status(db: Session, email_id: int, status: str, user_id: str) -> dict:
    e = _get_or_404(db, email_id, user_id)
    e.status = status
    db.commit()
    db.refresh(e)
    award = momentum.award(db, user_id, "email", email_id, momentum.STATUS_EVENT.get(status))
    res = _serialize(e, db)
    res["momentum"] = award
    return res


@router.post("/{email_id}/approve")
def approve_email(email_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    return _set_status(db, email_id, "approved", user.id)


@router.post("/{email_id}/reject")
def reject_email(email_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    return _set_status(db, email_id, "rejected", user.id)


@router.post("/{email_id}/mark-copied")
def mark_copied(email_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    return _set_status(db, email_id, "copied", user.id)


@router.post("/{email_id}/mark-sent-manual")
def mark_sent_manual(email_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    return _set_status(db, email_id, "sent_manual", user.id)


# ----- Gmail send (disabled placeholder) -----

@router.post("/{email_id}/send-gmail")
def send_gmail(email_id: int, payload: GmailSendIn, db: Session = Depends(get_db), user: User = Depends(require_user)):
    """Disabled by default. Returns a friendly message instead of failing.

    When enabled later: requires status == 'approved' AND confirm_send == true.
    """
    e = _get_or_404(db, email_id, user.id)

    if not gmail_sender.gmail_enabled():
        return {
            "ok": False,
            "sent": False,
            "status": e.status,
            "message": "Gmail sending is disabled. Copy/manual send is available.",
        }

    # Enabled path (guarded; real send not implemented in this version).
    if e.status != "approved":
        raise HTTPException(
            status_code=400, detail="Email must be approved before sending."
        )
    if not payload.confirm_send:
        raise HTTPException(
            status_code=400, detail="Sending requires confirm_send: true."
        )
    try:
        gmail_sender.send_via_gmail(
            to_email=e.contact.email if e.contact else "",
            subject=e.subject or "",
            body=e.body or "",
            confirm_send=payload.confirm_send,
        )
    except (gmail_sender.GmailDisabled, gmail_sender.GmailNotConfigured) as exc:
        return {"ok": False, "sent": False, "status": e.status, "message": str(exc)}

    # (Unreachable in this MVP — send_via_gmail always raises.)
    e.status = "sent_via_gmail"
    db.commit()
    db.refresh(e)
    return {"ok": True, "sent": True, **_serialize(e, db)}
