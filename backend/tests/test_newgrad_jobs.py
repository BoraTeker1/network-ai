"""Tests for the newgrad-jobs.com ingestion adapter.

Fully offline: a fake fetcher maps URLs to small HTML fixtures that mirror the
real Webflow structure (title `"{title} at {company} | {location}"`, an h1, chip
lines, h2 sections, an Apply anchor, and the "This job has closed." marker).
"""

import json

import pytest

from app.models import Job
from app.services import newgrad_jobs as ng

SE = "/list-software-engineer-jobs"
BASE = ng.BASE_URL


def _detail_html(
    *,
    title="Software Engineer I",
    company="RTX",
    location="Tewksbury, MA",
    employment="Full-time",
    mode="Onsite",
    salary="$57K/yr - $109K/yr",
    level="Entry Level",
    apply_url="https://jobright.ai/jobs/info/abc123",
    closed=False,
    posted="June 1, 2026",
):
    closed_block = '<div class="closed">This job has closed.</div>' if closed else ""
    return f"""<!doctype html><html><head>
    <title>{title} at {company} | {location}</title></head><body>
    <nav>Home Hot Jobs</nav>
    <div class="companyname">{company}</div>
    <div class="text-block-65">{posted}</div>
    <a href="{apply_url}" class="applybtn">Apply Now</a>
    {closed_block}
    <h1 class="jobtitle">{title}</h1>
    <div class="flex"><div>{location}</div></div>
    <div class="text-block-47">{employment}</div>
    <div class="flex"><div>{mode}</div></div>
    <div class="text-block-47">{salary}</div>
    <div class="text-block-47">{level}</div>
    <p class="desc">{company} is seeking a {title} to design, build, and maintain
       software for advanced systems in a collaborative Agile environment.</p>
    <a href="{apply_url}">Apply Now</a>
    <h2>Responsibilities</h2><ul>
      <li>Design, develop, test, and maintain software</li>
      <li>Work with engineers in an Agile environment</li></ul>
    <h2>Qualification</h2>
      <div>Required</div><ul>
      <li>Bachelor's degree in a STEM field</li>
      <li>Experience with Python or C++</li></ul>
      <div>Preferred</div><ul>
      <li>Knowledge of CI/CD pipelines</li></ul>
    <h2>Benefits</h2><ul>
      <li>Medical</li><li>Dental</li><li>401(k) match</li></ul>
    <div class="company-about">{company} Glassdoor 3.8 Founded in 2020</div>
    <div>5 other Similar Jobs</div>
    </body></html>"""


def _category_html(cards, category=SE):
    """cards: list of (slug, title, company)."""
    blocks = []
    for slug, title, company in cards:
        blocks.append(
            f'''<div class="collection-item w-dyn-item">
            <a href="{category}/{slug}" class="w-inline-block">
              <div class="jobtitle">{title}</div>
              <div class="companyname_list">{company}</div>
            </a></div>'''
        )
    return "<html><body>" + "".join(blocks) + "</body></html>"


class FakeFetcher:
    """Maps URL -> html. Missing URLs raise (to exercise error handling)."""

    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def __call__(self, url):
        self.calls.append(url)
        if url not in self.pages:
            raise RuntimeError(f"404 {url}")
        return self.pages[url]


# ----- Parsing -----

def test_parse_category_extracts_cards():
    html = _category_html([
        ("se_at_rtx_1", "Software Engineer I", "RTX"),
        ("swe_at_walmart_2", "Software Engineer III", "Walmart"),
    ])
    cards = ng.parse_category(html, SE)
    assert len(cards) == 2
    assert cards[0]["url"] == f"{BASE}{SE}/se_at_rtx_1"
    assert cards[0]["title"] == "Software Engineer I"
    assert cards[1]["company"] == "Walmart"


def test_parse_detail_normalizes_all_fields():
    d = ng.parse_detail(_detail_html(), f"{BASE}{SE}/se_at_rtx_1")
    assert d["title"] == "Software Engineer I"
    assert d["company"] == "RTX"
    assert d["location"] == "Tewksbury, MA"
    assert d["employment_type"] == "Full-time"
    assert d["work_mode"] == "Onsite"
    assert d["salary_range"] == "$57K/yr - $109K/yr"
    assert d["level"] == "Entry Level"
    assert d["posted_at"] == "June 1, 2026"
    assert d["is_closed"] is False
    assert "design" in (d["description"] or "").lower()
    assert len(d["responsibilities"]) == 2
    assert any("STEM" in q for q in d["qualifications"])
    assert "Required" not in d["qualifications"] and "Preferred" not in d["qualifications"]
    assert d["benefits"] == ["Medical", "Dental", "401(k) match"]  # footer trimmed
    # jobright.ai is an aggregator, not a company ATS — must not be flagged official.
    assert d["external_apply_url"].startswith("https://jobright.ai/")
    assert d["apply_is_company_ats"] is False


def test_parse_detail_flags_company_ats():
    d = ng.parse_detail(
        _detail_html(apply_url="https://rtx.wd1.myworkdayjobs.com/job/123"),
        f"{BASE}{SE}/se_at_rtx_1",
    )
    assert d["apply_is_company_ats"] is True


def test_parse_detail_detects_closed():
    d = ng.parse_detail(_detail_html(closed=True), f"{BASE}{SE}/se_at_rtx_1")
    assert d["is_closed"] is True


def test_parse_detail_never_crashes_on_garbage():
    d = ng.parse_detail("<html><body>nope</body></html>", f"{BASE}{SE}/x_at_y_9")
    assert d["is_closed"] is False
    assert d["responsibilities"] == [] and d["benefits"] == []
    # company falls back to the slug when the page is unparseable.
    assert d["company"] == "Y"


# ----- Ingestion -----

def _pages_with(open_cards, *, closed=None, dup=False):
    cat = _category_html(open_cards)
    pages = {f"{BASE}{SE}": cat}
    for slug, title, company in open_cards:
        pages[f"{BASE}{SE}/{slug}"] = _detail_html(title=title, company=company)
    if closed:
        slug, title, company = closed
        pages[f"{BASE}{SE}/{slug}"] = _detail_html(title=title, company=company, closed=True)
    return pages


def _run(client_db, pages, **kw):
    fetcher = FakeFetcher(pages)
    res = ng.ingest_newgrad_jobs(
        client_db, categories=[SE], request_delay=0, fetcher=fetcher,
        sleep=lambda *_: None, **kw,
    )
    return res, fetcher


def test_ingest_creates_and_skips_closed(db_session):
    cards = [
        ("se_at_rtx_1", "Software Engineer I", "RTX"),
        ("closed_at_acme_2", "Backend Engineer", "Acme"),
    ]
    pages = _pages_with(cards[:1], closed=cards[1])
    pages[f"{BASE}{SE}"] = _category_html(cards)  # category lists both

    res, _ = _run(db_session, pages)
    assert res["fetched_count"] == 2
    assert res["created_count"] == 1
    assert res["skipped_closed_count"] == 1
    assert res["duplicate_count"] == 0
    assert db_session.query(Job).count() == 1
    job = db_session.query(Job).first()
    assert job.source == "newgrad-jobs.com"
    assert job.source_url.endswith("/se_at_rtx_1")
    assert json.loads(job.benefits) == ["Medical", "Dental", "401(k) match"]


def test_ingest_dedupes_within_batch(db_session):
    # Two distinct cards whose detail pages produce identical company+title+
    # location+apply_url -> same external_id -> one created, one duplicate.
    cards = [
        ("se_at_rtx_1", "Software Engineer I", "RTX"),
        ("se_at_rtx_copy", "Software Engineer I", "RTX"),
    ]
    pages = _pages_with(cards)
    res, _ = _run(db_session, pages)
    assert res["created_count"] == 1
    assert res["duplicate_count"] == 1
    assert db_session.query(Job).count() == 1


def test_ingest_updates_existing_on_rerun(db_session):
    cards = [("se_at_rtx_1", "Software Engineer I", "RTX")]
    pages = _pages_with(cards)
    first, _ = _run(db_session, pages)
    assert first["created_count"] == 1

    second, _ = _run(db_session, pages)
    assert second["created_count"] == 0
    assert second["updated_count"] == 1
    assert db_session.query(Job).count() == 1  # no duplicate row


def test_ingest_missing_category_is_non_fatal(db_session):
    # Empty page map => category fetch raises => recorded as an error, no crash.
    res, _ = _run(db_session, {})
    assert res["errors"]
    assert res["created_count"] == 0
    assert res["fetched_count"] == 0


def test_ingest_respects_max_per_category(db_session):
    cards = [(f"se_at_co{i}_{i}", f"Engineer {i}", f"Co{i}") for i in range(5)]
    pages = _pages_with(cards)
    res, fetcher = _run(db_session, pages, max_per_category=2)
    assert res["created_count"] == 2
    # 1 category fetch + 2 detail fetches.
    assert len(fetcher.calls) == 3


# ----- Endpoint -----

def test_ingest_endpoint_returns_summary(client, monkeypatch):
    cards = [("se_at_rtx_1", "Software Engineer I", "RTX")]
    pages = _pages_with(cards)
    monkeypatch.setattr(ng, "fetch", FakeFetcher(pages))

    r = client.post(
        "/jobs/ingest/newgrad-jobs",
        json={"categories": [SE], "max_per_category": 5, "request_delay": 0},
    )
    assert r.status_code == 200
    data = r.json()
    for key in (
        "fetched_count", "created_count", "updated_count",
        "skipped_closed_count", "duplicate_count", "errors",
    ):
        assert key in data
    assert data["source"] == "newgrad-jobs.com"
    assert data["created_count"] == 1


def test_jobs_endpoint_exposes_source_and_normalized_fields(client, monkeypatch):
    cards = [("se_at_rtx_1", "Software Engineer I", "RTX")]
    monkeypatch.setattr(ng, "fetch", FakeFetcher(_pages_with(cards)))
    client.post(
        "/jobs/ingest/newgrad-jobs",
        json={"categories": [SE], "request_delay": 0},
    )
    jobs = client.get("/jobs").json()
    assert jobs
    job = jobs[0]
    assert job["source"] == "newgrad-jobs.com"
    assert job["work_mode"] == "Onsite"
    assert job["salary_range"] == "$57K/yr - $109K/yr"
    assert job["is_closed"] is False
    assert isinstance(job["benefits"], list)
