import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


# ─── Shape rule registry ────────────────────────────────────────────────────
# Each entry: keyword list → augmentation function
# Augmentation receives (values: dict, text: str) and returns updated values dict.

class KnowledgeAgent:
    """Knowledge Agent: Stores geometric theorems and common patterns to augment Parser output."""

    def augment_semantic_data(self, semantic_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("==[KnowledgeAgent] Augmenting semantic data==")
        text = str(semantic_data.get("input_text", "")).lower()
        logger.debug(f"[KnowledgeAgent] Input text for matching: '{text[:200]}'")

        shape_type = self._detect_shape(text, semantic_data.get("type", ""))
        if shape_type:
            semantic_data["type"] = shape_type
            values = semantic_data.get("values", {})
            values = self._augment_values(shape_type, values, text)
            semantic_data["values"] = values
        else:
            logger.info("[KnowledgeAgent] No special rule matched. Returning data unchanged.")

        logger.debug(f"[KnowledgeAgent] Output semantic data: {semantic_data}")
        return semantic_data

    # ─── Shape detection ────────────────────────────────────────────────────
    def _detect_shape(self, text: str, llm_type: str) -> str | None:
        """Detect shape from text keywords. LLM type provides a hint."""
        checks = [
            (["hình vuông", "square"],                      "square"),
            (["hình chữ nhật", "rectangle"],                "rectangle"),
            (["hình thoi", "rhombus"],                      "rhombus"),
            (["hình bình hành", "parallelogram"],            "parallelogram"),
            (["hình thang vuông"],                           "right_trapezoid"),
            (["hình thang", "trapezoid", "trapezium"],       "trapezoid"),
            (["tam giác vuông", "right triangle"],           "right_triangle"),
            (["tam giác đều", "equilateral triangle", "equilateral"], "equilateral_triangle"),
            (["tam giác cân", "isosceles"],                  "isosceles_triangle"),
            (["tam giác", "triangle"],                       "triangle"),
            (["đường tròn", "circle"],                       "circle"),
        ]
        for keywords, shape in checks:
            if any(kw in text for kw in keywords):
                logger.info(f"[KnowledgeAgent] Rule MATCH: '{shape}' detected (keyword match).")
                return shape

        # Fallback: trust LLM-detected type if it's a known type
        known = {
            "rectangle", "square", "rhombus", "parallelogram",
            "trapezoid", "right_trapezoid", "triangle", "right_triangle",
            "equilateral_triangle", "isosceles_triangle", "circle",
        }
        if llm_type in known:
            logger.info(f"[KnowledgeAgent] Using LLM-detected type '{llm_type}'.")
            return llm_type

        return None

    # ─── Value augmentation ──────────────────────────────────────────────────
    def _augment_values(self, shape: str, values: dict, text: str) -> dict:
        ab = values.get("AB")
        ad = values.get("AD")
        bc = values.get("BC")
        cd = values.get("CD")

        if shape == "rectangle":
            if ab and ad:
                values.setdefault("CD", ab)
                values.setdefault("BC", ad)
                values.setdefault("angle_A", 90)
                logger.info(f"[KnowledgeAgent] Rectangle: AB=CD={ab}, AD=BC={ad}, angle_A=90°")
            else:
                values.setdefault("angle_A", 90)

        elif shape == "square":
            side = ab or ad or bc or cd or values.get("side")
            if side:
                values.update({"AB": side, "BC": side, "CD": side, "DA": side, "angle_A": 90})
                logger.info(f"[KnowledgeAgent] Square: all sides={side}, angle_A=90°")
            else:
                values.setdefault("angle_A", 90)

        elif shape == "rhombus":
            side = ab or values.get("side")
            if side:
                values.update({"AB": side, "BC": side, "CD": side, "DA": side})
                logger.info(f"[KnowledgeAgent] Rhombus: all sides={side}")

        elif shape == "parallelogram":
            if ab:
                values.setdefault("CD", ab)
            if ad:
                values.setdefault("BC", ad)
            logger.info(f"[KnowledgeAgent] Parallelogram: AB||CD, AD||BC")

        elif shape == "trapezoid":
            logger.info("[KnowledgeAgent] Trapezoid: AB||CD (bottom||top)")

        elif shape == "right_trapezoid":
            logger.info("[KnowledgeAgent] Right trapezoid: AB||CD, AD⊥AB")
            values.setdefault("angle_A", 90)

        elif shape == "equilateral_triangle":
            side = ab or values.get("side")
            if side:
                values.update({"AB": side, "BC": side, "CA": side, "angle_A": 60})
                logger.info(f"[KnowledgeAgent] Equilateral triangle: all sides={side}, angle_A=60°")

        elif shape == "right_triangle":
            # Try to infer which vertex is the right angle
            rt_vertex = _detect_right_angle_vertex(text)
            values.setdefault(f"angle_{rt_vertex}", 90)
            logger.info(f"[KnowledgeAgent] Right triangle: angle_{rt_vertex}=90°")

        elif shape == "isosceles_triangle":
            logger.info("[KnowledgeAgent] Isosceles triangle: AB=AC (default, LLM may override)")

        elif shape == "circle":
            logger.info("[KnowledgeAgent] Circle detected — no side augmentation needed.")

        return values


def _detect_right_angle_vertex(text: str) -> str:
    """Heuristic: detect which vertex is right angle from text."""
    for vertex in ["A", "B", "C", "D"]:
        patterns = [f"vuông tại {vertex}", f"góc {vertex} vuông", f"right angle at {vertex}"]
        if any(p.lower() in text for p in patterns):
            return vertex
    return "A"  # default
