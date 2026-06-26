"""Curated Turkey + Remote/EU opportunity feed for junior Turkish engineers.

Compliant by design: sources are a curated SAMPLE seed, public job-board APIs
(no key), company pages, and manual JSON import. We NEVER scrape LinkedIn,
Kariyer.net, Youthall, Techcareer, Coderspace, or any protected/hostile site,
never automate a browser, never auto-apply, and never auto-send.

Each opportunity carries a CONSERVATIVE "can a Turkey-based junior realistically
apply?" label (with a reason) and flows into the existing /outreach copilot.

`GET /opportunities` never makes a network call — it serves stored rows (seeded
on first use). Public-API fetching is an explicit, separate, resilient action.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from ..models import Opportunity

# ----- Controlled vocab + labels -----

LABEL_STRONG = "Strong fit for Turkey-based candidates"
LABEL_POSSIBLE = "Possibly eligible"
LABEL_UNCLEAR = "Unclear"
LABEL_NO = "Probably not eligible"

# Filter keys ↔ human labels (the API filters by key).
APPLICABILITY_KEYS = {
    "strong": LABEL_STRONG,
    "possible": LABEL_POSSIBLE,
    "unclear": LABEL_UNCLEAR,
    "no": LABEL_NO,
}
_LABEL_TO_KEY = {v: k for k, v in APPLICABILITY_KEYS.items()}

_SENIOR_LEVELS = {"senior", "lead", "staff", "principal"}
_JUNIOR_LEVELS = {"internship", "new_grad", "junior"}

SEED_SOURCE = "curated-sample"
_SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "turkey_eu_jobs_seed.json"

# Term banks for the deterministic classifier.
_US_AUTH_TERMS = (
    "us work authorization", "authorized to work in the united states",
    "authorized to work in the us", "must be authorized to work in the us",
    "us citizen", "u.s. citizen", "remote us only", "remote within the us",
    "us only", "u.s. only", "requires us work",
)
_EU_CITIZEN_TERMS = (
    "eu citizen", "eu citizenship", "must be an eu citizen",
    "right to work in the eu", "eu work permit required", "eea citizen",
)
_WORLDWIDE_TERMS = ("worldwide", "anywhere", "global remote", "remote, global",
                    "remote — anywhere", "from anywhere", "any country")
_EMEA_TERMS = ("emea",)
_EUROPE_TERMS = ("europe", "european")
_TURKEY_TERMS = ("turkey", "türkiye", "turkiye", "istanbul", "ankara", "izmir")
_CONTRACTOR_TERMS = ("contractor", "b2b", "contract basis", "freelance")
_RELOCATION_TERMS = ("relocation", "visa sponsorship", "sponsor a visa",
                     "we sponsor", "sponsorship available")


# ----- Inference helpers -----

def _infer_seniority(title: str, explicit: str | None) -> str:
    if explicit:
        e = explicit.lower().strip()
        if e in (_JUNIOR_LEVELS | _SENIOR_LEVELS | {"mid", "unknown"}):
            return e
    t = (title or "").lower()
    if "intern" in t:
        return "internship"
    if any(w in t for w in ("new grad", "new-grad", "graduate", "university", "campus")):
        return "new_grad"
    if any(w in t for w in ("junior", "jr.", "jr ", "entry", "associate")):
        return "junior"
    if any(w in t for w in ("senior", "sr.", "sr ", "lead", "staff", "principal")):
        return "senior"
    if "mid" in t:
        return "mid"
    return "unknown"


def _infer_remote_policy(location: str, explicit: str | None, text: str) -> str:
    if explicit and explicit.lower() in ("remote", "hybrid", "onsite"):
        return explicit.lower()
    blob = f"{location} {text}".lower()
    if "hybrid" in blob:
        return "hybrid"
    if "remote" in blob:
        return "remote"
    if any(w in blob for w in ("on-site", "onsite", "in office", "in-office")):
        return "onsite"
    return "unknown"


def _infer_region(location: str, explicit: str | None, remote_policy: str, text: str) -> str:
    if explicit and explicit.lower() in ("turkey", "europe", "remote", "global"):
        return explicit.lower()
    blob = f"{location} {text}".lower()
    if any(t in blob for t in _TURKEY_TERMS):
        return "turkey"
    if any(t in blob for t in _WORLDWIDE_TERMS):
        return "global"
    if any(t in blob for t in _EMEA_TERMS) or any(t in blob for t in _EUROPE_TERMS):
        return "europe"
    if remote_policy == "remote":
        return "remote"
    return "unknown"


# ----- Turkey-applicability classifier (deterministic, conservative) -----

def classify_turkey_applicability(
    *, title="", description="", location="", remote_policy="unknown",
    country_scope=None, tags=None, work_auth_note=None, seniority="unknown",
    accepts_turkey_based=None,
) -> tuple[str, str]:
    """Return (label, reason). Conservative: never claims eligibility unless the
    text supports it."""
    blob = " ".join(
        str(x) for x in (title, description, location, country_scope, work_auth_note,
                         " ".join(tags or []))
    ).lower()

    # Explicit override wins.
    if accepts_turkey_based is True:
        return LABEL_STRONG, "The listing explicitly accepts Turkey-based candidates."
    if accepts_turkey_based is False:
        return LABEL_NO, "The listing explicitly excludes Turkey-based candidates."

    # --- Disqualifiers first ---
    if seniority in _SENIOR_LEVELS:
        return LABEL_NO, "Senior-level role; this feed targets junior/new-grad candidates."
    if any(t in blob for t in _US_AUTH_TERMS):
        return LABEL_NO, "Requires US work authorization / US-only — not workable from Turkey."
    if any(t in blob for t in _EU_CITIZEN_TERMS):
        return LABEL_NO, "Requires EU citizenship / EU right-to-work — Turkey isn't in the EU."
    onsite = remote_policy == "onsite"
    has_relocation = any(t in blob for t in _RELOCATION_TERMS)
    if onsite and not any(t in blob for t in _TURKEY_TERMS) and not has_relocation:
        return LABEL_NO, "On-site outside Turkey with no relocation/sponsorship mentioned."

    # --- Strong fit ---
    # Any Turkey location (Istanbul/Ankara/… or "Turkey") is a strong fit for a
    # Turkey-based candidate — including on-site roles (they're already here).
    if any(t in blob for t in _TURKEY_TERMS):
        return LABEL_STRONG, "Turkey-based role."
    if remote_policy == "remote":
        if any(t in blob for t in _WORLDWIDE_TERMS):
            return LABEL_STRONG, "Remote worldwide — open to Turkey-based candidates."
        if any(t in blob for t in _EMEA_TERMS):
            return LABEL_STRONG, "Remote within EMEA, which includes Turkey."
        if any(t in blob for t in _CONTRACTOR_TERMS):
            return LABEL_STRONG, "Remote and contractor-friendly — workable from Turkey."

    # --- Possibly eligible ---
    if remote_policy == "remote" and any(t in blob for t in _EUROPE_TERMS):
        return LABEL_POSSIBLE, "Remote in Europe — verify Turkey isn't excluded by country."
    if has_relocation:
        return LABEL_POSSIBLE, "Relocation/visa sponsorship mentioned — verify your eligibility."

    # --- Unclear ---
    if remote_policy == "remote":
        return LABEL_UNCLEAR, "Remote but region not specified — verify eligibility on the page."
    if not (location or "").strip():
        return LABEL_UNCLEAR, "Missing location / work-authorization details."
    return LABEL_UNCLEAR, "Eligibility for Turkey-based candidates is unclear — verify it yourself."


# ----- Normalization -----

def normalize_record(raw: dict, *, source: str, is_sample: bool) -> dict:
    """Turn a raw source record into normalized Opportunity column values."""
    title = (raw.get("title") or "").strip()
    company = (raw.get("company") or raw.get("company_name") or "").strip()
    location = (raw.get("location") or "").strip()
    description = (raw.get("description") or "").strip()
    tags = raw.get("tags") or raw.get("tags_json") or []
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except (ValueError, TypeError):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
    text = f"{description} {' '.join(tags)}"

    seniority = _infer_seniority(title, raw.get("seniority_level"))
    remote_policy = _infer_remote_policy(location, raw.get("remote_policy"), text)
    region = _infer_region(location, raw.get("target_region"), remote_policy, text)
    work_auth_note = raw.get("work_auth_note")
    country_scope = raw.get("country_scope")
    accepts = raw.get("accepts_turkey_based")

    label, reason = classify_turkey_applicability(
        title=title, description=description, location=location,
        remote_policy=remote_policy, country_scope=country_scope, tags=tags,
        work_auth_note=work_auth_note, seniority=seniority, accepts_turkey_based=accepts,
    )

    return {
        "source": source,
        "external_id": raw.get("external_id") or raw.get("slug") or raw.get("id"),
        "company": company or None,
        "title": title or None,
        "location": location or None,
        "url": raw.get("url") or None,
        "source_url": raw.get("source_url") or None,
        "target_region": region,
        "seniority_level": seniority,
        "remote_policy": remote_policy,
        "country_scope": country_scope,
        "accepts_turkey_based": accepts,
        "turkey_applicability_label": label,
        "turkey_applicability_reason": reason,
        "language_expectation": raw.get("language_expectation"),
        "work_auth_note": work_auth_note,
        "description": description or None,
        "tags_json": json.dumps(tags) if tags else None,
        "raw_source_json": json.dumps(raw)[:8000],
        "date_posted": raw.get("date_posted") or raw.get("created_at"),
        "is_sample": is_sample,
    }


def _upsert(db: Session, normalized: dict) -> bool:
    """Insert or update by (source, external_id). Returns True if newly created."""
    existing = None
    if normalized.get("external_id") is not None:
        existing = (
            db.query(Opportunity)
            .filter(
                Opportunity.source == normalized["source"],
                Opportunity.external_id == normalized["external_id"],
            )
            .first()
        )
    created = existing is None
    row = existing or Opportunity()
    for key, value in normalized.items():
        setattr(row, key, value)
    if created:
        row.date_seen = datetime.utcnow()
        db.add(row)
    return created


def import_records(db: Session, records: list[dict], *, source: str, is_sample: bool,
                   source_provider: str | None = None,
                   source_confidence: str | None = None) -> dict:
    created = updated = 0
    for raw in records:
        if not (raw.get("title") or raw.get("company") or raw.get("company_name")):
            continue
        normalized = normalize_record(raw, source=source, is_sample=is_sample)
        normalized["source_provider"] = source_provider or source
        normalized["source_confidence"] = source_confidence
        if _upsert(db, normalized):
            created += 1
        else:
            updated += 1
    db.commit()
    return {"created": created, "updated": updated,
            "total": db.query(Opportunity).count()}


# ----- Seed (curated sample) -----

def load_seed() -> list[dict]:
    try:
        data = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
        return data.get("jobs", [])
    except (OSError, ValueError):
        return []


def ensure_seeded(db: Session) -> None:
    """Insert the curated sample feed once, so the page is never empty in a demo."""
    if db.query(Opportunity).count() > 0:
        return
    jobs = load_seed()
    if jobs:
        import_records(db, jobs, source=SEED_SOURCE, is_sample=True,
                       source_provider="sample", source_confidence="sample_demo")


# ----- Public API adapter (Arbeitnow — public, no key) -----

ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"


def fetch_arbeitnow(limit: int = 50) -> list[dict]:
    """Fetch a page of public EU job-board listings. Network call lives ONLY here;
    callers wrap it so a failure never breaks the seeded feed."""
    import requests  # local import keeps the module importable/offline by default

    resp = requests.get(ARBEITNOW_URL, timeout=15,
                        headers={"User-Agent": "network-ai/0.1 (compliant feed)"})
    resp.raise_for_status()
    data = resp.json().get("data", [])[:limit]
    out = []
    for j in data:
        out.append({
            "external_id": j.get("slug"),
            "company": j.get("company_name"),
            "title": j.get("title"),
            "location": j.get("location"),
            "remote_policy": "remote" if j.get("remote") else None,
            "tags": (j.get("tags") or []) + (j.get("job_types") or []),
            "description": j.get("description") or "",
            "url": j.get("url"),
            "source_url": j.get("url"),
            "date_posted": j.get("created_at"),
        })
    return out


def refresh_public_sources(db: Session, limit: int = 50) -> dict:
    """Fetch + store public listings. Resilient: errors are reported, not raised,
    so the seeded feed keeps working."""
    errors: list[str] = []
    result = {"created": 0, "updated": 0}
    try:
        records = fetch_arbeitnow(limit=limit)
        result = import_records(db, records, source="arbeitnow", is_sample=False,
                                source_provider="arbeitnow", source_confidence="public_api")
    except Exception as exc:  # network/parse failure — degrade gracefully
        errors.append(f"arbeitnow: {type(exc).__name__}")
    return {**result, "errors": errors, "total": db.query(Opportunity).count()}


# ----- Official ATS adapters (public job-board APIs, no key, no scraping) -----
# Each is the API a company publishes to embed its OWN listings. The single
# network call per provider lives in a fetch_* function so the module stays
# importable/offline and tests can monkeypatch it.

import html as _html
import re as _re

_UA = {"User-Agent": "network-ai/0.1 (compliant feed)"}


def _strip_html(text: str) -> str:
    # Unescape entities FIRST (Greenhouse returns escaped HTML), then drop tags.
    return _re.sub(r"<[^>]+>", " ", _html.unescape(text or "")).strip()


def _ms_to_date(value) -> str | None:
    if isinstance(value, (int, float)):
        return datetime.utcfromtimestamp(value / 1000).date().isoformat()
    return None


# --- Lever ---

def fetch_lever(token: str) -> list[dict]:
    import requests
    resp = requests.get(f"https://api.lever.co/v0/postings/{token}?mode=json",
                        timeout=15, headers=_UA)
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else []


def _lever_to_record(posting: dict, company: str) -> dict:
    cats = posting.get("categories") or {}
    wt = (posting.get("workplaceType") or "").lower()
    remote_policy = {"on-site": "onsite", "remote": "remote", "hybrid": "hybrid"}.get(wt)
    location = (cats.get("location") or "").strip()
    if posting.get("country") == "TR" and "turkey" not in location.lower():
        location = f"{location}, Turkey".strip(", ")
    return {
        "external_id": posting.get("id"),
        "company": company,
        "title": posting.get("text"),
        "location": location,
        "remote_policy": remote_policy,
        "description": (posting.get("descriptionPlain") or "")[:4000],
        "tags": [t for t in (cats.get("team"), cats.get("commitment")) if t],
        "url": posting.get("hostedUrl") or posting.get("applyUrl"),
        "source_url": posting.get("hostedUrl"),
        "date_posted": _ms_to_date(posting.get("createdAt")),
    }


# --- Greenhouse ---

def fetch_greenhouse(token: str) -> list[dict]:
    import requests
    resp = requests.get(
        f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true",
        timeout=15, headers=_UA)
    resp.raise_for_status()
    return resp.json().get("jobs", [])


def _greenhouse_to_record(posting: dict, company: str) -> dict:
    loc = (posting.get("location") or {}).get("name") or ""
    depts = [d.get("name") for d in (posting.get("departments") or []) if d.get("name")]
    return {
        "external_id": str(posting.get("id")),
        "company": company,
        "title": posting.get("title"),
        "location": loc,
        "remote_policy": None,  # inferred from text by normalize_record
        "description": _strip_html(posting.get("content"))[:4000],
        "tags": depts,
        "url": posting.get("absolute_url"),
        "source_url": posting.get("absolute_url"),
        "date_posted": posting.get("updated_at"),
    }


# --- Ashby ---

def fetch_ashby(token: str) -> list[dict]:
    import requests
    resp = requests.get(
        f"https://api.ashbyhq.com/posting-api/job-board/{token}",
        timeout=15, headers=_UA)
    resp.raise_for_status()
    return resp.json().get("jobs", [])


def _ashby_to_record(posting: dict, company: str) -> dict:
    remote_policy = "remote" if posting.get("isRemote") else None
    tags = [t for t in (posting.get("team"), posting.get("department"),
                        posting.get("employmentType")) if t]
    return {
        "external_id": posting.get("id"),
        "company": company,
        "title": posting.get("title"),
        "location": posting.get("location") or "",
        "remote_policy": remote_policy,
        "description": (posting.get("descriptionPlain")
                        or _strip_html(posting.get("descriptionHtml")))[:4000],
        "tags": tags,
        "url": posting.get("jobUrl") or posting.get("applyUrl"),
        "source_url": posting.get("jobUrl"),
        "date_posted": posting.get("publishedAt") or posting.get("publishedDate"),
    }


# Supported ATS providers and their record-mappers. The fetcher is resolved by
# NAME at call time (via _provider_fetch) so tests can monkeypatch fetch_*.
_PROVIDER_MAPPERS = {
    "lever": _lever_to_record,
    "greenhouse": _greenhouse_to_record,
    "ashby": _ashby_to_record,
}


def _provider_fetch(provider: str, token: str) -> list[dict]:
    if provider == "lever":
        return fetch_lever(token)
    if provider == "greenhouse":
        return fetch_greenhouse(token)
    if provider == "ashby":
        return fetch_ashby(token)
    raise KeyError(provider)


# ----- Source registry (curated Turkish / Turkey-relevant companies) -----
# Only entries with a VERIFIED public ATS endpoint are enabled. Companies without
# a confirmed public token are kept disabled/manual (careers_url + notes) — we
# never invent board tokens. To enable one: confirm its board, set ats_provider +
# board_token, and flip enabled=True.

SOURCE_REGISTRY: list[dict] = [
    # --- Enabled: verified live public Lever boards ---
    {"id": "dreamgames", "company_name": "Dream Games", "ats_provider": "lever",
     "board_token": "dreamgames", "careers_url": "https://jobs.lever.co/dreamgames",
     "country_scope": "Turkey", "company_category": "Gaming", "priority": 1,
     "enabled": True, "source_confidence": "official_ats",
     "notes": "Verified live Lever board (Istanbul)."},
    {"id": "codeway", "company_name": "Codeway", "ats_provider": "lever",
     "board_token": "codeway", "careers_url": "https://jobs.lever.co/codeway",
     "country_scope": "Turkey", "company_category": "Consumer apps", "priority": 1,
     "enabled": True, "source_confidence": "official_ats",
     "notes": "Verified live Lever board (Istanbul/Barcelona)."},
    {"id": "commencis", "company_name": "Commencis", "ats_provider": "lever",
     "board_token": "commencis", "careers_url": "https://jobs.lever.co/commencis",
     "country_scope": "Turkey", "company_category": "Software/consulting", "priority": 2,
     "enabled": True, "source_confidence": "official_ats",
     "notes": "Verified live Lever board (Istanbul)."},
    # --- Disabled/manual: no verified public ATS endpoint (do NOT invent tokens) ---
    {"id": "trendyol", "company_name": "Trendyol", "ats_provider": "manual",
     "board_token": None, "careers_url": "https://careers.trendyol.com",
     "country_scope": "Turkey", "company_category": "E-commerce", "priority": 1,
     "enabled": False, "source_confidence": "manual_curated",
     "notes": "Uses own ATS; no public Lever/Greenhouse/Ashby token found."},
    {"id": "getir", "company_name": "Getir", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://getir.careers-page.com", "country_scope": "Turkey",
     "company_category": "Q-commerce", "priority": 1, "enabled": False,
     "source_confidence": "manual_curated", "notes": "careers-page.com ATS; no public API found."},
    {"id": "insider", "company_name": "Insider", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://insiderone.com/careers", "country_scope": "Turkey",
     "company_category": "MarTech", "priority": 1, "enabled": False,
     "source_confidence": "manual_curated", "notes": "Own careers site; no public token found."},
    {"id": "peak", "company_name": "Peak Games", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://www.peak.com/career", "country_scope": "Turkey",
     "company_category": "Gaming", "priority": 2, "enabled": False,
     "source_confidence": "manual_curated", "notes": "No public ATS token found."},
    {"id": "papara", "company_name": "Papara", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://www.papara.com/career", "country_scope": "Turkey",
     "company_category": "Fintech", "priority": 2, "enabled": False,
     "source_confidence": "manual_curated", "notes": "No public ATS token found."},
    {"id": "midas", "company_name": "Midas", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://www.getmidas.com/kariyer", "country_scope": "Turkey",
     "company_category": "Fintech", "priority": 2, "enabled": False,
     "source_confidence": "manual_curated", "notes": "No public ATS token found."},
    {"id": "hepsiburada", "company_name": "Hepsiburada", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://kariyer.hepsiburada.com", "country_scope": "Turkey",
     "company_category": "E-commerce", "priority": 2, "enabled": False,
     "source_confidence": "manual_curated", "notes": "Own ATS; no public API found."},
    {"id": "picus", "company_name": "Picus Security", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://www.picussecurity.com/careers-at-picus", "country_scope": "Global",
     "company_category": "Cybersecurity", "priority": 2, "enabled": False,
     "source_confidence": "manual_curated", "notes": "HubSpot-linked careers; no public ATS token found."},
    {"id": "marti", "company_name": "Martı", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://www.marti.tech/careers", "country_scope": "Turkey",
     "company_category": "Mobility", "priority": 3, "enabled": False,
     "source_confidence": "manual_curated", "notes": "No public ATS token found."},
    {"id": "armut", "company_name": "Armut / HomeRun", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://www.armut.com/kariyer", "country_scope": "Turkey",
     "company_category": "Marketplace", "priority": 3, "enabled": False,
     "source_confidence": "manual_curated", "notes": "No public ATS token found."},
    {"id": "mobileaction", "company_name": "MobileAction", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://www.mobileaction.co/careers", "country_scope": "Global",
     "company_category": "App analytics", "priority": 3, "enabled": False,
     "source_confidence": "manual_curated", "notes": "No public ATS token found."},
]


def list_sources() -> list[dict]:
    """The source registry with status — for GET /opportunities/sources."""
    return [
        {**s, "live": bool(s.get("enabled") and s.get("ats_provider") in _PROVIDER_MAPPERS)}
        for s in SOURCE_REGISTRY
    ]


def _refresh_one(db: Session, src: dict) -> dict:
    status = {"id": src["id"], "company": src["company_name"],
              "provider": src["ats_provider"], "jobs_imported": 0}
    provider = src.get("ats_provider")
    if not src.get("enabled") or provider not in _PROVIDER_MAPPERS:
        return {**status, "status": "skipped"}
    mapper = _PROVIDER_MAPPERS[provider]
    try:
        postings = _provider_fetch(provider, src["board_token"])
        records = [mapper(p, src["company_name"]) for p in postings]
        r = import_records(
            db, records, source=f'{src["ats_provider"]}:{src["board_token"]}',
            is_sample=False, source_provider=src["ats_provider"],
            source_confidence=src.get("source_confidence", "official_ats"),
        )
        return {**status, "status": "success",
                "jobs_imported": r["created"] + r["updated"], "created": r["created"]}
    except Exception as exc:  # one source failing never breaks the rest
        return {**status, "status": "failed", "error": type(exc).__name__}


def refresh_sources(db: Session) -> dict:
    """Refresh all ENABLED official ATS sources. Per-source status; resilient."""
    results = [_refresh_one(db, s) for s in SOURCE_REGISTRY]
    return {
        "sources": results,
        "created": sum(r.get("created", 0) for r in results),
        "succeeded": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
        "total": db.query(Opportunity).count(),
    }


def refresh_source(db: Session, source_id: str) -> dict | None:
    src = next((s for s in SOURCE_REGISTRY if s["id"] == source_id), None)
    if src is None:
        return None
    return _refresh_one(db, src)


# Back-compat alias (older endpoint/tests) — now refreshes the full registry.
def refresh_turkish_sources(db: Session) -> dict:
    result = refresh_sources(db)
    errors = [f'{r["id"]}: {r.get("error")}' for r in result["sources"] if r["status"] == "failed"]
    return {"created": result["created"], "updated": 0, "errors": errors,
            "total": result["total"]}


# ----- Filtering + ranking + serialization -----

def _tags(row: Opportunity) -> list[str]:
    try:
        return json.loads(row.tags_json) if row.tags_json else []
    except (ValueError, TypeError):
        return []


_CONFIDENCE_BONUS = {"official_ats": 12, "public_api": 6, "manual_curated": 3,
                     "sample_demo": 0, "unknown": 0}


def _score(row: Opportunity, profile_skills: set[str]) -> float:
    key = _LABEL_TO_KEY.get(row.turkey_applicability_label, "unclear")
    score = {"strong": 100, "possible": 60, "unclear": 30, "no": 0}[key]
    if row.seniority_level in _JUNIOR_LEVELS:
        score += 25
    elif row.seniority_level == "unknown":
        score += 8
    elif row.seniority_level == "mid":
        score += 4
    if row.target_region in ("turkey", "remote", "europe", "global"):
        score += 10
    score += _CONFIDENCE_BONUS.get(row.source_confidence or "unknown", 0)
    if profile_skills:
        overlap = len(profile_skills & {t.lower() for t in _tags(row)})
        score += min(20, 5 * overlap)
    return score


def serialize(row: Opportunity) -> dict:
    return {
        "id": row.id,
        "source": row.source,
        "company": row.company,
        "title": row.title,
        "location": row.location,
        "url": row.url,
        "source_url": row.source_url,
        "target_region": row.target_region,
        "seniority_level": row.seniority_level,
        "remote_policy": row.remote_policy,
        "country_scope": row.country_scope,
        "turkey_applicability_label": row.turkey_applicability_label,
        "turkey_applicability_reason": row.turkey_applicability_reason,
        "language_expectation": row.language_expectation,
        "work_auth_note": row.work_auth_note,
        "tags": _tags(row),
        "date_posted": row.date_posted,
        "is_sample": bool(row.is_sample),
        "source_provider": row.source_provider,
        "source_confidence": row.source_confidence,
        "outreach_prefill": outreach_prefill(row),
    }


def list_opportunities(
    db: Session, *, region=None, seniority=None, remote_only=False,
    applicability=None, tag=None, source=None, confidence=None,
    include_ineligible=False, profile_skills=None, limit=100,
) -> list[dict]:
    q = db.query(Opportunity)
    if region:
        q = q.filter(Opportunity.target_region == region)
    if seniority:
        q = q.filter(Opportunity.seniority_level == seniority)
    if remote_only:
        q = q.filter(Opportunity.remote_policy == "remote")
    if applicability and applicability in APPLICABILITY_KEYS:
        # Explicitly asking for a label shows exactly that label (incl. "no").
        q = q.filter(Opportunity.turkey_applicability_label == APPLICABILITY_KEYS[applicability])
    elif not include_ineligible:
        # Default: hide "Probably not eligible" (e.g. US-only / EU-citizenship-only).
        q = q.filter(Opportunity.turkey_applicability_label != LABEL_NO)
    if source:
        q = q.filter(Opportunity.source_provider == source)
    if confidence:
        q = q.filter(Opportunity.source_confidence == confidence)

    rows = q.all()
    if tag:
        tl = tag.lower()
        rows = [r for r in rows if any(tl == t.lower() for t in _tags(r))]

    skills = {s.lower() for s in (profile_skills or [])}
    rows.sort(
        key=lambda r: (_score(r, skills), r.date_seen or datetime.min),
        reverse=True,
    )
    return [serialize(r) for r in rows[:limit]]


# ----- Outreach integration -----

def outreach_prefill(row: Opportunity) -> dict:
    """Prefill payload for the /outreach copilot from an opportunity."""
    region = row.target_region if row.target_region in ("turkey", "europe", "remote", "global") else "remote"
    # Domestic Turkey roles default to Turkish; everything else to English.
    language = "tr" if region == "turkey" else "en"
    include_location_line = region in ("europe", "remote", "global")
    jd = row.description or ""
    if row.title or row.company:
        jd = f"{row.title or ''} at {row.company or ''}\n{jd}".strip()
    return {
        "company": row.company or "",
        "role": row.title or "",
        "jd_text": jd,
        "target_region": region,
        "language": language,
        "include_location_line": include_location_line,
    }
