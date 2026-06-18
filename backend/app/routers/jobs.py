"""Job endpoints.

Ingestion from SimplifyJobs/New-Grad-Positions, list/detail reads, and
deterministic matching/ranking against the saved demo-user profile.

NOTE: static paths like /jobs/matches/ranked are declared BEFORE the
/jobs/{job_id} catch-all so they aren't swallowed by the int path param.
"""

import json

import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Job
from ..schemas import NewGradIngestIn
from ..services.job_ingestion import ingest_jobs
from ..services import matcher, newgrad_jobs, strategy
from ..services.contact_search import contact_searches_for_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _loads_list(blob: str | None) -> list:
    try:
        val = json.loads(blob) if blob else []
        return val if isinstance(val, list) else []
    except (ValueError, TypeError):
        return []


def _serialize(job: Job) -> dict:
    """Convert a Job row into a clean JSON-friendly dict.

    Includes the richer normalized fields (populated by newer adapters such as
    newgrad-jobs.com); older Simplify rows simply return null/empty for them.
    """
    return {
        "id": job.id,
        "source": job.source,
        "company": job.company,
        "title": job.title,
        "location": job.location,
        "url": job.url,
        "employment_type": job.employment_type,
        "work_mode": job.work_mode,
        "salary_range": job.salary_range,
        "level": job.level,
        "description": job.description,
        "responsibilities": _loads_list(job.responsibilities),
        "qualifications": _loads_list(job.qualifications),
        "benefits": _loads_list(job.benefits),
        "source_url": job.source_url,
        "external_apply_url": job.external_apply_url,
        "is_closed": bool(job.is_closed),
        "posted_at": job.posted_at,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "discovered_at": job.discovered_at.isoformat() if job.discovered_at else None,
    }


# ----- Ingestion -----

@router.post("/ingest/simplify")
def ingest_simplify(db: Session = Depends(get_db)):
    """Fetch + parse + store deduplicated jobs from the SimplifyJobs README."""
    try:
        result = ingest_jobs(db)
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch SimplifyJobs README: {exc}",
        )
    except Exception as exc:  # parsing/db safety net for the MVP
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")
    return result


@router.post("/ingest/newgrad-jobs")
def ingest_newgrad(
    payload: NewGradIngestIn | None = None, db: Session = Depends(get_db)
):
    """Fetch + parse + store deduplicated jobs from newgrad-jobs.com category
    pages. Permission-first and conservative: only newgrad-jobs.com is fetched,
    requests are rate-limited and capped, closed jobs are skipped, and no
    external boards are scraped. Page-level failures are returned in `errors`
    rather than raising, so a missing category never breaks the run.
    """
    payload = payload or NewGradIngestIn()
    return newgrad_jobs.ingest_newgrad_jobs(
        db,
        categories=payload.categories or None,
        max_per_category=payload.max_per_category or 15,
        request_delay=payload.request_delay
        if payload.request_delay is not None
        else 0.5,
    )


# ----- Matching / ranking (static paths first) -----

@router.post("/match-all")
def match_all_jobs(db: Session = Depends(get_db)):
    """Score every stored job against the saved demo-user profile."""
    try:
        return matcher.match_all(db)
    except ValueError as exc:  # no profile saved yet
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/matches/ranked")
def list_ranked_matches(limit: int = 100, db: Session = Depends(get_db)):
    """Return jobs with match scores, highest first."""
    return matcher.ranked_matches(db, limit=limit)


# ----- Reads -----

@router.get("")
def list_jobs(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    """Return stored jobs as a clean JSON array (newest first)."""
    jobs = (
        db.query(Job)
        .order_by(Job.id.desc())
        .offset(offset)
        .limit(min(limit, 500))
        .all()
    )
    return [_serialize(job) for job in jobs]


@router.post("/{job_id}/match")
def match_one_job(job_id: int, db: Session = Depends(get_db)):
    """Score a single job against the saved demo-user profile (upsert)."""
    try:
        return matcher.match_job(db, job_id)
    except ValueError as exc:  # no profile saved yet
        raise HTTPException(status_code=400, detail=str(exc))
    except LookupError as exc:  # job not found
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{job_id}/contact-searches")
def job_contact_searches(job_id: int, db: Session = Depends(get_db)):
    """Manual LinkedIn/Google contact-search suggestions for a job's company."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    if not job.company:
        raise HTTPException(
            status_code=404, detail=f"Job {job_id} has no company to search for"
        )
    return contact_searches_for_job(job.company, job.title)


@router.get("/{job_id}/strategy")
def job_strategy(job_id: int, db: Session = Depends(get_db)):
    """Deterministic outreach strategy for a job (who/how-many/tone/sequence).

    Uses the job's score against the saved profile when available; falls back
    to 0 (Poor Fit) if no profile is saved yet.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    profile = matcher.get_demo_profile(db)
    if profile is None:
        return strategy.outreach_strategy(0, job, 0)

    result = matcher.score_job(matcher._profile_skills(profile), job)
    return strategy.outreach_strategy(
        result["score"], job, len(result["matched_skills"])
    )


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Return a single job by id."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return _serialize(job)
