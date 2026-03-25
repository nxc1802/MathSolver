import os
from openai import AsyncOpenAI
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class GeometryAgent:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("MEGALLM_API_KEY", "").strip(),
            base_url=os.getenv("MEGALLM_BASE_URL", "").strip()
        )
        self.model = os.getenv("MEGALLM_MODEL", "openai-gpt-oss-20b").strip()

    async def generate_dsl(self, semantic_data: Dict[str, Any]) -> str:
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

        Output ONLY the DSL lines.
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
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Semantic Data: {semantic_data}"}
            ]
        )
        
        return response.choices[0].message.content.strip()
