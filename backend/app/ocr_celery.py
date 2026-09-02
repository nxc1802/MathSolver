"""OCR pipeline with confidence gateway support."""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, Optional

import anyio

from config.loader import load_agent_config
from vision_ocr.canonical_schema import CanonicalOCRResult

if TYPE_CHECKING:
    from agents.ocr_agent import OCRAgent

logger = logging.getLogger(__name__)


async def ocr_from_image_url(
    image_url: str,
    fallback_agent: "OCRAgent",
    raw_image_path: Optional[str] = None,
) -> CanonicalOCRResult:
    """
    Process OCR from image URL using OCRAgent (Pix2Text Engine).
    Returns full CanonicalOCRResult with confidence metadata.
    If confidence < gateway threshold, triggers VLM correction (if enabled).
    """
    # Get canonical OCR result (with confidence)
    canonical = await fallback_agent.process_url_canonical(image_url)

    # Check confidence gateway
    ocr_config = load_agent_config("ocr")
    gateway = ocr_config.confidence_gateway

    if gateway and gateway.enabled:
        threshold = gateway.threshold
        ocr_confidence = canonical.confidence

        logger.info(
            f"[OCR Gateway] confidence={ocr_confidence:.3f}, threshold={threshold:.2f}, "
            f"gateway_triggered={ocr_confidence < threshold}"
        )

        if ocr_confidence < threshold and gateway.correction.enabled:
            try:
                from agents.vlm_corrector import VLMCorrectorAgent

                corrector = VLMCorrectorAgent(config=gateway.correction)
                correction_result = await corrector.correct(
                    ocr_result=canonical,
                    image_url=image_url,
                    image_path=raw_image_path,
                )

                if correction_result and correction_result.get("changed"):
                    corrected_text = correction_result.get("corrected_text", canonical.text)
                    corrected_confidence = correction_result.get("confidence", ocr_confidence)
                    logger.info(
                        f"[OCR Gateway] VLM correction applied: "
                        f"confidence {ocr_confidence:.3f} → {corrected_confidence:.3f}"
                    )
                    # Return updated canonical result
                    canonical = CanonicalOCRResult(
                        text=corrected_text,
                        latex=canonical.latex,
                        elements=canonical.elements,
                        reading_order=canonical.reading_order,
                        confidence=corrected_confidence,
                        metadata={
                            **canonical.metadata,
                            "vlm_correction": True,
                            "original_confidence": ocr_confidence,
                            "corrections": correction_result.get("corrections", []),
                        },
                    )
                else:
                    logger.info("[OCR Gateway] VLM correction: no changes needed")
            except ImportError:
                logger.warning("[OCR Gateway] VLM corrector not available, skipping correction")
            except Exception as e:
                logger.warning(f"[OCR Gateway] VLM correction failed: {e}")

    return canonical
