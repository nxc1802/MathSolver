import asyncio
import logging

from vision_ocr.pipeline import OcrVisionPipeline

logger = logging.getLogger(__name__)


class ImprovedOCRAgent:
    """
    API-facing OCR: composes ``OcrVisionPipeline`` (vision only) with optional LLM refinement.
    Celery OCR workers should import ``OcrVisionPipeline`` directly from ``vision_ocr``.
    """

    def __init__(self, skip_llm_refinement: bool = False):
        self._skip_llm_refinement = bool(skip_llm_refinement)
        self._vision = OcrVisionPipeline()
        logger.info(
            "[ImprovedOCRAgent] Vision pipeline ready (skip_llm_refinement=%s)...",
            self._skip_llm_refinement,
        )

        if self._skip_llm_refinement:
            self.llm = None
            logger.info("[ImprovedOCRAgent] LLM client skipped (raw OCR only).")
        else:
            from app.llm_client import get_llm_client

            self.llm = get_llm_client()
            logger.info("[ImprovedOCRAgent] Multi-Layer LLM Client initialized.")

    async def process_image(self, image_path: str) -> str:
        combined_text = await self._vision.process_image(image_path)

        if not combined_text.strip():
            return combined_text

        if self._skip_llm_refinement or self.llm is None:
            logger.info("[ImprovedOCRAgent] Skipping MegaLLM refinement (raw OCR output).")
            return combined_text

        try:
            logger.info("[ImprovedOCRAgent] Sending to MegaLLM for refinement...")
            refined_text = await asyncio.wait_for(
                self.refine_with_llm(combined_text), timeout=30.0
            )
            return refined_text
        except asyncio.TimeoutError:
            logger.error("[ImprovedOCRAgent] MegaLLM refinement timed out.")
            return combined_text
        except Exception as e:
            logger.error("[ImprovedOCRAgent] MegaLLM refinement failed: %s", e)
            return combined_text

    async def refine_with_llm(self, text: str) -> str:
        if not text.strip():
            return ""
        if self.llm is None:
            logger.warning("[ImprovedOCRAgent] refine_with_llm: no LLM client; returning raw text.")
            return text

        prompt = f"""Bạn là một chuyên gia số hóa tài liệu toán học.
Dưới đây là kết quả OCR thô từ một trang sách toán Tiếng Việt.
Kết quả này có thể chứa lỗi chính tả, lỗi định dạng mã LaTeX, hoặc bị ngắt quãng không logic.

Nhiệm vụ của bạn:
1. Sửa lỗi chính tả tiếng Việt.
2. Đảm bảo các công thức toán học được viết đúng định dạng LaTeX và nằm trong cặp dấu $...$.
3. Giữ nguyên cấu trúc logic của bài toán.
4. Trả về nội dung đã được làm sạch dưới dạng Markdown.

Nội dung OCR thô:
---
{text}
---

Kết quả làm sạch:"""

        try:
            refined = await self.llm.chat_completions_create(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            logger.info("[ImprovedOCRAgent] LLM refinement complete.")
            return refined
        except Exception as e:
            logger.error("[ImprovedOCRAgent] LLM refinement failed: %s", e)
            return text

    async def process_url(self, url: str) -> str:
        combined_text = await self._vision.process_url(url)

        if not combined_text.strip() or combined_text.lstrip().startswith("Error:"):
            return combined_text

        if self._skip_llm_refinement or self.llm is None:
            return combined_text

        try:
            return await asyncio.wait_for(self.refine_with_llm(combined_text), timeout=30.0)
        except asyncio.TimeoutError:
            logger.error("[ImprovedOCRAgent] MegaLLM refinement timed out.")
            return combined_text
        except Exception as e:
            logger.error("[ImprovedOCRAgent] MegaLLM refinement failed: %s", e)
            return combined_text


class OCRAgent(ImprovedOCRAgent):
    """Alias for compatibility with existing code."""

    pass
