"""Job endpoints.

Ingestion from SimplifyJobs/New-Grad-Positions, plus list/detail reads.
Ranking against a profile is a later slice.
"""

import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Job
from ..services.job_ingestion import ingest_jobs

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


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Return a single job by id."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return _serialize(job)
