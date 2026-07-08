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
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from . import resume_parser
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

# Job-function classification, so tech students and business students each see
# only what's relevant. Three buckets: software engineering, business (consulting/
# finance/marketing/PM/ops/HR…), and other (creative/admin/non-software-eng). The
# feed shows engineering + business by default and hides "other" noise.
FUNCTION_SWE = "software_engineering"
FUNCTION_BUSINESS = "business"
FUNCTION_OTHER = "other"
FUNCTION_KEYS = (FUNCTION_SWE, FUNCTION_BUSINESS, FUNCTION_OTHER)

# Strong, unambiguous engineering signals — these win even when another word is
# also present (e.g. "Software Engineer, Performance Marketing" is still SWE).
_SWE_STRONG_TERMS = (
    "software engineer", "software developer", "backend engineer", "back-end engineer",
    "backend developer", "frontend engineer", "front-end engineer", "frontend developer",
    "full stack", "full-stack", "fullstack", "web developer", "web engineer",
    "mobile developer", "mobile engineer", "ios developer", "ios engineer",
    "android developer", "android engineer", "devops", "site reliability", "sre",
    "platform engineer", "data engineer", "machine learning engineer", "ml engineer",
    "qa engineer", "test automation", "automation engineer", "security engineer",
    "backend", "frontend", "back-end", "front-end", "game developer", "game engineer",
    "programmer", "embedded software", "firmware", "swe", "sde",
)
# Creative / admin / non-software-engineering roles. Checked before business so a
# "Marketing Artist" reads as creative, not business.
_OTHER_TERMS = (
    "artist", "designer", "sound", "copywriter", "content", "community", "writer",
    "illustrator", "animator", "photographer", "video", "motion", "assistant",
    "receptionist", "office manager", "facilities", "concept", "mechanical",
    "civil", "chemical", "electrical", "industrial", "biomedical", "hardware",
    "scientist", "research",
)
# Business / commercial / corporate-function roles (what business students want).
_BUSINESS_TERMS = (
    "consult", "business analyst", "data analyst", "analyst", "business",
    "finance", "financial", "fp&a", "accountant", "accounting", "audit", "tax",
    "marketing", "sales", "solutions engineer", "solution engineer", "sales engineer",
    "support engineer", "customer engineer", "pre-sales", "presales",
    "account manager", "account executive", "business development", "strategy",
    "strategic", "operations", "product manager", "project manager", "program manager",
    "procurement", "supply chain", "commercial", "economist", "management trainee",
    "graduate program", "human resources", "recruit", "talent", "people partner",
    "hrbp", "legal", "counsel", "growth", "category manager", "customer success",
    "partnership", "investment", "banking", "associate consultant",
)
# Weak engineering signals — used only if nothing above matched.
_SWE_WEAK_TERMS = ("engineer", "developer", "engineering")


def classify_job_function(title: str = "", tags=None) -> str:
    """Return FUNCTION_SWE / FUNCTION_BUSINESS / FUNCTION_OTHER from title + tags.

    Deliberately ignores the JD body (prose causes false positives). Order is
    chosen so strong engineering wins first, then creative/admin, then business,
    then a weak engineering fallback; anything unmatched is "other"."""
    blob = " ".join([title or "", " ".join(str(t) for t in (tags or []))]).lower()
    if any(t in blob for t in _SWE_STRONG_TERMS):
        return FUNCTION_SWE
    if any(t in blob for t in _OTHER_TERMS):
        return FUNCTION_OTHER
    if any(t in blob for t in _BUSINESS_TERMS):
        return FUNCTION_BUSINESS
    if any(t in blob for t in _SWE_WEAK_TERMS):
        return FUNCTION_SWE
    return FUNCTION_OTHER

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
# US/North-America-scoped LOCATIONS (not work-auth phrasing). Matched only against
# the location + country_scope fields (never the description) to avoid false hits
# from words like "usability". A Turkey-based junior can't take these unless the
# role is also worldwide/EMEA/Europe/Turkey-open.
_US_LOCATION_TERMS = (
    "united states", "usa", "u.s.a", "u.s.", "us-based", "u.s based",
    "north america", "americas only", "us remote", "remote us", "remote - us",
    "remote, us", "remote (us", "us only", "u.s. only",
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

# Description-level signals, consulted ONLY when the title is neutral. Kept to
# unambiguous phrases (incl. Turkish) — prose like "work with senior engineers"
# must not flip a label, so there is no senior detection from the body.
_NEW_GRAD_TEXT_TERMS = ("new grad", "new-grad", "recent graduate", "fresh graduate",
                        "yeni mezun", "üniversite son sınıf")
_JUNIOR_TEXT_TERMS = ("entry level", "entry-level", "0-1 year", "0–1 year",
                      "0-2 year", "0–2 year", "no prior experience",
                      "no previous experience", "junior")
_INTERN_TEXT_TERMS = ("internship", "intern position", "stajyer", "staj programı")


def _infer_seniority(title: str, explicit: str | None, text: str = "") -> str:
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
    # Neutral title (e.g. plain "Software Engineer") — look for explicit
    # junior-friendly phrases in the JD body before giving up. Most sources
    # put "new grad" / "yeni mezun" / "0-2 years" in the description, not the
    # title, which starved the New grad / Junior tabs.
    blob = (text or "").lower()
    if blob:
        if any(w in blob for w in _NEW_GRAD_TEXT_TERMS):
            return "new_grad"
        if any(w in blob for w in _INTERN_TEXT_TERMS):
            return "internship"
        if any(w in blob for w in _JUNIOR_TEXT_TERMS):
            return "junior"
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
    # US/North-America-located roles are hidden by default (this feed is Turkey →
    # remote/EU). Checked on location + scope only, and skipped when the role is
    # also open worldwide/EMEA/Europe/Turkey (e.g. a US company hiring "Worldwide").
    loc_blob = " ".join(str(x) for x in (location, country_scope)).lower()
    broadly_open = any(
        t in loc_blob
        for t in (_WORLDWIDE_TERMS + _EMEA_TERMS + _EUROPE_TERMS + _TURKEY_TERMS)
    )
    if any(t in loc_blob for t in _US_LOCATION_TERMS) and not broadly_open:
        return LABEL_NO, "US/North-America-based location — not workable from Turkey."
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

    seniority = _infer_seniority(title, raw.get("seniority_level"), text)
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
        "job_function": classify_job_function(title=title, tags=tags),
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
    """Fetch public EU job-board listings, paginating until `limit` is reached
    (the API serves ~100 per page). Network call lives ONLY here; callers wrap
    it so a failure never breaks the seeded feed."""
    import requests  # local import keeps the module importable/offline by default

    data: list[dict] = []
    page = 1
    while len(data) < limit and page <= 5:
        resp = requests.get(ARBEITNOW_URL, params={"page": page}, timeout=15,
                            headers={"User-Agent": "network-ai/0.1 (compliant feed)"})
        resp.raise_for_status()
        batch = resp.json().get("data", [])
        if not batch:
            break
        data.extend(batch)
        page += 1
    data = data[:limit]
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


def refresh_public_sources(db: Session, limit: int = 200) -> dict:
    """Fetch + store public remote/EU listings (Arbeitnow + Remotive + Jobicy —
    all keyless public APIs, no scraping). Resilient: each feed is independent, so
    one failing reports an error and the others (and the seeded feed) keep working.

    Per each provider's public-API terms, listings are attributed to the source
    (source_provider) and link back to the original posting (url/source_url)."""
    errors: list[str] = []
    created = updated = 0

    def _store(name: str, records: list[dict]) -> None:
        nonlocal created, updated
        r = import_records(db, records, source=name, is_sample=False,
                           source_provider=name, source_confidence="public_api")
        created += r["created"]
        updated += r["updated"]

    try:
        _store("arbeitnow", fetch_arbeitnow(limit=limit))
    except Exception as exc:  # network/parse failure — degrade gracefully
        errors.append(f"arbeitnow: {type(exc).__name__}")
    try:
        _store("remotive", [_remotive_to_record(j) for j in fetch_remotive(limit=limit)])
    except Exception as exc:
        errors.append(f"remotive: {type(exc).__name__}")
    try:
        # Jobicy's public API caps `count` at 50 per request.
        _store("jobicy", [_jobicy_to_record(j) for j in fetch_jobicy(count=min(limit, 50))])
    except Exception as exc:
        errors.append(f"jobicy: {type(exc).__name__}")

    return {"created": created, "updated": updated, "errors": errors,
            "total": db.query(Opportunity).count()}


# --- Remotive (public remote-job API, no key; remote-only listings) ---

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"


def fetch_remotive(limit: int = 50, category: str = "software-dev") -> list[dict]:
    """Fetch a page of Remotive's public remote jobs (defaults to the software
    category). Network call lives ONLY here so callers can degrade gracefully."""
    import requests

    params: dict = {"limit": limit}
    if category:
        params["category"] = category
    resp = requests.get(REMOTIVE_URL, params=params, timeout=15, headers=_UA)
    resp.raise_for_status()
    return resp.json().get("jobs", [])[:limit]


def _remotive_to_record(j: dict) -> dict:
    loc = (j.get("candidate_required_location") or "").strip()
    tags = list(j.get("tags") or [])
    if j.get("category"):
        tags.append(j["category"])
    return {
        "external_id": str(j.get("id")) if j.get("id") is not None else j.get("url"),
        "company": j.get("company_name"),
        "title": j.get("title"),
        "location": loc,
        "country_scope": loc or None,          # "Worldwide"/"EMEA"/… → classifier
        "remote_policy": "remote",             # Remotive is remote-only
        "description": _strip_html(j.get("description"))[:4000],
        "tags": tags,
        "url": j.get("url"),
        "source_url": j.get("url"),
        "date_posted": j.get("publication_date") or j.get("created_at"),
    }


# --- Jobicy (public remote-job API, no key; remote-only listings) ---

JOBICY_URL = "https://jobicy.com/api/v2/remote-jobs"


def fetch_jobicy(count: int = 50, geo: str | None = None,
                 industry: str = "dev") -> list[dict]:
    """Fetch a page of Jobicy's public remote jobs (defaults to the dev industry).
    Network call lives ONLY here so callers can degrade gracefully."""
    import requests

    params: dict = {"count": count}
    if geo:
        params["geo"] = geo
    if industry:
        params["industry"] = industry
    resp = requests.get(JOBICY_URL, params=params, timeout=15, headers=_UA)
    resp.raise_for_status()
    return resp.json().get("jobs", [])[:count]


def _jobicy_to_record(j: dict) -> dict:
    geo = (j.get("jobGeo") or "").strip()
    industry = j.get("jobIndustry") or []
    jtype = j.get("jobType") or []
    if isinstance(industry, str):
        industry = [industry]
    if isinstance(jtype, str):
        jtype = [jtype]
    desc = j.get("jobDescription") or j.get("jobExcerpt") or ""
    return {
        "external_id": str(j.get("id")) if j.get("id") is not None else j.get("url"),
        "company": j.get("companyName"),
        "title": j.get("jobTitle"),
        "location": geo,
        "country_scope": geo or None,          # "Worldwide"/"Europe"/… → classifier
        "remote_policy": "remote",             # Jobicy is remote-only
        "seniority_level": (j.get("jobLevel") or "").lower() or None,
        "description": _strip_html(desc)[:4000],
        "tags": [str(x) for x in (industry + jtype)],
        "url": j.get("url"),
        "source_url": j.get("url"),
        "date_posted": j.get("pubDate"),
    }


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
    # --- Enabled: verified live Lever boards (identity confirmed by location, not
    # just an HTTP 200 — namesake tokens like a US "Peak" clinic were rejected) ---
    {"id": "trendyol", "company_name": "Trendyol", "ats_provider": "lever",
     "board_token": "trendyol", "careers_url": "https://careers.trendyol.com",
     "country_scope": "Turkey", "company_category": "E-commerce", "priority": 1,
     "enabled": True, "source_confidence": "official_ats",
     "notes": "Verified live Lever board (Istanbul/Kocaeli; some Gulf roles)."},
    {"id": "getir", "company_name": "Getir", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://getir.careers-page.com", "country_scope": "Turkey",
     "company_category": "Q-commerce", "priority": 1, "enabled": False,
     "source_confidence": "manual_curated", "notes": "careers-page.com ATS; no public API found."},
    {"id": "insider", "company_name": "Insider", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://insiderone.com/careers", "country_scope": "Turkey",
     "company_category": "MarTech", "priority": 1, "enabled": False,
     "source_confidence": "manual_curated", "notes": "Own careers site; no public token found."},
    {"id": "peak", "company_name": "Peak Games", "ats_provider": "lever",
     "board_token": "peakgames", "careers_url": "https://www.peak.com/career",
     "country_scope": "Turkey", "company_category": "Gaming", "priority": 2,
     "enabled": True, "source_confidence": "official_ats",
     "notes": "Verified live Lever board (Istanbul). NB: greenhouse 'peak' is an unrelated US clinic."},
    {"id": "papara", "company_name": "Papara", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://www.papara.com/career", "country_scope": "Turkey",
     "company_category": "Fintech", "priority": 2, "enabled": False,
     "source_confidence": "manual_curated", "notes": "No public ATS token found."},
    {"id": "midas", "company_name": "Midas", "ats_provider": "lever",
     "board_token": "getmidas", "careers_url": "https://www.getmidas.com/kariyer",
     "country_scope": "Turkey", "company_category": "Fintech", "priority": 2,
     "enabled": True, "source_confidence": "official_ats",
     "notes": "Verified live Lever board (Istanbul)."},
    {"id": "hepsiburada", "company_name": "Hepsiburada", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://kariyer.hepsiburada.com", "country_scope": "Turkey",
     "company_category": "E-commerce", "priority": 2, "enabled": False,
     "source_confidence": "manual_curated", "notes": "Own ATS; no public API found."},
    {"id": "picus", "company_name": "Picus Security", "ats_provider": "lever",
     "board_token": "picus", "careers_url": "https://www.picussecurity.com/careers-at-picus",
     "country_scope": "Global", "company_category": "Cybersecurity", "priority": 2,
     "enabled": True, "source_confidence": "official_ats",
     "notes": "Verified live Lever board (Ankara HQ; some EU/US roles, filtered by applicability)."},
    {"id": "goodjobgames", "company_name": "Good Job Games", "ats_provider": "greenhouse",
     "board_token": "goodjobgames", "careers_url": "https://www.goodjobgames.com/career/",
     "country_scope": "Turkey", "company_category": "Gaming", "priority": 2,
     "enabled": True, "source_confidence": "official_ats",
     "notes": "Verified live Greenhouse board (Istanbul/Sarıyer, all roles Turkey-located) — 2026-07-08."},
    {"id": "iyzico", "company_name": "iyzico", "ats_provider": "lever",
     "board_token": "iyzico", "careers_url": "https://jobs.lever.co/iyzico",
     "country_scope": "Turkey", "company_category": "Fintech", "priority": 2,
     "enabled": True, "source_confidence": "official_ats",
     "notes": "Verified live Lever board (Istanbul) — 2026-07-01."},
    # --- Enabled: verified strong EU / global-remote employers (Turkey → remote/EU
    # wedge). Identity confirmed by sample job locations at verification time;
    # US-only roles are hidden by the conservative applicability classifier. ---
    {"id": "canonical", "company_name": "Canonical", "ats_provider": "greenhouse",
     "board_token": "canonical", "careers_url": "https://canonical.com/careers",
     "country_scope": "Global", "company_category": "Open-source software", "priority": 1,
     "enabled": True, "source_confidence": "official_ats",
     "notes": "Verified live Greenhouse board — remote-first, hires 'Home based - EMEA' (includes Turkey) — 2026-07-01."},
    {"id": "remotecom", "company_name": "Remote.com", "ats_provider": "greenhouse",
     "board_token": "remotecom", "careers_url": "https://remote.com/careers",
     "country_scope": "Global", "company_category": "HR tech (remote-first)", "priority": 1,
     "enabled": True, "source_confidence": "official_ats",
     "notes": "Verified live Greenhouse board — 'Remote-EMEA' roles — 2026-07-01."},
    {"id": "gitlab", "company_name": "GitLab", "ats_provider": "greenhouse",
     "board_token": "gitlab", "careers_url": "https://about.gitlab.com/jobs/",
     "country_scope": "Global", "company_category": "DevTools (remote-first)", "priority": 1,
     "enabled": True, "source_confidence": "official_ats",
     "notes": "Verified live Greenhouse board — all-remote company — 2026-07-01."},
    {"id": "spotify", "company_name": "Spotify", "ats_provider": "lever",
     "board_token": "spotify", "careers_url": "https://www.lifeatspotify.com/jobs",
     "country_scope": "Europe", "company_category": "Consumer tech", "priority": 1,
     "enabled": True, "source_confidence": "official_ats",
     "notes": "Verified live Lever board (Stockholm/London + EU) — 2026-07-01."},
    {"id": "adyen", "company_name": "Adyen", "ats_provider": "greenhouse",
     "board_token": "adyen", "careers_url": "https://careers.adyen.com",
     "country_scope": "Europe", "company_category": "Fintech", "priority": 1,
     "enabled": True, "source_confidence": "official_ats",
     "notes": "Verified live Greenhouse board (Amsterdam HQ) — 2026-07-01."},
    {"id": "n26", "company_name": "N26", "ats_provider": "greenhouse",
     "board_token": "n26", "careers_url": "https://n26.com/en/careers",
     "country_scope": "Europe", "company_category": "Fintech", "priority": 2,
     "enabled": True, "source_confidence": "official_ats",
     "notes": "Verified live Greenhouse board (Berlin/Barcelona/Paris) — 2026-07-01."},
    {"id": "hellofresh", "company_name": "HelloFresh", "ats_provider": "greenhouse",
     "board_token": "hellofresh", "careers_url": "https://careers.hellofresh.com",
     "country_scope": "Europe", "company_category": "E-commerce", "priority": 2,
     "enabled": True, "source_confidence": "official_ats",
     "notes": "Verified live Greenhouse board (Berlin HQ + global) — 2026-07-01."},
    {"id": "celonis", "company_name": "Celonis", "ats_provider": "greenhouse",
     "board_token": "celonis", "careers_url": "https://www.celonis.com/careers/",
     "country_scope": "Europe", "company_category": "Enterprise software", "priority": 2,
     "enabled": True, "source_confidence": "official_ats",
     "notes": "Verified live Greenhouse board (Munich HQ) — 2026-07-01."},
    {"id": "doctolib", "company_name": "Doctolib", "ats_provider": "greenhouse",
     "board_token": "doctolib", "careers_url": "https://careers.doctolib.com",
     "country_scope": "Europe", "company_category": "Health tech", "priority": 2,
     "enabled": True, "source_confidence": "official_ats",
     "notes": "Verified live Greenhouse board (Paris/Berlin) — 2026-07-01."},
    {"id": "bitpanda", "company_name": "Bitpanda", "ats_provider": "greenhouse",
     "board_token": "bitpanda", "careers_url": "https://www.bitpanda.com/en/career",
     "country_scope": "Europe", "company_category": "Fintech", "priority": 2,
     "enabled": True, "source_confidence": "official_ats",
     "notes": "Verified live Greenhouse board (Vienna HQ) — 2026-07-01."},
    {"id": "typeform", "company_name": "Typeform", "ats_provider": "greenhouse",
     "board_token": "typeform", "careers_url": "https://www.typeform.com/careers/",
     "country_scope": "Europe", "company_category": "SaaS", "priority": 2,
     "enabled": True, "source_confidence": "official_ats",
     "notes": "Verified live Greenhouse board (Barcelona; 'Germany (Remote)' style roles) — 2026-07-01."},
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
    # --- Most-desired employers (directory only). These use custom career sites
    # with NO public ATS API and scraping is prohibited, so they are listed as
    # curated careers links — no jobs are fetched. Enable one only if a verified
    # public ATS board (Lever/Greenhouse/Ashby/Workable) is confirmed. ---
    {"id": "mckinsey", "company_name": "McKinsey & Company", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://www.mckinsey.com/careers/search-jobs", "country_scope": "Turkey",
     "company_category": "Consulting (MBB)", "priority": 1, "enabled": False,
     "source_confidence": "manual_curated", "notes": "Custom careers site; no public ATS API — directory link only."},
    {"id": "bcg", "company_name": "Boston Consulting Group", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://careers.bcg.com", "country_scope": "Turkey",
     "company_category": "Consulting (MBB)", "priority": 1, "enabled": False,
     "source_confidence": "manual_curated", "notes": "Custom careers site; no public ATS API — directory link only."},
    {"id": "bain", "company_name": "Bain & Company", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://www.bain.com/careers/find-a-role/", "country_scope": "Turkey",
     "company_category": "Consulting (MBB)", "priority": 1, "enabled": False,
     "source_confidence": "manual_curated", "notes": "Custom careers site; no public ATS API — directory link only."},
    {"id": "google", "company_name": "Google (Turkey)", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://www.google.com/about/careers/applications/jobs/results/?location=Turkey",
     "country_scope": "Turkey", "company_category": "Big Tech", "priority": 1, "enabled": False,
     "source_confidence": "manual_curated", "notes": "Custom careers site; scraping prohibited — directory link only."},
    {"id": "amazon", "company_name": "Amazon (Turkey)", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://www.amazon.jobs/en/locations/turkey", "country_scope": "Turkey",
     "company_category": "Big Tech", "priority": 1, "enabled": False,
     "source_confidence": "manual_curated", "notes": "Custom careers site; scraping prohibited — directory link only."},
    {"id": "microsoft", "company_name": "Microsoft (Turkey)", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://jobs.careers.microsoft.com/global/en/search?lc=Turkey", "country_scope": "Turkey",
     "company_category": "Big Tech", "priority": 1, "enabled": False,
     "source_confidence": "manual_curated", "notes": "Custom careers site; no public ATS API — directory link only."},
    {"id": "isbank", "company_name": "Türkiye İş Bankası", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://www.isbank.com.tr/en/about-isbank/career", "country_scope": "Turkey",
     "company_category": "Banking", "priority": 1, "enabled": False,
     "source_confidence": "manual_curated", "notes": "Own careers portal; no public ATS API — directory link only."},
    {"id": "garantibbva", "company_name": "Garanti BBVA", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://www.garantibbvakariyer.com", "country_scope": "Turkey",
     "company_category": "Banking", "priority": 2, "enabled": False,
     "source_confidence": "manual_curated", "notes": "Own careers portal; no public ATS API — directory link only."},
    {"id": "akbank", "company_name": "Akbank", "ats_provider": "manual", "board_token": None,
     "careers_url": "https://www.akbank.com/tr-tr/kariyer", "country_scope": "Turkey",
     "company_category": "Banking", "priority": 2, "enabled": False,
     "source_confidence": "manual_curated", "notes": "Own careers portal; no public ATS API — directory link only."},
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


def reclassify_stored(db: Session) -> int:
    """Re-run seniority inference (and, when it changes, the applicability
    label) over every stored row. Refreshing only overwrites rows still served
    by their source, so classifier improvements would otherwise never reach
    older/delisted rows. Returns how many rows changed."""
    changed = 0
    for row in db.query(Opportunity).all():
        try:
            raw = json.loads(row.raw_source_json or "{}")
        except (ValueError, TypeError):
            raw = {}
        tags = _tags(row)
        text = f"{row.description or ''} {' '.join(tags)}"
        seniority = _infer_seniority(row.title or "", raw.get("seniority_level"), text)
        if seniority == row.seniority_level:
            continue
        row.seniority_level = seniority
        row.turkey_applicability_label, row.turkey_applicability_reason = (
            classify_turkey_applicability(
                title=row.title or "", description=row.description or "",
                location=row.location or "", remote_policy=row.remote_policy or "unknown",
                country_scope=row.country_scope, tags=tags,
                work_auth_note=row.work_auth_note, seniority=seniority,
                accepts_turkey_based=row.accepts_turkey_based,
            )
        )
        changed += 1
    if changed:
        db.commit()
    return changed


def refresh_all(db: Session) -> dict:
    """Refresh everything in one action: official ATS sources (Lever/Greenhouse/
    Ashby) AND public job APIs (Arbeitnow/Remotive/Jobicy), then re-run the
    classifier over stored rows so older listings pick up inference fixes.
    Each part is independently resilient, so one failing source never breaks
    the others."""
    ats = refresh_sources(db)
    public = refresh_public_sources(db)
    public_errors = public.get("errors", [])
    return {
        "created": ats["created"] + public["created"],
        "succeeded": ats["succeeded"],
        "failed": ats["failed"] + len(public_errors),
        "skipped": ats["skipped"],
        "errors": public_errors,
        "ats": ats,
        "public": public,
        "reclassified": reclassify_stored(db),
        "total": db.query(Opportunity).count(),
    }


# Back-compat alias (older endpoint/tests) — now refreshes the full registry.
def refresh_turkish_sources(db: Session) -> dict:
    result = refresh_sources(db)
    errors = [f'{r["id"]}: {r.get("error")}' for r in result["sources"] if r["status"] == "failed"]
    return {"created": result["created"], "updated": 0, "errors": errors,
            "total": result["total"]}


# ----- Filtering + ranking + serialization -----

def parse_posted_date(raw) -> datetime | None:
    """Best-effort parse of the raw `date_posted` string into naive UTC.

    Sources disagree on format: Arbeitnow stores epoch seconds, Lever a bare
    date, Greenhouse/Remotive/Jobicy ISO datetimes with or without an offset.
    Unparseable/missing values return None (treated as "date unknown")."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s.isdigit():  # epoch seconds (Arbeitnow)
        try:
            return datetime.utcfromtimestamp(int(s))
        except (ValueError, OverflowError, OSError):
            return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _posted_within(row: Opportunity, days: int) -> bool:
    posted = parse_posted_date(row.date_posted)
    if posted is None:
        return False  # a freshness filter should never surface undated roles
    return posted >= datetime.utcnow() - timedelta(days=days)


def _tags(row: Opportunity) -> list[str]:
    try:
        return json.loads(row.tags_json) if row.tags_json else []
    except (ValueError, TypeError):
        return []


def _function(row: Opportunity) -> str:
    """Stored job_function, computed on the fly for legacy rows (pre-migration)."""
    return getattr(row, "job_function", None) or classify_job_function(
        title=row.title or "", tags=_tags(row)
    )


_CONFIDENCE_BONUS = {"official_ats": 12, "public_api": 6, "manual_curated": 3,
                     "sample_demo": 0, "unknown": 0}


def _searchable_text(row: Opportunity) -> str:
    """Title + description + tags, lowercased — the haystack for skill matching.

    Scans the JD body (not just tags) so a Python role with no "python" tag
    still matches a Python resume."""
    return " ".join(
        filter(None, [row.title or "", row.description or "", " ".join(_tags(row))])
    ).lower()


def _match_reason(matched: list[str], total: int) -> str:
    if not matched:
        return "No overlap with your listed skills yet — verify fit on the role page."
    shown = ", ".join(matched[:4])
    extra = len(matched) - 4
    if extra > 0:
        shown += f" +{extra} more"
    return f"Matches {len(matched)} of your {total} skills: {shown}"


def skill_match(row: Opportunity, profile_skills) -> dict:
    """Which of the user's OWN skills this role emphasizes (token-aware over the
    title, description, and tags). Never invents skills — only reports overlap —
    and returns matched/missing plus a short human reason for the card. Empty
    (reason=None) when no profile is saved."""
    skills = [s for s in (profile_skills or []) if s]
    if not skills:
        return {"matched_skills": [], "missing_skills": [], "matched_count": 0,
                "total_skills": 0, "reason": None}
    text = _searchable_text(row)
    matched = [s for s in skills if resume_parser.skill_in_text(s, text)]
    missing = [s for s in skills if s not in matched]
    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "matched_count": len(matched),
        "total_skills": len(skills),
        "reason": _match_reason(matched, len(skills)),
    }


def _score(row: Opportunity, profile_skills) -> float:
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
        overlap = skill_match(row, profile_skills)["matched_count"]
        score += min(25, 5 * overlap)
    return score


def serialize(row: Opportunity, profile_skills=None) -> dict:
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
        "job_function": _function(row),
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
        "match": skill_match(row, profile_skills),
    }


def list_opportunities(
    db: Session, *, region=None, seniority=None, remote_only=False,
    applicability=None, tag=None, source=None, confidence=None, function=None,
    posted_within_days=None, include_ineligible=False, profile_skills=None,
    limit=100,
) -> list[dict]:
    q = db.query(Opportunity)
    # Real users must never mistake the demo seed for real roles: once any real
    # listing exists, sample rows are hidden unless explicitly requested via
    # confidence=sample_demo. (An all-sample DB still shows them so a fresh
    # local demo is never empty.)
    has_real = (
        db.query(Opportunity.id).filter(Opportunity.is_sample.isnot(True)).first()
        is not None
    )
    if has_real and confidence != "sample_demo":
        q = q.filter(Opportunity.is_sample.isnot(True))
    if region:
        q = q.filter(Opportunity.target_region == region)
    if seniority:
        # "entry_level" groups new-grad + junior: in practice each applies to the
        # other's roles, and the split made the feed look emptier than it is.
        if seniority == "entry_level":
            q = q.filter(Opportunity.seniority_level.in_(("new_grad", "junior")))
        else:
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
    # Freshness filter (Python-side: date_posted is a raw string with
    # per-source formats — see parse_posted_date).
    if posted_within_days:
        rows = [r for r in rows if _posted_within(r, posted_within_days)]
    # Function filter (computed lazily so legacy rows filter too):
    #   "all" (default) → engineering + business, hides creative/admin "other"
    #   "software_engineering" / "business" / "other" → exactly that bucket
    #   "any" → no filter at all
    if function and function != "any":
        if function == "all":
            rows = [r for r in rows if _function(r) in (FUNCTION_SWE, FUNCTION_BUSINESS)]
        else:
            rows = [r for r in rows if _function(r) == function]

    skills = [s for s in (profile_skills or []) if s]
    rows.sort(
        key=lambda r: (_score(r, skills), r.date_seen or datetime.min),
        reverse=True,
    )
    return [serialize(r, profile_skills=skills) for r in rows[:limit]]


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
        "id": row.id,
        "company": row.company or "",
        "role": row.title or "",
        "jd_text": jd,
        "url": row.url or "",
        "target_region": region,
        "language": language,
        "include_location_line": include_location_line,
    }
