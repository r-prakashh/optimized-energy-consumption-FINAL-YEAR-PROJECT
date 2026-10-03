"""Optional Claude integration shared by the bill reader and the assistant.

Everything that uses it degrades gracefully: with no Anthropic credentials
configured, `get_client()` returns None and callers fall back to the local
OCR parser / rule-based assistant, so the free-tier deployment keeps working
without a paid API key.
"""
from __future__ import annotations

import os

CLAUDE_MODEL = os.getenv("ENERGY_CLAUDE_MODEL", "claude-opus-5-5")

# Server-side refusal fallback: if a safety classifier declines a request,
# the API re-runs it on Anthropic's recommended fallback model in the same
# call instead of returning an empty refusal.
FALLBACK_HEADERS = {"anthropic-beta": "server-side-fallback-2026-07-01"}
FALLBACK_BODY = {"fallbacks": "default"}

_client = None
_client_checked = False


def get_client():
    """Returns an Anthropic client, or None when no credentials are set."""
    global _client, _client_checked
    if _client_checked:
        return _client
    _client_checked = True
    if os.getenv("ENERGY_DISABLE_LLM") == "1":
        return None
    if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
        return None
    try:
        import anthropic

        _client = anthropic.Anthropic(timeout=90.0, max_retries=2)
    except Exception:  # pragma: no cover - SDK missing / misconfigured
        _client = None
    return _client


def llm_available() -> bool:
    return get_client() is not None
