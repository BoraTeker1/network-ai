"""Compliant contact-discovery architecture.

PRINCIPLES:
- NO scraping of LinkedIn or random websites. Ever.
- NO invented contact info. Providers must return real, sourced data.
- Manual entry is fully supported today. API providers (Hunter, People Data
  Labs) are PLACEHOLDERS: the interface exists, but no network calls are made
  and nothing runs unless a key is configured.
- Missing keys never raise a 500 — discovery returns a helpful message instead.

To add a real provider later: implement `discover()` to call the provider's API
(respecting its ToS), set `email_confidence`/`source`, and return the same dict
shape. Keep manual-first behavior intact.
"""

from abc import ABC, abstractmethod

from .. import config


def _why_relevant(contact_type: str, goal: dict | None, company: str | None) -> str:
    goal_text = (goal or {}).get("outreach_goal") or "advice"
    base = {
        "recruiter": "Recruiters can confirm whether the role is open to new grads and how to apply.",
        "technical_recruiter": "Technical recruiters screen engineering candidates and can flag what to highlight.",
        "hiring_manager": "The hiring manager owns the role and decides who advances.",
        "engineer": "An engineer on the team can share honest day-to-day context — ideal for an advice-first ask.",
        "alumni": "Shared background makes a warm, low-pressure intro more natural.",
        "founder": "At smaller companies a founder may respond directly to a thoughtful note.",
    }.get(contact_type, "Relevant to your outreach goal.")
    return f"{base} Aligns with your goal of '{goal_text}'" + (
        f" at {company}." if company else "."
    )


def _risk_note(source: str) -> str:
    if source == "manual":
        return "You added this contact manually — verify the email before sending."
    return "Returned by a configured compliant provider; review before sending."


class ContactDiscoveryProvider(ABC):
    """Interface every discovery provider implements."""

    name: str = "provider"

    @abstractmethod
    def available(self) -> bool:
        """True only when the provider is configured (e.g. API key present)."""

    @abstractmethod
    def discover(
        self, *, company: str, contact_type: str, max_results: int,
        job: dict, goal: dict,
    ) -> list[dict]:
        """Return contact dicts. Must never scrape or invent data."""


class ManualProvider(ContactDiscoveryProvider):
    """Surfaces contacts the user already added manually for this company.

    This is the only provider that returns results today — and only from data
    the user themselves entered.
    """

    name = "manual"

    def __init__(self, existing_contacts: list[dict]):
        self._contacts = existing_contacts

    def available(self) -> bool:
        return True

    def discover(self, *, company, contact_type, max_results, job, goal) -> list[dict]:
        company_l = (company or "").lower()
        results = []
        for c in self._contacts:
            if company_l and (c.get("company") or "").lower() != company_l:
                continue
            if contact_type and c.get("contact_type") and c["contact_type"] != contact_type:
                continue
            results.append(
                {
                    "id": c.get("id"),
                    "name": c.get("name"),
                    "title": c.get("title"),
                    "company": c.get("company"),
                    "email": c.get("email"),
                    "email_confidence": c.get("email_confidence"),
                    "source": "manual",
                    "contact_type": c.get("contact_type"),
                    "why_relevant": c.get("why_relevant")
                    or _why_relevant(c.get("contact_type") or contact_type, goal, company),
                    "risk_note": c.get("risk_note") or _risk_note("manual"),
                }
            )
        return results[:max_results]


class HunterProvider(ContactDiscoveryProvider):
    """Placeholder for Hunter.io. No network call until implemented + keyed."""

    name = "hunter"

    def available(self) -> bool:
        return bool(config.get_hunter_api_key())

    def discover(self, *, company, contact_type, max_results, job, goal) -> list[dict]:
        # Intentionally not implemented — wiring a real, ToS-compliant call is a
        # later phase. Returning [] keeps the endpoint safe and non-failing.
        return []


class PeopleDataLabsProvider(ContactDiscoveryProvider):
    """Placeholder for People Data Labs. No network call until implemented + keyed."""

    name = "pdl"

    def available(self) -> bool:
        return bool(config.get_pdl_api_key())

    def discover(self, *, company, contact_type, max_results, job, goal) -> list[dict]:
        return []


def discover_contacts(
    *, existing_contacts: list[dict], company: str, contact_type: str,
    max_results: int, job: dict, goal: dict,
) -> dict:
    """Run every available provider and aggregate results.

    Returns a dict (never raises for missing keys):
      {
        "api_discovery_configured": bool,
        "providers_available": [names...],
        "message": str,
        "results": [contact dicts...],
      }
    """
    manual = ManualProvider(existing_contacts)
    api_providers = [HunterProvider(), PeopleDataLabsProvider()]
    available_api = [p for p in api_providers if p.available()]

    results: list[dict] = manual.discover(
        company=company, contact_type=contact_type, max_results=max_results,
        job=job, goal=goal,
    )
    for provider in available_api:
        results.extend(
            provider.discover(
                company=company, contact_type=contact_type,
                max_results=max_results, job=job, goal=goal,
            )
        )

    providers_available = [manual.name] + [p.name for p in available_api]
    if available_api:
        message = (
            f"Automatic discovery active via: {', '.join(p.name for p in available_api)}. "
            "Review each contact before any outreach."
        )
    else:
        message = (
            "Automatic discovery is not configured. Add contacts manually or "
            "configure a compliant provider (HUNTER_API_KEY / PDL_API_KEY)."
        )

    return {
        "api_discovery_configured": bool(available_api),
        "providers_available": providers_available,
        "message": message,
        "results": results[:max_results],
    }
