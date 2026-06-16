"""Profile/resume parsing tests."""

from app.services.resume_parser import (
    extract_experience_summary,
    extract_skills,
    parse_resume,
)


def test_extract_skills_is_token_aware():
    # "Java" must NOT be matched inside "JavaScript".
    skills = extract_skills("Senior JavaScript and TypeScript developer")
    assert "JavaScript" in skills
    assert "TypeScript" in skills
    assert "Java" not in skills


def test_extract_skills_matches_standalone_java():
    skills = extract_skills("Built services in Java and Python")
    assert "Java" in skills
    assert "Python" in skills


def test_extract_skills_canonical_order_no_dupes():
    skills = extract_skills("python PYTHON Python react React")
    assert skills.count("Python") == 1
    assert skills.count("React") == 1
    # Canonical order: Python is listed before React in KNOWN_SKILLS.
    assert skills.index("Python") < skills.index("React")


def test_experience_summary_truncates_on_word_boundary():
    text = "word " * 200
    summary = extract_experience_summary(text, max_len=50)
    assert len(summary) <= 51  # 50 + ellipsis
    assert summary.endswith("…")


def test_parse_resume_shape():
    parsed = parse_resume("Python, FastAPI, Docker engineer")
    assert set(parsed.keys()) == {"skills", "experience_summary"}
    assert "Python" in parsed["skills"]
