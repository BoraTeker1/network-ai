"""LinkedIn draft generation.

Generates a LinkedIn connection note (300-char cap) or a post-accept DM, stored
as an EmailDraft row so the entire review → approve → copy → mark-sent-manual
workflow in the /emails router is reused unchanged. Nothing is
ever auto-sent — copy/paste into LinkedIn yourself is the only ToS-safe path.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_user
from ..models import Contact, EmailDraft, Goal, Opportunity, User
from ..schemas import LinkedInDraftIn
from ..services import linkedin_generator, plans
from ..services.profiles import get_profile, profile_skills
from ..services.rate_limit import rate_limit
from .emails import _serialize

router = APIRouter(prefix="/linkedin", tags=["linkedin"])


@router.post("/draft")
def draft_linkedin(
    payload: LinkedInDraftIn,
    db: Session = Depends(get_db),
    _rl: None = Depends(rate_limit("email_draft")),
    user: User = Depends(plans.enforce_limit("email_draft")),
):
    """Generate and store a LinkedIn draft (LLM when configured, else template)."""
    if payload.kind not in linkedin_generator.VALID_KINDS:
        raise HTTPException(
            status_code=400,
            detail=f"kind must be one of: {', '.join(linkedin_generator.VALID_KINDS)}",
        )

    opp = db.query(Opportunity).filter(Opportunity.id == payload.opportunity_id).first()
    if opp is None:
        raise HTTPException(
            status_code=404, detail=f"Opportunity {payload.opportunity_id} not found"
        )
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

    profile = get_profile(db, user.id)
    skills = profile_skills(profile)
    summary = profile.experience_summary if profile else None

    goal_dict = {
        "target_role": goal.target_role if goal else None,
        "outreach_goal": goal.outreach_goal if goal else None,
        "tone_preference": goal.tone_preference if goal else None,
    }
    job_dict = {"company": opp.company, "title": opp.title, "location": opp.location}
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
        user_id=user.id,
        opportunity_id=opp.id,
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
