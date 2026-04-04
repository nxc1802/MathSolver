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
You are a Geometry DSL Generator. Convert semantic geometry data into a precise Geometry DSL program.

=== DSL COMMANDS ===
POINT(A)                    — declare a point
LENGTH(AB, 5)               — distance between A and B is 5
ANGLE(A, 90)                — interior angle at vertex A is 90°
PARALLEL(AB, CD)            — segment AB is parallel to CD
PERPENDICULAR(AB, CD)       — segment AB is perpendicular to CD
MIDPOINT(M, AB)             — M is the midpoint of segment AB
CIRCLE(O, 5)                — circle with center O and radius 5
SEGMENT(M, N)               — auxiliary segment MN to be drawn
POLYGON_ORDER(A, B, C, D)   — the order in which vertices form the polygon boundary

=== RULES ===
1. Always declare POINTs first, in POLYGON_ORDER sequence.
2. Always emit POLYGON_ORDER for any polygon (triangle, quadrilateral, etc.).
3. For RECTANGLES/SQUARES: emit PERPENDICULAR(AB, AD) + PARALLEL(AB, CD) + PARALLEL(AD, BC).
4. For PARALLELOGRAMS: emit PARALLEL(AB, CD) + PARALLEL(AD, BC) only (no PERPENDICULAR).
5. For TRAPEZOIDS: emit PARALLEL for the parallel pair only.
6. For MIDPOINTS: use MIDPOINT(M, AB).
7. For AUXILIARY LINES: Always use SEGMENT(X, Y) for any line mentioned (e.g., altitude, median, connecting midpoints) that is NOT part of the main POLYGON_ORDER.
8. For CIRCLES: use CIRCLE(O, r). No polygon needed.
9. Emit enough constraints to uniquely determine the shape. Do not add redundant ones.
10. Output ONLY DSL lines — NO explanation, NO markdown, NO code blocks.

=== SHAPE EXAMPLES ===

[Rectangle ABCD, AB=5, AD=10]
POLYGON_ORDER(A, B, C, D)
POINT(A)
POINT(B)
POINT(C)
POINT(D)
LENGTH(AB, 5)
LENGTH(AD, 10)
PERPENDICULAR(AB, AD)
PARALLEL(AB, CD)
PARALLEL(AD, BC)

[Triangle ABC, AB=6, BC=8, right angle at C]
POLYGON_ORDER(A, B, C)
POINT(A)
POINT(B)
POINT(C)
LENGTH(AB, 6)
LENGTH(BC, 8)
PERPENDICULAR(CA, CB)

[Parallelogram ABCD, AB=8, AD=5]
POLYGON_ORDER(A, B, C, D)
POINT(A)
POINT(B)
POINT(C)
POINT(D)
LENGTH(AB, 8)
LENGTH(AD, 5)
PARALLEL(AB, CD)
PARALLEL(AD, BC)

[Rectangle ABCD AB=10, AD=20, M midpoint AB, N midpoint AD, find MN]
POLYGON_ORDER(A, B, C, D)
POINT(A)
POINT(B)
POINT(C)
POINT(D)
POINT(M)
POINT(N)
LENGTH(AB, 10)
LENGTH(AD, 20)
PERPENDICULAR(AB, AD)
PARALLEL(AB, CD)
PARALLEL(AD, BC)
MIDPOINT(M, AB)
MIDPOINT(N, AD)
SEGMENT(M, N)

[Circle with center O radius 7]
POINT(O)
CIRCLE(O, 7)
"""

        logger.debug("[GeometryAgent] Calling LLM (Multi-Layer)...")
        content = await self.llm.chat_completions_create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Semantic Data: {json.dumps(semantic_data, ensure_ascii=False)}"}
            ]
        )
        dsl = content.strip() if content else ""
        logger.info(f"[GeometryAgent] DSL generated ({len(dsl.splitlines())} lines).")
        logger.debug(f"[GeometryAgent] DSL output:\n{dsl}")
        return dsl
