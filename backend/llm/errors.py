import re
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    RATE_LIMIT = "RATE_LIMIT"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    AUTH_ERROR = "AUTH_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    TIMEOUT = "TIMEOUT"
    NETWORK = "NETWORK"
    SERVER_ERROR = "SERVER_ERROR"
    UNKNOWN = "UNKNOWN"


class ErrorClassifier:
    """Classifies exceptions from LiteLLM and HTTP client into structured ErrorCategory."""

    @staticmethod
    def classify(exc: Exception) -> ErrorCategory:
        err_msg = str(exc).lower()
        err_type = type(exc).__name__.lower()

        # 1. Authentication / Permission errors (Disable key)
        if any(w in err_msg for w in ["invalid_api_key", "invalid api key", "unauthorized", "authentication", "api_key_invalid", "permission_denied"]) or "auth" in err_type:
            return ErrorCategory.AUTH_ERROR

        # 2. Permanent Quota Exhaustion
        if any(w in err_msg for w in ["daily quota", "quota exceeded", "billing", "credit", "insufficient_quota"]):
            return ErrorCategory.QUOTA_EXHAUSTED

        # 3. Rate Limit / Resource Exhausted (Temporary Cooldown)
        if any(w in err_msg for w in ["rate limit", "ratelimit", "429", "resource_exhausted", "too many requests"]) or "ratelimit" in err_type:
            return ErrorCategory.RATE_LIMIT

        # 4. Timeout errors
        if any(w in err_msg for w in ["timeout", "timed out", "deadline_exceeded"]) or "timeout" in err_type:
            return ErrorCategory.TIMEOUT

        # 5. Network / Connection errors
        if any(w in err_msg for w in ["connection error", "connection reset", "broken pipe", "connect_error", "remotedisconnected"]):
            return ErrorCategory.NETWORK

        # 6. Server errors (500, 502, 503, 504)
        if any(w in err_msg for w in ["500", "502", "503", "504", "internal server error", "bad gateway", "service unavailable", "overloaded"]):
            return ErrorCategory.SERVER_ERROR

        # 7. Invalid Request (e.g. context length exceeded, bad params - do not key-retry)
        if any(w in err_msg for w in ["context_length_exceeded", "maximum context length", "invalid_request_error", "bad request", "400"]):
            return ErrorCategory.INVALID_REQUEST

        return ErrorCategory.UNKNOWN

    @staticmethod
    def extract_retry_after(exc: Exception) -> Optional[int]:
        """Attempts to extract Retry-After duration from exception message or headers."""
        err_msg = str(exc)
        # Check for patterns like "retry after 45s" or "Retry-After: 30"
        match = re.search(r"(?:retry[-_ ]after|retry in)\s*:?\s*(\d+)", err_msg, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        return None
