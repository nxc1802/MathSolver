"""Normalize URLs / env strings (HF secrets and copy-paste often include trailing newlines)."""


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


def openai_compatible_api_key(raw: str | None) -> str:
    """Return sanitized API key, or a placeholder so AsyncOpenAI() can be constructed without env at build time."""
    k = sanitize_env(raw)
    return k if k else _OPENAI_API_KEY_BUILD_PLACEHOLDER
