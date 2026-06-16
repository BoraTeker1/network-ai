"""OpenAI client wrapper — Responses API ONLY.

Hard rules (enforced by code review, not just convention):
- Uses ONLY the Responses API (`client.responses.create`).
- Does NOT use Chat Completions, Assistants, Files, Vector Stores, or embeddings.
- Runs only in the backend. The API key is read from env via app.config and is
  NEVER logged, printed, returned, or included in any exception message.
- Any failure raises LLMError; callers fall back to deterministic generation.
"""

import json
import re

from .. import config


class LLMError(Exception):
    """Raised on any LLM unavailability/failure. Messages are key-free."""


def llm_available() -> bool:
    """True when an OpenAI key + provider are configured (no network call)."""
    return config.has_openai()


def _strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` fences a model might wrap JSON in."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _extract_json(text: str) -> dict:
    """Parse strict JSON from model output, tolerating code fences / prose."""
    candidate = _strip_code_fences(text)
    try:
        return json.loads(candidate)
    except (ValueError, TypeError):
        # Last resort: grab the outermost {...} block.
        match = re.search(r"\{.*\}", candidate, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def generate_json_with_openai(prompt: str) -> dict:
    """Send `prompt` to the OpenAI Responses API and return parsed JSON.

    Raises LLMError if the key is missing, the SDK isn't installed, the call
    fails, or the response isn't valid JSON. The raw key is never surfaced.
    """
    if not llm_available():
        raise LLMError("OpenAI is not configured")

    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise LLMError("openai package not installed") from exc

    try:
        client = OpenAI(api_key=config.get_openai_api_key())
        # Responses API — the ONLY OpenAI endpoint this app uses.
        response = client.responses.create(
            model=config.get_openai_model(),
            input=prompt,
            instructions=(
                "You are a careful writing assistant. Respond with STRICT JSON "
                "only — no prose, no markdown fences."
            ),
        )
        text = response.output_text
    except Exception as exc:
        # Never echo the exception detail verbatim to callers/logs — it could
        # in theory contain request context. Keep it generic and key-free.
        raise LLMError(f"OpenAI request failed: {type(exc).__name__}") from None

    if not text or not text.strip():
        raise LLMError("OpenAI returned an empty response")

    try:
        data = _extract_json(text)
    except (ValueError, TypeError) as exc:
        raise LLMError("OpenAI response was not valid JSON") from None

    if not isinstance(data, dict):
        raise LLMError("OpenAI response JSON was not an object")
    return data
