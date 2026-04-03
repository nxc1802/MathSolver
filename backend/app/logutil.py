"""log_step (debug), pipeline (debug), access log ở middleware."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from app.logging_setup import PIPELINE_LOGGER_NAME, STEPS_LOGGER_NAME

_pipeline = logging.getLogger(PIPELINE_LOGGER_NAME)
_steps = logging.getLogger(STEPS_LOGGER_NAME)


def is_debug_mode() -> bool:
    """Chi tiết từng bước chỉ khi LOG_LEVEL=debug."""
    return os.getenv("LOG_LEVEL", "info").strip().lower() == "debug"


def _truncate(val: Any, max_len: int = 2000) -> Any:
    if val is None:
        return None
    if isinstance(val, (int, float, bool)):
        return val
    s = str(val)
    if len(s) > max_len:
        return s[:max_len] + f"... (+{len(s) - max_len} chars)"
    return s


def log_step(step: str, **fields: Any) -> None:
    """Chỉ khi LOG_LEVEL=debug: DB / cache / orchestrator."""
    if not is_debug_mode():
        return
    safe = {k: _truncate(v) for k, v in fields.items()}
    try:
        payload = json.dumps(safe, ensure_ascii=False, default=str)
    except Exception:
        payload = str(safe)
    _steps.debug("[step:%s] %s", step, payload)


def log_pipeline_success(operation: str, **fields: Any) -> None:
    """Chỉ hiện khi debug (pipeline SUCCESS không dùng ở info — đã có app.access)."""
    if not is_debug_mode():
        return
    safe = {k: _truncate(v, 500) for k, v in fields.items()}
    _pipeline.info(
        "SUCCESS %s %s",
        operation,
        json.dumps(safe, ensure_ascii=False, default=str),
    )


def log_pipeline_failure(operation: str, error: str | None = None, **fields: Any) -> None:
    """Thất bại pipeline: luôn dùng WARNING để vẫn thấy khi LOG_LEVEL=warning."""
    if is_debug_mode():
        safe = {k: _truncate(v, 500) for k, v in fields.items()}
        _pipeline.warning(
            "FAIL %s err=%s %s",
            operation,
            _truncate(error, 300),
            json.dumps(safe, ensure_ascii=False, default=str),
        )
    else:
        _pipeline.warning("FAIL %s", operation)
