"""
VLM OCR Corrector Agent.

Uses a multimodal Vision-Language Model to correct OCR errors when confidence is low.
Strictly adheres to READ/CORRECT/PRESERVE boundaries — never SOLVE/INFER/INVENT.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from config.schemas import OCRCorrectionConfig
from llm.service import get_llm_service
from vision_ocr.canonical_schema import CanonicalOCRResult

logger = logging.getLogger(__name__)


class VLMCorrectorAgent:
    """
    VLM-based OCR correction agent.

    Receives raw image + OCR output + confidence and uses a multimodal LLM
    to correct OCR recognition errors.

    Strict boundary:
    - READ: Re-read text and formulas from the image
    - CORRECT: Fix OCR misrecognitions
    - PRESERVE: Keep all original information intact

    Never:
    - SOLVE: Do not solve the math problem
    - INFER: Do not infer missing geometry values
    - INVENT: Do not add information not visible in the image
    """

    def __init__(self, config: Optional[OCRCorrectionConfig] = None):
        self.config = config or OCRCorrectionConfig()
        self.llm_service = get_llm_service()

    async def correct(
        self,
        ocr_result: CanonicalOCRResult,
        image_url: Optional[str] = None,
        image_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Correct OCR errors using VLM.

        Args:
            ocr_result: The original OCR result with text and confidence
            image_url: URL of the original image (for multimodal input)
            image_path: Local path to the original image

        Returns:
            Dict with corrected_text, changed, confidence, corrections[]
        """
        if not image_url and not image_path:
            logger.warning("[VLMCorrector] No image provided, skipping correction")
            return {"changed": False, "corrected_text": ocr_result.text, "confidence": ocr_result.confidence, "corrections": []}

        system_prompt = """You are an OCR Correction Agent for Vietnamese mathematical geometry problems.

=== YOUR TASK ===
You receive:
1. An image of a math problem
2. OCR-extracted text (which may contain errors)
3. OCR confidence score

Your job is to CORRECT OCR recognition errors by re-reading the image carefully.

=== STRICT BOUNDARIES ===
You MUST ONLY:
- READ: Re-read text, numbers, and mathematical formulas from the image
- CORRECT: Fix misrecognized characters, numbers, symbols, and LaTeX
- PRESERVE: Keep all original information intact

You MUST NOT:
- SOLVE: Do not solve or attempt to solve the math problem
- INFER: Do not infer missing values or geometry relationships
- INVENT: Do not add any information not visible in the image
- If a value is unclear or unreadable, mark it as "?" — do NOT guess

=== OUTPUT FORMAT ===
Output ONLY a JSON object:
{
    "corrected_text": "The corrected full text with proper LaTeX",
    "changed": true/false,
    "confidence": 0.95,
    "corrections": [
        {
            "original": "SA = 8",
            "corrected": "SA = 6",
            "reason": "OCR misread digit 6 as 8"
        }
    ]
}

If no corrections are needed, set "changed": false and return the original text."""

        user_content_parts = []

        # Add image content for multimodal input
        if image_url:
            user_content_parts.append({
                "type": "image_url",
                "image_url": {"url": image_url},
            })

        user_content_parts.append({
            "type": "text",
            "text": f"""OCR Extracted Text (confidence: {ocr_result.confidence:.3f}):

{ocr_result.text}

Please carefully compare the image with the OCR text above and correct any recognition errors.""",
        })

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content_parts},
        ]

        try:
            raw_response = await self.llm_service.acomplete(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout_seconds,
                agent_name="vlm_corrector",
            )

            result = self._parse_correction_response(raw_response, ocr_result.text)
            logger.info(
                f"[VLMCorrector] Correction result: changed={result.get('changed')}, "
                f"corrections={len(result.get('corrections', []))}"
            )
            return result

        except Exception as e:
            logger.error(f"[VLMCorrector] Correction failed: {e}")
            return {
                "changed": False,
                "corrected_text": ocr_result.text,
                "confidence": ocr_result.confidence,
                "corrections": [],
            }

    def _parse_correction_response(self, raw: str, original_text: str) -> Dict[str, Any]:
        """Parse VLM correction response JSON."""
        try:
            cleaned = raw.strip()
            # Extract JSON from markdown code block if present
            json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
            if json_match:
                cleaned = json_match.group(1).strip()

            # Try direct JSON parse
            brace_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if brace_match:
                cleaned = brace_match.group(1)

            data = json.loads(cleaned)

            return {
                "corrected_text": data.get("corrected_text", original_text),
                "changed": bool(data.get("changed", False)),
                "confidence": float(data.get("confidence", 0.9)),
                "corrections": data.get("corrections", []),
            }
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"[VLMCorrector] Failed to parse response: {e}")
            return {
                "changed": False,
                "corrected_text": original_text,
                "confidence": 0.5,
                "corrections": [],
            }
