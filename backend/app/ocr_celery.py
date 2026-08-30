"""Run OCR on a remote worker via Celery (queue `ocr`) when OCR_USE_CELERY is enabled."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

import anyio

if TYPE_CHECKING:
    from agents.ocr_agent import OCRAgent

logger = logging.getLogger(__name__)


async def ocr_from_image_url(image_url: str, fallback_agent: "OCRAgent") -> str:
    """
    Process OCR from image URL using OCRAgent (Pix2Text Engine).
    """
    return await fallback_agent.process_url(image_url)

