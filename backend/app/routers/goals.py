"""Job-search / outreach goal endpoints (per authenticated user).

A Goal captures what the user is looking for and how they want to reach out.
It feeds email generation later. CRUD only — nothing here sends anything.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_user
from ..models import CONTACT_TYPES, OUTREACH_GOALS, Goal, User
from ..schemas import GoalIn

router = APIRouter(prefix="/goals", tags=["goals"])


def _serialize(goal: Goal) -> dict:
    return {
        "id": goal.id,
        "target_role": goal.target_role,
        "target_location": goal.target_location,
        "target_company_type": goal.target_company_type,
        "outreach_goal": goal.outreach_goal,
        "tone_preference": goal.tone_preference,
        "max_contacts_per_company": goal.max_contacts_per_company,
        "preferred_contact_types": json.loads(goal.preferred_contact_types)
        if goal.preferred_contact_types
        else [],
        "notes": goal.notes,
        "created_at": goal.created_at.isoformat() if goal.created_at else None,
        "updated_at": goal.updated_at.isoformat() if goal.updated_at else None,
    }


def _validate(payload: GoalIn) -> None:
    if payload.outreach_goal and payload.outreach_goal not in OUTREACH_GOALS:
        raise HTTPException(
            status_code=400,
            detail=f"outreach_goal must be one of: {', '.join(OUTREACH_GOALS)}",
        )
    for ct in payload.preferred_contact_types or []:
        if ct not in CONTACT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"preferred_contact_types must be from: {', '.join(CONTACT_TYPES)}",
            )


def _apply(goal: Goal, payload: GoalIn) -> None:
    goal.target_role = payload.target_role
    goal.target_location = payload.target_location
    goal.target_company_type = payload.target_company_type
    goal.outreach_goal = payload.outreach_goal
    goal.tone_preference = payload.tone_preference
    if payload.max_contacts_per_company is not None:
        goal.max_contacts_per_company = payload.max_contacts_per_company
    goal.preferred_contact_types = (
        json.dumps(payload.preferred_contact_types)
        if payload.preferred_contact_types is not None
        else goal.preferred_contact_types
    )
    goal.notes = payload.notes


@router.get("")
def list_goals(db: Session = Depends(get_db), user: User = Depends(require_user)):
    goals = (
        db.query(Goal)
        .filter(Goal.user_id == user.id)
        .order_by(Goal.id.desc())
        .all()
    )
    return [_serialize(g) for g in goals]


@router.post("")
def create_goal(payload: GoalIn, db: Session = Depends(get_db), user: User = Depends(require_user)):
    _validate(payload)
    goal = Goal(user_id=user.id)
    _apply(goal, payload)
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return _serialize(goal)


@router.patch("/{goal_id}")
def update_goal(goal_id: int, payload: GoalIn, db: Session = Depends(get_db), user: User = Depends(require_user)):
    _validate(payload)
    goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
    if goal is None:
        raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")
    _apply(goal, payload)
    db.commit()
    db.refresh(goal)
    return _serialize(goal)


@router.delete("/{goal_id}")
def delete_goal(goal_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
    if goal is None:
        raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")
    db.delete(goal)
    db.commit()
    return {"status": "deleted", "id": goal_id}
