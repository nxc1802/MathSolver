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
        print(f"[GeometryAgent] Generating DSL from semantic data: {semantic_data}")
        system_prompt = "Convert geometry JSON to DSL: POINT(A), LINE(A,B), TRIANGLE(A,B,C), LENGTH(A,B,5), ANGLE(vertex,60), PARALLEL(AB,CD), PERPENDICULAR(AB,CD)."
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str(semantic_data)}
            ]
        )
        
        dsl = response.choices[0].message.content.strip()
        print(f"[GeometryAgent] Generated DSL: {dsl}")
        return dsl
