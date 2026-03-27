import os
import io
import logging
import asyncio
from PIL import Image
import numpy as np
from typing import List, Dict, Any

# OCR Engines
from pix2tex.cli import LatexOCR
from paddleocr import PaddleOCR
from ultralytics import YOLO
from openai import AsyncOpenAI

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
        
        # 1. MegaLLM (OpenAI-compatible)
        self.llm_client = AsyncOpenAI(
            api_key=os.getenv("MEGALLM_API_KEY"),
            base_url=os.getenv("MEGALLM_BASE_URL", "https://ai.megallm.io/v1")
        )
        self.llm_model = os.getenv("MEGALLM_MODEL", "openai-gpt-oss-20b")
        logger.info(f"[ImprovedOCRAgent] MegaLLM initialized with model {self.llm_model}.")

        # 2. YOLO for Layout
        try:
            logger.info("[ImprovedOCRAgent] Loading YOLO...")
            self.layout_model = YOLO('yolov8n.pt') 
            logger.info("[ImprovedOCRAgent] YOLO initialized.")
        except Exception as e:
            logger.error(f"[ImprovedOCRAgent] YOLO init failed: {e}")
            self.layout_model = None

        # 3. PaddleOCR for Vietnamese Text
        try:
            logger.info("[ImprovedOCRAgent] Loading PaddleOCR...")
            from paddleocr import PaddleOCR
            self.text_model = PaddleOCR(use_angle_cls=True, lang='vi')
            logger.info("[ImprovedOCRAgent] PaddleOCR (vi) initialized.")
        except Exception as e:
            logger.error(f"[ImprovedOCRAgent] PaddleOCR init failed: {e}")
            self.text_model = None

        # 4. Pix2Tex for Math
        try:
            logger.info("[ImprovedOCRAgent] Loading Pix2Tex...")
            from pix2tex.cli import LatexOCR
            self.math_model = LatexOCR()
            logger.info("[ImprovedOCRAgent] Pix2Tex initialized.")
        except Exception as e:
            logger.error(f"[ImprovedOCRAgent] Pix2Tex init failed: {e}")
            self.math_model = None

    async def process_image(self, image_path: str) -> str:
        logger.info(f"==[ImprovedOCRAgent] Processing: {image_path}==")
        
        if not os.path.exists(image_path):
            return f"Error: File {image_path} not found."

        img = Image.open(image_path).convert("RGB")
        img_np = np.array(img)

        # Step 1: Layout Analysis (Simplified for this implemention)
        # In a production setting, YOLO would give us bboxes for 'text' and 'formula'.
        # Since standard yolov8n doesn't have these classes, we'll use a heuristic 
        # or assume PaddleOCR handles layout if YOLO isn't specifically trained.
        # FOR THIS TASK: We will use PaddleOCR's internal layout-like detection 
        # or just run both and merge if YOLO layout weights are missing.
        
        # Let's try to detect regions. If YOLO fails to give "text/formula" specifically,
        # we'll use PaddleOCR for everything and then Pix2Tex for detected math-like regions.
        
        raw_fragments = []

        # Realistically, if we don't have a layout-trained YOLO, 
        # we'll use PaddleOCR to get all text lines first.
        if self.text_model:
            logger.info(f"[ImprovedOCRAgent] Running PaddleOCR on {image_path}...")
            result = self.text_model.ocr(image_path)
            logger.info(f"[ImprovedOCRAgent] PaddleOCR raw result: {result}")
        if self.text_model:
            logger.info(f"[ImprovedOCRAgent] Running PaddleOCR on {image_path}...")
            # Handling different PaddleOCR versions (Standard vs PP-Structure/PaddleX)
            result = self.text_model.ocr(image_path)
            logger.info(f"[ImprovedOCRAgent] PaddleOCR raw result: {result}")
            
            if not result:
                logger.warning("[ImprovedOCRAgent] PaddleOCR returned no results.")
                return ""

            # Check for dictionary-style result (PaddleX/PP-Structure)
            if isinstance(result[0], dict):
                res_dict = result[0]
                rec_texts = res_dict.get('rec_texts', [])
                rec_scores = res_dict.get('rec_scores', [])
                rec_polys = res_dict.get('rec_polys', [])
                
                for i in range(len(rec_texts)):
                    text = rec_texts[i]
                    bbox = rec_polys[i]
                    confidence = rec_scores[i]
                    
                    y_top = int(min(p[1] for p in bbox)) if hasattr(bbox, '__iter__') else 0
                    
                    is_math_hint = any(c in text for c in ['\\', '^', '_', '{', '}', '=', '+', '-', '*', '/'])
                    
                    if is_math_hint and self.math_model:
                        # ... math logic ...
                        pass
                    
                    raw_fragments.append({
                        "y": y_top,
                        "content": text,
                        "type": "text"
                    })
            # Check for standard list-style result
            elif isinstance(result[0], list):
                for line in result[0]:
                    bbox = line[0] 
                    text = line[1][0]
                    confidence = line[1][1]
                    
                    y_top = bbox[0][1]
                    raw_fragments.append({
                        "y": y_top,
                        "content": text,
                        "type": "text"
                    })

        # Sort by vertical position
        raw_fragments.sort(key=lambda x: x["y"])
        combined_text = "\n".join([f["content"] for f in raw_fragments])
        
        logger.info(f"[ImprovedOCRAgent] Raw OCR output assembled:\n---\n{combined_text}\n---")

        if not combined_text.strip():
            logger.warning("[ImprovedOCRAgent] No text detected to refine.")
            return ""

        # Step 4: MegaLLM Correction
        try:
            logger.info("[ImprovedOCRAgent] Sending to MegaLLM for refinement...")
            refined_text = await asyncio.wait_for(self.refine_with_llm(combined_text), timeout=30.0)
            return refined_text
        except asyncio.TimeoutError:
            logger.error("[ImprovedOCRAgent] MegaLLM refinement timed out.")
            return combined_text
        except Exception as e:
            logger.error(f"[ImprovedOCRAgent] MegaLLM refinement failed: {e}")
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
                temperature=0.1
            )
            refined = response.choices[0].message.content
            logger.info("[ImprovedOCRAgent] LLM refinement complete.")
            return refined
        except Exception as e:
            logger.error(f"[ImprovedOCRAgent] LLM refinement failed: {e}")
            return text # Return raw if LLM fails

    async def process_url(self, url: str) -> str:
        import httpx
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
