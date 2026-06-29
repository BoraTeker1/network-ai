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


# ----- LLM provider selection -----
# Claude (Anthropic) is the primary provider. OpenAI is kept as a secondary
# fallback. With no key for either, the app uses deterministic templates.


def get_llm_provider() -> str:
    """Preferred provider: 'anthropic' (default) or 'openai'."""
    return _get("LLM_PROVIDER", "anthropic").lower()


# ----- Anthropic (Claude — primary) -----

def get_anthropic_api_key() -> str:
    """Raw key — for internal use by the LLM client ONLY. Never return/log this."""
    return _get("ANTHROPIC_API_KEY")


def get_anthropic_model() -> str:
    # Default to the latest, most capable Claude model. Override via env to trade
    # cost/latency (e.g. claude-sonnet-4-6, claude-haiku-4-5).
    return _get("ANTHROPIC_MODEL", "claude-opus-4-8")


def has_anthropic() -> bool:
    """True when an Anthropic key is present (the default/primary provider)."""
    return bool(get_anthropic_api_key())


# ----- OpenAI (secondary / fallback) -----

def get_openai_api_key() -> str:
    """Raw key — for internal use by the LLM client ONLY. Never return/log this."""
    return _get("OPENAI_API_KEY")


def get_openai_model() -> str:
    return _get("OPENAI_MODEL", "gpt-4.1-mini")


def has_openai() -> bool:
    """True only when an OpenAI key is present."""
    return bool(get_openai_api_key())


def has_llm() -> bool:
    """True when ANY supported LLM provider is configured."""
    return has_anthropic() or has_openai()


# ----- Contact discovery providers -----

def get_hunter_api_key() -> str:
    return _get("HUNTER_API_KEY")


def get_pdl_api_key() -> str:
    return _get("PDL_API_KEY")


# ----- Event recommendation providers (optional, compliant APIs only) -----
# Leave blank to keep API-backed event discovery OFF. The feature still works
# with high-quality manual search links. No scraping is ever performed.

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
