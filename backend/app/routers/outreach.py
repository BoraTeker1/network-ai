"""Paste-a-JD bilingual outreach — draft from a pasted job description.

Stateless and copilot-only: the user pastes a JD they found themselves, names a
contact, picks a language (English/Turkish) and channel (email / LinkedIn note),
and optionally adds remote/EU framing. We personalize the draft with the saved
profile's REAL skills, return quality/risk checklists and manual "who to contact"
guidance, and store/send nothing — AI proposes, the user reviews, edits, copies,
and sends manually. No scraping, no auto-send.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import DEMO_USER_ID, Profile
from ..schemas import OutreachPasteIn
from ..services import outreach

router = APIRouter(prefix="/outreach", tags=["outreach"])


def _profile_skills(db: Session) -> tuple[list[str], str | None]:
    """Return (skills, experience_summary) for the demo profile, or ([], None)."""
    profile = db.query(Profile).filter(Profile.user_id == DEMO_USER_ID).first()
    if profile is None:
        return [], None
    try:
        skills = json.loads(profile.skills) if profile.skills else []
    except (ValueError, TypeError):
        skills = []
    return skills, profile.experience_summary


@router.post("/draft-from-paste")
def draft_from_paste(payload: OutreachPasteIn, db: Session = Depends(get_db)):
    """Draft a personalized bilingual outreach message from a pasted JD."""
    jd_text = (payload.jd_text or "").strip()
    if not jd_text:
        raise HTTPException(status_code=400, detail="jd_text must not be empty")

    skills, resume_summary = _profile_skills(db)

    return outreach.generate(
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
