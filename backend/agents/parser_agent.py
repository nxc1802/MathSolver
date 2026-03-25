import os
from openai import AsyncOpenAI
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class ParserAgent:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("MEGALLM_API_KEY", "").strip(),
            base_url=os.getenv("MEGALLM_BASE_URL", "").strip()
        )
        self.model = os.getenv("MEGALLM_MODEL", "openai-gpt-oss-20b").strip()

    async def process(self, text: str, feedback: str = None) -> Dict[str, Any]:
        prompt = f"Problem: {text}"
        if feedback:
            prompt += f"\nFeedback from previous attempt: {feedback}"
        
        print(f"[ParserAgent] Sending prompt to LLM...")
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a geometry expert. Extract points, lengths, angles, and constraints into JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        import json
        raw_content = response.choices[0].message.content
        print(f"[ParserAgent] Raw LLM Response: {raw_content}")
        return json.loads(raw_content)
