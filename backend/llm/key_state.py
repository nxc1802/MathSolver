import time
import json
import hashlib
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class KeyState(str, Enum):
    AVAILABLE = "AVAILABLE"
    COOLDOWN = "COOLDOWN"
    EXHAUSTED = "EXHAUSTED"
    DISABLED = "DISABLED"


def hash_key(api_key: str) -> str:
    """Returns SHA-256 short fingerprint of API key for safe identification & logging."""
    if not api_key:
        return "empty"
    digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    return f"key_{digest[:12]}"


class KeyMetadata(BaseModel):
    key_hash: str
    state: KeyState = KeyState.AVAILABLE
    retry_at: float = 0.0
    failure_count: int = 0
    last_error: Optional[str] = None
    updated_at: float = Field(default_factory=time.time)


class BaseKeyStateStore(ABC):
    @abstractmethod
    async def get_state(self, key_hash: str) -> KeyMetadata:
        pass

    @abstractmethod
    async def set_state(self, key_hash: str, metadata: KeyMetadata, ttl_seconds: Optional[int] = None) -> None:
        pass


class MemoryKeyStateStore(BaseKeyStateStore):
    """Thread-safe In-Memory Key State Store."""

    def __init__(self):
        self._store: Dict[str, KeyMetadata] = {}

    async def get_state(self, key_hash: str) -> KeyMetadata:
        now = time.time()
        meta = self._store.get(key_hash)
        if not meta:
            meta = KeyMetadata(key_hash=key_hash)
            self._store[key_hash] = meta
            return meta

        # Auto-recover from cooldown if time has passed
        if meta.state == KeyState.COOLDOWN and now >= meta.retry_at:
            meta.state = KeyState.AVAILABLE
            meta.last_error = None
            meta.updated_at = now
            self._store[key_hash] = meta
        return meta

    async def set_state(self, key_hash: str, metadata: KeyMetadata, ttl_seconds: Optional[int] = None) -> None:
        metadata.updated_at = time.time()
        self._store[key_hash] = metadata


class RedisKeyStateStore(BaseKeyStateStore):
    """Distributed Redis Key State Store with fallback to Memory store."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis = None
        self._redis_disabled = False
        self._memory_fallback = MemoryKeyStateStore()
        self._prefix = "mathsolver:llm:key:"

    def _get_redis(self):
        if self._redis_disabled:
            return None
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(self.redis_url, decode_responses=True, socket_connect_timeout=2.0)
            except Exception as e:
                self._redis_disabled = True
                logger.info(f"[RedisKeyStateStore] Redis unavailable ({e}). Using in-memory fallback store.")
        return self._redis

    async def get_state(self, key_hash: str) -> KeyMetadata:
        if self._redis_disabled:
            return await self._memory_fallback.get_state(key_hash)

        r = self._get_redis()
        if not r:
            return await self._memory_fallback.get_state(key_hash)

        try:
            raw = await r.get(f"{self._prefix}{key_hash}")
            if not raw:
                meta = KeyMetadata(key_hash=key_hash)
                return meta
            data = json.loads(raw)
            meta = KeyMetadata(**data)

            # Auto-recover from cooldown
            now = time.time()
            if meta.state == KeyState.COOLDOWN and now >= meta.retry_at:
                meta.state = KeyState.AVAILABLE
                meta.last_error = None
                meta.updated_at = now
                await self.set_state(key_hash, meta)
            return meta
        except Exception as e:
            self._redis_disabled = True
            logger.info(f"[RedisKeyStateStore] Redis connection failed ({e}). Switching to in-memory store.")
            return await self._memory_fallback.get_state(key_hash)

    async def set_state(self, key_hash: str, metadata: KeyMetadata, ttl_seconds: Optional[int] = None) -> None:
        metadata.updated_at = time.time()
        if self._redis_disabled:
            await self._memory_fallback.set_state(key_hash, metadata, ttl_seconds)
            return

        r = self._get_redis()
        if not r:
            await self._memory_fallback.set_state(key_hash, metadata, ttl_seconds)
            return

        try:
            payload = metadata.model_dump_json()
            r_key = f"{self._prefix}{key_hash}"
            if ttl_seconds and ttl_seconds > 0:
                await r.set(r_key, payload, ex=ttl_seconds)
            else:
                await r.set(r_key, payload)
        except Exception as e:
            self._redis_disabled = True
            await self._memory_fallback.set_state(key_hash, metadata, ttl_seconds)

