"""Demo seed endpoint.

One call to make the app demo-ready WITHOUT touching the network: it saves a
sample profile, inserts a few illustrative jobs, ranks them, and generates a
batch of outreach drafts. Non-destructive and idempotent — existing data is
left in place and seed rows are de-duplicated by a stable external_id.

This exists purely to make the local demo fast. It never scrapes or sends.
"""

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import DEMO_USER_ID, Job, Message, Profile
from ..services import matcher, message_generator
from ..services.resume_parser import parse_resume

router = APIRouter(prefix="/demo", tags=["demo"])

SEED_SOURCE = "demo-seed"

_DEMO_RESUME = """\
Alex Rivera — Software Engineer (New Grad)
B.S. Computer Science, 2025. International student seeking new-grad SWE roles.

Skills: Python, FastAPI, TypeScript, React, Next.js, PostgreSQL, SQL, Docker, Git, REST API.

Experience:
- Built a full-stack job-search tool with a FastAPI backend and a React/Next.js frontend.
- Internship: shipped REST APIs in Python, wrote PostgreSQL queries, containerized services with Docker.
- Coursework in machine learning and distributed systems.
"""

# (company, title, location) — illustrative new-grad postings.
_DEMO_JOBS = [
    ("Stripe", "Software Engineer, New Grad", "Remote"),
    ("Datadog", "Backend Engineer (Early Career)", "New York, NY"),
    ("Rippling", "Full Stack Engineer I", "San Francisco, CA"),
    ("Notion", "Software Engineer - University Grad", "Remote"),
    ("Snowflake", "Associate Data Engineer", "Bellevue, WA"),
    ("Robinhood", "Product Manager, Associate", "Menlo Park, CA"),
]


def _seed_external_id(company: str, title: str) -> str:
    return f"{company}::{title}".lower().replace(" ", "-")


@router.post("/seed")
def seed_demo(db: Session = Depends(get_db)):
    """Seed a demo profile, jobs, matches, and drafts. Safe to run repeatedly."""
    actions: list[str] = []

    # 1. Profile (upsert the single demo user).
    profile = db.query(Profile).filter(Profile.user_id == DEMO_USER_ID).first()
    if profile is None:
        profile = Profile(user_id=DEMO_USER_ID)
        db.add(profile)
        actions.append("created demo profile")
    else:
        actions.append("reused existing profile")
    parsed = parse_resume(_DEMO_RESUME)
    profile.raw_resume = _DEMO_RESUME
    profile.skills = json.dumps(parsed["skills"])
    profile.experience_summary = parsed["experience_summary"]
    db.commit()
    db.refresh(profile)

    # 2. Demo jobs (dedup by stable external_id).
    jobs_added = 0
    for company, title, location in _DEMO_JOBS:
        external_id = _seed_external_id(company, title)
        exists = (
            db.query(Job)
            .filter(Job.source == SEED_SOURCE, Job.external_id == external_id)
            .first()
        )
        if exists:
            continue
        db.add(
            Job(
                source=SEED_SOURCE,
                external_id=external_id,
                company=company,
                title=title,
                location=location,
                url="https://example.com/apply",
                raw=json.dumps({"demo": True}),
            )
        )
        jobs_added += 1
    db.commit()
    actions.append(f"added {jobs_added} demo jobs")

    # 3. Rank everything against the profile.
    matcher.match_all(db)
    actions.append("ranked all jobs")

    # 4. Generate drafts for the top demo jobs (only if none exist yet).
    drafts_created = 0
    if db.query(Message).count() == 0:
        skills = json.loads(profile.skills) if profile.skills else []
        top = matcher.ranked_matches(db, limit=2)
        for match in top:
            job = db.query(Job).filter(Job.id == match["job_id"]).first()
            if job is None:
                continue
            for mtype, text in message_generator.build_drafts(
                profile_skills=skills,
                company=job.company or "the company",
                role=job.title or "this role",
            ):
                db.add(
                    Message(
                        user_id=DEMO_USER_ID,
                        job_id=job.id,
                        message_type=mtype,
                        content=text,
                        status="draft",
                    )
                )
                drafts_created += 1
        db.commit()
    actions.append(f"created {drafts_created} drafts")

    return {
        "ok": True,
        "actions": actions,
        "total_jobs": db.query(Job).count(),
        "total_messages": db.query(Message).count(),
    }
