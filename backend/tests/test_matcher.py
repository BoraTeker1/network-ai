"""Match-scoring tests: granularity + real profile-skill flow."""

from app.models import Job
from app.services.matcher import score_job

SKILLS = ["Python", "FastAPI", "React", "TypeScript", "SQL", "Docker"]


def _job(title, location="Remote", company="Acme"):
    return Job(title=title, location=location, company=company)


def test_strong_new_grad_swe_is_strong_target():
    r = score_job(SKILLS, _job("Software Engineer, New Grad"))
    assert r["score"] >= 75
    assert r["recommendation"] == "Strong Target"


def test_non_engineering_role_scores_low():
    r = score_job(SKILLS, _job("Marketing Manager", location="New York, NY"))
    assert r["score"] < 25
    assert r["recommendation"] in ("Low Priority", "Poor Fit")


def test_scores_are_granular_across_roles():
    # Different role areas / seniorities should NOT all collapse onto one number.
    titles = [
        "Software Engineer, New Grad",
        "Frontend Engineer (New Grad)",
        "Associate Data Engineer",
        "Backend Engineer I",
        "Junior Developer",
    ]
    scores = {t: score_job(SKILLS, _job(t))["score"] for t in titles}
    assert len(set(scores.values())) >= 4, scores


def test_profile_skills_drive_matched_skills():
    # A frontend role should surface the user's frontend skills.
    r = score_job(SKILLS, _job("Frontend Engineer, New Grad"))
    assert "React" in r["matched_skills"]
    assert "TypeScript" in r["matched_skills"]


def test_skill_area_alignment_differs_by_role():
    frontend = score_job(SKILLS, _job("Frontend Engineer, New Grad"))
    backend = score_job(SKILLS, _job("Backend Engineer, New Grad"))
    assert frontend["matched_skills"] != backend["matched_skills"]


def test_no_profile_skills_yields_zero_skill_component():
    r = score_job([], _job("Software Engineer, New Grad"))
    skill = next(b for b in r["breakdown"] if b["label"] == "Skill alignment")
    assert skill["points"] == 0
    assert r["matched_skills"] == []


def test_breakdown_components_within_bounds():
    r = score_job(SKILLS, _job("Software Engineer, New Grad"))
    for b in r["breakdown"]:
        assert 0 <= b["points"] <= b["max"]
    assert 0 <= r["score"] <= 100
