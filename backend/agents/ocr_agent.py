"""
OCR Agent (v5.4).
Pure visual perception agent responsible for recognizing text, mathematical formulas, and layout
from geometry problem images.
Supports two configurable engines via agent_models.yaml:
- 'vlm' (default): Direct high-precision, zero-RAM multimodal VLM (Gemini Vision).
- 'pix2text': Local PyTorch/ONNX Pix2Text engine with Confidence Gateway.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from vision_ocr.canonical_schema import CanonicalOCRResult

logger = logging.getLogger(__name__)


class ImprovedOCRAgent:
    """
    Math OCR Agent (v5.4).
    Dynamically routes to Direct Multimodal VLM or Local Pix2Text Engine based on config.
    """

    def __init__(self, **kwargs):
        self._vision = None
        self._vlm_corrector = None
        logger.info("[ImprovedOCRAgent] Math OCR Agent ready (Configurable VLM / Pix2Text).")

    def _get_engine_mode(self) -> str:
        try:
            from config.loader import load_agent_config
            cfg = load_agent_config("ocr")
            return getattr(cfg, "ocr_engine", "vlm") or "vlm"
        except Exception:
            return "vlm"

    async def process_image_canonical(self, image_path: str) -> CanonicalOCRResult:
        """
        Processes image and returns full CanonicalOCRResult structure.
        """
        mode = self._get_engine_mode()
        if mode == "vlm":
            from agents.vlm_corrector import VLMCorrectorAgent
            if self._vlm_corrector is None:
                self._vlm_corrector = VLMCorrectorAgent()
            return await self._vlm_corrector.extract_direct(image_path=image_path)
        else:
            if self._vision is None:
                from vision_ocr.pipeline import OcrVisionPipeline
                self._vision = OcrVisionPipeline()
            return await self._vision.process_image_canonical(image_path)

    async def process_image(self, image_path: str) -> str:
        """
        Processes image and returns reconstructed Markdown text containing inline and display LaTeX.
        """
        canonical = await self.process_image_canonical(image_path)
        return canonical.text

    async def process_url_canonical(self, url: str) -> CanonicalOCRResult:
        """
        Fetches image from URL and returns full CanonicalOCRResult.
        """
        mode = self._get_engine_mode()
        if mode == "vlm":
            from agents.vlm_corrector import VLMCorrectorAgent
            if self._vlm_corrector is None:
                self._vlm_corrector = VLMCorrectorAgent()
            return await self._vlm_corrector.extract_direct(image_url=url)
        else:
            if self._vision is None:
                from vision_ocr.pipeline import OcrVisionPipeline
                self._vision = OcrVisionPipeline()
            return await self._vision.process_url_canonical(url)

    async def process_url(self, url: str) -> str:
        """
        Fetches image from URL and returns reconstructed Markdown text with LaTeX.
        """
        canonical = await self.process_url_canonical(url)
        return canonical.text


class OCRAgent(ImprovedOCRAgent):
    """Alias for backward compatibility."""
    pass

