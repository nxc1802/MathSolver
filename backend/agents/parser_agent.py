import os
from openai import AsyncOpenAI
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class ParserAgent:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("MEGALLM_API_KEY"),
            base_url=os.getenv("MEGALLM_BASE_URL")
        )
        self.model = os.getenv("MEGALLM_MODEL", "openai-gpt-oss-20b")

    async def process(self, text: str, feedback: str = None) -> Dict[str, Any]:
        system_prompt = """
        You are a Geometry Parser Agent. Your task is to extract geometric entities and constraints from natural language text.
        Output ONLY a JSON object with the following structure:
        {
            "entities": ["Point A", "Point B", ...],
            "type": "triangle",
            "values": {"AB": 5, "AC": 7, "angle_A": 60}
        }
        If feedback is provided, correct the previous logic.
        """
        
        user_content = f"Text: {text}"
        if feedback:
            user_content += f"\nFeedback from previous attempt: {feedback}. Please correct the constraints."

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"}
        )
        
        import json
        return json.loads(response.choices[0].message.content)
