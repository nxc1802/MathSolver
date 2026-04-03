import os
import json
import logging
from openai import AsyncOpenAI
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

from app.url_utils import openai_compatible_api_key, sanitize_env


from app.llm_client import get_llm_client


class GeometryAgent:
    def __init__(self):
        self.llm = get_llm_client()

    async def generate_dsl(self, semantic_data: Dict[str, Any]) -> str:
        logger.info("==[GeometryAgent] Generating DSL from semantic data==")
        logger.debug(f"[GeometryAgent] Input semantic data: {json.dumps(semantic_data, ensure_ascii=False, indent=2)}")

        system_prompt = """
        You are a Geometry DSL Generator. Your task is to convert semantic geometric data into a structured Geometry DSL.
        
        Supported DSL Commands:
        - POINT(id)
        - LINE(p1, p2)
        - TRIANGLE(p1, p2, p3)
        - CIRCLE(center, radius_value)
        - LENGTH(p1p2, value)
        - ANGLE(vertex, degree_value)
        - PARALLEL(p1p2, p3p4)
        - PERPENDICULAR(p1p2, p3p4)

        Avoid Redundancy: Do not output redundant constraints. For example, if all side lengths of an equilateral triangle are specified, do not also output all internal angles as constraints unless explicitly needed.
        Output ONLY the DSL lines, no explanation, no markdown code blocks.
        Example Input: {"entities": ["A", "B", "C"], "type": "triangle", "values": {"AB": 5, "AC": 7, "angle_A": 60}}
        Example Output:
        POINT(A)
        POINT(B)
        POINT(C)
        TRIANGLE(ABC)
        LENGTH(AB, 5)
        LENGTH(AC, 7)
        ANGLE(A, 60)
        """

        logger.debug("[GeometryAgent] Calling LLM (Multi-Layer)...")
        content = await self.llm.chat_completions_create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Semantic Data: {semantic_data}"}
            ]
        )
        dsl = content.strip() if content else ""
        logger.info(f"[GeometryAgent] DSL generated ({len(dsl.splitlines())} lines).")
        logger.debug(f"[GeometryAgent] DSL output:\n{dsl}")
        return dsl
