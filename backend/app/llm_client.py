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
        # 1. OpenRouter (Primary)
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
        self.openrouter_client = AsyncOpenAI(
            api_key=openai_compatible_api_key(self.openrouter_api_key),
            base_url="https://openrouter.ai/api/v1",
            timeout=120.0,
            default_headers={
                "HTTP-Referer": "https://mathsolver.ai", # Optional
                "X-Title": "MathSolver Backend",
            }
        )

        # 2. MegaLLM (Fallback)
        self.megallm_api_key = os.getenv("MEGALLM_API_KEY")
        self.megallm_model = os.getenv("MEGALLM_MODEL", "openai-gpt-oss-20b")
        self.megallm_client = AsyncOpenAI(
            api_key=openai_compatible_api_key(self.megallm_api_key),
            base_url=sanitize_env(os.getenv("MEGALLM_BASE_URL")) or "https://ai.megallm.io/v1",
            timeout=120.0,
        )

    async def chat_completions_create(
        self, 
        messages: List[Dict[str, str]], 
        response_format: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> str:
        """
        Tries OpenRouter first with retries, then falls back to MegaLLM on failure.
        Returns the text content of the message.
        """
        
        # --- PHASE 1: OpenRouter (with 3 retries) ---
        MAX_RETRIES = 3
        RETRY_DELAY = 5 # seconds

        if self.openrouter_api_key:
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    logger.info(f"[LLM] Attempting OpenRouter ({self.openrouter_model}) - Attempt {attempt}/{MAX_RETRIES}...")
                    response = await self.openrouter_client.chat.completions.create(
                        model=self.openrouter_model,
                        messages=messages,
                        response_format=response_format,
                        **kwargs
                    )
                    
                    if not response or not getattr(response, "choices", None):
                         logger.warning(f"[LLM] OpenRouter returned invalid response structure on attempt {attempt}.")
                         if attempt < MAX_RETRIES:
                             await asyncio.sleep(RETRY_DELAY)
                             continue
                         break

                    content = response.choices[0].message.content
                    if content:
                        logger.info(f"[LLM] OpenRouter: SUCCESS on attempt {attempt}.")
                        return content
                    
                    logger.warning(f"[LLM] OpenRouter returned empty content on attempt {attempt}.")
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                except Exception as e:
                    err_msg = f"{type(e).__name__}: {str(e)}"
                    if attempt < MAX_RETRIES:
                        logger.warning(f"[LLM] OpenRouter: FAILED ({err_msg}) on attempt {attempt}. Retrying in {RETRY_DELAY}s...")
                        await asyncio.sleep(RETRY_DELAY)
                    else:
                        logger.error(f"[LLM] OpenRouter: FINAL FAILURE after {MAX_RETRIES} attempts ({err_msg}). Falling back...")
        else:
            logger.info("[LLM] OPENROUTER_API_KEY not found, skipping to MegaLLM.")

        # --- PHASE 2: MegaLLM (Fallback) ---
        try:
            logger.info(f"[LLM] Attempting MegaLLM ({self.megallm_model})...")
            response = await self.megallm_client.chat.completions.create(
                model=self.megallm_model,
                messages=messages,
                response_format=response_format,
                **kwargs
            )
            content = response.choices[0].message.content
            if content:
                logger.info("[LLM] MegaLLM: SUCCESS.")
                return content
            raise ValueError("MegaLLM returned empty content.")
        except Exception as e:
            err_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"[LLM] MegaLLM: CRITICAL FAILURE ({err_msg})")
            raise e

# Global instance for easy reuse (singleton-ish)
_llm_client = None

def get_llm_client() -> MultiLayerLLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = MultiLayerLLMClient()
    return _llm_client
