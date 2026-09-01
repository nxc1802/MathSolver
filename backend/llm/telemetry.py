import time
import uuid
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class LLMTelemetryRecord(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent: str
    tier: int = 1
    model: str
    provider: str
    key_id: str
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    status: str = "success"  # success, retry, failed
    retry_count: int = 0
    error: Optional[str] = None


class LLMTelemetry:
    """Safe LLM observability and logging."""

    @staticmethod
    def log_record(record: LLMTelemetryRecord) -> None:
        logger.info(
            f"[LLMTelemetry] req={record.request_id[:8]} agent={record.agent} tier={record.tier} "
            f"model={record.model} key={record.key_id} lat={record.latency_ms:.0f}ms "
            f"in_tok={record.input_tokens} out_tok={record.output_tokens} status={record.status} "
            f"retries={record.retry_count}"
        )


telemetry = LLMTelemetry()
