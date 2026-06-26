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


# ----- Public source resilience (no network in normal tests) -----

def test_refresh_public_source_failure_is_graceful(client, monkeypatch):
    def _boom(limit=50):
        raise RuntimeError("network down")

    monkeypatch.setattr(opp, "fetch_arbeitnow", _boom)
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
    # Companies without a verified token are disabled/manual (no invented token).
    assert by_id["trendyol"]["enabled"] is False
    assert by_id["trendyol"]["board_token"] is None
    assert by_id["trendyol"]["live"] is False


def test_refresh_sources_skips_disabled_and_imports_enabled(client, monkeypatch):
    monkeypatch.setattr(opp, "fetch_lever", lambda token: _LEVER_SAMPLE)
    client.get("/opportunities")  # seed
    body = client.post("/opportunities/refresh-sources").json()
    statuses = {s["id"]: s["status"] for s in body["sources"]}
    assert statuses["dreamgames"] == "success"
    assert statuses["trendyol"] == "skipped"   # disabled/manual not refreshed
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


def test_dedupe_on_reimport(client):
    payload = {"jobs": [{
        "external_id": "dup-1", "company": "Dup Co", "title": "Junior Engineer",
        "location": "Istanbul, Turkey", "description": "x", "tags": ["Python"],
    }], "source": "manual-import"}
    first = client.post("/opportunities/import", json=payload).json()
    second = client.post("/opportunities/import", json=payload).json()
    assert first["created"] == 1
    assert second["created"] == 0 and second["updated"] == 1  # deduped, not duplicated
