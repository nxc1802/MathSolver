import asyncio
import logging
from typing import Callable, Any, Optional
from llm.errors import ErrorClassifier, ErrorCategory
from llm.key_pool import APIKeyPool

logger = logging.getLogger(__name__)


class KeyRetryPolicy:
    """Level 1 Key-level retry policy for the same model across available keys."""

    def __init__(self, max_key_attempts: int = 3):
        self.max_key_attempts = max_key_attempts

    def should_retry(self, category: ErrorCategory) -> bool:
        return category in (
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.TIMEOUT,
            ErrorCategory.NETWORK,
            ErrorCategory.SERVER_ERROR,
        )
