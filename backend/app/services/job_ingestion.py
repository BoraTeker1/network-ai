"""Job ingestion service.

Pulls new-grad roles from the SimplifyJobs/New-Grad-Positions GitHub README,
parses the HTML job tables, and stores deduplicated jobs in SQLite.

The README is rendered as HTML <table> rows (not markdown tables). Each job
row has 5 cells: Company | Role | Location | Apply links | Date posted.
A company cell of "↳" means "same company as the row above".

No LLM calls — deterministic parsing only.
"""

import hashlib
import html
import json
import re

import requests
from sqlalchemy.orm import Session

from ..models import Job

SOURCE = "simplify-newgrad"
README_URL = (
    "https://raw.githubusercontent.com/"
    "SimplifyJobs/New-Grad-Positions/dev/README.md"
)

# Decorative markers that appear in company/role cells but aren't part of data.
_MARKERS = ["🔥", "🛂", "🇺🇸", "⭐", "🔒", "🎓"]


def fetch_readme(url: str = README_URL) -> str:
    """Download the README text. Raises requests.RequestException on failure."""
    resp = requests.get(url, timeout=30, headers={"User-Agent": "network-ai/0.1"})
    resp.raise_for_status()
    return resp.text


def _strip_tags(cell: str) -> str:
    """Turn a table cell's HTML into clean plain text."""
    # Preserve multi-value separators before dropping tags.
    cell = re.sub(r"</?br\s*/?>", ", ", cell, flags=re.IGNORECASE)
    cell = re.sub(r"<[^>]+>", "", cell)
    cell = html.unescape(cell)
    for marker in _MARKERS:
        cell = cell.replace(marker, "")
    # Collapse whitespace and tidy stray separators.
    cell = re.sub(r"\s+", " ", cell).strip()
    return cell.strip(", ").strip()


def _first_href(cell: str) -> str | None:
    """Return the first hyperlink in a cell (the real application URL)."""
    match = re.search(r'href="([^"]+)"', cell)
    return html.unescape(match.group(1)) if match else None


def _dedup_id(company: str, role_title: str, location: str, job_url: str) -> str:
    """Stable hash used as external_id for company+role+location+url dedup."""
    key = "|".join([company, role_title, location, job_url]).lower()
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def parse_jobs(readme_text: str) -> list[dict]:
    """Parse all job rows from the README HTML into clean dicts."""
    jobs: list[dict] = []
    last_company = ""

    rows = re.findall(r"<tr>(.*?)</tr>", readme_text, flags=re.DOTALL | re.IGNORECASE)
    for row in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.DOTALL | re.IGNORECASE)
        if len(cells) < 4:
            continue  # header rows / malformed rows

        company_raw = _strip_tags(cells[0])
        if company_raw in ("", "↳", "—", "-"):
            company = last_company  # continuation row inherits the company above
        else:
            company = company_raw
            last_company = company

        role_title = _strip_tags(cells[1])
        location = _strip_tags(cells[2])
        job_url = _first_href(cells[3])

        # Skip rows we can't act on (closed roles with no application link,
        # or rows missing core fields).
        if not company or not role_title or not job_url:
            continue

        jobs.append(
            {
                "company": company,
                "role_title": role_title,
                "location": location,
                "job_url": job_url,
                "source": SOURCE,
            }
        )

    return jobs


def ingest_jobs(db: Session) -> dict:
    """Fetch, parse, and store deduplicated jobs. Returns ingest counts."""
    readme_text = fetch_readme()
    parsed = parse_jobs(readme_text)

    ingested = 0
    skipped_duplicates = 0
    seen_in_batch: set[str] = set()

    for job in parsed:
        external_id = _dedup_id(
            job["company"], job["role_title"], job["location"], job["job_url"]
        )

        # Dedupe within this batch and against what's already stored.
        if external_id in seen_in_batch:
            skipped_duplicates += 1
            continue
        seen_in_batch.add(external_id)

        exists = (
            db.query(Job)
            .filter(Job.source == SOURCE, Job.external_id == external_id)
            .first()
        )
        if exists:
            skipped_duplicates += 1
            continue

        db.add(
            Job(
                source=SOURCE,
                external_id=external_id,
                company=job["company"],
                title=job["role_title"],
                location=job["location"],
                url=job["job_url"],
                raw=json.dumps(job),
            )
        )
        ingested += 1

    db.commit()

    return {
        "ingested": ingested,
        "skipped_duplicates": skipped_duplicates,
        "parsed_rows": len(parsed),
        "total_in_db": db.query(Job).count(),
        "source": SOURCE,
    }
