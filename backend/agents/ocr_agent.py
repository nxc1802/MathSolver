"""
OCR Agent (v5.3).
Pure visual perception agent responsible for recognizing text, mathematical formulas, and layout
from geometry problem images using Pix2Text.
Strictly adheres to the Design Principle:
- OCR only extracts and structures visual content without LLM hallucinations or semantic alteration.
- Emits structured CanonicalOCRResult for downstream Problem Parser / VLM.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from vision_ocr.canonical_schema import CanonicalOCRResult
from vision_ocr.pipeline import OcrVisionPipeline

logger = logging.getLogger(__name__)


class ImprovedOCRAgent:
    """
    Math OCR Agent (v5.3).
    Wraps ``OcrVisionPipeline`` (Pix2Text) and produces CanonicalOCRResult.
    """

    def __init__(self, **kwargs):
        self._vision = OcrVisionPipeline()
        logger.info("[ImprovedOCRAgent] Math OCR Vision Pipeline ready (Pix2Text Engine).")

    async def process_image(self, image_path: str) -> str:
        """
        Processes image and returns reconstructed Markdown text containing inline and display LaTeX.
        """
        canonical = await self._vision.process_image_canonical(image_path)
        return canonical.text

    async def process_image_canonical(self, image_path: str) -> CanonicalOCRResult:
        """
        Processes image and returns full CanonicalOCRResult structure:
        - text: Markdown string with LaTeX formulas
        - latex: List of all extracted mathematical expressions
        - elements: Region bounding boxes and classifications
        - reading_order: Document sequential layout reading order
        - confidence: Extraction confidence score
        """
        return await self._vision.process_image_canonical(image_path)

    async def process_url(self, url: str) -> str:
        """
        Fetches image from URL and returns reconstructed Markdown text with LaTeX.
        """
        return await self._vision.process_url(url)

    async def process_url_canonical(self, url: str) -> CanonicalOCRResult:
        """
        Fetches image from URL and returns full CanonicalOCRResult.
        """
        return await self._vision.process_url_canonical(url)


class OCRAgent(ImprovedOCRAgent):
    """Alias for backward compatibility."""
    pass
