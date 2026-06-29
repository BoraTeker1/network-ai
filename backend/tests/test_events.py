"""Event recommendation tests.

Cover the safety-critical guarantees: search terms come from the strongest job
match, manual fallback links always appear, past/out-of-window events are
dropped, real provider events always carry source_url + fetched_at, ranking
favors fresh+relevant events, and the endpoint returns a stable shape with no
data. Provider HTTP is mocked — no network calls.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.models import DEMO_USER_ID, Goal, Job
from app.services import events


def _now():
    return datetime.now(timezone.utc)


@pytest.fixture(autouse=True)
def _hermetic_providers(monkeypatch):
    """No real network in tests: stub confs.tech to return nothing by default.
    Individual tests opt into provider data by overriding this."""
    monkeypatch.setattr(events, "_fetch_confs_tech_raw", lambda year, topic: [])


def _date(days_from_now):
    return (_now() + timedelta(days=days_from_now)).strftime("%Y-%m-%d")


def _ct(name, url, start, *, end=None, online=False, city=None, country=None):
    rec = {"name": name, "url": url, "startDate": start, "online": online}
    if end:
        rec["endDate"] = end
    if city:
        rec["city"] = city
    if country:
        rec["country"] = country
    return rec


@pytest.fixture
def seeded_job(db_session):
    job = Job(
        source="test", external_id="e1",
        company="Acme", title="Backend Engineer, New Grad", location="Atlanta, GA",
        url="https://example.com/apply",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def _save_profile(client):
    r = client.post("/profile/resume-text", json={
        "resume_text": "New grad. Skills: Python, FastAPI, SQL, Docker, PostgreSQL."
    })
    assert r.status_code == 200


# ----- Search-term construction -----

def test_search_context_built_from_strongest_match(client, seeded_job, db_session):
    _save_profile(client)
    assert client.post("/jobs/match-all").status_code == 200

    context, best = events.build_search_context(db_session)
    assert best is not None
    assert context["company"] == "Acme"
    assert context["role_family"] == "Backend engineering"
    # Top matched skills flow into the keyword set.
    assert any(s in context["matched_skills"] for s in ("Python", "FastAPI", "SQL"))
    assert "Atlanta, GA" == context["location"]
    assert context["company"] in context["keywords"]


def test_role_family_inference():
    assert events._role_family("Senior AI Engineer")[0] == "AI / ML engineering"
    assert events._role_family("Data Engineer")[0] == "Data engineering"
    assert events._role_family("Frontend Developer")[0] == "Frontend engineering"
    # Unknown -> safe default, never blank.
    assert events._role_family(None)[0] == "Software engineering"


# ----- Manual fallback links (no API keys) -----

def test_manual_links_returned_when_no_providers(client, seeded_job, monkeypatch):
    _save_profile(client)
    assert client.post("/jobs/match-all").status_code == 200

    data = client.get("/events/recommendations").json()
    assert data["recommendations"] == []
    assert "No verified upcoming events" in data["message"]
    links = data["search_links"]
    assert 5 <= len(links) <= 13
    # Every link is a real, prefilled URL with provider + rationale.
    for link in links:
        assert link["url"].startswith("http")
        assert link["provider"] in {"google", "kommunity", "eventbrite", "meetup",
                                    "luma", "company"}
        assert link["why"]
    # Company-specific searches appear because we know the company.
    assert any(link["provider"] == "company" for link in links)
    # Turkey-localized: Kommunity (the local tech-events platform) is surfaced.
    assert any(link["provider"] == "kommunity" for link in links)
    # Ticketmaster is gone; it must not appear as a provider anymore.
    assert "ticketmaster" not in {p["provider"] for p in data["providers"]}


def test_endpoint_stable_shape_with_no_data(client):
    """No profile, no jobs — still a usable, fully-populated response."""
    data = client.get("/events/recommendations").json()
    assert data["ready"] is False
    assert data["strongest_match"] is None
    assert data["recommendations"] == []
    # Manual links still built from generic tech-networking context.
    assert len(data["search_links"]) >= 5
    assert data["disclaimer"]
    expected = {"ready", "message", "strongest_match", "search_context", "filters",
                "providers", "recommendations", "search_links", "disclaimer"}
    assert expected <= set(data.keys())


# ----- Turkey localization of manual links -----

def test_manual_links_are_turkey_localized(client, seeded_job):
    """The keyless fallback surfaces Kommunity + Turkish communities, not US-only
    sources."""
    _save_profile(client)
    assert client.post("/jobs/match-all").status_code == 200

    links = client.get("/events/recommendations").json()["search_links"]
    km = [l for l in links if l["provider"] == "kommunity"]
    assert km, "expected at least one Kommunity link"
    assert all("kommunity.com" in l["url"] for l in km)
    # A Turkish tech-community search is present.
    assert any("Türkiye" in l["query"] or "topluluk" in l["query"].lower()
               for l in links)


def test_remote_match_nudges_turkish_hub_cities(client, remote_job, monkeypatch):
    """A remote match (no real city) nudges Turkish hub cities, never US ones."""
    _save_profile(client)
    assert client.post("/jobs/match-all").status_code == 200

    links = client.get("/events/recommendations").json()["search_links"]
    hub_labels = " ".join(l["label"] for l in links if "hub city" in l["label"].lower())
    assert hub_labels, "expected hub-city nudges for a remote match"
    assert any(city in hub_labels for city in ("İstanbul", "Ankara", "İzmir"))
    assert "Atlanta" not in hub_labels and "New York" not in hub_labels


# ----- Remote / non-city location normalization -----

@pytest.fixture
def remote_job(db_session):
    job = Job(
        source="test", external_id="r1",
        company="Notion", title="Backend Engineer, New Grad", location="Remote",
        url="https://example.com/apply",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Remote", None),
        ("remote", None),
        ("Anywhere", None),
        ("United States", None),
        ("USA", None),
        ("US", None),
        ("Multiple Locations", None),
        ("Various", None),
        ("Hybrid", None),
        ("N/A", None),
        ("Remote - US", None),
        ("Remote (USA)", None),
        ("Atlanta, GA", "Atlanta, GA"),
        ("New York", "New York"),
    ],
)
def test_normalize_event_location_values(raw, expected):
    assert events.normalize_event_location(raw, None, None) == expected


def test_normalize_prefers_user_then_goal_then_job():
    # Explicit user location wins, even over a real goal/job city.
    assert events.normalize_event_location("Remote", "Chicago", "Boston") == "Boston"
    # Goal city is used when the job is remote.
    assert events.normalize_event_location("Remote", "Chicago", None) == "Chicago"
    # Falls back to job city when nothing else is a city.
    assert events.normalize_event_location("Seattle", None, None) == "Seattle"
    # Everything remote/unknown -> None.
    assert events.normalize_event_location("Remote", "Anywhere", None) is None


def test_remote_match_resolves_to_no_city(client, remote_job, monkeypatch):
    """A remote match never resolves to a geo city; the message says so."""
    _save_profile(client)
    assert client.post("/jobs/match-all").status_code == 200

    data = client.get("/events/recommendations").json()
    assert data["search_context"]["is_remote"] is True
    assert data["search_context"]["city"] is None
    assert "remote" in data["message"].lower()


def test_remote_job_still_returns_manual_links(client, remote_job):
    _save_profile(client)
    assert client.post("/jobs/match-all").status_code == 200

    data = client.get("/events/recommendations").json()
    assert len(data["search_links"]) >= 5
    # The remote nudge adds example hub-city searches.
    assert any("hub city" in link["label"].lower() for link in data["search_links"])
    # No link claims a fake local city; queries fall back to "near me".
    assert any("near me" in link["query"].lower() for link in data["search_links"])


def test_confs_tech_provider_ok_when_api_works_but_empty(client, remote_job, monkeypatch):
    """confs.tech reachable but with no in-window events still reports ok/empty."""
    _save_profile(client)
    assert client.post("/jobs/match-all").status_code == 200
    monkeypatch.setattr(events, "_fetch_confs_tech_raw", lambda year, topic: [])

    data = client.get("/events/recommendations").json()
    ct = next(p for p in data["providers"] if p["provider"] == "confs_tech")
    assert ct["configured"] is True
    assert ct["ok"] is True  # call succeeded even though results are empty
    assert ct["count"] == 0
    assert data["recommendations"] == []


def test_user_location_overrides_remote_job(client, remote_job, monkeypatch, db_session):
    _save_profile(client)
    assert client.post("/jobs/match-all").status_code == 200

    # With an explicit ?location=Boston, the remote job is overridden.
    context, _ = events.build_search_context(db_session, location_override="Boston")
    assert context["city"] == "Boston"
    assert context["is_remote"] is False


def test_goal_city_used_when_job_is_remote(client, remote_job, db_session):
    _save_profile(client)
    assert client.post("/jobs/match-all").status_code == 200
    db_session.add(Goal(user_id=DEMO_USER_ID, target_role="Backend Engineer",
                        target_location="Denver"))
    db_session.commit()

    context, _ = events.build_search_context(db_session)
    assert context["city"] == "Denver"
    assert context["is_remote"] is False


# ----- confs.tech provider (real conferences, no key) -----

def test_topics_for_family_mapping():
    assert "data" in events._topics_for_family("AI / ML engineering")
    assert "security" in events._topics_for_family("Security engineering")
    assert "android" in events._topics_for_family("Mobile engineering")
    # Unknown family -> safe default, never empty.
    assert events._topics_for_family("Nonexistent") == events._CONFS_TECH_DEFAULT_TOPICS


def test_confs_tech_returns_real_conferences(client, seeded_job, monkeypatch):
    _save_profile(client)
    assert client.post("/jobs/match-all").status_code == 200

    def stub(year, topic):
        if topic == "general":
            return [
                _ct("Backend Conf ATL", "https://confs/atl", _date(20),
                    city="Atlanta", country="USA"),
                _ct("PyOnline 2026", "https://confs/online", _date(40), online=True),
            ]
        return []

    monkeypatch.setattr(events, "_fetch_confs_tech_raw", stub)

    data = client.get("/events/recommendations?days_ahead=90").json()
    ct = next(p for p in data["providers"] if p["provider"] == "confs_tech")
    assert ct["configured"] is True and ct["ok"] is True
    recs = data["recommendations"]
    assert len(recs) == 2
    for rec in recs:
        assert rec["source_name"] == "confs_tech"
        assert rec["source_url"].startswith("http")
        assert rec["fetched_at"]
        assert rec["event_type"] == "conference"
        assert rec["freshness_label"] in events.FRESHNESS_LABELS


def test_confs_tech_filters_past_and_out_of_window(client, seeded_job, monkeypatch):
    _save_profile(client)
    assert client.post("/jobs/match-all").status_code == 200

    def stub(year, topic):
        if topic == "general":
            return [
                _ct("Past Conf", "https://confs/past", _date(-10)),
                _ct("Far Conf", "https://confs/far", _date(200)),
                _ct("In Window", "https://confs/ok", _date(15), city="Denver"),
            ]
        return []

    monkeypatch.setattr(events, "_fetch_confs_tech_raw", stub)

    urls = {
        r["source_url"]
        for r in client.get("/events/recommendations?days_ahead=30").json()["recommendations"]
    }
    assert urls == {"https://confs/ok"}


def test_confs_tech_ongoing_multiday_not_dropped(client, seeded_job, monkeypatch):
    _save_profile(client)
    assert client.post("/jobs/match-all").status_code == 200

    def stub(year, topic):
        # Started yesterday, ends in 2 days -> still upcoming/ongoing, keep it.
        if topic == "general":
            return [_ct("Ongoing Summit", "https://confs/ongoing",
                        _date(-1), end=_date(2), city="Austin")]
        return []

    monkeypatch.setattr(events, "_fetch_confs_tech_raw", stub)
    urls = {r["source_url"] for r in
            client.get("/events/recommendations").json()["recommendations"]}
    assert "https://confs/ongoing" in urls


def test_confs_tech_include_online_false_drops_pure_online(client, seeded_job, monkeypatch):
    _save_profile(client)
    assert client.post("/jobs/match-all").status_code == 200

    def stub(year, topic):
        if topic == "general":
            return [
                _ct("Pure Online", "https://confs/online", _date(10), online=True),
                _ct("In Person", "https://confs/inperson", _date(10), city="Miami"),
            ]
        return []

    monkeypatch.setattr(events, "_fetch_confs_tech_raw", stub)
    urls = {
        r["source_url"] for r in
        client.get("/events/recommendations?include_online=false").json()["recommendations"]
    }
    assert urls == {"https://confs/inperson"}  # pure-online dropped


def test_confs_tech_dedupes_same_conf_across_topics(client, seeded_job, monkeypatch):
    _save_profile(client)
    assert client.post("/jobs/match-all").status_code == 200

    # Same conference URL appears in two topic files -> surfaced once.
    dup = _ct("Cross-listed Conf", "https://confs/dup", _date(12), city="Seattle")
    monkeypatch.setattr(events, "_fetch_confs_tech_raw",
                        lambda year, topic: [dup])

    recs = client.get("/events/recommendations").json()["recommendations"]
    assert sum(1 for r in recs if r["source_url"] == "https://confs/dup") == 1


def test_confs_tech_provider_ok_when_all_topics_fail(client, seeded_job, monkeypatch):
    _save_profile(client)
    assert client.post("/jobs/match-all").status_code == 200

    def boom(year, topic):
        raise RuntimeError("github down")

    monkeypatch.setattr(events, "_fetch_confs_tech_raw", boom)
    data = client.get("/events/recommendations").json()
    ct = next(p for p in data["providers"] if p["provider"] == "confs_tech")
    assert ct["ok"] is False
    assert len(data["search_links"]) >= 5  # manual fallback still works
