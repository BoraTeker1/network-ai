"""Curated Turkey + Remote/EU opportunity feed: seeding, classifier conservatism,
filters, ranking, public-source resilience, outreach prefill, no-network safety."""

import pytest

from app.services import opportunities as opp


# ----- Classifier (deterministic + conservative) -----

def test_remote_worldwide_is_strong():
    label, _ = opp.classify_turkey_applicability(
        title="Junior Developer", description="Fully remote, hire anyone worldwide.",
        location="Remote — Worldwide", remote_policy="remote",
        country_scope="Worldwide", seniority="junior",
    )
    assert label == opp.LABEL_STRONG


def test_emea_remote_is_strong():
    label, _ = opp.classify_turkey_applicability(
        title="Junior Full-Stack", description="Remote within EMEA.",
        location="Remote — EMEA", remote_policy="remote", country_scope="EMEA",
        seniority="junior",
    )
    assert label == opp.LABEL_STRONG


def test_turkey_role_is_strong():
    label, _ = opp.classify_turkey_applicability(
        title="Junior Backend Engineer", description="Hybrid in Istanbul.",
        location="Istanbul, Turkey", remote_policy="hybrid", seniority="junior",
    )
    assert label == opp.LABEL_STRONG


def test_europe_remote_unclear_country_is_possible():
    label, _ = opp.classify_turkey_applicability(
        title="Graduate Engineer", description="Remote in Europe. Country eligibility not stated.",
        location="Remote — Europe", remote_policy="remote", country_scope="Europe",
        seniority="new_grad",
    )
    assert label == opp.LABEL_POSSIBLE


def test_relocation_is_possible():
    label, _ = opp.classify_turkey_applicability(
        title="Junior Backend", description="On-site in Paris. Visa sponsorship available.",
        location="Paris, France", remote_policy="onsite", country_scope="France",
        work_auth_note="Relocation and visa sponsorship available.", seniority="junior",
    )
    assert label == opp.LABEL_POSSIBLE


def test_us_only_is_not_eligible():
    label, _ = opp.classify_turkey_applicability(
        title="Junior SWE", description="Remote US only. Must be authorized to work in the US.",
        location="Remote US", remote_policy="remote", country_scope="US only",
        work_auth_note="Must be authorized to work in the United States.", seniority="junior",
    )
    assert label == opp.LABEL_NO


def test_usa_location_is_not_eligible():
    # Plain "USA" / "North America" scope (no work-auth phrasing) is still hidden.
    for loc in ("USA", "United States", "Remote (USA)", "North America"):
        label, _ = opp.classify_turkey_applicability(
            title="Junior Software Engineer", description="Remote role.",
            location=loc, remote_policy="remote", country_scope=loc, seniority="junior",
        )
        assert label == opp.LABEL_NO, loc


def test_us_company_hiring_worldwide_stays_strong():
    # A US company hiring worldwide IS workable from Turkey — must not be hidden.
    label, _ = opp.classify_turkey_applicability(
        title="Junior Developer", description="We hire anywhere.",
        location="Remote — Worldwide", remote_policy="remote",
        country_scope="Worldwide", seniority="junior",
    )
    assert label == opp.LABEL_STRONG


def test_usa_term_does_not_false_positive_on_description():
    # "usability" in the description must not trip the US-location gate; the gate
    # only reads location + country_scope, and this is a Turkey role.
    label, _ = opp.classify_turkey_applicability(
        title="Junior Frontend Engineer",
        description="Improve usability and accessibility of our app.",
        location="Istanbul, Turkey", remote_policy="hybrid", seniority="junior",
    )
    assert label == opp.LABEL_STRONG


def test_eu_citizenship_is_not_eligible():
    label, _ = opp.classify_turkey_applicability(
        title="Graduate Engineer", description="Amsterdam. EU citizenship required.",
        location="Amsterdam, Netherlands", remote_policy="onsite",
        work_auth_note="Must be an EU citizen with the right to work in the EU.",
        seniority="new_grad",
    )
    assert label == opp.LABEL_NO


def test_senior_only_is_not_eligible():
    label, _ = opp.classify_turkey_applicability(
        title="Senior Backend Engineer", description="Remote EMEA, 6+ years.",
        location="Remote — EMEA", remote_policy="remote", seniority="senior",
    )
    assert label == opp.LABEL_NO


def test_remote_region_unspecified_is_unclear():
    label, _ = opp.classify_turkey_applicability(
        title="Junior SWE", description="Remote role.", location="Remote",
        remote_policy="remote", seniority="junior",
    )
    assert label == opp.LABEL_UNCLEAR


# ----- Seeding + endpoint -----

def test_seed_loads_and_endpoint_returns_normalized(client):
    resp = client.get("/opportunities")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] > 0
    item = data["items"][0]
    for key in ("company", "title", "target_region", "seniority_level",
                "turkey_applicability_label", "turkey_applicability_reason",
                "tags", "outreach_prefill"):
        assert key in item


def test_seed_is_idempotent(client):
    first = client.get("/opportunities").json()["count"]
    second = client.get("/opportunities").json()["count"]
    assert first == second  # ensure_seeded does not duplicate


def test_filters_region_and_seniority(client):
    client.get("/opportunities")  # seed
    tr = client.get("/opportunities?region=turkey").json()["items"]
    assert tr and all(i["target_region"] == "turkey" for i in tr)
    interns = client.get("/opportunities?seniority=internship").json()["items"]
    assert all(i["seniority_level"] == "internship" for i in interns)


def test_filter_applicability_strong(client):
    client.get("/opportunities")
    strong = client.get("/opportunities?applicability=strong").json()["items"]
    assert strong
    assert all(i["turkey_applicability_label"] == opp.LABEL_STRONG for i in strong)


def test_ranking_prefers_strong_fit_junior(client):
    items = client.get("/opportunities").json()["items"]
    top = items[0]
    assert top["turkey_applicability_label"] == opp.LABEL_STRONG
    assert top["seniority_level"] in ("internship", "new_grad", "junior")
    # The US-only / EU-citizenship samples must not rank at the top.
    assert top["turkey_applicability_label"] != opp.LABEL_NO


# ----- Resume-aware matching (Phase 1) -----

def _two_equivalent_roles(db_session):
    """Two same-tier (strong / junior / remote-worldwide) roles that differ only
    by tech stack, so skill matching is the only ranking tiebreaker."""
    opp.import_records(db_session, [
        {"external_id": "py-role", "company": "PyCo", "title": "Junior Backend Engineer",
         "location": "Remote — Worldwide", "remote": True, "remote_policy": "remote",
         "country_scope": "Worldwide",
         "description": "Junior backend role building APIs with Python and FastAPI."},
        {"external_id": "go-role", "company": "GoCo", "title": "Junior Backend Engineer",
         "location": "Remote — Worldwide", "remote": True, "remote_policy": "remote",
         "country_scope": "Worldwide",
         "description": "Junior backend role building services in Go and Kubernetes."},
    ], source="test", is_sample=False)


def test_match_breakdown_reports_overlapping_skills(db_session):
    _two_equivalent_roles(db_session)
    items = opp.list_opportunities(db_session, profile_skills=["Python", "FastAPI", "SQL"])
    py = next(i for i in items if i["company"] == "PyCo")
    assert set(py["match"]["matched_skills"]) == {"Python", "FastAPI"}
    assert py["match"]["matched_count"] == 2
    assert py["match"]["total_skills"] == 3
    assert "Python" in py["match"]["reason"]


def test_resume_skills_break_ranking_ties(db_session):
    _two_equivalent_roles(db_session)
    items = opp.list_opportunities(db_session, profile_skills=["Python", "FastAPI"])
    companies = [i["company"] for i in items if i["company"] in ("PyCo", "GoCo")]
    # The Python/FastAPI resume ranks the Python role above the otherwise-identical Go role.
    assert companies.index("PyCo") < companies.index("GoCo")


def test_no_profile_leaves_match_empty(db_session):
    _two_equivalent_roles(db_session)
    items = opp.list_opportunities(db_session)
    assert all(i["match"]["reason"] is None for i in items)
    assert all(i["match"]["matched_skills"] == [] for i in items)


# ----- Source registry (Phase 2: verified live boards) -----

def test_live_sources_are_the_verified_set():
    live = {s["id"] for s in opp.list_sources() if s["live"]}
    assert live == {"dreamgames", "codeway", "commencis",
                    "trendyol", "peak", "midas", "picus"}


def test_every_live_source_has_a_real_provider_and_token():
    for s in opp.list_sources():
        if s["live"]:
            assert s["board_token"], f"{s['id']} live but has no board_token"
            assert s["ats_provider"] in opp._PROVIDER_MAPPERS
    # Disabled/manual sources must never carry an invented token.
    for s in opp.SOURCE_REGISTRY:
        if not s.get("enabled"):
            assert s.get("board_token") is None


# ----- Public source resilience (no network in normal tests) -----

def test_refresh_public_source_failure_is_graceful(client, monkeypatch):
    def _boom(limit=50):
        raise RuntimeError("network down")

    monkeypatch.setattr(opp, "fetch_arbeitnow", _boom)
    monkeypatch.setattr(opp, "fetch_remotive", lambda limit=50: [])
    monkeypatch.setattr(opp, "fetch_jobicy", lambda count=50: [])
    # Seed first so there's a feed to preserve.
    client.get("/opportunities")
    resp = client.post("/opportunities/refresh-public-sources")
    assert resp.status_code == 200
    body = resp.json()
    assert body["errors"]  # error reported, not raised
    # Seeded feed still works.
    assert client.get("/opportunities").json()["count"] > 0


def test_get_opportunities_makes_no_network_call(client, monkeypatch):
    # If GET tried to hit the network, this would raise.
    def _boom(*a, **k):
        raise AssertionError("GET /opportunities must not call the network")

    monkeypatch.setattr(opp, "fetch_arbeitnow", _boom)
    resp = client.get("/opportunities")
    assert resp.status_code == 200


def test_public_import_adapter_normalizes(client, monkeypatch):
    sample = [{
        "slug": "ext-remote-1", "company_name": "Remote Co", "title": "Junior Engineer",
        "location": "Remote — Worldwide", "remote": True, "tags": ["python"],
        "description": "Remote worldwide junior role.", "url": "https://x/y",
        "created_at": "2026-06-01",
    }]
    monkeypatch.setattr(opp, "fetch_arbeitnow", lambda limit=50: sample)
    monkeypatch.setattr(opp, "fetch_remotive", lambda limit=50: [])
    monkeypatch.setattr(opp, "fetch_jobicy", lambda count=50: [])
    resp = client.post("/opportunities/refresh-public-sources")
    assert resp.status_code == 200 and resp.json()["created"] >= 1
    imported = client.get("/opportunities?source=arbeitnow").json()["items"]
    assert imported and imported[0]["company"] == "Remote Co"


# ----- Manual JSON import -----

def test_manual_import(client):
    payload = {
        "jobs": [{
            "external_id": "manual-1", "company": "Acme TR", "title": "Junior Backend Engineer",
            "location": "Istanbul, Turkey", "remote_policy": "hybrid",
            "description": "Junior backend role in Istanbul.", "tags": ["Python"],
        }],
        "source": "manual-import",
    }
    resp = client.post("/opportunities/import", json=payload)
    assert resp.status_code == 200 and resp.json()["created"] == 1
    items = client.get("/opportunities?source=manual-import").json()["items"]
    assert items[0]["company"] == "Acme TR"


# ----- Outreach prefill -----

def test_outreach_prefill_turkey_defaults_turkish(client):
    items = client.get("/opportunities?region=turkey").json()["items"]
    pre = items[0]["outreach_prefill"]
    assert pre["target_region"] == "turkey"
    assert pre["language"] == "tr"
    assert pre["company"] and pre["role"]


def test_outreach_prefill_remote_defaults_english_with_location(client):
    items = client.get("/opportunities?region=global").json()["items"]
    pre = items[0]["outreach_prefill"]
    assert pre["language"] == "en"
    assert pre["include_location_line"] is True


def test_opportunities_module_has_no_module_level_network_client():
    # `requests` is imported lazily inside fetch_* only.
    assert "requests" not in dir(opp)


# ----- Real Turkish-company source (Lever public API) -----

_LEVER_SAMPLE = [
    {
        "id": "lever-1", "text": "Junior Game Developer",
        "categories": {"location": "Istanbul", "team": "Engineering", "commitment": "Full-time"},
        "country": "TR", "workplaceType": "on-site",
        "descriptionPlain": "Build mobile games in Unity. New grads welcome.",
        "hostedUrl": "https://jobs.lever.co/dreamgames/lever-1",
        "createdAt": 1717000000000,
    },
    {
        "id": "lever-2", "text": "DevOps Engineer",
        "categories": {"location": "Istanbul", "team": "Platform", "commitment": "Full-time"},
        "country": "TR", "workplaceType": "hybrid",
        "descriptionPlain": "Own our CI/CD and cloud infra.",
        "hostedUrl": "https://jobs.lever.co/dreamgames/lever-2",
        "createdAt": 1717100000000,
    },
]


def test_lever_record_mapping():
    rec = opp._lever_to_record(_LEVER_SAMPLE[0], "Dream Games")
    assert rec["company"] == "Dream Games"
    assert rec["title"] == "Junior Game Developer"
    assert "Turkey" in rec["location"]          # country TR appended
    assert rec["remote_policy"] == "onsite"
    assert rec["url"].startswith("https://jobs.lever.co/")
    assert rec["date_posted"]                    # epoch ms → ISO date


def test_refresh_turkish_sources_creates_turkey_rows(client, monkeypatch):
    monkeypatch.setattr(opp, "fetch_lever", lambda token: _LEVER_SAMPLE)
    client.get("/opportunities")  # seed first
    resp = client.post("/opportunities/refresh-turkish-sources")
    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] >= 2 and not body["errors"]
    items = client.get("/opportunities?source=lever").json()["items"]
    assert items and all(i["target_region"] == "turkey" for i in items)
    # An Istanbul on-site role is a strong fit for a Turkey-based candidate.
    assert any(i["turkey_applicability_label"] == opp.LABEL_STRONG for i in items)


def test_refresh_turkish_sources_is_resilient(client, monkeypatch):
    def _boom(token):
        raise RuntimeError("lever down")

    monkeypatch.setattr(opp, "fetch_lever", _boom)
    client.get("/opportunities")
    resp = client.post("/opportunities/refresh-turkish-sources")
    assert resp.status_code == 200
    assert resp.json()["errors"]                 # reported, not raised
    assert client.get("/opportunities").json()["count"] > 0  # seeded feed intact


def test_istanbul_onsite_is_strong_fit():
    label, _ = opp.classify_turkey_applicability(
        title="DevOps Engineer", description="Own our infra.",
        location="Istanbul", remote_policy="onsite", seniority="unknown",
    )
    assert label == opp.LABEL_STRONG


# ----- Greenhouse / Ashby adapter normalization -----

def test_greenhouse_normalization():
    posting = {
        "id": 123, "title": "Backend Engineer",
        "location": {"name": "Remote - EMEA"},
        "absolute_url": "https://boards.greenhouse.io/acme/jobs/123",
        "content": "&lt;p&gt;Remote within EMEA. Build APIs.&lt;/p&gt;",
        "departments": [{"name": "Engineering"}], "updated_at": "2026-06-01T00:00:00Z",
    }
    rec = opp._greenhouse_to_record(posting, "Acme")
    assert rec["external_id"] == "123" and rec["company"] == "Acme"
    assert rec["location"] == "Remote - EMEA"
    assert "Engineering" in rec["tags"]
    assert "<" not in rec["description"]  # HTML stripped
    norm = opp.normalize_record(rec, source="greenhouse:acme", is_sample=False)
    assert norm["target_region"] == "europe"


def test_ashby_normalization():
    posting = {
        "id": "uuid-1", "title": "Junior Engineer", "location": "Istanbul",
        "isRemote": False, "team": "Platform", "employmentType": "FullTime",
        "jobUrl": "https://jobs.ashbyhq.com/acme/uuid-1",
        "descriptionPlain": "Junior role in Istanbul.", "publishedAt": "2026-06-01",
    }
    rec = opp._ashby_to_record(posting, "Acme TR")
    assert rec["external_id"] == "uuid-1" and rec["company"] == "Acme TR"
    assert rec["url"].startswith("https://jobs.ashbyhq.com/")
    norm = opp.normalize_record(rec, source="ashby:acme", is_sample=False)
    assert norm["target_region"] == "turkey"


# ----- Source registry -----

def test_sources_registry_endpoint(client):
    data = client.get("/opportunities/sources").json()["sources"]
    by_id = {s["id"]: s for s in data}
    # Verified Lever boards are enabled + live.
    assert by_id["dreamgames"]["enabled"] and by_id["dreamgames"]["live"]
    assert by_id["dreamgames"]["source_confidence"] == "official_ats"
    assert by_id["trendyol"]["enabled"] and by_id["trendyol"]["live"]
    # Companies without a verified token are disabled/manual (no invented token).
    assert by_id["getir"]["enabled"] is False
    assert by_id["getir"]["board_token"] is None
    assert by_id["getir"]["live"] is False


def test_refresh_sources_skips_disabled_and_imports_enabled(client, monkeypatch):
    monkeypatch.setattr(opp, "fetch_lever", lambda token: _LEVER_SAMPLE)
    client.get("/opportunities")  # seed
    body = client.post("/opportunities/refresh-sources").json()
    statuses = {s["id"]: s["status"] for s in body["sources"]}
    assert statuses["dreamgames"] == "success"
    assert statuses["getir"] == "skipped"   # disabled/manual not refreshed
    assert body["succeeded"] >= 3 and body["created"] > 0
    # Imported rows carry official_ats confidence + lever provider.
    items = client.get("/opportunities?source=lever").json()["items"]
    assert items and all(i["source_confidence"] == "official_ats" for i in items)
    assert all(i["source_provider"] == "lever" for i in items)


def test_refresh_single_source(client, monkeypatch):
    monkeypatch.setattr(opp, "fetch_lever", lambda token: _LEVER_SAMPLE)
    r = client.post("/opportunities/refresh-source/dreamgames")
    assert r.status_code == 200 and r.json()["status"] == "success"
    assert client.post("/opportunities/refresh-source/nope").status_code == 404


def test_refresh_all_pulls_ats_and_public(client, monkeypatch):
    monkeypatch.setattr(opp, "fetch_lever", lambda token: _LEVER_SAMPLE)
    monkeypatch.setattr(opp, "fetch_arbeitnow", lambda limit=50: [])
    monkeypatch.setattr(opp, "fetch_remotive", lambda limit=50: _REMOTIVE_SAMPLE)
    monkeypatch.setattr(opp, "fetch_jobicy", lambda count=50: _JOBICY_SAMPLE)
    client.get("/opportunities")  # seed
    body = client.post("/opportunities/refresh-all").json()
    # Both halves ran and are reported.
    assert "ats" in body and "public" in body
    assert body["created"] >= 4              # 2 lever + remotive + jobicy
    assert body["succeeded"] >= 3            # 3 enabled Lever boards
    # Rows from both an ATS source and a public source are present.
    assert client.get("/opportunities?source=lever").json()["items"]
    assert client.get("/opportunities?source=remotive").json()["items"]


def test_refresh_all_is_resilient(client, monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(opp, "fetch_lever", _boom)
    monkeypatch.setattr(opp, "fetch_arbeitnow", _boom)
    monkeypatch.setattr(opp, "fetch_remotive", lambda limit=50: _REMOTIVE_SAMPLE)
    monkeypatch.setattr(opp, "fetch_jobicy", lambda count=50: [])
    client.get("/opportunities")
    body = client.post("/opportunities/refresh-all").json()
    assert body["failed"] >= 1                # lever + arbeitnow failures counted
    assert client.get("/opportunities").json()["count"] > 0  # seeded feed intact


def test_registry_includes_desired_employers_as_directory_only(client):
    by_id = {s["id"]: s for s in client.get("/opportunities/sources").json()["sources"]}
    for cid in ("mckinsey", "bcg", "bain", "google", "amazon", "isbank"):
        assert cid in by_id, cid
        s = by_id[cid]
        assert s["enabled"] is False          # directory only — never fetched
        assert s["live"] is False
        assert s["board_token"] is None       # no invented ATS token
        assert s["careers_url"].startswith("http")


# ----- US-only hidden by default; confidence labels -----

def test_us_only_hidden_by_default_but_visible_on_request(client):
    default_items = client.get("/opportunities").json()["items"]
    assert all(i["turkey_applicability_label"] != opp.LABEL_NO for i in default_items)
    not_eligible = client.get("/opportunities?applicability=no").json()["items"]
    assert any("US" in (i["company"] or "") for i in not_eligible)
    assert all(i["turkey_applicability_label"] == opp.LABEL_NO for i in not_eligible)


def test_seed_rows_have_sample_confidence(client):
    items = client.get("/opportunities?confidence=sample_demo").json()["items"]
    assert items and all(i["source_confidence"] == "sample_demo" for i in items)


# ----- Job-function classifier + SWE filter -----

def test_classify_job_function():
    f = opp.classify_job_function
    # Engineering
    assert f(title="Senior Backend Engineer") == opp.FUNCTION_SWE
    assert f(title="Junior iOS Developer") == opp.FUNCTION_SWE
    assert f(title="DevOps Engineer") == opp.FUNCTION_SWE
    assert f(title="Software Engineer, Performance Marketing") == opp.FUNCTION_SWE
    assert f(title="Engineer", tags=["Engineering"]) == opp.FUNCTION_SWE
    # Business
    assert f(title="Business Analyst") == opp.FUNCTION_BUSINESS
    assert f(title="Associate Consultant") == opp.FUNCTION_BUSINESS
    assert f(title="Investment Banking Analyst") == opp.FUNCTION_BUSINESS
    assert f(title="Management Trainee") == opp.FUNCTION_BUSINESS
    assert f(title="Performance Marketing Specialist") == opp.FUNCTION_BUSINESS
    assert f(title="Sales Engineer") == opp.FUNCTION_BUSINESS
    # Creative / admin → other
    assert f(title="Concept Artist") == opp.FUNCTION_OTHER
    assert f(title="Executive Assistant") == opp.FUNCTION_OTHER
    assert f(title="Product Designer") == opp.FUNCTION_OTHER
    assert f(title="Data Scientist") == opp.FUNCTION_OTHER


def test_function_filter_separates_eng_and_business(client):
    payload = {"jobs": [
        {"external_id": "swe-1", "company": "Acme TR", "title": "Junior Backend Engineer",
         "location": "Istanbul, Turkey", "description": "x", "tags": ["Python"]},
        {"external_id": "biz-1", "company": "Consult TR", "title": "Business Analyst",
         "location": "Istanbul, Turkey", "description": "x", "tags": ["Strategy"]},
        {"external_id": "art-1", "company": "Studio TR", "title": "Concept Artist",
         "location": "Istanbul, Turkey", "description": "x", "tags": ["Art"]},
    ], "source": "manual-import"}
    client.post("/opportunities/import", json=payload)

    def titles(q):
        return {i["title"] for i in client.get(f"/opportunities?source=manual-import{q}").json()["items"]}

    # Default (all = engineering + business) shows both, hides creative "other".
    default = titles("")
    assert "Junior Backend Engineer" in default and "Business Analyst" in default
    assert "Concept Artist" not in default
    # Each field shows only its bucket.
    assert titles("&function=software_engineering") == {"Junior Backend Engineer"}
    assert titles("&function=business") == {"Business Analyst"}
    # function=any surfaces everything, incl. creative/admin.
    assert "Concept Artist" in titles("&function=any")


# ----- Remotive / Jobicy public remote-board adapters -----

_REMOTIVE_SAMPLE = [{
    "id": 555, "url": "https://remotive.com/remote-jobs/x-555",
    "title": "Junior Backend Developer", "company_name": "Remotive Co",
    "category": "Software Development", "tags": ["Python", "Django"],
    "job_type": "full_time", "publication_date": "2026-06-20",
    "candidate_required_location": "Worldwide",
    "description": "<p>Remote worldwide junior role.</p>",
}]

_JOBICY_SAMPLE = [{
    "id": 777, "url": "https://jobicy.com/jobs/x-777",
    "jobTitle": "Junior Frontend Engineer", "companyName": "Jobicy Co",
    "jobIndustry": ["Dev"], "jobType": ["full-time"], "jobGeo": "EMEA",
    "jobLevel": "Junior", "jobExcerpt": "Remote EMEA.",
    "jobDescription": "<p>Remote within EMEA.</p>", "pubDate": "2026-06-21",
}]


def test_remotive_record_mapping():
    rec = opp._remotive_to_record(_REMOTIVE_SAMPLE[0])
    assert rec["company"] == "Remotive Co"
    assert rec["title"] == "Junior Backend Developer"
    assert rec["remote_policy"] == "remote"
    assert rec["country_scope"] == "Worldwide"
    assert "<" not in rec["description"]          # HTML stripped
    norm = opp.normalize_record(rec, source="remotive", is_sample=False)
    assert norm["turkey_applicability_label"] == opp.LABEL_STRONG
    assert norm["job_function"] == opp.FUNCTION_SWE


def test_jobicy_record_mapping():
    rec = opp._jobicy_to_record(_JOBICY_SAMPLE[0])
    assert rec["company"] == "Jobicy Co"
    assert rec["title"] == "Junior Frontend Engineer"
    assert rec["remote_policy"] == "remote"
    assert rec["country_scope"] == "EMEA"
    assert "<" not in rec["description"]
    norm = opp.normalize_record(rec, source="jobicy", is_sample=False)
    assert norm["target_region"] == "europe"      # EMEA → europe
    assert norm["turkey_applicability_label"] == opp.LABEL_STRONG
    assert norm["job_function"] == opp.FUNCTION_SWE


def test_refresh_public_sources_is_resilient_per_feed(client, monkeypatch):
    def _boom(limit=50):
        raise RuntimeError("arbeitnow down")

    monkeypatch.setattr(opp, "fetch_arbeitnow", _boom)
    monkeypatch.setattr(opp, "fetch_remotive", lambda limit=50: _REMOTIVE_SAMPLE)
    monkeypatch.setattr(opp, "fetch_jobicy", lambda count=50: _JOBICY_SAMPLE)
    client.get("/opportunities")  # seed
    body = client.post("/opportunities/refresh-public-sources").json()
    assert any("arbeitnow" in e for e in body["errors"])   # one feed failed
    assert body["created"] >= 2                            # the other two imported
    remotive = client.get("/opportunities?source=remotive").json()["items"]
    assert remotive and remotive[0]["company"] == "Remotive Co"
    jobicy = client.get("/opportunities?source=jobicy").json()["items"]
    assert jobicy and jobicy[0]["company"] == "Jobicy Co"


def test_dedupe_on_reimport(client):
    payload = {"jobs": [{
        "external_id": "dup-1", "company": "Dup Co", "title": "Junior Engineer",
        "location": "Istanbul, Turkey", "description": "x", "tags": ["Python"],
    }], "source": "manual-import"}
    first = client.post("/opportunities/import", json=payload).json()
    second = client.post("/opportunities/import", json=payload).json()
    assert first["created"] == 1
    assert second["created"] == 0 and second["updated"] == 1  # deduped, not duplicated
