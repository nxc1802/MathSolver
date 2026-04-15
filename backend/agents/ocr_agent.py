import os
import uuid
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_OCR_MAX_EDGE = 2000
_CROP_PAD = 4


class ImprovedOCRAgent:
    """
    Advanced OCR Agent using a hybrid pipeline:
    1. YOLO for layout analysis (text vs formula).
    2. PaddleOCR for Vietnamese text extraction.
    3. Pix2Tex for LaTeX formula extraction.
    4. Optional MegaLLM for semantic correction and formatting (skipped when ``skip_llm_refinement`` is True,
       e.g. on the dedicated OCR Celery worker; the API Space runs ``refine_with_llm`` on the raw text).
    """

    def __init__(self, skip_llm_refinement: bool = False):
        self._skip_llm_refinement = bool(skip_llm_refinement)
        logger.info("[ImprovedOCRAgent] Initializing engines (skip_llm_refinement=%s)...", self._skip_llm_refinement)

        if self._skip_llm_refinement:
            self.llm = None
            logger.info("[ImprovedOCRAgent] LLM client skipped (raw OCR only).")
        else:
            from app.llm_client import get_llm_client

            self.llm = get_llm_client()
            logger.info("[ImprovedOCRAgent] Multi-Layer LLM Client initialized.")

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

    def _preprocess_image_for_ocr(self, src_path: str) -> Tuple[str, bool]:
        """Resize large images, CLAHE on luminance; returns path (may be new temp file)."""
        img = cv2.imread(src_path, cv2.IMREAD_COLOR)
        if img is None:
            g = cv2.imread(src_path, cv2.IMREAD_GRAYSCALE)
            if g is None:
                logger.warning("[ImprovedOCRAgent] OpenCV could not read %s; using original.", src_path)
                return src_path, False
            img = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
        h, w = img.shape[:2]
        max_dim = max(h, w)
        if max_dim > _OCR_MAX_EDGE:
            scale = _OCR_MAX_EDGE / max_dim
            img = cv2.resize(
                img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA
            )
            logger.info("[ImprovedOCRAgent] Resized for OCR to max edge %s", _OCR_MAX_EDGE)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        den = cv2.fastNlMeansDenoising(gray, None, 8, 7, 21)
        out = f"temp_ocr_prep_{uuid.uuid4().hex}.png"
        cv2.imwrite(out, den)
        return out, True

    def _load_bgr_for_crops(self, path: str) -> Optional[np.ndarray]:
        im = cv2.imread(path, cv2.IMREAD_COLOR)
        if im is None:
            g = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if g is None:
                return None
            im = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
        return im

    def _crop_from_quad(self, img_bgr: np.ndarray, bbox) -> Optional[np.ndarray]:
        try:
            pts = np.array(bbox, dtype=np.float32)
            xs = pts[:, 0]
            ys = pts[:, 1]
            H, W = img_bgr.shape[:2]
            x1 = max(0, int(xs.min()) - _CROP_PAD)
            y1 = max(0, int(ys.min()) - _CROP_PAD)
            x2 = min(W, int(xs.max()) + _CROP_PAD)
            y2 = min(H, int(ys.max()) + _CROP_PAD)
            if x2 <= x1 or y2 <= y1:
                return None
            return img_bgr[y1:y2, x1:x2].copy()
        except Exception as e:
            logger.debug("[ImprovedOCRAgent] crop failed: %s", e)
            return None

    def _latex_from_crop_bgr(self, crop_bgr: np.ndarray) -> Optional[str]:
        if self.math_model is None or crop_bgr is None or crop_bgr.size == 0:
            return None
        ch, cw = crop_bgr.shape[:2]
        if ch < 10 or cw < 10:
            return None
        try:
            from PIL import Image

            rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(rgb)
            out = self.math_model(pil)
            if isinstance(out, str) and out.strip():
                return out.strip()
        except Exception as e:
            logger.debug("[ImprovedOCRAgent] Pix2Tex on crop failed: %s", e)
        return None

    def _maybe_math_from_crop(self, img_bgr: Optional[np.ndarray], bbox, text: str) -> str:
        if img_bgr is None or not self.math_model:
            return text
        is_math_hint = any(
            c in text for c in ["\\", "^", "_", "{", "}", "=", "+", "-", "*", "/"]
        )
        if not is_math_hint:
            return text
        crop = self._crop_from_quad(img_bgr, bbox)
        latex = self._latex_from_crop_bgr(crop) if crop is not None else None
        if latex:
            logger.info("[ImprovedOCRAgent] Pix2Tex replaced line fragment (len=%s)", len(latex))
            return f"${latex}$"
        return text

    async def process_image(self, image_path: str) -> str:
        logger.info("==[ImprovedOCRAgent] Processing: %s==", image_path)

        if not os.path.exists(image_path):
            return f"Error: File {image_path} not found."

        prep_path, prep_cleanup = self._preprocess_image_for_ocr(image_path)
        paddle_path = prep_path if prep_cleanup else image_path
        img_bgr = self._load_bgr_for_crops(prep_path if prep_cleanup else image_path)

        raw_fragments: List[Dict[str, Any]] = []

        try:
            if self.text_model:
                logger.info("[ImprovedOCRAgent] Running PaddleOCR on %s...", paddle_path)
                result = self.text_model.ocr(paddle_path)
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
                        score = rec_scores[i] if i < len(rec_scores) else None
                        if score is not None and float(score) < 0.45:
                            logger.debug(
                                "[ImprovedOCRAgent] Low-confidence line (score=%s): %s",
                                score,
                                text[:80],
                            )

                        y_top = int(min(p[1] for p in bbox)) if hasattr(bbox, "__iter__") else 0
                        content = self._maybe_math_from_crop(img_bgr, bbox, text)
                        raw_fragments.append({"y": y_top, "content": content, "type": "text"})
                elif isinstance(result[0], list):
                    for line in result[0]:
                        bbox = line[0]
                        text = line[1][0]
                        score = line[1][1] if len(line[1]) > 1 else None
                        if score is not None and float(score) < 0.45:
                            logger.debug(
                                "[ImprovedOCRAgent] Low-confidence line (score=%s): %s",
                                score,
                                text[:80],
                            )

                        y_top = int(bbox[0][1])
                        content = self._maybe_math_from_crop(img_bgr, bbox, text)
                        raw_fragments.append({"y": y_top, "content": content, "type": "text"})
        finally:
            if prep_cleanup and os.path.exists(prep_path):
                try:
                    os.remove(prep_path)
                except OSError:
                    pass

        raw_fragments.sort(key=lambda x: x["y"])
        combined_text = "\n".join([f["content"] for f in raw_fragments])

        logger.info(
            "[ImprovedOCRAgent] Raw OCR output assembled:\n---\n%s\n---", combined_text
        )

        if not combined_text.strip():
            logger.warning("[ImprovedOCRAgent] No text detected to refine.")
            return ""

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
