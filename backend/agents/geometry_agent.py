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

    async def generate_dsl(self, semantic_data: Dict[str, Any], previous_dsl: str = None) -> str:
        logger.info("==[GeometryAgent] Generating DSL from semantic data==")
        if previous_dsl:
            logger.info(f"[GeometryAgent] Using previous DSL context (len={len(previous_dsl)})")

        system_prompt = """
You are a Geometry DSL Generator. Convert semantic geometry data into a precise Geometry DSL program.

=== MULTI-TURN CONTEXT ===
If a PREVIOUS DSL is provided, your job is to UPDATE or EXTEND it.
1. DO NOT remove existing points unless the user explicitly asks to "redefine" or "move" them.
2. Ensure new segments/points connect correctly to existing ones.
3. Your output should be the ENTIRE updated DSL, not just the changes.

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
1. Primary Vertices: Always declare the main vertices of the shape (e.g., A, B, C, D) using POINT(X).
2. POLYGON_ORDER: Always emit POLYGON_ORDER(...) for the main shape using ONLY these primary vertices.
3. Auxiliary Points: Points like midpoints (M, N), intersections, or foot of perpendiculars should NOT be declared with POINT() individually; they are created via commands like MIDPOINT(M, AB).
4. RECTANGLES/SQUARES: Emit PERPENDICULAR(AB, AD) + PARALLEL(AB, CD) + PARALLEL(AD, BC).
5. PARALLELOGRAMS: Emit PARALLEL(AB, CD) + PARALLEL(AD, BC) only.
6. TRAPEZOIDS: Emit PARALLEL for the parallel pair only.
7. MIDPOINTS: Use MIDPOINT(M, AB).
8. AUXILIARY LINES: Always use SEGMENT(X, Y) for any line mentioned (e.g., altitude, connecting midpoints) that is NOT a boundary of the main polygon.
9. CIRCLES: Use CIRCLE(O, r). No polygon needed.
10. Uniqueness: Emit enough constraints to uniquely determine the shape.
11. Format: Output ONLY DSL lines — NO explanation, NO markdown, NO code blocks.

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

        user_content = f"Semantic Data: {json.dumps(semantic_data, ensure_ascii=False)}"
        if previous_dsl:
            user_content = f"PREVIOUS DSL:\n{previous_dsl}\n\nUPDATE WITH NEW DATA: {json.dumps(semantic_data, ensure_ascii=False)}"

        logger.debug("[GeometryAgent] Calling LLM (Multi-Layer)...")
        content = await self.llm.chat_completions_create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        )
        dsl = content.strip() if content else ""
        logger.info(f"[GeometryAgent] DSL generated ({len(dsl.splitlines())} lines).")
        logger.debug(f"[GeometryAgent] DSL output:\n{dsl}")
        return dsl
