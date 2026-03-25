import os
import json
import logging
from openai import AsyncOpenAI
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class ParserAgent:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("MEGALLM_API_KEY", "").strip(),
            base_url=os.getenv("MEGALLM_BASE_URL", "").strip()
        )
        self.model = os.getenv("MEGALLM_MODEL", "openai-gpt-oss-20b").strip()

    async def process(self, text: str, feedback: str = None) -> Dict[str, Any]:
        logger.info(f"==[ParserAgent] Processing input (len={len(text)})==")
        if feedback:
            logger.warning(f"[ParserAgent] Feedback from previous attempt: {feedback}")

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

        logger.debug(f"[ParserAgent] Calling LLM ({self.model}) ...")
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"}
        )

        raw = response.choices[0].message.content
        result = json.loads(raw)
        logger.info(f"[ParserAgent] LLM response received.")
        logger.debug(f"[ParserAgent] Parsed JSON: {json.dumps(result, ensure_ascii=False, indent=2)}")
        return result
