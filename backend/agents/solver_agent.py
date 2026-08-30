import json
import logging
import re
import sympy as sp
from typing import Dict, Any, List, Optional
from app.llm_client import get_llm_client
from solver.calculator import MathCalculator

logger = logging.getLogger(__name__)


def robust_json_decode(text: str) -> Dict[str, Any]:
    """
    Robust JSON decoder that handles unescaped LaTeX backslashes from LLMs.
    """
    clean = text.strip()
    if clean.startswith("```"):
        m = re.search(r"```(?:json)?\s*(.*?)\s*```", clean, re.DOTALL)
        if m:
            clean = m.group(1).strip()

    try:
        return json.loads(clean, strict=False)
    except Exception:
        pass

    # Escape unescaped raw backslashes
    try:
        fixed = re.sub(r'\\(?![/\"\\bfnrtu]|u[0-9a-fA-F]{4})', r'\\\\', clean)
        return json.loads(fixed, strict=False)
    except Exception:
        pass

    # Regex extraction fallback
    steps = re.findall(r'"([^"]*Bước[^"]*)"', clean)
    if not steps:
        steps = re.findall(r'"([^"]+)"', clean)
        steps = [
            s for s in steps
            if any(kw in s.lower() for kw in ['diện tích', 'thể tích', 'chiều cao', 'công thức', 'bước', 'ta có', '='])
        ]

    ans_m = re.search(r'"(?:final_)?answer"\s*:\s*"?([^"}\n]+)"?', clean)
    return {
        "step_by_step_solution": steps,
        "final_answer": ans_m.group(1).strip() if ans_m else ""
    }


class SolverAgent:
    def __init__(self):
        self.llm = get_llm_client()
        self.calculator = MathCalculator()

    async def solve(self, semantic_data: Dict[str, Any], engine_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Solves the geometric problem based on coordinates and the target question.
        Uses MathCalculator (SymPy Engine) to deterministically compute all formulas and values.
        """
        target_question = semantic_data.get("target_question")
        if not target_question:
            return {
                "answer": None,
                "steps": [],
                "symbolic_expression": None
            }

        logger.info(f"==[SolverAgent] Solving deterministically for: '{target_question}'==")

        input_text = semantic_data.get("input_text", "")
        coordinates = engine_result.get("coordinates", {})
        values = semantic_data.get("values", {})

        system_prompt = """
        You are a Precision Mathematical Geometry Solver.
        Provide the step-by-step mathematical reasoning in Vietnamese to answer the target question.
        
        CRITICAL: State the exact formula and calculation values in each step (e.g. S_{ABC} = (6^2 * sqrt(3)) / 4 = 9*sqrt(3), V = (1/3) * 9*sqrt(3) * 8 = 24*sqrt(3)).
        A deterministic SymPy calculation engine will verify and execute all calculations automatically.
        
        Output ONLY a JSON object with this structure:
        {
            "step_by_step_solution": [
                "Bước 1: Tính diện tích đáy...",
                "Bước 2: Xác định chiều cao...",
                "Bước 3: Áp dụng công thức tính thể tích..."
            ],
            "final_answer": "Đáp số cuối cùng"
        }
        """

        user_content = f"""
        INPUT_TEXT: {input_text}
        TARGET_QUESTION: {target_question}
        SEMANTIC_VALUES: {json.dumps(values, ensure_ascii=False)}
        COORDINATES: {json.dumps(coordinates)}
        """

        try:
            raw = await self.llm.chat_completions_create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"}
            )

            plan_data = robust_json_decode(raw)

            # 1. If structured steps_plan with calculation objects
            if "steps_plan" in plan_data and isinstance(plan_data["steps_plan"], list):
                if plan_data["steps_plan"] and isinstance(plan_data["steps_plan"][0], dict) and "calculation" in plan_data["steps_plan"][0]:
                    logger.info("[SolverAgent] Processing structured steps_plan via SymPy calculator...")
                    result = self.calculator.process_solution_plan(
                        steps_data=plan_data["steps_plan"],
                        target_question=target_question,
                        coordinates=coordinates,
                    )
                    return result
                else:
                    logger.info("[SolverAgent] Processing text steps_plan via SymPy calculator...")
                    return self.calculator.process_text_steps(plan_data["steps_plan"])

            # 2. If step_by_step_solution or steps list
            text_steps = plan_data.get("step_by_step_solution") or plan_data.get("steps") or []
            if text_steps:
                logger.info(f"[SolverAgent] Processing {len(text_steps)} text steps via SymPy calculator...")
                result = self.calculator.process_text_steps(text_steps)
                if not result.get("answer") and plan_data.get("final_answer"):
                    result["answer"] = str(plan_data["final_answer"])
                return result

            raise ValueError("No valid steps or step_by_step_solution found in LLM response.")

        except Exception as e:
            logger.error(f"[SolverAgent] Error generating/evaluating solution: {e}")
            return {
                "answer": "Không thể tính toán lời giải tại thời điểm này.",
                "steps": [f"Đã xảy ra lỗi trong quá trình tính toán: {str(e)}"],
                "symbolic_expression": None
            }
