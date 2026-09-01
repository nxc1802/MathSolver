import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

from llm.service import get_llm_service, LLMService
from agents.runtime import get_agent_runtime, AgentRuntime


class MultiLayerLLMClient:
    """
    Backward-compatible client adapter that delegates all completions to the high-performance
    AgentRuntime & LLMService infrastructure.
    """

    def __init__(self):
        self.service: LLMService = get_llm_service()
        self.runtime: AgentRuntime = get_agent_runtime()

    async def chat_completions_create(
        self,
        messages: List[Dict[str, Any]],
        response_format: Optional[Dict[str, Any]] = None,
        agent: str = "reasoning_solver",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        return await self.runtime.run(
            agent=agent,
            messages=messages,
            response_format=response_format,
            temperature_override=temperature,
            max_tokens_override=max_tokens,
            **kwargs
        )


_llm_client: Optional[MultiLayerLLMClient] = None


def get_llm_client() -> MultiLayerLLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = MultiLayerLLMClient()
    return _llm_client
