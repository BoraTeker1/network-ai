"""Contact management + compliant discovery.

Manual entry is the primary path today. /contacts/discover aggregates manually
added contacts (and any configured compliant provider) — it NEVER scrapes and
NEVER invents data. Missing provider keys return a helpful message, not a 500.

Static paths (/manual, /discover) are declared before /{contact_id}.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_user
from ..models import CONTACT_TYPES, Contact, Goal, Job, User
from ..schemas import ContactManualIn, DiscoverIn
from ..services import contact_discovery

router = APIRouter(prefix="/contacts", tags=["contacts"])


def _serialize(c: Contact) -> dict:
    return {
        "id": c.id,
        "job_id": c.job_id,
        "name": c.name,
        "title": c.title,
        "company": c.company,
        "email": c.email,
        "linkedin_url": c.linkedin_url,
        "contact_type": c.contact_type,
        "email_confidence": c.email_confidence,
        "source": c.source,
        "source_note": c.source_note,
        "why_relevant": c.why_relevant,
        "risk_note": c.risk_note,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.post("/manual")
def add_manual_contact(payload: ContactManualIn, db: Session = Depends(get_db), user: User = Depends(require_user)):
    """Add a contact the user found themselves. Never scraped, never invented."""
    if payload.contact_type and payload.contact_type not in CONTACT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"contact_type must be one of: {', '.join(CONTACT_TYPES)}",
        )
    company = payload.company
    if payload.job_id and not company:
        job = db.query(Job).filter(Job.id == payload.job_id).first()
        company = job.company if job else None

    contact = Contact(
        user_id=user.id,
        job_id=payload.job_id,
        name=payload.name,
        title=payload.title,
        company=company,
        email=payload.email,
        linkedin_url=payload.linkedin_url,
        contact_type=payload.contact_type,
        email_confidence=payload.email_confidence,
        source="manual",
        source_note=payload.source_note or "Manually added by the user.",
        why_relevant=contact_discovery._why_relevant(
            payload.contact_type or "contact", None, company
        ),
        risk_note=contact_discovery._risk_note("manual"),
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return _serialize(contact)


@router.post("/discover")
def discover(payload: DiscoverIn, db: Session = Depends(get_db), user: User = Depends(require_user)):
    """Aggregate manual contacts + any configured compliant provider.

    Returns {api_discovery_configured, providers_available, message, results}.
    """
    if payload.contact_type not in CONTACT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"contact_type must be one of: {', '.join(CONTACT_TYPES)}",
        )

    job = (
        db.query(Job).filter(Job.id == payload.job_id).first()
        if payload.job_id
        else None
    )
    goal = (
        db.query(Goal).filter(Goal.id == payload.goal_id).first()
        if payload.goal_id
        else None
    )
    company = job.company if job else ""

    existing = [
        _serialize(c)
        for c in db.query(Contact).filter(Contact.user_id == user.id).all()
    ]
    job_dict = {"company": company, "title": job.title if job else None}
    goal_dict = {"outreach_goal": goal.outreach_goal if goal else None}

    return contact_discovery.discover_contacts(
        existing_contacts=existing,
        company=company,
        contact_type=payload.contact_type,
        max_results=max(1, min(payload.max_results, 25)),
        job=job_dict,
        goal=goal_dict,
    )


@router.get("")
def list_contacts(job_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_user)):
    q = db.query(Contact).filter(Contact.user_id == user.id)
    if job_id is not None:
        q = q.filter(Contact.job_id == job_id)
    return [_serialize(c) for c in q.order_by(Contact.id.desc()).all()]


@router.get("/{contact_id}")
def get_contact(contact_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    c = db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == user.id).first()
    if c is None:
        raise HTTPException(status_code=404, detail=f"Contact {contact_id} not found")
    return _serialize(c)
