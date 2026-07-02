"""Small profile helpers shared by the outreach routers."""

import json

from sqlalchemy.orm import Session

from ..models import Profile


def get_profile(db: Session, user_id: str) -> Profile | None:
    """Return the given user's profile, or None if not saved yet."""
    return db.query(Profile).filter(Profile.user_id == user_id).first()


def profile_skills(profile: Profile | None) -> list[str]:
    """The profile's skills as a plain list ([] when absent/unparseable)."""
    if profile is None or not profile.skills:
        return []
    try:
        return json.loads(profile.skills)
    except (ValueError, TypeError):
        return []
