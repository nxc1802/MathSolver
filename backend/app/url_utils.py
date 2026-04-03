"""Normalize URLs / env strings (HF secrets and copy-paste often include trailing newlines)."""

import os


def sanitize_url(value: str | None) -> str | None:
    if value is None:
        return None
    s = value.strip().replace("\r", "").replace("\n", "").replace("\t", "")
    return s or None


def sanitize_env(value: str | None) -> str | None:
    """Strip whitespace and line breaks from environment-backed strings."""
    return sanitize_url(value)


# OpenAI SDK (>=1.x) requires a non-empty api_key at client construction (Docker build / prewarm has no secrets).
_OPENAI_API_KEY_BUILD_PLACEHOLDER = "build-placeholder-megallm-not-for-production"


def _strip_optional_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] in '"\'':
        if s[0] == s[-1]:
            return s[1:-1]
    return s


def openai_compatible_api_key(raw: str | None) -> str:
    """Return sanitized API key, or a placeholder so AsyncOpenAI() can be constructed without env at build time."""
    k = sanitize_env(raw)
    if k:
        return _strip_optional_quotes(k)
    return _OPENAI_API_KEY_BUILD_PLACEHOLDER


def megallm_base_url() -> str:
    """Same root as MegaLLM docs: https://ai.megallm.io/v1 (no trailing slash)."""
    raw = sanitize_env(os.getenv("MEGALLM_BASE_URL"))
    if not raw:
        return "https://ai.megallm.io/v1"
    return _strip_optional_quotes(raw).rstrip("/")


def megallm_model() -> str:
    """Default model id aligned with project env; override with MEGALLM_MODEL."""
    raw = sanitize_env(os.getenv("MEGALLM_MODEL"))
    if not raw:
        return "openai-gpt-oss-20b"
    return _strip_optional_quotes(raw)
