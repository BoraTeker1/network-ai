"""Job-ingestion parsing tests (no network — parse_jobs is pure)."""

from app.services.job_ingestion import _dedup_id, parse_jobs

SAMPLE_README = """
<table>
<tr><th>Company</th><th>Role</th><th>Location</th><th>Application</th><th>Date</th></tr>
<tr>
  <td><strong>Stripe</strong></td>
  <td>Software Engineer, New Grad</td>
  <td>Remote</td>
  <td><a href="https://stripe.com/apply">Apply</a></td>
  <td>Jun 01</td>
</tr>
<tr>
  <td>↳</td>
  <td>Backend Engineer</td>
  <td>New York, NY</td>
  <td><a href="https://stripe.com/apply2">Apply</a></td>
  <td>Jun 02</td>
</tr>
<tr>
  <td>ClosedCo</td>
  <td>Closed Role</td>
  <td>SF</td>
  <td>🔒</td>
  <td>Jun 03</td>
</tr>
</table>
"""


def test_parse_jobs_extracts_rows():
    jobs = parse_jobs(SAMPLE_README)
    titles = [j["role_title"] for j in jobs]
    assert "Software Engineer, New Grad" in titles
    assert "Backend Engineer" in titles


def test_continuation_row_inherits_company():
    jobs = parse_jobs(SAMPLE_README)
    backend = next(j for j in jobs if j["role_title"] == "Backend Engineer")
    assert backend["company"] == "Stripe"  # inherited from the ↳ row above


def test_rows_without_apply_link_are_skipped():
    jobs = parse_jobs(SAMPLE_README)
    assert all(j["role_title"] != "Closed Role" for j in jobs)


def test_dedup_id_is_stable_and_distinct():
    a = _dedup_id("Stripe", "SWE", "Remote", "u1")
    b = _dedup_id("Stripe", "SWE", "Remote", "u1")
    c = _dedup_id("Stripe", "SWE", "Remote", "u2")
    assert a == b
    assert a != c
