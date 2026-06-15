"""Job matching/ranking service.

Scores stored jobs against the saved demo-user profile with a simple,
deterministic 0-100 method. No LLM calls.

The source (SimplifyJobs) gives us only title/company/location — there is no
job description — so the rubric weights the signals we actually have. Role fit,
new-grad signal, and location form the backbone; skill overlap is a bonus that
applies when a profile skill appears in the title. This keeps the 4-tier labels
meaningful: a genuine new-grad SWE role can reach "Strong Target".

Score breakdown (max 100):
  - role-title fit ........... up to 40  (backend / AI / SWE flavored)
  - entry-level / new-grad ... up to 30
  - location ................. up to 15
  - skill overlap (bonus) .... up to 15  (title-only, so usually small)
"""

import json
import re

from sqlalchemy.orm import Session

from ..models import DEMO_USER_ID, Job, JobMatch, Profile
from . import strategy

# Strong signals that a role fits a backend/AI/new-grad SWE track.
_STRONG_ROLE_TERMS = [
    "software engineer",
    "software developer",
    "backend",
    "back end",
    "back-end",
    "full stack",
    "full-stack",
    "data engineer",
    "machine learning",
    "ml engineer",
    "ai engineer",
    "ai/ml",
    "artificial intelligence",
    "data scientist",
    "platform engineer",
    "infrastructure engineer",
    "sde",
    "swe",
]
# Weaker but still relevant role signals.
_GENERIC_ROLE_TERMS = ["engineer", "developer", "programmer", "analyst"]

# Phrases that indicate an entry-level / new-grad / intern posting.
_ENTRY_TERMS = [
    "new grad",
    "new graduate",
    "entry level",
    "entry-level",
    "early career",
    "early-career",
    "junior",
    "associate",
    "graduate",
    "campus",
    "university hire",
    "university grad",
    "rotational",
    "intern",
]


def _token_pattern(term: str) -> re.Pattern:
    """Token-aware, case-insensitive matcher (same idea as the resume parser)."""
    return re.compile(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", re.IGNORECASE)


def get_demo_profile(db: Session) -> Profile | None:
    """Return the single demo-user profile, or None if not saved yet."""
    return db.query(Profile).filter(Profile.user_id == DEMO_USER_ID).first()


def _profile_skills(profile: Profile) -> list[str]:
    return json.loads(profile.skills) if profile.skills else []


def _job_text(job: Job) -> str:
    """Searchable text for a job (no description available from SimplifyJobs)."""
    parts = [job.title, job.company, job.location]
    return " ".join(p for p in parts if p)


def _recommendation(score: int) -> str:
    """4-tier, decision-oriented label from the total score.

    Delegates to the strategy service so the label thresholds live in one place.
    """
    return strategy.label_for_score(score)


def score_job(profile_skills: list[str], job: Job) -> dict:
    """Score one job and return score + a structured, explainable breakdown.

    Keys: score, recommendation, explanation, matched_skills, missing_skills,
    and breakdown (a labeled component list for the match card).
    """
    text = _job_text(job)
    text_lower = text.lower()
    title_lower = (job.title or "").lower()
    location_lower = (job.location or "").lower()
    reasons: list[str] = []

    # --- 1. Role-title fit (up to 40) ---
    if any(term in title_lower for term in _STRONG_ROLE_TERMS):
        role_points = 40
        role_detail = "Strong backend/AI/SWE title"
    elif any(_token_pattern(term).search(title_lower) for term in _GENERIC_ROLE_TERMS):
        role_points = 20
        role_detail = "General engineering/developer title"
    else:
        role_points = 0
        role_detail = "Title isn't clearly an engineering role"
    reasons.append(f"Role fit (+{role_points})")

    # --- 2. Entry-level / new-grad signal (up to 30) ---
    ends_with_level = bool(re.search(r"\b(i|1)\s*$", title_lower))
    if any(term in title_lower for term in _ENTRY_TERMS) or ends_with_level:
        entry_points = 30
        entry_detail = "New-grad / entry-level signal detected"
    else:
        entry_points = 0
        entry_detail = "No explicit new-grad signal in the title"
    reasons.append(f"New-grad signal (+{entry_points})")

    # --- 3. Location (up to 15) ---
    if "remote" in location_lower:
        location_points = 15
        location_detail = "Remote-friendly"
    elif location_lower.strip():
        location_points = 7
        location_detail = f"On-site: {job.location}"
    else:
        location_points = 0
        location_detail = "Location unknown"
    reasons.append(f"Location (+{location_points})")

    # --- 4. Skill overlap bonus (up to 15) ---
    # Title-only text, so this is usually small — a bonus, not the backbone.
    matched_skills = [s for s in profile_skills if _token_pattern(s).search(text_lower)]
    missing_skills = [s for s in profile_skills if s not in matched_skills]
    if profile_skills:
        skill_points = min(15, round(15 * len(matched_skills) / len(profile_skills)))
    else:
        skill_points = 0
    if matched_skills:
        skill_detail = (
            f"{len(matched_skills)}/{len(profile_skills)} profile skills appear "
            f"in this posting's title"
        )
    elif profile_skills:
        skill_detail = "No profile skills in the title (titles rarely list skills)"
    else:
        skill_detail = "No skills on your profile yet — save a resume first"
    reasons.append(f"Skill overlap (+{skill_points})")

    score = role_points + entry_points + location_points + skill_points
    score = max(0, min(100, score))

    breakdown = [
        {"label": "Role fit", "points": role_points, "max": 40, "detail": role_detail},
        {"label": "New-grad signal", "points": entry_points, "max": 30, "detail": entry_detail},
        {"label": "Location", "points": location_points, "max": 15, "detail": location_detail},
        {"label": "Skill overlap", "points": skill_points, "max": 15, "detail": skill_detail},
    ]

    return {
        "score": score,
        "recommendation": _recommendation(score),
        "next_best_action": strategy.next_best_action(score, job, len(matched_skills)),
        "explanation": " | ".join(reasons),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "breakdown": breakdown,
    }


def _upsert_match(db: Session, profile: Profile, job: Job, result: dict) -> JobMatch:
    """Create or update the JobMatch row for this profile/job pair."""
    match = (
        db.query(JobMatch)
        .filter(JobMatch.profile_id == profile.id, JobMatch.job_id == job.id)
        .first()
    )
    reasons_blob = json.dumps(
        {
            "explanation": result["explanation"],
            "recommendation": result["recommendation"],
            "next_best_action": result["next_best_action"],
            "matched_skills": result["matched_skills"],
            "missing_skills": result["missing_skills"],
            "breakdown": result["breakdown"],
        }
    )
    if match is None:
        match = JobMatch(profile_id=profile.id, job_id=job.id)
        db.add(match)
    match.score = float(result["score"])
    match.reasons = reasons_blob
    return match


def match_job(db: Session, job_id: int) -> dict:
    """Score a single job against the demo profile and upsert the match."""
    profile = get_demo_profile(db)
    if profile is None:
        raise ValueError("No profile saved yet — paste a resume first.")

    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise LookupError(f"Job {job_id} not found")

    result = score_job(_profile_skills(profile), job)
    _upsert_match(db, profile, job, result)
    db.commit()

    return {
        "job_id": job.id,
        "company": job.company,
        "title": job.title,
        "location": job.location,
        "url": job.url,
        "match_score": result["score"],
        "recommendation": result["recommendation"],
        "next_best_action": result["next_best_action"],
        "explanation": result["explanation"],
        "matched_skills": result["matched_skills"],
        "missing_skills": result["missing_skills"],
        "breakdown": result["breakdown"],
    }


def match_all(db: Session) -> dict:
    """Score every stored job against the demo profile."""
    profile = get_demo_profile(db)
    if profile is None:
        raise ValueError("No profile saved yet — paste a resume first.")

    skills = _profile_skills(profile)
    jobs = db.query(Job).all()
    for job in jobs:
        result = score_job(skills, job)
        _upsert_match(db, profile, job, result)
    db.commit()

    return {"profile_id": profile.id, "matched_jobs": len(jobs)}


def ranked_matches(db: Session, limit: int = 100) -> list[dict]:
    """Return jobs joined with their match scores, highest score first."""
    profile = get_demo_profile(db)
    if profile is None:
        return []

    rows = (
        db.query(JobMatch, Job)
        .join(Job, Job.id == JobMatch.job_id)
        .filter(JobMatch.profile_id == profile.id)
        .order_by(JobMatch.score.desc(), Job.id.desc())
        .limit(min(limit, 500))
        .all()
    )

    results: list[dict] = []
    for match, job in rows:
        try:
            blob = json.loads(match.reasons) if match.reasons else {}
        except (ValueError, TypeError):
            blob = {}
        results.append(
            {
                "job_id": job.id,
                "company": job.company,
                "title": job.title,
                "location": job.location,
                "url": job.url,
                "match_score": match.score,
                "recommendation": blob.get("recommendation")
                or _recommendation(int(match.score)),
                "next_best_action": blob.get("next_best_action")
                or strategy.next_best_action(
                    match.score, job, len(blob.get("matched_skills", []))
                ),
                "explanation": blob.get("explanation"),
                "matched_skills": blob.get("matched_skills", []),
                "missing_skills": blob.get("missing_skills", []),
                "breakdown": blob.get("breakdown", []),
            }
        )
    return results
