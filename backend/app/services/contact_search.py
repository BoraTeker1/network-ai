"""Contact search suggestion service.

Generates MANUAL search queries/links only — no scraping, no automation,
no inventing specific people. The user opens these links and decides.
"""

import urllib.parse

_GOOGLE = "https://www.google.com/search?q="
_LINKEDIN_PEOPLE = "https://www.linkedin.com/search/results/people/?keywords="

# (label, persona keywords) for the five contact categories we suggest.
_PERSONAS = [
    ("Recruiters", "recruiter"),
    ("Technical recruiters", "technical recruiter software engineer"),
    ("Engineering managers", "engineering manager"),
    ("Software engineers", "software engineer"),
    ("New grad / early-career engineers", "new grad software engineer"),
]


def _google_url(query: str) -> str:
    return _GOOGLE + urllib.parse.quote_plus(query)


def _linkedin_url(keywords: str) -> str:
    return _LINKEDIN_PEOPLE + urllib.parse.quote_plus(keywords)


def contact_searches_for_job(company: str, role_title: str | None = None) -> list[dict]:
    """Return manual contact-search suggestions for a company/role.

    Each item has: label, query, google_search_url, linkedin_search_url.
    """
    company = (company or "").strip()

    suggestions: list[dict] = []
    for label, persona in _PERSONAS:
        # Google: restrict to LinkedIn profile pages via site: operator.
        google_query = f"site:linkedin.com/in {company} {persona}".strip()
        # LinkedIn people search uses plain keywords (no site: operator).
        linkedin_keywords = f"{company} {persona}".strip()
        suggestions.append(
            {
                "label": label,
                "query": google_query,
                "google_search_url": _google_url(google_query),
                "linkedin_search_url": _linkedin_url(linkedin_keywords),
            }
        )
    return suggestions
