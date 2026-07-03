"""Paste-a-JD bilingual outreach — draft from a pasted job description.

Stateless and copilot-only: the user pastes a JD they found themselves, names a
contact, picks a language (English/Turkish) and channel (email / LinkedIn note),
and optionally adds remote/EU framing. We personalize the draft with the saved
profile's REAL skills, return quality/risk checklists and manual "who to contact"
guidance, and store/send nothing — AI proposes, the user reviews, edits, copies,
and sends manually. No scraping, no auto-send.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_user
from ..models import Message, Profile, User
from ..schemas import OutreachPasteIn, OutreachSaveIn
from ..services import events, outreach, plans
from ..services.rate_limit import rate_limit

router = APIRouter(prefix="/outreach", tags=["outreach"])

# Pipeline statuses a freshly-saved draft may start in (mirrors the message
# approval workflow — see routers/messages.VALID_STATUSES).
_SAVE_STATUSES = {"draft", "approved", "copied", "sent_manually"}


@router.get("/contact-guidance")
def contact_guidance(
    company: str = Query("", description="Company to suggest contacts at."),
    language: str = Query("en"),
):
    """Who to contact at a company + safe manual search links — available BEFORE
    drafting, so the user can find a real person first, then draft to them. Builds
    URL strings only: no network call, no scraping, no auto-contact."""
    return outreach.contact_guidance(company, "tr" if language.startswith("tr") else "en")


def _profile_skills(db: Session, user_id: str) -> tuple[list[str], str | None]:
    """Return (skills, experience_summary) for the user's profile, or ([], None)."""
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if profile is None:
        return [], None
    try:
        skills = json.loads(profile.skills) if profile.skills else []
    except (ValueError, TypeError):
        skills = []
    return skills, profile.experience_summary


@router.post("/draft-from-paste")
def draft_from_paste(
    payload: OutreachPasteIn,
    db: Session = Depends(get_db),
    _rl: None = Depends(rate_limit("outreach_draft")),
    user: User = Depends(plans.enforce_limit("outreach_draft")),
):
    """Draft a personalized bilingual outreach message from a pasted JD."""
    jd_text = (payload.jd_text or "").strip()
    if not jd_text:
        raise HTTPException(status_code=400, detail="jd_text must not be empty")

    skills, resume_summary = _profile_skills(db, user.id)

    draft = outreach.generate(
        jd_text=jd_text,
        contact=payload.contact.model_dump() if payload.contact else {},
        language=payload.language,
        channel=payload.channel,
        tone=payload.tone,
        profile_skills=skills,
        resume_summary=resume_summary,
        company=payload.company,
        role=payload.role,
        target_region=payload.target_region,
        based_in=payload.based_in,
        timezone_overlap=payload.timezone_overlap,
        work_authorization_note=payload.work_authorization_note,
        include_location_line=payload.include_location_line,
        include_work_auth_line=payload.include_work_auth_line,
        skill_highlight=payload.skill_highlight,
    )
    events.track(db, "draft_created", user_id=user.id,
                 note=f"{draft['channel']}/{draft['language']}, llm={draft['llm_used']}")
    return draft


@router.post("/save-draft")
def save_draft(
    payload: OutreachSaveIn,
    db: Session = Depends(get_db),
    user: User = Depends(plans.enforce_limit("pipeline_save")),
):
    """Persist a reviewed outreach draft as a tracked pipeline item.

    This is what turns the stateless Opportunities→Outreach flow into a real
    pipeline: the draft becomes a Message the user can revisit, copy, mark sent
    manually, mark replied, follow up on, and later link to Next Move AI. Nothing
    is ever sent — the user still copies and sends everything themselves.
    """
    body = (payload.body or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="body must not be empty")

    channel = "linkedin" if (payload.channel or "").lower() == "linkedin" else "email"
    language = "tr" if (payload.language or "en").lower().startswith("tr") else "en"
    status = payload.status if payload.status in _SAVE_STATUSES else "copied"

    msg = Message(
        user_id=user.id,
        message_type=f"outreach_{channel}",
        content=body,
        subject=(payload.subject or None) if channel == "email" else None,
        status=status,
        company=(payload.company or "").strip() or None,
        title=(payload.role or "").strip() or None,
        channel=channel,
        language=language,
        job_url=(payload.job_url or "").strip() or None,
        contact_name=(payload.contact_name or "").strip() or None,
        contact_title=(payload.contact_title or "").strip() or None,
        opportunity_id=payload.opportunity_id,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    events.track(db, "pipeline_saved", user_id=user.id, note=f"message {msg.id}")

    # Reuse the messages serializer so the pipeline/Next Move see an identical
    # shape (checklist, tone, timestamps) to any other Message.
    from .messages import _serialize, _user_skills

    return _serialize(msg, _user_skills(db, user.id))
