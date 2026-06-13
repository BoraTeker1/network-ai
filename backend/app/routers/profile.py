"""Profile endpoints.

Single fake-user mode (DEMO_USER_ID). Pasting a resume creates the profile
the first time and updates it on every subsequent paste (no duplicates).
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import DEMO_USER_ID, Profile
from ..schemas import ResumeTextIn
from ..services.resume_parser import parse_resume

router = APIRouter(prefix="/profile", tags=["profile"])


def _serialize(profile: Profile) -> dict:
    """Convert a Profile row into a clean JSON-friendly dict."""
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "skills": json.loads(profile.skills) if profile.skills else [],
        "education": profile.education,
        "experience_summary": profile.experience_summary,
        "target_roles": json.loads(profile.target_roles) if profile.target_roles else [],
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
    }


@router.post("/resume-text")
def save_resume_text(payload: ResumeTextIn, db: Session = Depends(get_db)):
    """Save/replace the demo user's resume and extract a simple profile."""
    resume_text = payload.resume_text.strip()
    if not resume_text:
        raise HTTPException(status_code=400, detail="resume_text must not be empty")

    parsed = parse_resume(resume_text)

    # Upsert: reuse the existing demo-user profile if present.
    profile = db.query(Profile).filter(Profile.user_id == DEMO_USER_ID).first()
    if profile is None:
        profile = Profile(user_id=DEMO_USER_ID)
        db.add(profile)

    profile.raw_resume = resume_text
    profile.skills = json.dumps(parsed["skills"])
    profile.experience_summary = parsed["experience_summary"]

    db.commit()
    db.refresh(profile)
    return _serialize(profile)


@router.get("")
def get_profile(db: Session = Depends(get_db)):
    """Return the saved demo-user profile."""
    profile = db.query(Profile).filter(Profile.user_id == DEMO_USER_ID).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="No profile saved yet")
    return _serialize(profile)
