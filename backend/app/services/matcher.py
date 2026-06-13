"""Job matching/ranking service.

Scores stored jobs against the saved demo-user profile with a simple,
deterministic 0-100 method. No LLM calls.

Score breakdown (max 100):
  - skill overlap ............ up to 50
  - role-title fit ........... up to 25  (backend / AI / SWE flavored)
  - entry-level / new-grad ... up to 15
  - location ................. up to 10
"""

import json
import re

from sqlalchemy.orm import Session

from ..models import DEMO_USER_ID, Job, JobMatch, Profile

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


def score_job(profile_skills: list[str], job: Job) -> dict:
    """Return {score, explanation, matched_skills, missing_skills} for one job."""
    text = _job_text(job)
    text_lower = text.lower()
    title_lower = (job.title or "").lower()
    location_lower = (job.location or "").lower()
    reasons: list[str] = []

    # --- 1. Skill overlap (up to 50) ---
    matched_skills = [s for s in profile_skills if _token_pattern(s).search(text_lower)]
    missing_skills = [s for s in profile_skills if s not in matched_skills]
    if profile_skills:
        skill_points = round(50 * len(matched_skills) / len(profile_skills))
    else:
        skill_points = 0
    if matched_skills:
        reasons.append(
            f"Skill overlap: {len(matched_skills)}/{len(profile_skills)} "
            f"profile skills matched (+{skill_points})"
        )
    else:
        reasons.append("Skill overlap: no profile skills found in job text (+0)")

    # --- 2. Role-title fit (up to 25) ---
    if any(term in title_lower for term in _STRONG_ROLE_TERMS):
        role_points = 25
        reasons.append("Role fit: strong backend/AI/SWE title (+25)")
    elif any(_token_pattern(term).search(title_lower) for term in _GENERIC_ROLE_TERMS):
        role_points = 12
        reasons.append("Role fit: general engineering/developer title (+12)")
    else:
        role_points = 0
        reasons.append("Role fit: title not clearly engineering (+0)")

    # --- 3. Entry-level / new-grad signal (up to 15) ---
    ends_with_level = bool(re.search(r"\b(i|1)\s*$", title_lower))
    if any(term in title_lower for term in _ENTRY_TERMS) or ends_with_level:
        entry_points = 15
        reasons.append("Entry-level/new-grad signal detected (+15)")
    else:
        entry_points = 0
        reasons.append("Entry-level signal: none detected (+0)")

    # --- 4. Location (up to 10) ---
    if "remote" in location_lower:
        location_points = 10
        reasons.append("Location: remote-friendly (+10)")
    elif location_lower.strip():
        location_points = 5
        reasons.append("Location: on-site/known location (+5)")
    else:
        location_points = 0
        reasons.append("Location: unknown (+0)")

    score = skill_points + role_points + entry_points + location_points
    score = max(0, min(100, score))

    return {
        "score": score,
        "explanation": " | ".join(reasons),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
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
            "matched_skills": result["matched_skills"],
            "missing_skills": result["missing_skills"],
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
        "match_score": result["score"],
        "explanation": result["explanation"],
        "matched_skills": result["matched_skills"],
        "missing_skills": result["missing_skills"],
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
                "explanation": blob.get("explanation"),
                "matched_skills": blob.get("matched_skills", []),
                "missing_skills": blob.get("missing_skills", []),
            }
        )
    return results
