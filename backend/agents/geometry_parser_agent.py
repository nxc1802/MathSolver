import json
import logging
import re
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

from app.llm_client import get_llm_client


class GeometryParserAgent:
    """
    Unified Geometry Parser Agent (v6.0):
    Directly extracts semantic entities, dimensions, target question,
    and generates high-precision Geometry DSL in a single, high-fidelity LLM inference step.
    """

    def __init__(self):
        self.llm = get_llm_client()

    async def process(
        self,
        text: str,
        feedback: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        logger.info(f"==[GeometryParserAgent] Parsing problem & generating DSL (len={len(text)}) (v6.0)==")
        if feedback:
            logger.warning(f"[GeometryParserAgent] Feedback from previous attempt: {feedback}")
        if context:
            logger.info(f"[GeometryParserAgent] Using previous context (dsl_len={len(context.get('geometry_dsl', ''))})")

        system_prompt = """You are an expert Geometry Parser & DSL Generator.
Analyze the Vietnamese/LaTeX mathematical geometry problem and extract both the structured semantics AND the executable Geometry DSL program in a single step.

=== DSL SPECIFICATION ===
-- 2D & 3D Basic Primitives --
POINT(A)                             — declare a point (supports A, B, A1, B1, A', B', S, O, M, N, H)
POINT(A, x, y, z)                    — declare a point with explicit coordinates
LENGTH(AB, 5)                        — distance between A and B is 5
ANGLE(A, 90)                         — angle at vertex A is 90°
PARALLEL(AB, CD)                     — segment AB is parallel to CD
PERPENDICULAR(AB, CD)                — segment AB is perpendicular to CD
MIDPOINT(M, AB)                      — M is the midpoint of segment AB
SECTION(E, A, C, k)                  — E satisfies vector AE = k * vector AC (k is decimal, e.g. 0.5)
LINE(A, B)                           — infinite line passing through A and B
RAY(A, B)                            — ray starting at A and passing through B
CIRCLE(O, 5)                         — circle with center O and radius 5
SEGMENT(M, N)                        — auxiliary segment MN to be drawn
POLYGON_ORDER(A, B, C, D)            — polygon boundary vertex ordering
TRIANGLE(ABC)                        — 2D triangle

-- 3D Polyhedrons & Round Solids --
PYRAMID(S_ABCD)                      — pyramid with apex S and base ABCD (supports S_ABC, S_ABCD, S_ABCDE)
PRISM(ABC_DEF)                       — triangular prism with bases ABC and DEF
PRISM(ABCD_A1B1C1D1)                 — quadrilateral prism
TETRAHEDRON(ABCD)                    — tetrahedron with 4 vertices
CUBE(ABCD_A1B1C1D1)                  — cube
CUBOID(ABCD_A1B1C1D1)                — rectangular cuboid
FRUSTUM_PYRAMID(ABCD_A1B1C1D1)       — frustum of a pyramid (chóp cụt)
CYLINDER(O_O1, r, h)                 — cylinder with axis O-O1, radius r, height h
CONE(S_O, r, h)                      — cone with apex S, base center O, radius r, height h
SPHERE(O, r)                         — sphere with center O and radius r

-- 3D High-Level Spatial Relations --
PERPENDICULAR_PLANE(SO, ABCD)        — line SO is perpendicular to plane ABCD (SO ⊥ base)
COPLANAR(A, B, C, D)                 — 4 points lie on the same plane
POINT_ON_PLANE(P, ABC)               — point P lies on plane ABC

=== OUTPUT FORMAT ===
Output ONLY a JSON object with this EXACT structure (no markdown, no extra keys):
{
    "type": "cube|cuboid|tetrahedron|cone|cylinder|frustum|pyramid|prism|sphere|rectangle|triangle|circle|parallelogram|trapezoid|square|rhombus|general",
    "entities": ["Point S", "Point A", "Point B", "Point C", "Point D", "Point O"],
    "values": {"AB": 10, "SO": 15},
    "target_question": "Tính thể tích khối chóp S.ABCD",
    "analysis": "Tóm tắt bài toán ngắn gọn bằng tiếng Việt.",
    "geometry_dsl": "PYRAMID(S_ABCD)\\nLENGTH(AB, 10)\\nLENGTH(SO, 15)\\nPERPENDICULAR_PLANE(SO, ABCD)"
}

=== RULES ===
1. If the problem specifies a 3D pyramid (e.g. S.ABCD with square base 10, height SO=15), generate PYRAMID(S_ABCD), LENGTH(AB, 10), LENGTH(SO, 15), PERPENDICULAR_PLANE(SO, ABCD).
2. If the problem mentions midpoints, auxiliary lines, include MIDPOINT(M, AB), SEGMENT(S, M), etc.
3. Keep DSL commands clean, upper-case, and syntactically valid.
"""

        user_content = f"Đề bài toán:\n{text}"
        if context:
            user_content = f"PREVIOUS CONTEXT:\n{context.get('analysis', '')}\nDSL:\n{context.get('geometry_dsl', '')}\n\nNEW REQUEST:\n{text}"

        if feedback:
            user_content += f"\n\nPhản hồi từ lần chạy trước: {feedback}. Vui lòng sửa lại DSL và ràng buộc chính xác."

        logger.debug("[GeometryParserAgent] Calling LLM...")
        raw = await self.llm.chat_completions_create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
        )

        try:
            cleaned = self._clean_json(raw)
            data = json.loads(cleaned)
        except Exception as e:
            logger.warning(f"[GeometryParserAgent] JSON parse failed: {e}. Raw: {raw[:300]}")
            data = {
                "type": "general",
                "entities": [],
                "values": {},
                "target_question": text,
                "analysis": text,
                "geometry_dsl": "",
            }

        # Normalize DSL field
        dsl = data.get("geometry_dsl", "")
        if isinstance(dsl, list):
            dsl = "\n".join(dsl)
        data["geometry_dsl"] = dsl.strip()

        logger.info(f"[GeometryParserAgent] Success: type={data.get('type')}, dsl_lines={len(data['geometry_dsl'].splitlines())}")
        return data

    def _clean_json(self, raw: str) -> str:
        s = raw.strip()
        json_match = re.search(r"```(?:json)?(.*?)```", s, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
        # Fallback: search for first { and last }
        brace_match = re.search(r"(\{.*\})", s, re.DOTALL)
        if brace_match:
            return brace_match.group(1).strip()
        return s.strip()
