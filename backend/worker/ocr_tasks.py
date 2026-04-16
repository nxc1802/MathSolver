"""Celery tasks for OCR-only worker queue (`ocr`)."""

from __future__ import annotations

import asyncio
import logging

from worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="worker.ocr_tasks.run_ocr_from_url")
def run_ocr_from_url(image_url: str) -> str:
    """
    Download image from public URL and run OCR models only (YOLO / PaddleOCR / Pix2Tex).
    LLM post-processing runs on the API via ``OCRAgent.refine_with_llm`` after the result is returned.
    """
    from vision_ocr.pipeline import OcrVisionPipeline

    pipeline = OcrVisionPipeline()
    logger.info("[run_ocr_from_url] starting OCR for url host=%s", image_url.split("/")[2] if "/" in image_url else "?")
    text = asyncio.run(pipeline.process_url(image_url))
    logger.info("[run_ocr_from_url] done, text_len=%s", len(text or ""))
    return text if text is not None else ""
