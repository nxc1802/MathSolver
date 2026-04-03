import os
import json
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
        )

    async def chat_completions_create(
        self, 
        messages: List[Dict[str, str]], 
        response_format: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> str:
        """
        Tries OpenRouter first, then falls back to MegaLLM on ANY exception.
        Returns the text content of the message.
        """
        
        # --- PHASE 1: OpenRouter ---
        if self.openrouter_api_key:
            try:
                logger.info(f"[LLM] Attempting OpenRouter ({self.openrouter_model})...")
                response = await self.openrouter_client.chat.completions.create(
                    model=self.openrouter_model,
                    messages=messages,
                    response_format=response_format,
                    **kwargs
                )
                content = response.choices[0].message.content
                if content:
                    logger.info("[LLM] OpenRouter: SUCCESS.")
                    return content
                logger.warning("[LLM] OpenRouter returned empty content, falling back...")
            except Exception as e:
                logger.warning(f"[LLM] OpenRouter: FAILED ({type(e).__name__}: {e}). Falling back to MegaLLM...")
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
            logger.error(f"[LLM] MegaLLM: CRITICAL FAILURE ({type(e).__name__}: {e})")
            raise e

# Global instance for easy reuse (singleton-ish)
_llm_client = None

def get_llm_client() -> MultiLayerLLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = MultiLayerLLMClient()
    return _llm_client
