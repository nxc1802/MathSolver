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
        logger.info("==[GeometryAgent] Generating DSL from semantic data (v5.2)==")
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
-- Basic Primitives --
POINT(A)                             — declare a point (supports A, B, A1, B1, A', B', M1, S1)
POINT(A, x, y, z)                    — declare a point with explicit 2D/3D coordinates
LENGTH(AB, 5)                        — distance between A and B is 5 (2D/3D)
ANGLE(A, 90)                         — interior angle at vertex A is 90°
PARALLEL(AB, CD)                     — segment AB is parallel to CD (2D/3D)
PERPENDICULAR(AB, CD)                — segment AB is perpendicular to CD (2D/3D)
MIDPOINT(M, AB)                      — M is the midpoint of segment AB
SECTION(E, A, C, k)                  — E satisfies vector AE = k * vector AC (k is decimal, e.g. 0.5)
LINE(A, B)                           — infinite line passing through A and B
RAY(A, B)                            — ray starting at A and passing through B
CIRCLE(O, 5)                         — circle with center O and radius 5 (2D)
SEGMENT(M, N)                        — auxiliary segment MN to be drawn
POLYGON_ORDER(A, B, C, D)            — polygon boundary vertex ordering
TRIANGLE(ABC)                        — 2D triangle

-- 3D High-Level Constraints --
PERPENDICULAR_PLANE(SO, ABCD)        — line SO is perpendicular to plane ABCD (generates SO ⊥ AB, SO ⊥ AC)
COPLANAR(A, B, C, D)                 — 4 points lie on the same plane
POINT_ON_PLANE(P, ABC)               — point P lies on plane ABC

-- 3D Polyhedrons & Round Solids --
PYRAMID(S_ABCD)                      — pyramid with apex S and base ABCD
PRISM(ABC_DEF)                       — triangular prism with bases ABC and DEF
PRISM(ABCD_A1B1C1D1)                 — quadrilateral prism
TETRAHEDRON(ABCD)                    — tetrahedron with 4 vertices
CUBE(ABCD_A1B1C1D1)                  — cube with 2 square bases ABCD and A1B1C1D1
CUBOID(ABCD_A1B1C1D1)                — rectangular cuboid / parallelepiped
FRUSTUM(ABCD_A1B1C1D1)               — truncated pyramid
CONE(S, O, r)                        — cone with apex S, base center O, radius r
CYLINDER(O1, O2, r)                  — cylinder with base centers O1, O2, radius r
SPHERE(O, r)                         — sphere with center O and radius r

=== RULES ===
1. 3D Coordinates: Use POINT(A, x, y, z) if specific coordinates are given in the problem or for base anchoring.
2. Space Geometry: For pyramids/prisms/cubes/cones/cylinders, use the specialized 3D commands.
3. Altitudes in 3D: When height/altitude from apex S to base ABCD is given at foot O, use:
   POINT(S)
   POINT(O)
   PERPENDICULAR_PLANE(SO, ABCD)
   LENGTH(SO, height)
4. Primary Vertices: Always declare all vertices using POINT(X).
5. Format: Output ONLY DSL lines — NO explanation, NO markdown code fences (```).

=== SHAPE EXAMPLES ===

--- Case 1: Square Pyramid S.ABCD, AB=10, SO ⊥ (ABCD), SO=15 ---
PYRAMID(S_ABCD)
POINT(A, 0, 0, 0)
POINT(B, 10, 0, 0)
POINT(C, 10, 10, 0)
POINT(D, 0, 10, 0)
POINT(S)
POINT(O)
SECTION(O, A, C, 0.5)
PERPENDICULAR_PLANE(SO, ABCD)
LENGTH(SO, 15)
POLYGON_ORDER(A, B, C, D)

--- Case 2: Cube ABCD.A1B1C1D1 with side a=5 ---
CUBE(ABCD_A1B1C1D1)
POINT(A, 0, 0, 0)
POINT(B, 5, 0, 0)
POINT(C, 5, 5, 0)
POINT(D, 0, 5, 0)
POINT(A1, 0, 0, 5)
POINT(B1, 5, 0, 5)
POINT(C1, 5, 5, 5)
POINT(D1, 0, 5, 5)

--- Case 3: Right Triangular Prism ABC.A1B1C1, ABC right at A, AB=3, AC=4, AA1=6 ---
PRISM(ABC_A1B1C1)
POINT(A, 0, 0, 0)
POINT(B, 3, 0, 0)
POINT(C, 0, 4, 0)
POINT(A1)
POINT(B1)
POINT(C1)
LENGTH(AA1, 6)
PERPENDICULAR_PLANE(AA1, ABC)

--- Case 4: Cone with apex S, base center O, radius r=4, height h=7 ---
POINT(O, 0, 0, 0)
POINT(S, 0, 0, 7)
CONE(S, O, 4, 7)

--- Case 5: Cylinder with base centers O1, O2, radius r=3, height=8 ---
POINT(O1, 0, 0, 0)
POINT(O2, 0, 0, 8)
CYLINDER(O1, O2, 3)

--- Case 6: Regular Tetrahedron ABCD with edge a=6 ---
TETRAHEDRON(ABCD, 6)
POINT(A)
POINT(B)
POINT(C)
POINT(D)
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
        if dsl.startswith("```"):
            import re
            m = re.search(r"```(?:dsl)?\s*(.*?)\s*```", dsl, re.DOTALL)
            if m:
                dsl = m.group(1).strip()
        logger.info(f"[GeometryAgent] DSL generated ({len(dsl.splitlines())} lines).")
        logger.debug(f"[GeometryAgent] DSL output:\n{dsl}")
        return dsl
