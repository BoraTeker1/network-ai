"""LinkedIn draft generation.

Generates a LinkedIn connection note (300-char cap) or a post-accept DM, stored
as an EmailDraft row so the entire review → approve → copy → mark-sent-manual
workflow (and Momentum) in the /emails router is reused unchanged. Nothing is
ever auto-sent — copy/paste into LinkedIn yourself is the only ToS-safe path.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import DEMO_USER_ID, Contact, EmailDraft, Goal, Job
from ..schemas import LinkedInDraftIn
from ..services import linkedin_generator, matcher
from .emails import _serialize

router = APIRouter(prefix="/linkedin", tags=["linkedin"])


@router.post("/draft")
def draft_linkedin(payload: LinkedInDraftIn, db: Session = Depends(get_db)):
    """Generate and store a LinkedIn draft (LLM when configured, else template)."""
    if payload.kind not in linkedin_generator.VALID_KINDS:
        raise HTTPException(
            status_code=400,
            detail=f"kind must be one of: {', '.join(linkedin_generator.VALID_KINDS)}",
        )

    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {payload.job_id} not found")
    contact = db.query(Contact).filter(Contact.id == payload.contact_id).first()
    if contact is None:
        raise HTTPException(
            status_code=404, detail=f"Contact {payload.contact_id} not found"
        )
    goal = (
        db.query(Goal).filter(Goal.id == payload.goal_id).first()
        if payload.goal_id
        else None
    )

    profile = matcher.get_demo_profile(db)
    skills = matcher._profile_skills(profile) if profile else []
    summary = profile.experience_summary if profile else None

    goal_dict = {
        "target_role": goal.target_role if goal else None,
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

    result = linkedin_generator.generate_linkedin(
        kind=payload.kind,
        profile_skills=skills,
        experience_summary=summary,
        goal=goal_dict,
        job=job_dict,
        contact=contact_dict,
        tone=payload.tone,
    )

    draft = EmailDraft(
        user_id=DEMO_USER_ID,
        job_id=job.id,
        contact_id=contact.id,
        goal_id=goal.id if goal else None,
        subject=result["subject"],          # None for LinkedIn
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
