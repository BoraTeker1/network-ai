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


# ----- Deployment / security (production-readiness layer) -----

def get_allowed_origins() -> list[str]:
    """CORS origins, comma-separated via ALLOWED_ORIGINS. Never a wildcard —
    credentialed CORS requires an explicit list."""
    raw = _get("ALLOWED_ORIGINS", "http://localhost:3000")
    return [o.strip() for o in raw.split(",") if o.strip()]


def cookie_secure() -> bool:
    """Set COOKIE_SECURE=true in production (HTTPS). Default false so local dev
    and tests (http://testserver) keep working."""
    return _get("COOKIE_SECURE", "false").lower() in ("1", "true", "yes", "on")


def trust_proxy() -> bool:
    """Only honor X-Forwarded-For when explicitly behind a trusted proxy."""
    return _get("TRUST_PROXY", "false").lower() in ("1", "true", "yes", "on")


def session_ttl_days() -> int:
    try:
        return max(1, int(_get("SESSION_TTL_DAYS", "30")))
    except ValueError:
        return 30


# ----- Gmail (disabled by default) -----

def gmail_send_enabled() -> bool:
    return _get("GMAIL_SEND_ENABLED", "false").lower() in ("1", "true", "yes", "on")


def get_google_client_id() -> str:
    return _get("GOOGLE_CLIENT_ID")


def get_google_client_secret() -> str:
    return _get("GOOGLE_CLIENT_SECRET")
