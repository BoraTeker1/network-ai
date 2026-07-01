"""Job matching/ranking service.

Scores stored jobs against the saved demo-user profile with a deterministic
0-100 method. No LLM calls.

The source (SimplifyJobs) gives us only title/company/location — there is no
job description — so the rubric weights the signals we actually have. To avoid
the old "everything clusters at one number" problem, each component is GRADED
(several tiers, not just on/off) and skill alignment is computed from the user's
ACTUAL saved skills mapped onto the role's area. Two different roles therefore
rarely land on the exact same score.

Score breakdown (max 100):
  - role-title fit ........... up to 42  (graded: SWE > AI/ML > specialized > generic)
  - entry-level / new-grad ... up to 26  (graded by how explicit the signal is)
  - location ................. up to 14  (remote > hybrid > on-site > unknown)
  - skill alignment .......... up to 18  (YOUR skills mapped onto the role's area)
"""

import json
import re

from sqlalchemy.orm import Session

from ..models import Job, JobMatch, Profile
from . import strategy

# --- Role-title tiers (most specific wins) ---
# Exact software-engineering titles — the bullseye for a new-grad SWE search.
_SWE_TERMS = ["software engineer", "software developer", "sde", "swe"]
# AI / ML / data-science roles.
_AIML_TERMS = [
    "machine learning",
    "ml engineer",
    "ai engineer",
    "ai/ml",
    "artificial intelligence",
    "data scientist",
    "applied scientist",
    "deep learning",
    "nlp",
]
# Specialized engineering roles (still strong, slightly below a plain SWE title).
_SPECIALIZED_TERMS = [
    "backend",
    "back end",
    "back-end",
    "full stack",
    "full-stack",
    "frontend",
    "front end",
    "front-end",
    "data engineer",
    "platform engineer",
    "infrastructure engineer",
    "devops",
    "cloud engineer",
    "security engineer",
    "site reliability",
    "mobile engineer",
    "android",
    "ios",
]
# Weak but still relevant role signals.
_GENERIC_ROLE_TERMS = ["engineer", "developer", "programmer", "analyst"]

# --- Entry-level / seniority tiers (graded by explicitness) ---
_SENIORITY_TIERS = [
    (26, "Explicit new-grad role",
     ["new grad", "new graduate", "university grad", "university hire",
      "college grad", "campus"]),
    (23, "Entry-level / early-career", ["entry level", "entry-level",
                                        "early career", "early-career"]),
    (20, "Graduate / rotational program", ["graduate", "rotational"]),
    (18, "Associate level", ["associate"]),
    (17, "Junior level", ["junior"]),
    (10, "Internship", ["intern"]),
]

# --- Skill alignment: map a role's area keyword -> the canonical skills it implies.
# Lets a profile's skills actually move the score even though we only have a
# title (SimplifyJobs has no descriptions). Keys are matched token-aware.
_AREA_SKILLS = {
    "backend": ["Python", "Java", "FastAPI", "Flask", "Django", "Spring Boot",
                "SQL", "PostgreSQL", "MySQL", "MongoDB", "REST API", "Docker"],
    "back end": ["Python", "Java", "FastAPI", "Flask", "Django", "SQL",
                 "PostgreSQL", "REST API", "Docker"],
    "back-end": ["Python", "Java", "FastAPI", "Flask", "Django", "SQL",
                 "PostgreSQL", "REST API", "Docker"],
    "full stack": ["JavaScript", "TypeScript", "React", "Next.js", "Python",
                   "SQL", "PostgreSQL", "REST API", "Docker"],
    "full-stack": ["JavaScript", "TypeScript", "React", "Next.js", "Python",
                   "SQL", "PostgreSQL", "REST API", "Docker"],
    "frontend": ["JavaScript", "TypeScript", "React", "Next.js"],
    "front end": ["JavaScript", "TypeScript", "React", "Next.js"],
    "front-end": ["JavaScript", "TypeScript", "React", "Next.js"],
    "web": ["JavaScript", "TypeScript", "React", "Next.js", "REST API"],
    "data engineer": ["Python", "SQL", "PostgreSQL", "MySQL", "AWS", "Docker"],
    "data scientist": ["Python", "SQL", "Machine Learning"],
    "data": ["Python", "SQL", "PostgreSQL", "Machine Learning"],
    "machine learning": ["Python", "Machine Learning", "LLM", "RAG"],
    "ml": ["Python", "Machine Learning", "LLM", "RAG"],
    "ai": ["Python", "Machine Learning", "LLM", "RAG"],
    "artificial intelligence": ["Python", "Machine Learning", "LLM", "RAG"],
    "applied scientist": ["Python", "Machine Learning", "LLM", "RAG"],
    "nlp": ["Python", "Machine Learning", "LLM", "RAG"],
    "platform": ["Docker", "AWS", "Python", "Git"],
    "infrastructure": ["Docker", "AWS", "Git", "Python"],
    "devops": ["Docker", "AWS", "Git"],
    "cloud": ["AWS", "Docker"],
    "site reliability": ["Docker", "AWS", "Git", "Python"],
    "sre": ["Docker", "AWS", "Git", "Python"],
    "java": ["Java", "Spring Boot"],
    "python": ["Python", "FastAPI", "Flask", "Django"],
    "android": ["Java"],
}
# Broadly-applicable skills, used when a role is clearly engineering but names
# no specific area (e.g. a plain "Software Engineer" title).
_GENERAL_SWE_SKILLS = ["Python", "Java", "JavaScript", "TypeScript", "SQL",
                       "Git", "REST API", "Docker"]


def _token_pattern(term: str) -> re.Pattern:
    """Token-aware, case-insensitive matcher (same idea as the resume parser)."""
    return re.compile(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", re.IGNORECASE)


def get_profile(db: Session, user_id: str) -> Profile | None:
    """Return the given user's profile, or None if not saved yet."""
    return db.query(Profile).filter(Profile.user_id == user_id).first()


def _profile_skills(profile: Profile) -> list[str]:
    return json.loads(profile.skills) if profile.skills else []


def _job_text(job: Job) -> str:
    """Searchable text for a job (no description available from SimplifyJobs)."""
    parts = [job.title, job.company, job.location]
    return " ".join(p for p in parts if p)


def _recommendation(score: int) -> str:
    """4-tier, decision-oriented label (thresholds live in the strategy service)."""
    return strategy.label_for_score(score)


def _role_score(title_lower: str) -> tuple[int, str]:
    """Graded role-title fit (most specific tier wins)."""
    if any(t in title_lower for t in _SWE_TERMS):
        return 42, "Direct software-engineering title"
    if any(_token_pattern(t).search(title_lower) for t in _AIML_TERMS):
        return 38, "AI / ML / data-science role"
    if any(t in title_lower for t in _SPECIALIZED_TERMS):
        return 36, "Specialized engineering role"
    if any(_token_pattern(t).search(title_lower) for t in _GENERIC_ROLE_TERMS):
        return 22, "General engineering/developer title"
    return 0, "Title isn't clearly an engineering role"


def _seniority_score(title_lower: str) -> tuple[int, str]:
    """Graded new-grad / entry-level signal."""
    for points, detail, terms in _SENIORITY_TIERS:
        if any(t in title_lower for t in terms):
            return points, detail
    # A trailing roman/arabic "I" (e.g. "Engineer I") implies the first level.
    if re.search(r"\b(i|1)\s*$", title_lower):
        return 13, "Level-1 title (e.g. 'Engineer I')"
    return 0, "No explicit new-grad signal in the title"


def _location_score(location_lower: str, raw_location: str | None) -> tuple[int, str]:
    """Graded location desirability."""
    if "remote" in location_lower:
        return 14, "Remote-friendly"
    if "hybrid" in location_lower:
        return 10, "Hybrid"
    if location_lower.strip():
        return 7, f"On-site: {raw_location}"
    return 0, "Location unknown"


def _skill_alignment(profile_skills: list[str], title_lower: str,
                     text_lower: str, role_points: int) -> tuple[int, list[str], list[str], str]:
    """Score the user's ACTUAL skills against the role's area.

    Returns (points, matched_skills, missing_skills, detail). Different roles map
    to different area skills, so the user's specific skill set spreads the score
    out instead of collapsing every posting onto one number.
    """
    if not profile_skills:
        return 0, [], list(profile_skills), (
            "No skills on your profile yet — save a resume first"
        )

    profile_set = set(profile_skills)
    # 1) Skill names that literally appear in the posting (rare but strong).
    direct = {s for s in profile_skills if _token_pattern(s).search(text_lower)}
    # 2) Skills implied by the role's area keyword(s) in the title.
    area_relevant: set[str] = set()
    for keyword, skills in _AREA_SKILLS.items():
        if _token_pattern(keyword).search(title_lower):
            area_relevant.update(skills)
    relevant = direct | (area_relevant & profile_set)
    # 3) Fallback: a clearly-engineering role with no named area still rewards
    #    broadly-applicable SWE skills the user has.
    if not relevant and role_points >= 36:
        relevant = profile_set & set(_GENERAL_SWE_SKILLS)

    matched = [s for s in profile_skills if s in relevant]  # canonical order
    missing = [s for s in profile_skills if s not in relevant]

    frac = len(matched) / len(profile_skills)
    points = round(18 * frac)
    # Small extra credit when a skill is named outright in the posting.
    points = min(18, points + 3 * len(direct))

    if matched:
        detail = (
            f"{len(matched)}/{len(profile_skills)} of your skills fit this role's "
            f"area: {', '.join(matched[:4])}"
            + ("…" if len(matched) > 4 else "")
        )
    else:
        detail = "None of your saved skills line up with this role's area"
    return points, matched, missing, detail


def score_job(profile_skills: list[str], job: Job) -> dict:
    """Score one job and return score + a structured, explainable breakdown.

    Keys: score, recommendation, next_best_action, explanation, matched_skills,
    missing_skills, and breakdown (a labeled component list for the match card).
    """
    text_lower = _job_text(job).lower()
    title_lower = (job.title or "").lower()
    location_lower = (job.location or "").lower()

    role_points, role_detail = _role_score(title_lower)
    entry_points, entry_detail = _seniority_score(title_lower)
    location_points, location_detail = _location_score(location_lower, job.location)
    skill_points, matched_skills, missing_skills, skill_detail = _skill_alignment(
        profile_skills, title_lower, text_lower, role_points
    )

    score = role_points + entry_points + location_points + skill_points
    score = max(0, min(100, score))

    reasons = [
        f"Role fit (+{role_points})",
        f"New-grad signal (+{entry_points})",
        f"Location (+{location_points})",
        f"Skill alignment (+{skill_points})",
    ]
    breakdown = [
        {"label": "Role fit", "points": role_points, "max": 42, "detail": role_detail},
        {"label": "New-grad signal", "points": entry_points, "max": 26, "detail": entry_detail},
        {"label": "Location", "points": location_points, "max": 14, "detail": location_detail},
        {"label": "Skill alignment", "points": skill_points, "max": 18, "detail": skill_detail},
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


def match_job(db: Session, job_id: int, user_id: str) -> dict:
    """Score a single job against the user's profile and upsert the match."""
    profile = get_profile(db, user_id)
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


def match_all(db: Session, user_id: str) -> dict:
    """Score every stored job against the user's profile."""
    profile = get_profile(db, user_id)
    if profile is None:
        raise ValueError("No profile saved yet — paste a resume first.")

    skills = _profile_skills(profile)
    jobs = db.query(Job).all()
    for job in jobs:
        result = score_job(skills, job)
        _upsert_match(db, profile, job, result)
    db.commit()

    return {"profile_id": profile.id, "matched_jobs": len(jobs)}


def ranked_matches(db: Session, user_id: str, limit: int = 100) -> list[dict]:
    """Return the user's jobs+match scores, highest score first."""
    profile = get_profile(db, user_id)
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
