import time
import random
import logging
from typing import Dict, List, Optional, Tuple
from llm.key_state import KeyState, KeyMetadata, BaseKeyStateStore, RedisKeyStateStore, MemoryKeyStateStore, hash_key
from config.settings import settings

logger = logging.getLogger(__name__)


class APIKeyPool:
    """Multi-Provider API Key Pool with Round-Robin Selection and Automatic State Management."""

    def __init__(self, state_store: Optional[BaseKeyStateStore] = None):
        if state_store is not None:
            self.state_store = state_store
        else:
            try:
                self.state_store = RedisKeyStateStore(settings.redis_url)
            except Exception:
                self.state_store = MemoryKeyStateStore()

        self._provider_keys: Dict[str, List[str]] = {}
        self._provider_indices: Dict[str, int] = {}
        self._init_from_settings()

    def _init_from_settings(self) -> None:
        creds = settings.get_provider_credentials()
        for provider, prov_cred in creds.items():
            self._provider_keys[provider] = list(prov_cred.keys)
            self._provider_indices[provider] = 0
            logger.info(f"[APIKeyPool] Initialized pool for '{provider}' with {len(prov_cred.keys)} keys")

    def register_keys(self, provider: str, keys: List[str]) -> None:
        if provider not in self._provider_keys:
            self._provider_keys[provider] = []
            self._provider_indices[provider] = 0
        for k in keys:
            if k and k not in self._provider_keys[provider]:
                self._provider_keys[provider].append(k)

    async def get_next_key(self, provider: str) -> Optional[Tuple[str, str]]:
        """
        Returns (api_key, key_hash) for an AVAILABLE key using round-robin.
        If all keys are on cooldown, returns the one with the earliest retry_at.
        If no keys configured, returns None.
        """
        keys = self._provider_keys.get(provider, [])
        if not keys:
            # Check fallback to gemini or any available
            if provider == "google":
                keys = self._provider_keys.get("gemini", [])
            elif provider in ("openai", "openrouter"):
                keys = self._provider_keys.get(provider, [])

        if not keys:
            return None

        n = len(keys)
        start_idx = self._provider_indices.get(provider, 0)

        # 1. Round-robin search for AVAILABLE key
        for offset in range(n):
            idx = (start_idx + offset) % n
            candidate_key = keys[idx]
            k_hash = hash_key(candidate_key)
            meta = await self.state_store.get_state(k_hash)

            if meta.state == KeyState.AVAILABLE:
                self._provider_indices[provider] = (idx + 1) % n
                return candidate_key, k_hash

        # 2. If all keys are on cooldown/exhausted, find the earliest cooldown recovery
        best_candidate: Optional[Tuple[str, str, float]] = None
        for candidate_key in keys:
            k_hash = hash_key(candidate_key)
            meta = await self.state_store.get_state(k_hash)
            if meta.state == KeyState.COOLDOWN:
                if best_candidate is None or meta.retry_at < best_candidate[2]:
                    best_candidate = (candidate_key, k_hash, meta.retry_at)

        if best_candidate:
            candidate_key, k_hash, retry_at = best_candidate
            now = time.time()
            wait_needed = max(0.0, retry_at - now)
            logger.warning(
                f"[APIKeyPool] All {provider} keys on cooldown. Key {k_hash} available in {wait_needed:.1f}s"
            )
            # If wait is very short (< 3s), use it
            if wait_needed < 3.0:
                return candidate_key, k_hash

        # Return first non-disabled key as emergency attempt
        for candidate_key in keys:
            k_hash = hash_key(candidate_key)
            meta = await self.state_store.get_state(k_hash)
            if meta.state != KeyState.DISABLED:
                return candidate_key, k_hash

        return None

    async def mark_success(self, key: str) -> None:
        k_hash = hash_key(key)
        meta = await self.state_store.get_state(k_hash)
        meta.state = KeyState.AVAILABLE
        meta.failure_count = 0
        meta.last_error = None
        await self.state_store.set_state(k_hash, meta)

    async def mark_cooldown(self, key: str, retry_after: Optional[int] = None, error_msg: Optional[str] = None) -> None:
        k_hash = hash_key(key)
        meta = await self.state_store.get_state(k_hash)
        meta.failure_count += 1

        # Exponential backoff with jitter
        base_cooldown = retry_after if retry_after else settings.llm_cooldown_seconds
        factor = min(2 ** (meta.failure_count - 1), 8)
        jitter = random.uniform(0.8, 1.2)
        total_duration = int(base_cooldown * factor * jitter)

        meta.state = KeyState.COOLDOWN
        meta.retry_at = time.time() + total_duration
        meta.last_error = error_msg
        logger.warning(f"[APIKeyPool] Key {k_hash} moved to COOLDOWN for {total_duration}s (failures={meta.failure_count})")
        await self.state_store.set_state(k_hash, meta, ttl_seconds=total_duration + 60)

    async def mark_exhausted(self, key: str, error_msg: Optional[str] = None) -> None:
        k_hash = hash_key(key)
        meta = await self.state_store.get_state(k_hash)
        meta.state = KeyState.EXHAUSTED
        meta.last_error = error_msg
        # Cooldown for 6 hours
        meta.retry_at = time.time() + 21600
        logger.error(f"[APIKeyPool] Key {k_hash} marked EXHAUSTED (daily quota): {error_msg}")
        await self.state_store.set_state(k_hash, meta, ttl_seconds=21600)

    async def mark_disabled(self, key: str, error_msg: Optional[str] = None) -> None:
        k_hash = hash_key(key)
        meta = await self.state_store.get_state(k_hash)
        meta.state = KeyState.DISABLED
        meta.last_error = error_msg
        logger.error(f"[APIKeyPool] Key {k_hash} DISABLED permanently (Auth/Invalid): {error_msg}")
        await self.state_store.set_state(k_hash, meta)


_GLOBAL_KEY_POOL: Optional[APIKeyPool] = None


def get_key_pool() -> APIKeyPool:
    global _GLOBAL_KEY_POOL
    if _GLOBAL_KEY_POOL is None:
        _GLOBAL_KEY_POOL = APIKeyPool()
    return _GLOBAL_KEY_POOL
