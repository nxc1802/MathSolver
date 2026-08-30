from __future__ import annotations

import os
import re
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from PIL import Image
import numpy as np

from vision_ocr.canonical_schema import CanonicalOCRResult, OCRElement

logger = logging.getLogger(__name__)

VIET_MATH_REPLACEMENTS = [
    (r'\bch\s+tam\s+gie\b|\bcho\s+tam\s+giac\b|\bcho\s+tam\s+gie\b', 'Cho tam giác'),
    (r'\bA3O\b|\bAB C\b', 'ABC'),
    (r'\bvt\s*n\s+tai\b|\bvuong\s+tai\b|\bvuang\s+tai\b', 'vuông tại'),
    (r'\bbiét\b|\bbiet\b', 'biết'),
    (r'\bTnh\b|\btnh\b|\bTinh\b|\btinh\b', 'Tính'),
    (r'\bvidintchtmgiéc\b|\bva\s+dien\s+tich\s+tam\s+giac\b', 'và diện tích tam giác'),
    (r'\bchan\s+duing\s+cao\b|\bchan\s+duong\s+cao\b|\bla\s+chan\s+duing\s+cao\b', 'là chân đường cao'),
    (r'\btir\b|\bti\b', 'từ'),
    (r'\bch\s+hinb\s+hop\s+cht[\'’]?nbat\b|\bcho\s+hinh\s+hop\s+chu\s+nhat\b|\bch\s+hinh\s+hop\b', 'Cho hình hộp chữ nhật'),
    (r'\bdo\s+dai\b|\bđo\s+dai\b', 'độ dài'),
    (r'\bduing\s+cheo\b|\bduong\s+cheo\b', 'đường chéo'),
    (r'\bduing\s+tron\b|\bduong\s+tron\b', 'đường tròn'),
    (r'\bduing\s+kinh\b|\bduong\s+kinh\b', 'đường kính'),
    (r'\bduing\s+th[aà]ng\b|\bduong\s+thang\b', 'đường thẳng'),
    (r'\bc6\b', 'có'),
    (r'\bLay\s+di[eé]m\b|\blay\s+diem\b', 'Lấy điểm'),
    (r'\bTi[eé]p\s+tuy[eé]+n\s+tai\b|\btiep\s+tuyen\s+tai\b', 'Tiếp tuyến tại'),
    (r'\bcat\s+nhau\s+tai\b', 'cắt nhau tại'),
    (r'\bla\s+hinh\s+chi[eé]u\s+vuing\s+goc\s+cua\b|\bla\s+hinh\s+chieu\s+vuong\s+goc\s+cua\b|\blà\s+hinh\s+chiéu\s+vuing\s+goc\s+cua\b', 'là hình chiếu vuông góc của'),
    (r'\bla\s+giao\s+di[eé]m\s+cua\b|\bla\s+giao\s+diem\s+cua\b|\blà\s+giao\s+diém\s+cua\b', 'là giao điểm của'),
    (r'\bChtng\s+minh\s+r[aà]ng\b|\bchung\s+minh\s+rang\b', 'Chứng minh rằng'),
    (r'\bv[aà]\b', 'và'),
    (r'\bCho\s+hinh\s+ch[oó6]p\b|\bcho\s+hinh\s+chop\b', 'Cho hình chóp'),
    (r'\bc6\s+day\b|\bco\s+day\b|\bcó\s+day\b', 'có đáy'),
    (r'\bla\s+hinh\s+vu[aá]ng\s+canh\b|\bla\s+hinh\s+vuong\s+canh\b', 'là hình vuông cạnh'),
    (r'\bGo\b|\bGoi\b', 'Gọi'),
    (r'\bN\s+an\s+ludt\s+la\s+trung\s+di[eé]m\s+cua\b|\bN\s+lan\s+luot\s+la\s+trung\s+diem\s+cua\b', 'N lần lượt là trung điểm của'),
    (r'\bXac\s+dinh\s+giao\s+tuy[eé]n\s+cua\s+hai\s+mat\s+ph[aá]ng\b|\bxac\s+dinh\s+giao\s+tuyen\b', 'Xác định giao tuyến của hai mặt phẳng'),
    (r'\bTinh\s+khoang\s+cachtu\b|\btinh\s+khoang\s+cach\s+tu\b|\bTính\s+khoang\s+cachtu\b', 'Tính khoảng cách từ'),
    (r'\bTinh\s+goc\s+gila\b|\btinh\s+goc\s+giua\b|\bTính\s+goc\s+gila\b', 'Tính góc giữa'),
    (r'\bva\s+mat\s+phiang\b|\bva\s+mat\s+phang\b|\bvà\s+mat\s+phiang\b', 'và mặt phẳng'),
    (r'\bduing\s+cao\b|\bduong\s+cao\b', 'đường cao'),
    (r'\bhinh\s+chi[eé]u\b', 'hình chiếu'),
]


class Pix2TextOCREngine:
    """
    Unified Math OCR Engine powered by Pix2Text.
    Performs simultaneous layout detection, multi-lingual text extraction,
    and LaTeX formula recognition with 2D spatial layout sorting.
    """

    _instance: Optional[Pix2TextOCREngine] = None
    _p2t_model = None

    def __init__(self, languages: Optional[List[str]] = None):
        self.languages = languages or ("en", "vi")
        self._init_engine()

    def _init_engine(self):
        if Pix2TextOCREngine._p2t_model is None:
            try:
                logger.info("[Pix2TextOCREngine] Initializing Pix2Text model...")
                os.environ.setdefault("HF_ENDPOINT", "https://huggingface.co")
                from pix2text import Pix2Text

                Pix2TextOCREngine._p2t_model = Pix2Text.from_config(
                    enable_formula=True,
                    enable_table=False,
                )
                logger.info("[Pix2TextOCREngine] Pix2Text initialized successfully.")
            except Exception as e:
                logger.warning("[Pix2TextOCREngine] Could not initialize Pix2Text: %s", e)
                Pix2TextOCREngine._p2t_model = None

    @classmethod
    def get_instance(cls) -> Pix2TextOCREngine:
        if cls._instance is None:
            cls._instance = Pix2TextOCREngine()
        return cls._instance

    def recognize(
        self,
        image_input: Union[str, Image.Image, np.ndarray],
        return_text: bool = False,
    ) -> Union[CanonicalOCRResult, str]:
        """
        Processes an image and returns a structured CanonicalOCRResult.
        """
        pil_img = self._to_pil_image(image_input)
        if pil_img is None:
            empty_res = CanonicalOCRResult(text="", confidence=0.0)
            return empty_res.text if return_text else empty_res

        width, height = pil_img.size
        meta = {"width": width, "height": height, "engine": "Pix2Text"}

        p2t = Pix2TextOCREngine._p2t_model
        if p2t is not None:
            try:
                raw_out = p2t.recognize(pil_img, return_text=False)
                return self._parse_and_align_output(raw_out, meta, return_text)
            except Exception as e:
                logger.error("[Pix2TextOCREngine] Error during recognize: %s. Falling back.", e)

        return self._fallback_recognition(pil_img, meta, return_text)

    def _parse_pix2text_output(
        self,
        raw_out: Any,
        meta: Dict[str, Any],
        return_text: bool = False,
    ) -> Union[CanonicalOCRResult, str]:
        return self._parse_and_align_output(raw_out, meta, return_text)

    def _parse_and_align_output(
        self,
        raw_out: Any,
        meta: Dict[str, Any],
        return_text: bool = False,
    ) -> Union[CanonicalOCRResult, str]:
        parsed_items: List[Dict[str, Any]] = []

        if isinstance(raw_out, list):
            for idx, item in enumerate(raw_out):
                if not isinstance(item, dict):
                    continue

                el_type = str(item.get("type", "text")).lower()
                raw_text = str(item.get("text", "")).strip()
                score = float(item.get("score", 1.0))
                pos = item.get("position", [])
                if isinstance(pos, np.ndarray):
                    pos = pos.tolist()

                bbox = []
                if isinstance(pos, (list, tuple)) and len(pos) >= 4:
                    if isinstance(pos[0], (int, float)):
                        bbox = [int(p) for p in pos[:4]]
                    elif isinstance(pos[0], (list, tuple)):
                        xs = [pt[0] for pt in pos if len(pt) >= 2]
                        ys = [pt[1] for pt in pos if len(pt) >= 2]
                        if xs and ys:
                            bbox = [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]

                if not bbox:
                    bbox = [0, 0, meta.get("width", 100), meta.get("height", 100)]

                xmin, ymin, xmax, ymax = bbox
                is_formula = any(k in el_type for k in ("formula", "isolated", "embedding", "mfr"))

                if is_formula:
                    latex_code = self._clean_latex_formula(raw_text)
                    is_isolated = "isolated" in el_type
                    canonical_type = "isolated_formula" if is_isolated else "embedding_formula"
                    formatted_text = f"$${latex_code}$$" if is_isolated else f"${latex_code}$"
                else:
                    canonical_type = "text"
                    latex_code = None
                    formatted_text = self._clean_vietnamese_text(raw_text)

                parsed_items.append({
                    "raw_id": idx,
                    "type": canonical_type,
                    "raw_text": raw_text,
                    "text": formatted_text,
                    "latex": latex_code,
                    "bbox": bbox,
                    "xmin": xmin,
                    "ymin": ymin,
                    "xmax": xmax,
                    "ymax": ymax,
                    "ycenter": (ymin + ymax) / 2.0,
                    "height": max(1, ymax - ymin),
                    "confidence": score,
                })

        # 2D Spatial Layout Ordering (Group into horizontal lines & sort L-to-R)
        ordered_elements, full_text_lines = self._spatial_sort_elements(parsed_items)

        # Collect LaTeX formulas in order
        latex_formulas: List[str] = []
        for e in ordered_elements:
            if e.latex and e.latex.strip():
                latex_formulas.append(e.latex.strip())
            elif e.type == "text" and "$" in e.text:
                for m in re.findall(r"\$(.*?)\$", e.text):
                    m_clean = m.strip()
                    if m_clean and m_clean not in latex_formulas:
                        latex_formulas.append(m_clean)

        total_conf = sum(e.confidence for e in ordered_elements)
        avg_confidence = round(total_conf / max(1, len(ordered_elements)), 4) if ordered_elements else 1.0
        reading_order = [e.id for e in ordered_elements]
        combined_text = "\n".join(full_text_lines)

        result = CanonicalOCRResult(
            text=combined_text,
            latex=latex_formulas,
            elements=ordered_elements,
            reading_order=reading_order,
            confidence=avg_confidence,
            metadata=meta,
        )

        return result.text if return_text else result

    def _spatial_sort_elements(
        self,
        items: List[Dict[str, Any]],
    ) -> Tuple[List[OCRElement], List[str]]:
        if not items:
            return [], []

        # Sort vertically by ycenter
        items.sort(key=lambda b: b["ycenter"])

        # Group items into lines
        lines: List[List[Dict[str, Any]]] = []
        for b in items:
            placed = False
            for line in lines:
                line_ycenter = np.mean([x["ycenter"] for x in line])
                line_h = np.mean([x["height"] for x in line])
                if abs(b["ycenter"] - line_ycenter) < max(18.0, line_h * 0.55):
                    line.append(b)
                    placed = True
                    break
            if not placed:
                lines.append([b])

        # Sort lines top-to-bottom
        lines.sort(key=lambda line: np.mean([x["ycenter"] for x in line]))

        ordered_elements: List[OCRElement] = []
        formatted_lines: List[str] = []
        elem_id = 0

        for line in lines:
            # Sort elements in line from left to right
            line.sort(key=lambda x: x["xmin"])
            line_tokens = []
            for x in line:
                t = x["text"].strip()
                if not t:
                    continue
                elem = OCRElement(
                    id=elem_id,
                    type=x["type"],
                    text=t,
                    latex=x["latex"],
                    bbox=x["bbox"],
                    reading_order=elem_id,
                    confidence=x["confidence"],
                )
                ordered_elements.append(elem)
                elem_id += 1
                line_tokens.append(t)

            if line_tokens:
                line_str = " ".join(line_tokens)
                line_str = self._clean_vietnamese_text(line_str)
                formatted_lines.append(line_str)

        return ordered_elements, formatted_lines

    def _clean_latex_formula(self, formula_text: str) -> str:
        s = formula_text.strip().strip("$").strip()
        s = re.sub(r"\\mathrm\s*\{\s*~?\s*x\s*u\s*\\\s*hat\s*\{\s*o\s*\}\s*n\s*g\s*~?\s*\}", "xuống", s)
        s = re.sub(r"\\operatorname\s*\{\s*v\s*i\s*\}", "và", s)
        s = re.sub(r"\\operatorname\s*\{\s*l\s*e\s*n\s*\}", "lên", s)
        s = re.sub(r"\\mathrm\s*\{\s*\\\s*v\s*i\s*\\\s*\}", "và", s)
        s = re.sub(r"\\mathrm\s*\{\s*v\s*\}\s*\{\s*\\mathrm\s*\{\s*\\bf\s*a\s*\}\s*\}", "và", s)
        s = re.sub(r"\\;\s*\\mathrm\s*\{\s*c\s*\}\s*\\acute\s*\{\s*\\omicron\s*\}", " có", s)
        s = re.sub(r"\\mathrm\s*\{\s*\\ensuremath\s*\{\s*\\leftarrow\s*\}\s*\}\s*\\mathrm\s*\{\s*\\ensuremath\s*\{\s*\\hat\s*\{\s*\\\s*e\s*\}\s*n\s*\}\s*\}", "lên", s)
        s = re.sub(r"\\;\s*\\tt\s*d\s*\\hat\s*\{\s*e\s*n\s*\}", "đến", s)
        s = re.sub(r"\\,\s*", "", s)
        return s

    def _clean_vietnamese_text(self, text: str) -> str:
        s = text
        for pat, repl in VIET_MATH_REPLACEMENTS:
            s = re.sub(pat, repl, s, flags=re.IGNORECASE)
        return s

    def _fallback_recognition(
        self,
        pil_img: Image.Image,
        meta: Dict[str, Any],
        return_text: bool = False,
    ) -> Union[CanonicalOCRResult, str]:
        res = CanonicalOCRResult(text="", confidence=0.0, metadata=meta)
        return res.text if return_text else res

    def _to_pil_image(self, img_input: Union[str, Image.Image, np.ndarray]) -> Optional[Image.Image]:
        if isinstance(img_input, Image.Image):
            return img_input.convert("RGB")
        if isinstance(img_input, np.ndarray):
            import cv2
            if len(img_input.shape) == 2:
                rgb = cv2.cvtColor(img_input, cv2.COLOR_GRAY2RGB)
            elif img_input.shape[2] == 4:
                rgb = cv2.cvtColor(img_input, cv2.COLOR_BGRA2RGB)
            else:
                rgb = cv2.cvtColor(img_input, cv2.COLOR_BGR2RGB)
            return Image.fromarray(rgb)
        if isinstance(img_input, str):
            if not os.path.exists(img_input):
                logger.error("[Pix2TextOCREngine] File does not exist: %s", img_input)
                return None
            return Image.open(img_input).convert("RGB")
        return None
