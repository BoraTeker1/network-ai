"""Backend settings, read from environment / backend/.env.

SAFETY:
- Secrets are read here and NEVER logged, printed, or returned to the frontend.
- backend/.env is only READ (via python-dotenv); this module never writes it.
- Helpers expose booleans like `has_openai()` so callers can branch on
  availability without ever touching the raw key.
"""

import os

try:
    from dotenv import load_dotenv

    # Loads backend/.env when the server is started from the backend/ dir.
    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional at runtime
    pass


def _get(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


# ----- LLM (OpenAI Responses API only) -----

def get_openai_api_key() -> str:
    """Raw key — for internal use by the LLM client ONLY. Never return/log this."""
    return _get("OPENAI_API_KEY")


def get_llm_provider() -> str:
    return _get("LLM_PROVIDER", "openai").lower()


def get_openai_model() -> str:
    return _get("OPENAI_MODEL", "gpt-4.1-mini")


def has_openai() -> bool:
    """True only when provider is openai AND a key is present."""
    return get_llm_provider() == "openai" and bool(get_openai_api_key())


# ----- Contact discovery providers -----

def get_hunter_api_key() -> str:
    return _get("HUNTER_API_KEY")


def get_pdl_api_key() -> str:
    return _get("PDL_API_KEY")


# ----- Event recommendation providers (optional, compliant APIs only) -----
# Leave blank to keep API-backed event discovery OFF. The feature still works
# with high-quality manual search links. No scraping is ever performed.

def get_ticketmaster_api_key() -> str:
    return _get("TICKETMASTER_API_KEY")


def has_ticketmaster() -> bool:
    """True only when a Ticketmaster Discovery API key is present."""
    return bool(get_ticketmaster_api_key())


def get_eventbrite_api_token() -> str:
    return _get("EVENTBRITE_API_TOKEN")


def get_meetup_api_key() -> str:
    return _get("MEETUP_API_KEY")


# ----- Gmail (disabled by default) -----

def gmail_send_enabled() -> bool:
    return _get("GMAIL_SEND_ENABLED", "false").lower() in ("1", "true", "yes", "on")


def get_google_client_id() -> str:
    return _get("GOOGLE_CLIENT_ID")


def get_google_client_secret() -> str:
    return _get("GOOGLE_CLIENT_SECRET")
