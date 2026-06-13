"""Resume parsing service.

Extracts a simple profile from raw resume text using keyword matching.
No LLM calls yet — deterministic and offline.
"""

import re

# Canonical skill names we look for. Matching is case-insensitive and
# token-aware (so "Java" does not match inside "JavaScript").
KNOWN_SKILLS = [
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "React",
    "Next.js",
    "FastAPI",
    "Flask",
    "Django",
    "Spring Boot",
    "SQL",
    "PostgreSQL",
    "MySQL",
    "MongoDB",
    "Docker",
    "AWS",
    "Git",
    "REST API",
    "Machine Learning",
    "LLM",
    "RAG",
]


def _skill_pattern(skill: str) -> re.Pattern:
    """Build a token-aware, case-insensitive regex for one skill.

    Lookarounds prevent partial-token matches: "java" won't match the
    "java" inside "javascript", and "aws" won't match inside "flaws".
    """
    escaped = re.escape(skill.lower())
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", re.IGNORECASE)


_SKILL_PATTERNS = [(skill, _skill_pattern(skill)) for skill in KNOWN_SKILLS]


def extract_skills(resume_text: str) -> list[str]:
    """Return the canonical skills found in the resume, in canonical order."""
    text = resume_text.lower()
    return [skill for skill, pattern in _SKILL_PATTERNS if pattern.search(text)]


def extract_experience_summary(resume_text: str, max_len: int = 280) -> str:
    """Return a short plain-text summary from the start of the resume."""
    # Collapse all whitespace/newlines into single spaces.
    collapsed = re.sub(r"\s+", " ", resume_text).strip()
    if len(collapsed) <= max_len:
        return collapsed
    # Cut at the last word boundary before the limit so we don't split a word.
    truncated = collapsed[:max_len].rsplit(" ", 1)[0]
    return f"{truncated}…"


def parse_resume(raw_resume: str) -> dict:
    """Return a simple structured profile dict from resume text."""
    return {
        "skills": extract_skills(raw_resume),
        "experience_summary": extract_experience_summary(raw_resume),
    }
