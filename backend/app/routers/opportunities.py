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
from ..deps import optional_user, require_user
from ..models import LABEL_FEEDBACK_VERDICTS, LabelFeedback, Opportunity, Profile, User
from ..schemas import LabelFeedbackIn, OpportunityImportIn
from ..services import events, opportunities
from ..services.rate_limit import rate_limit

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def _profile_skills(db: Session, user: User | None) -> list[str]:
    if user is None:
        return []
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile is None or not profile.skills:
        return []
    try:
        return json.loads(profile.skills)
    except (ValueError, TypeError):
        return []


@router.get("")
def list_opportunities(
    db: Session = Depends(get_db),
    user: User | None = Depends(optional_user),
    region: str | None = Query(None),
    seniority: str | None = Query(None),
    remote: bool = Query(False),
    applicability: str | None = Query(None),
    tag: str | None = Query(None),
    source: str | None = Query(None),          # filters by source provider
    confidence: str | None = Query(None),
    function: str = Query("all"),  # all|software_engineering|business|other|any
    include_ineligible: bool = Query(False),
    limit: int = Query(100, ge=1, le=300),
):
    """Ranked Turkey-relevant opportunities. Seeds the sample feed on first use;
    no network call happens here. "Probably not eligible" roles (e.g. US-only)
    are hidden by default — pass include_ineligible=true or applicability=no.
    Engineering + business roles by default (creative/admin "other" hidden) — pass
    function=software_engineering, function=business, function=other, or function=any.
    The feed serves real listings only; pull them with POST /opportunities/refresh-all."""
    items = opportunities.list_opportunities(
        db, region=region, seniority=seniority, remote_only=remote,
        applicability=applicability, tag=tag, source=source, confidence=confidence,
        function=function, include_ineligible=include_ineligible,
        profile_skills=_profile_skills(db, user), limit=limit,
    )
    if user is not None:
        # One event per feed load (not per card) — enough for the funnel.
        events.track(db, "opportunity_viewed", user_id=user.id,
                     note=f"{len(items)} items")
    return {
        "count": len(items),
        "function": function,
        "applicability_labels": opportunities.APPLICABILITY_KEYS,
        "items": items,
    }


@router.post("/{opportunity_id}/label-feedback", status_code=201)
def label_feedback(
    opportunity_id: int,
    payload: LabelFeedbackIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """Record whether the Turkey-applicability label looked right or wrong —
    the validation signal for the classifier itself."""
    if payload.verdict not in LABEL_FEEDBACK_VERDICTS:
        raise HTTPException(
            status_code=422,
            detail=f"verdict must be one of: {', '.join(LABEL_FEEDBACK_VERDICTS)}",
        )
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if opp is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    fb = LabelFeedback(
        user_id=user.id,
        opportunity_id=opportunity_id,
        label=opp.turkey_applicability_label,
        verdict=payload.verdict,
        reason=(payload.reason or "").strip() or None,
    )
    db.add(fb)
    db.commit()
    return {"status": "recorded", "opportunity_id": opportunity_id,
            "verdict": payload.verdict}


@router.get("/sources")
def list_sources():
    """The curated source registry (enabled live ATS sources + disabled/manual)."""
    return {"sources": opportunities.list_sources()}


@router.post("/import")
def import_opportunities(payload: OpportunityImportIn, db: Session = Depends(get_db), _rl: None = Depends(rate_limit("opps_refresh")), _user: User = Depends(require_user)):
    """Import curated jobs from pasted JSON (e.g. from company career pages).
    No scraping — the user supplies the records."""
    return opportunities.import_records(
        db, payload.jobs, source=payload.source or "manual-import",
        is_sample=payload.is_sample,
        source_provider=payload.source or "manual-import",
        source_confidence="sample_demo" if payload.is_sample else "manual_curated",
    )


@router.post("/refresh-public-sources")
def refresh_public_sources(db: Session = Depends(get_db), limit: int = Query(50, ge=1, le=100), _rl: None = Depends(rate_limit("opps_refresh")), _user: User = Depends(require_user)):
    """Fetch + store public job-board listings (Arbeitnow, no key). Resilient:
    on failure it reports the error and leaves the seeded feed intact."""
    return opportunities.refresh_public_sources(db, limit=limit)


@router.post("/refresh-sources")
def refresh_sources(db: Session = Depends(get_db), _rl: None = Depends(rate_limit("opps_refresh")), _user: User = Depends(require_user)):
    """Refresh all ENABLED official Turkish/Turkey-relevant ATS sources (Lever/
    Greenhouse/Ashby public APIs — no key, not scraping). Per-source status;
    one source failing never breaks the others."""
    return opportunities.refresh_sources(db)


@router.post("/refresh-source/{source_id}")
def refresh_source(source_id: str, db: Session = Depends(get_db), _rl: None = Depends(rate_limit("opps_refresh")), _user: User = Depends(require_user)):
    """Refresh a single registry source by id."""
    result = opportunities.refresh_source(db, source_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Unknown source '{source_id}'")
    return result


@router.post("/refresh-all")
def refresh_all(db: Session = Depends(get_db), _rl: None = Depends(rate_limit("opps_refresh")), _user: User = Depends(require_user)):
    """Refresh everything: official ATS sources + public job APIs (Arbeitnow/
    Remotive/Jobicy) in one action. Resilient per source."""
    return opportunities.refresh_all(db)


@router.post("/refresh-turkish-sources")
def refresh_turkish_sources(db: Session = Depends(get_db), _rl: None = Depends(rate_limit("opps_refresh")), _user: User = Depends(require_user)):
    """Legacy alias for /refresh-sources (kept for back-compat)."""
    return opportunities.refresh_turkish_sources(db)
