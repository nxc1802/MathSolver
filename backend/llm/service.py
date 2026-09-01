import os
import re
import time
import uuid
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
import litellm
from llm.key_pool import APIKeyPool, get_key_pool
from llm.errors import ErrorClassifier, ErrorCategory
from llm.telemetry import telemetry, LLMTelemetryRecord
from config.settings import settings

logger = logging.getLogger(__name__)

# Suppress noisy LiteLLM logs
litellm.suppress_debug_info = True


class LLMService:
    """Core LLM Service providing LiteLLM Provider Abstraction, Key Pool Rotation, and First-Chunk Safe Streaming."""

    def __init__(self, key_pool: Optional[APIKeyPool] = None):
        self.key_pool = key_pool or get_key_pool()

    def _parse_provider_and_model(self, raw_model: str) -> tuple[str, str]:
        """Extracts provider and normalized model identifier (e.g. 'gemini/gemini-2.5-flash' -> ('gemini', 'gemini/gemini-2.5-flash'))."""
        raw = raw_model.strip()
        if "/" in raw:
            parts = raw.split("/", 1)
            provider = parts[0].lower()
            return provider, raw
        else:
            # Default to gemini if not prefixed
            return "gemini", f"gemini/{raw}"

    def _strip_thought_tags(self, text: str) -> str:
        """Strips <thought>...</thought> tags from thinking models for clean downstream consumption."""
        if not text or not isinstance(text, str):
            return text
        cleaned = re.sub(r"<thought>[\s\S]*?</thought>", "", text, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"<think>[\s\S]*?</think>", "", cleaned, flags=re.IGNORECASE).strip()
        return cleaned

    async def acomplete(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 8192,
        timeout: int = 120,
        response_format: Optional[Dict[str, Any]] = None,
        reasoning_effort: Optional[str] = None,
        agent_name: str = "general",
        tier_index: int = 1,
        **kwargs
    ) -> str:
        """
        Executes an LLM completion with Level-1 Key Pool rotation and safe retry.
        """
        provider, model_name = self._parse_provider_and_model(model)
        request_id = str(uuid.uuid4())
        max_key_retries = 3
        last_error = None

        for attempt in range(max_key_retries):
            key_info = await self.key_pool.get_next_key(provider)
            if not key_info:
                # No keys available, attempt with default env or raise
                api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
                key_hash = "env_default"
            else:
                api_key, key_hash = key_info

            start_time = time.time()
            try:
                litellm_kwargs: Dict[str, Any] = {
                    "model": model_name,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "timeout": timeout,
                    "api_key": api_key,
                }
                if response_format:
                    litellm_kwargs["response_format"] = response_format
                if reasoning_effort and "gemini" in model_name:
                    litellm_kwargs["reasoning_effort"] = reasoning_effort

                # Forward custom kwargs
                litellm_kwargs.update(kwargs)

                response = await litellm.acompletion(**litellm_kwargs)
                latency_ms = (time.time() - start_time) * 1000

                # Mark key success
                if key_info:
                    await self.key_pool.mark_success(api_key)

                content = response.choices[0].message.content or ""
                cleaned_content = self._strip_thought_tags(content)

                # Token usage
                in_tok = getattr(getattr(response, "usage", None), "prompt_tokens", 0)
                out_tok = getattr(getattr(response, "usage", None), "completion_tokens", 0)

                telemetry.log_record(
                    LLMTelemetryRecord(
                        request_id=request_id,
                        agent=agent_name,
                        tier=tier_index,
                        model=model_name,
                        provider=provider,
                        key_id=key_hash,
                        latency_ms=latency_ms,
                        input_tokens=in_tok,
                        output_tokens=out_tok,
                        status="success",
                        retry_count=attempt,
                    )
                )
                return cleaned_content

            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                category = ErrorClassifier.classify(e)
                retry_after = ErrorClassifier.extract_retry_after(e)
                last_error = e

                logger.warning(
                    f"[LLMService] Request {request_id[:8]} failed on {key_hash} ({category.value}): {e}"
                )

                # Update key state according to category
                if key_info:
                    if category == ErrorCategory.RATE_LIMIT:
                        await self.key_pool.mark_cooldown(api_key, retry_after=retry_after, error_msg=str(e))
                    elif category == ErrorCategory.QUOTA_EXHAUSTED:
                        await self.key_pool.mark_exhausted(api_key, error_msg=str(e))
                    elif category == ErrorCategory.AUTH_ERROR:
                        await self.key_pool.mark_disabled(api_key, error_msg=str(e))
                    else:
                        await self.key_pool.mark_cooldown(api_key, retry_after=15, error_msg=str(e))

                telemetry.log_record(
                    LLMTelemetryRecord(
                        request_id=request_id,
                        agent=agent_name,
                        tier=tier_index,
                        model=model_name,
                        provider=provider,
                        key_id=key_hash,
                        latency_ms=latency_ms,
                        status="retry" if attempt < max_key_retries - 1 else "failed",
                        retry_count=attempt + 1,
                        error=str(e),
                    )
                )

                # Non-retryable request errors should immediately fail up to cascade
                if category == ErrorCategory.INVALID_REQUEST:
                    raise

        # All key retries exhausted for this tier
        raise last_error or RuntimeError(f"All API key retries failed for model {model}")

    async def astream(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 8192,
        timeout: int = 120,
        agent_name: str = "general",
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Streaming with first-chunk dry-run protection to prevent duplicated token generation upon key retry.
        """
        provider, model_name = self._parse_provider_and_model(model)
        max_key_retries = 3

        for attempt in range(max_key_retries):
            key_info = await self.key_pool.get_next_key(provider)
            api_key = key_info[0] if key_info else (os.getenv("GOOGLE_API_KEY") or "")
            key_hash = key_info[1] if key_info else "env_default"

            try:
                response = await litellm.acompletion(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                    api_key=api_key,
                    stream=True,
                    **kwargs
                )

                # Dry-run receive first chunk
                first_chunk = None
                async for chunk in response:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        first_chunk = delta
                        break

                if key_info:
                    await self.key_pool.mark_success(api_key)

                # First chunk succeeded, start yielding without retries
                if first_chunk:
                    yield first_chunk

                async for chunk in response:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        yield delta
                return

            except Exception as e:
                category = ErrorClassifier.classify(e)
                logger.warning(f"[LLMService.astream] Stream attempt {attempt+1} failed on {key_hash}: {e}")
                if key_info:
                    await self.key_pool.mark_cooldown(api_key, error_msg=str(e))
                if attempt == max_key_retries - 1:
                    raise


_GLOBAL_LLM_SERVICE: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _GLOBAL_LLM_SERVICE
    if _GLOBAL_LLM_SERVICE is None:
        _GLOBAL_LLM_SERVICE = LLMService()
    return _GLOBAL_LLM_SERVICE
