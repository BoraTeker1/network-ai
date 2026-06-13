"""Job endpoints.

Ingestion from SimplifyJobs/New-Grad-Positions, list/detail reads, and
deterministic matching/ranking against the saved demo-user profile.

NOTE: static paths like /jobs/matches/ranked are declared BEFORE the
/jobs/{job_id} catch-all so they aren't swallowed by the int path param.
"""

import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Job
from ..services.job_ingestion import ingest_jobs
from ..services import matcher

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _serialize(job: Job) -> dict:
    """Convert a Job row into a clean JSON-friendly dict."""
    return {
        "id": job.id,
        "source": job.source,
        "company": job.company,
        "title": job.title,
        "location": job.location,
        "url": job.url,
        "created_at": job.created_at.isoformat() if job.created_at else None,
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


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Return a single job by id."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return _serialize(job)
