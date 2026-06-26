"""Curated Turkey + Remote/EU opportunity feed.

`GET /opportunities` serves stored rows (seeded from a curated SAMPLE feed on
first use) — it never makes a network call. Public-API import and manual JSON
import are explicit, separate, resilient actions. No scraping, no auto-apply,
no auto-send. Each row flows into the /outreach copilot via `outreach_prefill`.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import DEMO_USER_ID, Profile
from ..schemas import OpportunityImportIn
from ..services import opportunities

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def _profile_skills(db: Session) -> list[str]:
    profile = db.query(Profile).filter(Profile.user_id == DEMO_USER_ID).first()
    if profile is None or not profile.skills:
        return []
    try:
        return json.loads(profile.skills)
    except (ValueError, TypeError):
        return []


@router.get("")
def list_opportunities(
    db: Session = Depends(get_db),
    region: str | None = Query(None),
    seniority: str | None = Query(None),
    remote: bool = Query(False),
    applicability: str | None = Query(None),
    tag: str | None = Query(None),
    source: str | None = Query(None),          # filters by source provider
    confidence: str | None = Query(None),
    include_ineligible: bool = Query(False),
    limit: int = Query(100, ge=1, le=300),
):
    """Ranked Turkey-relevant opportunities. Seeds the sample feed on first use;
    no network call happens here. "Probably not eligible" roles (e.g. US-only)
    are hidden by default — pass include_ineligible=true or applicability=no."""
    opportunities.ensure_seeded(db)
    items = opportunities.list_opportunities(
        db, region=region, seniority=seniority, remote_only=remote,
        applicability=applicability, tag=tag, source=source, confidence=confidence,
        include_ineligible=include_ineligible, profile_skills=_profile_skills(db),
        limit=limit,
    )
    return {
        "count": len(items),
        "applicability_labels": opportunities.APPLICABILITY_KEYS,
        "items": items,
    }


@router.get("/sources")
def list_sources():
    """The curated source registry (enabled live ATS sources + disabled/manual)."""
    return {"sources": opportunities.list_sources()}


@router.post("/import")
def import_opportunities(payload: OpportunityImportIn, db: Session = Depends(get_db)):
    """Import curated jobs from pasted JSON (e.g. from company career pages).
    No scraping — the user supplies the records."""
    return opportunities.import_records(
        db, payload.jobs, source=payload.source or "manual-import",
        is_sample=payload.is_sample,
        source_provider=payload.source or "manual-import",
        source_confidence="sample_demo" if payload.is_sample else "manual_curated",
    )


@router.post("/refresh-public-sources")
def refresh_public_sources(db: Session = Depends(get_db), limit: int = Query(50, ge=1, le=100)):
    """Fetch + store public job-board listings (Arbeitnow, no key). Resilient:
    on failure it reports the error and leaves the seeded feed intact."""
    return opportunities.refresh_public_sources(db, limit=limit)


@router.post("/refresh-sources")
def refresh_sources(db: Session = Depends(get_db)):
    """Refresh all ENABLED official Turkish/Turkey-relevant ATS sources (Lever/
    Greenhouse/Ashby public APIs — no key, not scraping). Per-source status;
    one source failing never breaks the others."""
    return opportunities.refresh_sources(db)


@router.post("/refresh-source/{source_id}")
def refresh_source(source_id: str, db: Session = Depends(get_db)):
    """Refresh a single registry source by id."""
    result = opportunities.refresh_source(db, source_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Unknown source '{source_id}'")
    return result


@router.post("/refresh-turkish-sources")
def refresh_turkish_sources(db: Session = Depends(get_db)):
    """Legacy alias for /refresh-sources (kept for back-compat)."""
    return opportunities.refresh_turkish_sources(db)
