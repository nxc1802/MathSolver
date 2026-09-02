import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

from llm.service import get_llm_service, LLMService
from config.loader import load_agent_config


class MultiLayerLLMClient:
    """
    Backward-compatible client adapter that delegates completions to LLMService.
    Uses agent config for defaults but allows callers to override temperature/max_tokens
    for ad-hoc usage (e.g. knowledge queries, chat completions).
    """

    def __init__(self):
        self.service: LLMService = get_llm_service()

    async def chat_completions_create(
        self,
        messages: List[Dict[str, Any]],
        response_format: Optional[Dict[str, Any]] = None,
        agent: str = "reasoning_solver",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        config = load_agent_config(agent)
        model = config.tiers[0].model if config.tiers else "gemini/gemini-3.7-flash"
        return await self.service.acomplete(
            model=model,
            messages=messages,
            temperature=temperature if temperature is not None else config.temperature,
            max_tokens=max_tokens if max_tokens is not None else config.max_tokens,
            timeout=config.timeout_seconds,
            response_format=response_format,
            reasoning_effort=config.reasoning_effort,
            agent_name=agent,
            **kwargs
        )


_llm_client: Optional[MultiLayerLLMClient] = None


def get_llm_client() -> MultiLayerLLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = MultiLayerLLMClient()
    return _llm_client
