"""OCR from a local file path, optionally via Celery worker (upload temp blob first)."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from app.chat_image_upload import (
    delete_storage_object,
    upload_ephemeral_ocr_blob,
    validate_chat_image_bytes,
)
from app.ocr_celery import ocr_celery_enabled, ocr_from_image_url

if TYPE_CHECKING:
    from agents.ocr_agent import OCRAgent

logger = logging.getLogger(__name__)


async def ocr_from_local_image_path(
    local_path: str,
    original_filename: str | None,
    fallback_agent: "OCRAgent",
) -> str:
    """
    Run OCR on a file on local disk. If OCR_USE_Celery, upload to ephemeral storage URL
    then delegate to worker; otherwise process_image in-process.
    """
    if not ocr_celery_enabled():
        return await fallback_agent.process_image(local_path)

    with open(local_path, "rb") as f:
        body = f.read()
    ext = os.path.splitext(original_filename or local_path)[1].lower() or ".png"
    _, content_type = validate_chat_image_bytes(original_filename or local_path, body, None)
    bucket = os.getenv("SUPABASE_IMAGE_BUCKET", "image")
    path, url = upload_ephemeral_ocr_blob(body, ext, content_type)
    try:
        return await ocr_from_image_url(url, fallback_agent)
    finally:
        delete_storage_object(bucket, path)
