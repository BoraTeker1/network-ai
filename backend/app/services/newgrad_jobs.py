"""newgrad-jobs.com ingestion adapter.

A second, opt-in job source alongside the SimplifyJobs adapter
(`job_ingestion.py`). It follows the same shape — `fetch` → `parse` → upsert
deduplicated `Job` rows — so the rest of the app (matcher, strategy, UI) treats
both sources identically.

Compliance / honesty (these are product features, not limitations):
- Only pages on newgrad-jobs.com are fetched. We never touch LinkedIn, Indeed,
  Handshake, or any other protected board. The apply link a posting points to is
  preserved verbatim but never crawled.
- robots.txt (checked 2026-06) is `User-agent: * / Allow: /` (only Bytespider is
  disallowed); we send a plain, honest User-Agent and stay well within it.
- Conservative: requests are rate-limited (`request_delay`) and capped per
  category (`max_per_category`). No browser automation, no anti-bot bypass.
- Apply URLs frequently route through an aggregator (e.g. jobright.ai), so we do
  NOT claim a posting is "official" — `external_apply_url` is surfaced as-is and
  `apply_is_company_ats` is only true when the link is clearly a company ATS.

Most detail pages on this site are already marked "This job has closed."; those
are skipped (and any matching stored row is flagged `is_closed=True`).
"""

import hashlib
import html as _html
import json
import re
import time
from datetime import datetime

import requests
from sqlalchemy.orm import Session

from ..models import Job

SOURCE = "newgrad-jobs.com"
BASE_URL = "https://www.newgrad-jobs.com"

# Categories to ingest first. Missing categories (e.g. /list-it-support, which
# does not currently exist) are handled gracefully — they're recorded as a
# non-fatal error, never a crash.
DEFAULT_CATEGORY_PATHS = (
    "/list-software-engineer-jobs",
    "/list-data-science",
    "/list-cyber-security",
    "/list-it-support",
)

CLOSED_MARKER = "this job has closed"

# Known controlled vocabularies used to pick chips out of the detail page.
_EMPLOYMENT_TYPES = {
    "full-time", "part-time", "internship", "contract", "temporary",
    "full time", "part time",
}
_WORK_MODES = {"onsite", "on-site", "remote", "hybrid"}
_LEVELS = {
    "entry level", "new grad", "new graduate", "associate", "mid level",
    "senior level", "internship",
}
_SECTION_HEADS = {"responsibilities", "qualification", "qualifications", "benefits"}
# Lines that mark the start of the post-benefits "about the company" footer.
_FOOTER_MARKERS = ("similar jobs", "glassdoor", "founded in", "operates as")

_DATE_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+\d{1,2},\s+\d{4}\b"
)
_SALARY_RE = re.compile(r"\$\s?\d")
# Hostnames we treat as real company ATS / career sites (apply link is official).
_ATS_HOST_RE = re.compile(
    r"(myworkdayjobs\.com|greenhouse\.io|lever\.co|icims\.com|taleo\.net|"
    r"successfactors\.com|workday\.com|ashbyhq\.com|smartrecruiters\.com|"
    r"jobs\.[\w.-]+|careers\.[\w.-]+)",
    re.IGNORECASE,
)


# ----- HTTP -----

def fetch(url: str) -> str:
    """Download a page. Raises requests.RequestException on failure."""
    resp = requests.get(url, timeout=30, headers={"User-Agent": "network-ai/0.1"})
    resp.raise_for_status()
    return resp.text


# ----- Parsing helpers -----

def _clean(text: str) -> str:
    return _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))).strip()


def _visible_lines(page: str) -> list[str]:
    """Ordered, de-duplicated visible text segments (scripts/styles/nav removed)."""
    h = re.sub(r"<script.*?</script>", " ", page, flags=re.DOTALL | re.IGNORECASE)
    h = re.sub(r"<style.*?</style>", " ", h, flags=re.DOTALL | re.IGNORECASE)
    h = re.sub(r"<nav.*?</nav>", " ", h, flags=re.DOTALL | re.IGNORECASE)
    out: list[str] = []
    for m in re.finditer(r">([^<>]+)<", h):
        t = _html.unescape(m.group(1)).strip()
        if t and not t.lower().startswith("http"):
            if not out or out[-1] != t:
                out.append(t)
    return out


def _company_from_slug(detail_url: str) -> str | None:
    """Fallback company from the detail slug `..._at_<company>_<id>`."""
    slug = detail_url.rstrip("/").rsplit("/", 1)[-1]
    m = re.search(r"_at_([a-z0-9]+(?:_[a-z0-9]+)*)_\d+$", slug)
    if not m:
        return None
    return m.group(1).replace("_", " ").strip().title() or None


def parse_category(page: str, category_path: str) -> list[dict]:
    """Extract job cards (detail url + title/company hints) from a category page.

    Returns a list of {"url", "title", "company"} dicts. Only links under the
    given category path are returned, de-duplicated, order preserved.
    """
    prefix = re.escape(category_path.rstrip("/"))
    results: list[dict] = []
    seen: set[str] = set()
    # Each posting is a Webflow "w-dyn-item" card; split so title/company stay
    # associated with their own link.
    for chunk in re.split(r"w-dyn-item", page):
        m = re.search(rf'href="({prefix}/[^"#]+)"', chunk)
        if not m:
            continue
        path = _html.unescape(m.group(1))
        if path in seen or path.rstrip("/") == category_path.rstrip("/"):
            continue
        seen.add(path)
        tm = re.search(r'class="[^"]*jobtitle[^"]*"[^>]*>(.*?)</', chunk, re.DOTALL)
        cm = re.search(r'class="[^"]*companyname_list[^"]*"[^>]*>(.*?)</', chunk, re.DOTALL)
        results.append(
            {
                "url": BASE_URL + path if path.startswith("/") else path,
                "title": _clean(tm.group(1)) if tm else None,
                "company": _clean(cm.group(1)) if cm else None,
            }
        )
    return results


def _section_lists(lines: list[str]) -> dict[str, list[str]]:
    """Bucket bullet lines under Responsibilities / Qualifications / Benefits."""
    heads = {}
    for i, l in enumerate(lines):
        key = l.lower().rstrip(":")
        if key in _SECTION_HEADS and key not in heads:
            heads[key] = i
    resp_i = heads.get("responsibilities")
    qual_i = heads.get("qualification", heads.get("qualifications"))
    ben_i = heads.get("benefits")

    def _slice(start: int | None, end: int | None) -> list[str]:
        if start is None:
            return []
        body = lines[start + 1 : end if end is not None else len(lines)]
        items: list[str] = []
        for l in body:
            low = l.lower().rstrip(":")
            if low in {"required", "preferred"}:
                continue  # sub-labels under Qualification
            if any(mk in low for mk in _FOOTER_MARKERS):
                break  # reached the "about the company" footer
            items.append(l)
            if len(items) >= 25:
                break
        return items

    ordered = sorted(x for x in (resp_i, qual_i, ben_i) if x is not None)

    def _next_after(idx: int | None) -> int | None:
        if idx is None:
            return None
        later = [o for o in ordered if o > idx]
        return later[0] if later else None

    return {
        "responsibilities": _slice(resp_i, _next_after(resp_i)),
        "qualifications": _slice(qual_i, _next_after(qual_i)),
        "benefits": _slice(ben_i, _next_after(ben_i)),
    }


def parse_detail(page: str, source_url: str) -> dict:
    """Parse a detail page into a normalized job dict.

    Always returns a dict (never raises on missing fields) with an `is_closed`
    flag so callers can decide to skip. Missing fields are None / empty.
    """
    is_closed = CLOSED_MARKER in page.lower()

    title_m = re.search(r"<title>(.*?)</title>", page, re.DOTALL)
    title_tag = _html.unescape(title_m.group(1)).strip() if title_m else ""
    h1_m = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.DOTALL)
    h1 = _clean(h1_m.group(1)) if h1_m else None

    left, _, location = title_tag.partition(" | ")
    location = location.strip() or None
    company = left.rsplit(" at ", 1)[1].strip() if " at " in left else None
    if not company:
        company = _company_from_slug(source_url)
    title = h1 or (left.rsplit(" at ", 1)[0].strip() if " at " in left else left) or None
    if title:
        title = title.lstrip("#").strip()

    lines = _visible_lines(page)

    def _find(pred):
        return next((l for l in lines if pred(l)), None)

    employment_type = _find(lambda l: l.lower() in _EMPLOYMENT_TYPES)
    work_mode = _find(lambda l: l.lower() in _WORK_MODES)
    salary_range = _find(
        lambda l: _SALARY_RE.search(l)
        and ("-" in l or "k" in l.lower() or "yr" in l.lower())
        and len(l) <= 40
    )
    level = _find(lambda l: l.lower() in _LEVELS)

    posted_at = None
    for l in lines[:30]:
        m = _DATE_RE.search(l)
        if m:
            posted_at = m.group(0)
            break

    external_apply_url = None
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, re.DOTALL):
        txt = _clean(m.group(2)).lower()
        href = _html.unescape(m.group(1))
        if "apply" in txt and href.startswith("http"):
            external_apply_url = href
            break

    # Description: prefer the paragraph just before the Responsibilities heading;
    # otherwise the longest text block before the first section heading.
    sections = _section_lists(lines)
    description = None
    resp_idx = next(
        (i for i, l in enumerate(lines) if l.lower().rstrip(":") == "responsibilities"),
        None,
    )
    if resp_idx is not None:
        prior = [l for l in lines[:resp_idx] if len(l) > 60]
        if prior:
            description = max(prior, key=len)

    apply_is_company_ats = bool(
        external_apply_url and _ATS_HOST_RE.search(external_apply_url)
    )

    return {
        "title": title,
        "company": company,
        "location": location,
        "employment_type": employment_type,
        "work_mode": work_mode,
        "salary_range": salary_range,
        "level": level,
        "description": description,
        "responsibilities": sections["responsibilities"],
        "qualifications": sections["qualifications"],
        "benefits": sections["benefits"],
        "posted_at": posted_at,
        "source": SOURCE,
        "source_url": source_url,
        "external_apply_url": external_apply_url,
        "apply_is_company_ats": apply_is_company_ats,
        "is_closed": is_closed,
    }


# ----- Dedup + upsert -----

def _dedup_id(company: str | None, title: str | None, location: str | None,
              apply_or_source: str | None) -> str:
    """Stable external_id from company + title + location + apply/source url."""
    key = "|".join([company or "", title or "", location or "", apply_or_source or ""]).lower()
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def _apply_fields(job: Job, data: dict, external_id: str) -> None:
    """Write normalized fields onto a Job row (create or update path)."""
    job.source = SOURCE
    job.external_id = external_id
    job.company = data.get("company")
    job.title = data.get("title")
    job.location = data.get("location")
    job.employment_type = data.get("employment_type")
    job.work_mode = data.get("work_mode")
    job.salary_range = data.get("salary_range")
    job.level = data.get("level")
    job.description = data.get("description")
    job.responsibilities = json.dumps(data.get("responsibilities") or [])
    job.qualifications = json.dumps(data.get("qualifications") or [])
    job.benefits = json.dumps(data.get("benefits") or [])
    job.posted_at = data.get("posted_at")
    job.source_url = data.get("source_url")
    job.external_apply_url = data.get("external_apply_url")
    # Keep the generic `url` (used by existing UI/matcher) pointed at the honest
    # apply destination, falling back to the source page.
    job.url = data.get("external_apply_url") or data.get("source_url")
    job.is_closed = bool(data.get("is_closed"))
    job.discovered_at = datetime.utcnow()
    job.raw = json.dumps(data)


def ingest_newgrad_jobs(
    db: Session,
    *,
    categories: tuple[str, ...] | list[str] | None = None,
    max_per_category: int = 15,
    request_delay: float = 0.5,
    fetcher=None,
    sleep=None,
) -> dict:
    """Fetch category pages, then detail pages, and upsert deduplicated jobs.

    `fetcher`/`sleep` are injectable so tests can run fully offline (and so
    monkeypatching the module-level `fetch` works). Returns a summary dict and
    never raises for a single bad page — page-level problems are collected in
    `errors`.
    """
    fetcher = fetcher or fetch
    sleep = sleep or time.sleep
    categories = list(categories or DEFAULT_CATEGORY_PATHS)

    fetched_count = 0
    created_count = 0
    updated_count = 0
    skipped_closed_count = 0
    duplicate_count = 0
    errors: list[str] = []
    seen_in_batch: set[str] = set()

    for category in categories:
        cat_url = BASE_URL + category if category.startswith("/") else category
        try:
            cat_html = fetcher(cat_url)
        except Exception as exc:  # missing category, network blip — non-fatal
            errors.append(f"{category}: failed to fetch category page ({exc})")
            continue

        cards = parse_category(cat_html, category)
        if not cards:
            errors.append(f"{category}: no job cards found")
            continue

        for card in cards[: max(0, max_per_category)]:
            detail_url = card["url"]
            try:
                detail_html = fetcher(detail_url)
            except Exception as exc:
                errors.append(f"{detail_url}: failed to fetch detail page ({exc})")
                continue
            fetched_count += 1
            if request_delay:
                sleep(request_delay)  # polite, conservative rate limit

            data = parse_detail(detail_html, detail_url)
            # Carry over listing hints if the detail page was sparse.
            data["company"] = data.get("company") or card.get("company")
            data["title"] = data.get("title") or card.get("title")

            if not data.get("title") or not data.get("company"):
                errors.append(f"{detail_url}: missing title/company; skipped")
                continue

            external_id = _dedup_id(
                data["company"], data["title"], data["location"],
                data.get("external_apply_url") or data.get("source_url"),
            )

            existing = (
                db.query(Job)
                .filter(Job.source == SOURCE, Job.external_id == external_id)
                .first()
            )

            if data["is_closed"]:
                skipped_closed_count += 1
                # If we already stored it (open earlier), reflect that it closed.
                if existing is not None:
                    existing.is_closed = True
                    existing.discovered_at = datetime.utcnow()
                continue

            if external_id in seen_in_batch:
                duplicate_count += 1
                continue
            seen_in_batch.add(external_id)

            if existing is not None:
                _apply_fields(existing, data, external_id)
                updated_count += 1
            else:
                job = Job()
                _apply_fields(job, data, external_id)
                db.add(job)
                created_count += 1

    db.commit()

    return {
        "source": SOURCE,
        "categories": categories,
        "fetched_count": fetched_count,
        "created_count": created_count,
        "updated_count": updated_count,
        "skipped_closed_count": skipped_closed_count,
        "duplicate_count": duplicate_count,
        "errors": errors,
        "total_in_db": db.query(Job).count(),
    }
