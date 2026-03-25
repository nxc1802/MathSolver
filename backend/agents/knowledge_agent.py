import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class KnowledgeAgent:
    """Knowledge Agent: Stores geometric theorems and common patterns to augment Parser output."""

    def __init__(self):
        self.rules = {
            "triangle_equilateral": {
                "constraints": ["AB=BC", "BC=CA", "Angle_A=60", "Angle_B=60", "Angle_C=60"]
            },
            "square": {
                "constraints": ["AB=BC", "BC=CD", "CD=DA", "Angle_A=90", "Angle_B=90"]
            }
        }

    def augment_semantic_data(self, semantic_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("==[KnowledgeAgent] Augmenting semantic data==")
        text = str(semantic_data.get("input_text", "")).lower()
        logger.debug(f"[KnowledgeAgent] Input text for matching: '{text[:200]}'")

        if "đều" in text or "equilateral" in text:
            logger.info("[KnowledgeAgent] Rule MATCH: Equilateral triangle detected.")
            semantic_data["type"] = "triangle_equilateral"
            values = semantic_data.get("values", {})
            side = values.get("side") or values.get("AB")
            if side:
                values.update({"AB": side, "BC": side, "CA": side, "angle_A": 60})
                semantic_data["values"] = values
                logger.info(f"[KnowledgeAgent] Applied equilateral rule: all sides={side}, angle_A=60°")
            else:
                logger.warning("[KnowledgeAgent] Equilateral triangle detected but no side length found in values.")
        else:
            logger.info("[KnowledgeAgent] No special rule matched. Returning data unchanged.")

        logger.debug(f"[KnowledgeAgent] Output semantic data: {semantic_data}")
        return semantic_data
