"""
OCR vision pipeline (v5.3).
Powered solely by Pix2Text for unified layout, text, and LaTeX formula recognition.
No LLM hallucination in OCR layer; adheres to pure visual extraction.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Union
import cv2

from vision_ocr.canonical_schema import CanonicalOCRResult
from vision_ocr.pix2text_engine import Pix2TextOCREngine

logger = logging.getLogger(__name__)


class OcrVisionPipeline:
    """
    Unified Math OCR Vision Pipeline (v5.3).
    Replaces the fragmented multi-engine patchwork with Pix2Text.
    """

    def __init__(self) -> None:
        logger.info("[OcrVisionPipeline] Initializing Pix2Text unified engine...")
        self.engine = Pix2TextOCREngine.get_instance()

    async def process_image(self, image_path: str) -> str:
        """
        Extracts structured text from image and returns markdown text with LaTeX.
        Maintains backward compatibility with string-expecting consumers.
        """
        canonical = await self.process_image_canonical(image_path)
        return canonical.text

    async def process_image_canonical(self, image_path: str) -> CanonicalOCRResult:
        """
        Returns the full canonical OCR structure (text, LaTeX list, elements, bboxes, reading order).
        """
        logger.info("==[OcrVisionPipeline] Processing image with Pix2Text: %s==", image_path)
        if not os.path.exists(image_path):
            logger.error("[OcrVisionPipeline] Image file not found: %s", image_path)
            return CanonicalOCRResult(text=f"Error: Image not found at {image_path}", confidence=0.0)

        try:
            return self.engine.recognize(image_path, return_text=False)
        except Exception as e:
            logger.error("[OcrVisionPipeline] Processing failed: %s", e)
            return CanonicalOCRResult(text="", confidence=0.0)

    async def process_url(self, url: str) -> str:
        """
        Downloads image from URL and processes via Pix2Text.
        """
        canonical = await self.process_url_canonical(url)
        return canonical.text

    async def process_url_canonical(self, url: str) -> CanonicalOCRResult:
        import uuid
        import urllib.request

        local_filename = f"temp_url_ocr_{uuid.uuid4().hex}.png"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as resp, open(local_filename, "wb") as f:
                f.write(resp.read())
            result = await self.process_image_canonical(local_filename)
            return result
        except Exception as e:
            logger.error("[OcrVisionPipeline] process_url failed: %s", e)
            return CanonicalOCRResult(text=f"Error processing URL: {e}", confidence=0.0)
        finally:
            if os.path.exists(local_filename):
                try:
                    os.remove(local_filename)
                except Exception:
                    pass
