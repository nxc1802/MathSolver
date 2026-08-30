import os
import json
import re
import asyncio
import logging
from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

from app.url_utils import openai_compatible_api_key, sanitize_env


class MultiLayerLLMClient:
    def __init__(self):
        # 1. Models sequence loading
        self.models = []
        for i in range(1, 4):
            model = os.getenv(f"OPENROUTER_MODEL_{i}") or os.getenv(f"MODEL_{i}")
            if model:
                self.models.append(model)

        if not self.models:
            legacy_model = os.getenv("LLM_MODEL") or os.getenv("OPENROUTER_MODEL") or "gemma-4-31b-it"
            self.models = [legacy_model, "gemma-4-31b-it"]

        # 2. Key selection & Base URL configuration
        api_key = (
            os.getenv("GOOGLE_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("OPENROUTER_API_KEY_1")
            or os.getenv("OPENROUTER_API_KEY")
            or ""
        )

        base_url = os.getenv("LLM_BASE_URL")
        if not base_url:
            # Detect Google API Key format
            if api_key and (api_key.startswith("AQ.") or api_key.startswith("AIza")):
                base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
            else:
                base_url = "https://openrouter.ai/api/v1"

        if not api_key:
            logger.error("[LLM] No API key found in environment.")
            self.client = None
        else:
            logger.info(f"[LLM] Initializing LLM client with base_url={base_url}")
            self.client = AsyncOpenAI(
                api_key=openai_compatible_api_key(api_key),
                base_url=base_url,
                timeout=60.0,
                default_headers={
                    "HTTP-Referer": "https://mathsolver.ai",
                    "X-Title": "MathSolver Backend",
                }
            )

    async def chat_completions_create(
        self,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> str:
        """
        Implements Model Fallback Sequence with thought tag stripping for thinking models (Gemma 4).
        """
        if not self.client:
            raise ValueError("No API client configured. Check your API keys in .env.")

        MAX_ATTEMPTS = len(self.models)
        RETRY_DELAY = 1.0

        for attempt_idx in range(MAX_ATTEMPTS):
            current_model = self.models[attempt_idx]
            attempt_num = attempt_idx + 1

            try:
                logger.info(f"[LLM] Attempt {attempt_num}/{MAX_ATTEMPTS} using Model: {current_model}...")

                # Clean model name if prefix 'models/' exists
                model_name = current_model.replace("models/", "")

                response = await self.client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    response_format=response_format,
                    **kwargs
                )

                if not response or not getattr(response, "choices", None):
                    raise ValueError(f"Invalid response structure from model {current_model}")

                content = response.choices[0].message.content
                if content:
                    # Strip <thought>...</thought> tags from thinking models (Gemma 4)
                    cleaned_content = re.sub(r'<thought>.*?</thought>', '', content, flags=re.DOTALL).strip()
                    if not cleaned_content and content:
                        cleaned_content = content.strip()

                    logger.info(f"[LLM] SUCCESS on attempt {attempt_num} ({current_model}).")
                    return cleaned_content

                raise ValueError(f"Empty content from model {current_model}")

            except Exception as e:
                err_msg = f"{type(e).__name__}: {str(e)}"
                logger.warning(f"[LLM] FAILED on attempt {attempt_num} ({current_model}): {err_msg}")

                if attempt_num < MAX_ATTEMPTS:
                    logger.info(f"[LLM] Retrying next model in {RETRY_DELAY}s...")
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    logger.error(f"[LLM] FINAL FAILURE after {attempt_num} models.")
                    raise e


# Global instance
_llm_client = None

def get_llm_client() -> MultiLayerLLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = MultiLayerLLMClient()
    return _llm_client
