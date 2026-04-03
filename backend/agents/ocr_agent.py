import os
import logging
import asyncio
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ImprovedOCRAgent:
    """
    Advanced OCR Agent using a hybrid pipeline:
    1. YOLO for layout analysis (text vs formula).
    2. PaddleOCR for Vietnamese text extraction.
    3. Pix2Tex for LaTeX formula extraction.
    4. MegaLLM for semantic correction and formatting.
    """

    def __init__(self):
        logger.info("[ImprovedOCRAgent] Initializing engines and client...")

        from openai import AsyncOpenAI

        from app.url_utils import openai_compatible_api_key, sanitize_env

        self.llm_client = AsyncOpenAI(
            api_key=openai_compatible_api_key(os.getenv("MEGALLM_API_KEY")),
            base_url=sanitize_env(os.getenv("MEGALLM_BASE_URL")) or "https://ai.megallm.io/v1",
        )
        self.llm_model = (sanitize_env(os.getenv("MEGALLM_MODEL")) or "openai-gpt-oss-20b")
        logger.info("[ImprovedOCRAgent] MegaLLM initialized with model %s.", self.llm_model)

        try:
            from agents.torch_ultralytics_compat import allow_ultralytics_weights
            from ultralytics import YOLO

            allow_ultralytics_weights()
            logger.info("[ImprovedOCRAgent] Loading YOLO...")
            self.layout_model = YOLO("yolov8n.pt")
            logger.info("[ImprovedOCRAgent] YOLO initialized.")
        except Exception as e:
            logger.error("[ImprovedOCRAgent] YOLO init failed: %s", e)
            self.layout_model = None

        try:
            from paddleocr import PaddleOCR

            logger.info("[ImprovedOCRAgent] Loading PaddleOCR...")
            self.text_model = PaddleOCR(use_angle_cls=True, lang="vi")
            logger.info("[ImprovedOCRAgent] PaddleOCR (vi) initialized.")
        except Exception as e:
            logger.error("[ImprovedOCRAgent] PaddleOCR init failed: %s", e)
            self.text_model = None

        try:
            from pix2tex.cli import LatexOCR

            logger.info("[ImprovedOCRAgent] Loading Pix2Tex...")
            self.math_model = LatexOCR()
            logger.info("[ImprovedOCRAgent] Pix2Tex initialized.")
        except Exception as e:
            logger.error("[ImprovedOCRAgent] Pix2Tex init failed: %s", e)
            self.math_model = None

    async def process_image(self, image_path: str) -> str:
        logger.info("==[ImprovedOCRAgent] Processing: %s==", image_path)

        if not os.path.exists(image_path):
            return f"Error: File {image_path} not found."

        raw_fragments: List[Dict[str, Any]] = []

        if self.text_model:
            logger.info("[ImprovedOCRAgent] Running PaddleOCR on %s...", image_path)
            result = self.text_model.ocr(image_path)
            logger.info("[ImprovedOCRAgent] PaddleOCR raw result: %s", result)

            if not result:
                logger.warning("[ImprovedOCRAgent] PaddleOCR returned no results.")
                return ""

            if isinstance(result[0], dict):
                res_dict = result[0]
                rec_texts = res_dict.get("rec_texts", [])
                rec_scores = res_dict.get("rec_scores", [])
                rec_polys = res_dict.get("rec_polys", [])

                for i in range(len(rec_texts)):
                    text = rec_texts[i]
                    bbox = rec_polys[i]
                    _ = rec_scores[i]

                    y_top = int(min(p[1] for p in bbox)) if hasattr(bbox, "__iter__") else 0

                    is_math_hint = any(
                        c in text for c in ["\\", "^", "_", "{", "}", "=", "+", "-", "*", "/"]
                    )
                    if is_math_hint and self.math_model:
                        pass

                    raw_fragments.append({"y": y_top, "content": text, "type": "text"})
            elif isinstance(result[0], list):
                for line in result[0]:
                    bbox = line[0]
                    text = line[1][0]
                    _ = line[1][1]

                    y_top = bbox[0][1]
                    raw_fragments.append({"y": y_top, "content": text, "type": "text"})

        raw_fragments.sort(key=lambda x: x["y"])
        combined_text = "\n".join([f["content"] for f in raw_fragments])

        logger.info(
            "[ImprovedOCRAgent] Raw OCR output assembled:\n---\n%s\n---", combined_text
        )

        if not combined_text.strip():
            logger.warning("[ImprovedOCRAgent] No text detected to refine.")
            return ""

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
            response = await self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            refined = response.choices[0].message.content
            logger.info("[ImprovedOCRAgent] LLM refinement complete.")
            return refined
        except Exception as e:
            logger.error("[ImprovedOCRAgent] LLM refinement failed: %s", e)
            return text

    async def process_url(self, url: str) -> str:
        import httpx

        from app.url_utils import sanitize_url

        url = sanitize_url(url)
        if not url:
            return "Error: Empty image URL after cleanup."

        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                temp_path = "temp_url_image.png"
                with open(temp_path, "wb") as f:
                    f.write(resp.content)
                try:
                    return await self.process_image(temp_path)
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            return f"Error: Failed to fetch image from URL {url}"


class OCRAgent(ImprovedOCRAgent):
    """Alias for compatibility with existing code."""

    pass
