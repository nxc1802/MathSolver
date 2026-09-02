from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from config.loader import load_agent_config

if TYPE_CHECKING:
    from agents.ocr_agent import OCRAgent

logger = logging.getLogger(__name__)


async def ocr_from_local_image_path(
    local_path: str,
    original_filename: str | None,
    fallback_agent: "OCRAgent",
) -> str:
    """
    Run OCR on a file on local disk using Pix2Text + Confidence Gateway VLM Correction.
    """
    import inspect
    from vision_ocr.canonical_schema import CanonicalOCRResult

    canonical = None
    if hasattr(fallback_agent, "process_image_canonical"):
        try:
            res = fallback_agent.process_image_canonical(local_path)
            canonical = await res if inspect.isawaitable(res) else res
        except Exception:
            canonical = None

    if canonical is None or not isinstance(canonical, CanonicalOCRResult):
        if hasattr(fallback_agent, "process_image"):
            res = fallback_agent.process_image(local_path)
            text = await res if inspect.isawaitable(res) else res
            canonical = CanonicalOCRResult(text=str(text or ""), confidence=0.5 if not text else 0.8)
        else:
            canonical = CanonicalOCRResult(text="", confidence=0.0)

    ocr_config = load_agent_config("ocr")
    gateway = ocr_config.confidence_gateway

    if gateway and gateway.enabled:
        threshold = gateway.threshold
        ocr_confidence = canonical.confidence

        logger.info(
            f"[OCR Local Gateway] confidence={ocr_confidence:.3f}, threshold={threshold:.2f}, "
            f"gateway_triggered={ocr_confidence < threshold}"
        )

        if ocr_confidence < threshold and gateway.correction.enabled:
            try:
                from agents.vlm_corrector import VLMCorrectorAgent

                corrector = VLMCorrectorAgent(config=gateway.correction)
                correction_result = await corrector.correct(
                    ocr_result=canonical,
                    image_path=local_path,
                )

                if correction_result and correction_result.get("changed"):
                    logger.info(
                        f"[OCR Local Gateway] VLM correction applied: "
                        f"confidence {ocr_confidence:.3f} -> {correction_result.get('confidence', 0.9):.3f}"
                    )
                    return correction_result.get("corrected_text", canonical.text)
            except Exception as e:
                logger.warning(f"[OCR Local Gateway] VLM correction failed: {e}")

    return canonical.text


