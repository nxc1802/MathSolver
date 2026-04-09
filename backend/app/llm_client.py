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
        # 1. OpenRouter (Primary with Rotation)
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
        self.keys = []
        for i in range(1, 6):
            key = os.getenv(f"OPENROUTER_API_KEY_{i}")
            if key:
                self.keys.append(key)
        
        if not self.keys:
            # Fallback to single key if exists (legacy)
            single_key = os.getenv("OPENROUTER_API_KEY")
            if single_key:
                self.keys.append(single_key)

        self.clients = [
            AsyncOpenAI(
                api_key=openai_compatible_api_key(k),
                base_url="https://openrouter.ai/api/v1",
                timeout=120.0,
                default_headers={
                    "HTTP-Referer": "https://mathsolver.ai",
                    "X-Title": "MathSolver Backend",
                }
            ) for k in self.keys
        ]
        self.current_index = 0

    async def chat_completions_create(
        self, 
        messages: List[Dict[str, str]], 
        response_format: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> str:
        """
        Rotates through OpenRouter API keys on every attempt (success or failure).
        Tries up to 2 retries (total 3 attempts), with 0s delay.
        """
        MAX_RETRIES = 2
        RETRY_DELAY = 0 # seconds
        
        if not self.clients:
            logger.error("[LLM] No OpenRouter API keys found.")
            raise ValueError("No API keys configured.")

        for attempt in range(1, MAX_RETRIES + 2): # Up to 3 attempts total
            client = self.clients[self.current_index]
            key_id = self.current_index + 1
            
            try:
                logger.info(f"[LLM] Attempt {attempt}/{MAX_RETRIES + 1} using Key #{key_id} ({self.openrouter_model})...")
                response = await client.chat.completions.create(
                    model=self.openrouter_model,
                    messages=messages,
                    response_format=response_format,
                    **kwargs
                )
                
                if not response or not getattr(response, "choices", None):
                     raise ValueError("Invalid response structure from OpenRouter")

                content = response.choices[0].message.content
                if content:
                    logger.info(f"[LLM] SUCCESS on attempt {attempt} (Key #{key_id}).")
                    # Luôn xoay sang key tiếp theo sau khi thành công để chuẩn bị cho request tới
                    self.current_index = (self.current_index + 1) % len(self.clients)
                    return content
                
                raise ValueError("Empty content from OpenRouter")

            except Exception as e:
                err_msg = f"{type(e).__name__}: {str(e)}"
                logger.warning(f"[LLM] FAILED on attempt {attempt} (Key #{key_id}): {err_msg}")
                
                # Xoay key kể cả khi thất bại để attempt tiếp theo dùng key khác
                old_index = self.current_index
                self.current_index = (self.current_index + 1) % len(self.clients)
                
                if attempt <= MAX_RETRIES:
                    logger.info(f"[LLM] Switching from Key #{old_index + 1} to #{self.current_index + 1}. Retrying in {RETRY_DELAY}s...")
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    logger.error(f"[LLM] FINAL FAILURE after {attempt} attempts.")
                    raise e

# Global instance for easy reuse (singleton-ish)
_llm_client = None

def get_llm_client() -> MultiLayerLLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = MultiLayerLLMClient()
    return _llm_client
