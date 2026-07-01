"""Paste-a-JD bilingual outreach tests: EN/TR drafting, personalization,
framing, contact guidance, fallback, checklists, and safety guarantees."""

from app.services import llm_client, outreach

JD = """Senior Backend Engineer (Remote, EU)
Acme Cloud is hiring a backend engineer to work on our distributed platform.
You will build APIs in Python and Go. Remote within European time zones.
"""
CONTACT = {"name": "Jordan Smith", "title": "Engineering Manager", "company": "Acme Cloud"}
SKILLS = ["Python", "FastAPI", "React"]


# ----- Core drafting + fallback -----

def test_english_fallback_when_llm_unavailable(monkeypatch):
    monkeypatch.setattr(llm_client, "llm_available", lambda: False)
    result = outreach.generate(jd_text=JD, contact=CONTACT, language="en", channel="email")
    assert result["llm_used"] is False
    assert result["language"] == "en"
    assert result["channel"] == "email"
    assert result["body"] and result["subject"]
    assert "Acme Cloud" in result["body"]


def test_turkish_fallback_is_in_turkish(monkeypatch):
    monkeypatch.setattr(llm_client, "llm_available", lambda: False)
    result = outreach.generate(jd_text=JD, contact=CONTACT, language="tr", channel="email")
    assert result["llm_used"] is False
    assert result["language"] == "tr"
    assert "Merhaba" in result["body"]
    assert "teşekkür" in result["body"].lower()


def test_linkedin_note_has_no_subject(monkeypatch):
    monkeypatch.setattr(llm_client, "llm_available", lambda: False)
    result = outreach.generate(jd_text=JD, contact=CONTACT, language="en", channel="linkedin")
    assert result["channel"] == "linkedin"
    assert result["subject"] == ""
    assert result["body"]


def test_fallback_when_llm_raises(monkeypatch):
    monkeypatch.setattr(llm_client, "llm_available", lambda: True)

    def _boom(_prompt):
        raise llm_client.LLMError("simulated failure")

    monkeypatch.setattr(llm_client, "generate_json", _boom)
    result = outreach.generate(jd_text=JD, contact=CONTACT, language="en")
    assert result["llm_used"] is False
    assert result["body"]


# ----- Personalization with the saved profile's real skills -----

def test_draft_uses_profile_skills_when_present(monkeypatch):
    monkeypatch.setattr(llm_client, "llm_available", lambda: False)
    result = outreach.generate(
        jd_text=JD, contact=CONTACT, language="en", profile_skills=SKILLS
    )
    # Python/FastAPI are emphasized in the JD; React is not → not surfaced.
    assert "FastAPI" in result["relevant_skills"] or "Python" in result["relevant_skills"]
    assert "React" not in result["relevant_skills"]
    assert "FastAPI" in result["body"] or "Python" in result["body"]


def test_mentions_skill_passes_when_profile_skills_match_jd(monkeypatch):
    monkeypatch.setattr(llm_client, "llm_available", lambda: False)
    result = outreach.generate(
        jd_text=JD, contact=CONTACT, language="en", profile_skills=SKILLS
    )
    q = result["quality_checklist"]
    skill_item = next(i for i in q["items"] if i["key"] == "mentions_skill")
    assert skill_item["passed"] is True
    assert q["passed"] == q["total"]  # now every quality item can pass


def test_no_profile_keeps_generic_and_skill_item_unmet(monkeypatch):
    monkeypatch.setattr(llm_client, "llm_available", lambda: False)
    result = outreach.generate(jd_text=JD, contact=CONTACT, language="en")
    assert result["relevant_skills"] == []
    q = result["quality_checklist"]
    non_skill = [i for i in q["items"] if i["key"] != "mentions_skill"]
    assert all(i["passed"] for i in non_skill)


# ----- Region / location / work-authorization framing (never invented) -----

def test_does_not_invent_work_authorization(monkeypatch):
    monkeypatch.setattr(llm_client, "llm_available", lambda: False)
    # No note + flag off → no work-auth language at all.
    result = outreach.generate(
        jd_text=JD, contact=CONTACT, language="en", profile_skills=SKILLS,
        include_work_auth_line=False,
    )
    text = result["body"].lower()
    for term in ("visa", "sponsorship", "work authorization", "green card"):
        assert term not in text
    # Flag on but NO note provided → still nothing invented.
    result2 = outreach.generate(
        jd_text=JD, contact=CONTACT, language="en", profile_skills=SKILLS,
        include_work_auth_line=True, work_authorization_note=None,
    )
    assert "work authorization" not in result2["body"].lower()


def test_work_auth_note_used_verbatim_when_enabled(monkeypatch):
    monkeypatch.setattr(llm_client, "llm_available", lambda: False)
    note = "I hold EU citizenship and need no sponsorship."
    result = outreach.generate(
        jd_text=JD, contact=CONTACT, language="en", profile_skills=SKILLS,
        include_work_auth_line=True, work_authorization_note=note,
    )
    assert note in result["body"]


def test_turkish_location_line_only_when_enabled(monkeypatch):
    monkeypatch.setattr(llm_client, "llm_available", lambda: False)
    on = outreach.generate(
        jd_text=JD, contact=CONTACT, language="tr", profile_skills=SKILLS,
        include_location_line=True,
    )
    assert "CET" in on["body"] and "Türkiye" in on["body"]
    off = outreach.generate(
        jd_text=JD, contact=CONTACT, language="tr", profile_skills=SKILLS,
        include_location_line=False,
    )
    assert "CET" not in off["body"]


def test_region_phrase_reflected(monkeypatch):
    monkeypatch.setattr(llm_client, "llm_available", lambda: False)
    result = outreach.generate(
        jd_text=JD, contact=CONTACT, language="en", target_region="europe"
    )
    assert result["target_region"] == "europe"
    assert "Europe" in result["body"]


# ----- Contact guidance (manual search links only — no scraping/network) -----

def test_contact_guidance_roles_and_links():
    g = outreach.contact_guidance("Acme Cloud", "en")
    roles = {r["role"] for r in g["recommended_contact_roles"]}
    assert {"recruiter", "software_engineer", "engineering_manager"} <= roles
    assert g["contact_priority_order"][0] == "recruiter"
    assert len(g["manual_search_links"]) >= 4
    for link in g["manual_search_links"]:
        assert link["url"].startswith("https://")
        assert "Acme" in link["url"] or "Acme" in link["label"]


def test_outreach_module_makes_no_network_calls():
    # The service builds URL strings only — it must not import a network client.
    assert "requests" not in dir(outreach)
    assert not hasattr(outreach, "httpx")


# ----- Endpoint -----

def test_endpoint_rejects_empty_jd(client):
    resp = client.post("/outreach/draft-from-paste", json={"jd_text": "  "})
    assert resp.status_code == 400


def test_endpoint_returns_draft_with_guidance(client, monkeypatch):
    monkeypatch.setattr(llm_client, "llm_available", lambda: False)
    resp = client.post(
        "/outreach/draft-from-paste",
        json={
            "jd_text": JD,
            "contact": {"name": "Jordan", "company": "Acme Cloud"},
            "language": "tr",
            "channel": "email",
            "target_region": "remote",
            "include_location_line": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["language"] == "tr"
    assert data["body"]
    assert "quality_checklist" in data and "risk_checklist" in data
    assert "contact_guidance" in data and data["contact_guidance"]["manual_search_links"]
    assert "suggested_follow_up" in data


def test_endpoint_uses_saved_profile_skills(client, monkeypatch):
    monkeypatch.setattr(llm_client, "llm_available", lambda: False)
    # Save a profile via the resume-text endpoint so skills are extracted.
    client.post(
        "/profile/resume-text",
        json={"resume_text": "Software engineer. Skills: Python, FastAPI, SQL, Docker."},
    )
    resp = client.post(
        "/outreach/draft-from-paste",
        json={"jd_text": JD, "contact": {"company": "Acme Cloud"}, "language": "en"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["relevant_skills"]  # profile skills flowed through
    skill_item = next(
        i for i in data["quality_checklist"]["items"] if i["key"] == "mentions_skill"
    )
    assert skill_item["passed"] is True


def test_no_auto_send_routes(client):
    # The outreach surface is draft + read-only contact guidance + save-to-pipeline
    # (which only persists a reviewed draft) — never a send.
    outreach_paths = {
        r.path for r in client.app.routes if getattr(r, "path", "").startswith("/outreach")
    }
    assert outreach_paths == {
        "/outreach/draft-from-paste",
        "/outreach/contact-guidance",
        "/outreach/save-draft",
    }
    assert not any("send" in p for p in outreach_paths)


def test_contact_guidance_endpoint_is_safe_links_only(client):
    resp = client.get("/outreach/contact-guidance", params={"company": "Trendyol"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["company"] == "Trendyol"
    # Prioritized roles + manual search links the user opens themselves.
    assert data["recommended_contact_roles"]
    assert data["manual_search_links"]
    # No auto-contact: every link is just a URL string the user opens.
    assert all(l["url"].startswith("http") for l in data["manual_search_links"])


def test_contact_guidance_localizes_to_turkish(client):
    data = client.get(
        "/outreach/contact-guidance", params={"company": "Getir", "language": "tr"}
    ).json()
    labels = " ".join(r["label"] for r in data["recommended_contact_roles"]).lower()
    assert "işe alım" in labels or "yetenek" in labels
