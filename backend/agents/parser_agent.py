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


class ParserAgent:
    def __init__(self):
        self.llm = get_llm_client()

    async def process(self, text: str, feedback: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        logger.info(f"==[ParserAgent] Processing input (len={len(text)})==")
        if feedback:
            logger.warning(f"[ParserAgent] Feedback from previous attempt: {feedback}")
        if context:
            logger.info(f"[ParserAgent] Using previous context (dsl_len={len(context.get('geometry_dsl', ''))})")

        system_prompt = """
        You are a Geometry Parser Agent. Extract geometric entities and constraints from Vietnamese/LaTeX math problem text.
        
        === CONTEXT AWARENESS ===
        If previous context is provided, it means this is a follow-up request.
        - Combine old entities with new ones.
        - Update 'analysis' to reflect the entire problem state.
        
        Output ONLY a JSON object with this EXACT structure (no extra keys, no markdown):
        {
            "entities": ["Point A", "Point B", ...],
            "type": "rectangle|triangle|circle|parallelogram|trapezoid|square|rhombus|general",
            "values": {"AB": 5, "AC": 7, "angle_A": 60, "radius": 3},
            "analysis": "Tóm tắt ngắn gọn toàn bộ bài toán sau khi đã cập nhật các yêu cầu mới bằng tiếng Việt."
        }
        Rules:
        - "analysis" MUST be a meaningful and UP-TO-DATE summary of the problem in Vietnamese. 
        - Include midpoints, auxiliary points in "entities" if mentioned.
        - If feedback is provided, correct your previous output accordingly.
        """

        user_content = f"Text: {text}"
        if context:
            user_content = f"PREVIOUS ANALYSIS: {context.get('analysis')}\nNEW REQUEST: {text}"
        
        if feedback:
            user_content += f"\nFeedback from previous attempt: {feedback}. Please correct the constraints."

        logger.debug("[ParserAgent] Calling LLM (Multi-Layer)...")
        raw = await self.llm.chat_completions_create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"}
        )
        result = json.loads(raw)
        logger.info(f"[ParserAgent] LLM response received.")
        logger.debug(f"[ParserAgent] Parsed JSON: {json.dumps(result, ensure_ascii=False, indent=2)}")
        return result
