import os
import json
import asyncio
import logging
from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional
from app.url_utils import openai_compatible_api_key, sanitize_env

logger = logging.getLogger(__name__)

class MultiLayerLLMClient:
    def __init__(self):
        # 1. Models sequence loading
        self.models = []
        for i in range(1, 4):
            model = os.getenv(f"OPENROUTER_MODEL_{i}")
            if model:
                self.models.append(model)
        
        # Fallback to legacy OPENROUTER_MODEL if no numbered models found
        if not self.models:
            legacy_model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
            self.models = [legacy_model]

        # 2. Key selection (No rotation, always use the first available key)
        api_key = os.getenv("OPENROUTER_API_KEY_1") or os.getenv("OPENROUTER_API_KEY")
        
        if not api_key:
            logger.error("[LLM] No OpenRouter API key found.")
            self.client = None
        else:
            self.client = AsyncOpenAI(
                api_key=openai_compatible_api_key(api_key),
                base_url="https://openrouter.ai/api/v1",
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
        Implements Model Fallback Sequence: Model 1 -> Model 2 -> Model 3.
        Always starts from Model 1 for every new call.
        """
        if not self.client:
            raise ValueError("No API client configured. Check your API keys.")

        MAX_ATTEMPTS = len(self.models)
        RETRY_DELAY = 1.0 # second
        
        for attempt_idx in range(MAX_ATTEMPTS):
            current_model = self.models[attempt_idx]
            attempt_num = attempt_idx + 1
            
            try:
                logger.info(f"[LLM] Attempt {attempt_num}/{MAX_ATTEMPTS} using Model: {current_model}...")
                
                response = await self.client.chat.completions.create(
                    model=current_model,
                    messages=messages,
                    response_format=response_format,
                    **kwargs
                )
                
                if not response or not getattr(response, "choices", None):
                     raise ValueError(f"Invalid response structure from model {current_model}")

                content = response.choices[0].message.content
                if content:
                    logger.info(f"[LLM] SUCCESS on attempt {attempt_num} ({current_model}).")
                    return content
                
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

# Global instance for easy reuse (singleton-ish)
_llm_client = None

def get_llm_client() -> MultiLayerLLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = MultiLayerLLMClient()
    return _llm_client
