"""Normalize URLs / env strings (HF secrets and copy-paste often include trailing newlines)."""


def sanitize_url(value: str | None) -> str | None:
    if value is None:
        return None
    s = value.strip().replace("\r", "").replace("\n", "").replace("\t", "")
    return s or None


def sanitize_env(value: str | None) -> str | None:
    """Strip whitespace and line breaks from environment-backed strings."""
    return sanitize_url(value)
