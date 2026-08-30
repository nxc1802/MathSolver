from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.ocr_agent import OCRAgent

logger = logging.getLogger(__name__)


async def ocr_from_local_image_path(
    local_path: str,
    original_filename: str | None,
    fallback_agent: "OCRAgent",
) -> str:
    """
    Run OCR on a file on local disk using Pix2Text Engine in-process.
    """
    return await fallback_agent.process_image(local_path)

