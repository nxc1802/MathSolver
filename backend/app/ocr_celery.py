"""Run OCR on a remote worker via Celery (queue `ocr`) when OCR_USE_CELERY is enabled."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

import anyio

if TYPE_CHECKING:
    from agents.ocr_agent import OCRAgent

logger = logging.getLogger(__name__)


def ocr_celery_enabled() -> bool:
    return os.getenv("OCR_USE_CELERY", "").strip().lower() in ("1", "true", "yes", "on")


def _ocr_timeout_sec() -> float:
    raw = os.getenv("OCR_CELERY_TIMEOUT_SEC", "180")
    try:
        return max(30.0, float(raw))
    except ValueError:
        return 180.0


def _run_ocr_celery_sync(image_url: str) -> str:
    from worker.ocr_tasks import run_ocr_from_url

    async_result = run_ocr_from_url.apply_async(args=[image_url])
    return async_result.get(timeout=_ocr_timeout_sec())


def _is_ocr_error_response(text: str) -> bool:
    s = (text or "").lstrip()
    return s.startswith("Error:")


async def ocr_from_image_url(image_url: str, fallback_agent: "OCRAgent") -> str:
    """
    If OCR_USE_CELERY: delegate to Celery task `run_ocr_from_url` (worker queue `ocr`, raw OCR only),
    then run ``refine_with_llm`` on the API process.
    Else: use fallback_agent.process_url (in-process full pipeline).
    """
    if not ocr_celery_enabled():
        return await fallback_agent.process_url(image_url)
    logger.info("OCR_USE_CELERY: delegating OCR to Celery queue=ocr (LLM refine on API)")
    raw = await anyio.to_thread.run_sync(_run_ocr_celery_sync, image_url)
    raw = raw if raw is not None else ""
    if not raw.strip() or _is_ocr_error_response(raw):
        return raw
    return await fallback_agent.refine_with_llm(raw)
