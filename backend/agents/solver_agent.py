import json
import logging
import sympy as sp
from typing import Dict, Any, List
from app.llm_client import get_llm_client

logger = logging.getLogger(__name__)

class SolverAgent:
    def __init__(self):
        self.llm = get_llm_client()

    async def solve(self, semantic_data: Dict[str, Any], engine_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Solves the geometric problem based on coordinates and the target question.
        Returns a 'solution' dictionary with answer, steps, and symbolic_expression.
        """
        target_question = semantic_data.get("target_question")
        if not target_question:
            # If no question, just return an empty solution structure
            return {
                "answer": None,
                "steps": [],
                "symbolic_expression": None
            }

        logger.info(f"==[SolverAgent] Solving for: '{target_question}'==")

        input_text = semantic_data.get("input_text", "")
        coordinates = engine_result.get("coordinates", {})
        
        # We provide the coordinates and semantic context to the LLM to help it reason.
        # The LLM is tasked with generating the solution structure directly.
        
        system_prompt = """
        You are a Geometry Solver Agent. Your goal is to provide a step-by-step solution for a specific geometric question.
        
        === DATA PROVIDED ===
        1. Target Question: The specific question to answer.
        2. Geometry Data: Entities and values extracted from the problem.
        3. Coordinates: Calculated coordinates for all points.
        
        === REQUIREMENTS ===
        - Provide the solution in the SAME LANGUAGE as the user's input.
        - Use SymPy concepts if appropriate.
        - Steps should be clear, concise, and logical.
        - The final answer should be numerically or symbolically accurate based on the coordinates and geometric properties.
        - For geometric proofs (e.g., "Is AB perpendicular to AC?"), explain the reasoning based on the data.
        
        Output ONLY a JSON object with this structure:
        {
            "answer": "Chuỗi văn bản kết quả cuối cùng (kèm đơn vị nếu có)",
            "steps": [
                "Bước 1: ...",
                "Bước 2: ...",
                ...
            ],
            "symbolic_expression": "Biểu thức toán học rút gọn (LaTeX format optional)"
        }
        """

        user_content = f"""
        INPUT_TEXT: {input_text}
        TARGET_QUESTION: {target_question}
        SEMANTIC_DATA: {json.dumps(semantic_data, ensure_ascii=False)}
        COORDINATES: {json.dumps(coordinates)}
        """

        logger.debug("[SolverAgent] Requesting solution from LLM...")
        try:
            raw = await self.llm.chat_completions_create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"}
            )
            
            clean_raw = raw.strip()
            # Handle potential markdown code blocks if the response_format wasn't strictly honored
            if clean_raw.startswith("```"):
                import re
                match = re.search(r"```(?:json)?\s*(.*?)\s*```", clean_raw, re.DOTALL)
                if match:
                    clean_raw = match.group(1).strip()
            
            try:
                solution = json.loads(clean_raw)
            except json.JSONDecodeError:
                # Last resort: try to find anything between { and }
                import re
                json_match = re.search(r'(\{.*\})', clean_raw, re.DOTALL)
                if json_match:
                    solution = json.loads(json_match.group(1))
                else:
                    raise
            
            logger.info("[SolverAgent] Solution generated successfully.")
            return solution
        except Exception as e:
            logger.error(f"[SolverAgent] Error generating solution: {e}")
            logger.debug(f"[SolverAgent] Raw LLM output was: \n{raw if 'raw' in locals() else 'N/A'}")
            return {
                "answer": "Không thể tính toán lời giải tại thời điểm này.",
                "steps": ["Đã xảy ra lỗi trong quá trình xử lý lời giải."],
                "symbolic_expression": None
            }
