"""Next Move AI — analyze a reply the user pasted and propose their next move.

The user MANUALLY pastes the received reply (no scraping, no auto-reading). The
analysis is stateless; confirming an outcome reuses the existing message/email
outcome endpoints, which already award Momentum and prevent double-counting.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_user
from ..models import Contact, EmailDraft, Job, Message, User
from ..schemas import NextMoveIn
from ..services import next_move, plans
from ..services.rate_limit import rate_limit

router = APIRouter(prefix="/next-move", tags=["next-move"])


@router.post("/analyze")
def analyze(
    payload: NextMoveIn,
    db: Session = Depends(get_db),
    _rl: None = Depends(rate_limit("next_move")),
    user: User = Depends(plans.enforce_limit("next_move")),
):
    """Analyze a pasted reply and return summary, intent, next move, and drafts."""
    reply_text = (payload.reply_text or "").strip()
    if not reply_text:
        raise HTTPException(status_code=400, detail="reply_text must not be empty")

    company = role = contact_name = contact_title = None
    pipeline_target: dict = {"type": None, "id": None}

    # Resolve a linked pipeline item for context + as the update target.
    if payload.message_id is not None:
        msg = (
            db.query(Message)
            .filter(Message.id == payload.message_id, Message.user_id == user.id)
            .first()
        )
        if msg is None:
            raise HTTPException(status_code=404, detail="Linked message not found")
        pipeline_target = {"type": "message", "id": msg.id}
        # Outreach-copilot messages store company/title directly; legacy rows
        # fall back to the linked Job.
        company = msg.company or (msg.job.company if msg.job else None)
        role = msg.title or (msg.job.title if msg.job else None)
    elif payload.email_id is not None:
        email = (
            db.query(EmailDraft)
            .filter(EmailDraft.id == payload.email_id, EmailDraft.user_id == user.id)
            .first()
        )
        if email is None:
            raise HTTPException(status_code=404, detail="Linked email not found")
        pipeline_target = {"type": "email", "id": email.id}
        if email.opportunity:
            company, role = email.opportunity.company, email.opportunity.title
        elif email.job:
            company, role = email.job.company, email.job.title
        if email.contact:
            contact_name, contact_title = email.contact.name, email.contact.title

    # Standalone job/contact context (when no pipeline item is linked).
    if company is None and payload.job_id is not None:
        job = db.query(Job).filter(Job.id == payload.job_id).first()
        if job is not None:
            company, role = job.company, job.title
    if contact_name is None and payload.contact_id is not None:
        contact = (
            db.query(Contact)
            .filter(Contact.id == payload.contact_id, Contact.user_id == user.id)
            .first()
        )
        if contact is not None:
            contact_name, contact_title = contact.name, contact.title

    result = next_move.analyze_reply(
        reply_text=reply_text,
        context={
            "company": company,
            "role": role,
            "contact_name": contact_name,
            "contact_title": contact_title,
        },
    )
    result["pipeline_target"] = pipeline_target
    return result
