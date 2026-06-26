"""LLM client wrapper — Claude (Anthropic) primary, OpenAI as fallback.

Hard rules (enforced by code review, not just convention):
- Claude is called via the official Anthropic SDK Messages API
  (`client.messages.create`). OpenAI, when used, goes through the Responses API
  only (no Chat Completions / Assistants / Files / Vector Stores / embeddings).
- Runs only in the backend. API keys are read from env via app.config and are
  NEVER logged, printed, returned, or included in any exception message.
- Any failure raises LLMError; callers fall back to deterministic generation.
"""

import json
import re

from .. import config

_STRICT_JSON_INSTRUCTIONS = (
    "You are a careful, honest writing assistant. Respond with STRICT JSON "
    "only — no prose, no markdown fences."
)


class LLMError(Exception):
    """Raised on any LLM unavailability/failure. Messages are key-free."""


def llm_available() -> bool:
    """True when a Claude or OpenAI key is configured (no network call)."""
    return config.has_llm()


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


def _validate_json(text: str) -> dict:
    if not text or not text.strip():
        raise LLMError("LLM returned an empty response")
    try:
        data = _extract_json(text)
    except (ValueError, TypeError):
        raise LLMError("LLM response was not valid JSON") from None
    if not isinstance(data, dict):
        raise LLMError("LLM response JSON was not an object")
    return data


def _generate_with_anthropic(prompt: str) -> dict:
    """Send `prompt` to Claude via the Anthropic Messages API; return parsed JSON."""
    try:
        from anthropic import Anthropic
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise LLMError("anthropic package not installed") from exc

    try:
        client = Anthropic(api_key=config.get_anthropic_api_key())
        response = client.messages.create(
            model=config.get_anthropic_model(),
            max_tokens=2000,
            system=_STRICT_JSON_INSTRUCTIONS,
            messages=[{"role": "user", "content": prompt}],
        )
        # Join all text blocks in the response content.
        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
    except LLMError:
        raise
    except Exception as exc:
        # Never echo exception detail verbatim — keep it generic and key-free.
        raise LLMError(f"Anthropic request failed: {type(exc).__name__}") from None

    return _validate_json(text)


def _generate_with_openai(prompt: str) -> dict:
    """Send `prompt` to the OpenAI Responses API and return parsed JSON."""
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
            instructions=_STRICT_JSON_INSTRUCTIONS,
        )
        text = response.output_text
    except LLMError:
        raise
    except Exception as exc:
        raise LLMError(f"OpenAI request failed: {type(exc).__name__}") from None

    return _validate_json(text)


def generate_json(prompt: str) -> dict:
    """Generate strict JSON from the configured provider (Claude first).

    Raises LLMError if no provider is configured, the SDK isn't installed, the
    call fails, or the response isn't valid JSON. Raw keys are never surfaced.
    """
    if config.has_anthropic():
        return _generate_with_anthropic(prompt)
    if config.has_openai():
        return _generate_with_openai(prompt)
    raise LLMError("No LLM provider is configured")
