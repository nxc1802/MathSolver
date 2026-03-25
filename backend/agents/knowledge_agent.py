from typing import Dict, Any

class KnowledgeAgent:
    """Knowledge Agent for Phase 3.
    Stores geometric theorems and common patterns to augment the Parser's output.
    """
    def __init__(self):
        # Basic rule-based knowledge
        self.rules = {
            "triangle_equilateral": {
                "constraints": ["AB=BC", "BC=CA", "Angle_A=60", "Angle_B=60", "Angle_C=60"]
            },
            "square": {
                "constraints": ["AB=BC", "BC=CD", "CD=DA", "Angle_A=90", "Angle_B=90"]
            }
        }

    def augment_semantic_data(self, semantic_data: Dict[str, Any]) -> Dict[str, Any]:
        text = str(semantic_data.get("input_text", "")).lower()
        
        # Simple keyword matching to apply rules
        if "đều" in text or "equilateral" in text:
            semantic_data["type"] = "triangle_equilateral"
            # If side length is known, apply it to all sides
            values = semantic_data.get("values", {})
            side = values.get("side") or values.get("AB")
            if side:
                values.update({"AB": side, "BC": side, "CA": side, "angle_A": 60})
                semantic_data["values"] = values
        
        return semantic_data
