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
POINT(A, x, y, z)           — declare a point with explicit coordinates
LENGTH(AB, 5)               — distance between A and B is 5 (2D/3D)
ANGLE(A, 90)                — interior angle at vertex A is 90° (2D/3D)
PARALLEL(AB, CD)            — segment AB is parallel to CD (2D/3D)
PERPENDICULAR(AB, CD)       — segment AB is perpendicular to CD (2D/3D)
MIDPOINT(M, AB)             — M is the midpoint of segment AB
SECTION(E, A, C, k)         — E satisfies vector AE = k * vector AC (k is decimal)
LINE(A, B)                  — infinite line passing through A and B
RAY(A, B)                   — ray starting at A and passing through B
CIRCLE(O, 5)                — circle with center O and radius 5 (2D)
SPHERE(O, 5)                — sphere with center O and radius 5 (3D)
SEGMENT(M, N)               — auxiliary segment MN to be drawn
POLYGON_ORDER(A, B, C, D)   — the order in which vertices form the polygon boundary
TRIANGLE(ABC)               — equilateral/arbitrary triangle
PYRAMID(S_ABCD)             — pyramid with apex S and base ABCD
PRISM(ABC_DEF)              — triangular prism

=== RULES ===
1. 3D Coordinates: Use POINT(A, x, y, z) if specific coordinates are given in the problem.
2. Space Geometry: For pyramids/prisms, use the specialized commands.
3. Primary Vertices: Always declare the main vertices of the shape (e.g., A, B, C, D) using POINT(X).
4. POLYGON_ORDER: Always emit POLYGON_ORDER(...) for the main shape using ONLY these primary vertices.
5. All Points: EVERY point mentioned (A, B, C, H, M, etc.) MUST be declared with POINT(Name) first.
6. Altitudes/Perpendiculars: For an altitude AH to BC, use POINT(H) + PERPENDICULAR(AH, BC).
7. Format: Output ONLY DSL lines — NO explanation, NO markdown, NO code blocks.

=== SHAPE EXAMPLES ===

--- Case: Square Pyramid S.ABCD with side 10, height 15 ---
PYRAMID(S_ABCD)
POINT(A, 0, 0, 0)
POINT(B, 10, 0, 0)
POINT(C, 10, 10, 0)
POINT(D, 0, 10, 0)
POINT(S)
POINT(O)
SECTION(O, A, C, 0.5)
LENGTH(SO, 15)
PERPENDICULAR(SO, AC)
PERPENDICULAR(SO, AB)
POLYGON_ORDER(A, B, C, D)

--- Case: Right Triangle ABC at A, AB=3, AC=4, altitude AH ---
POLYGON_ORDER(A, B, C)
POINT(A)
POINT(B)
POINT(C)
POINT(H)
LENGTH(AB, 3)
LENGTH(AC, 4)
ANGLE(A, 90)
PERPENDICULAR(AH, BC)
SEGMENT(A, H)

--- Case: Rectangle ABCD with AB=5, AD=10 ---
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
