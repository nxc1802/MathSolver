import asyncio
import logging
import os

import pytest
from dotenv import load_dotenv

from app.llm_client import get_llm_client

logging.basicConfig(level=logging.INFO)
load_dotenv()


def _openrouter_configured() -> bool:
    return bool(os.getenv("OPENROUTER_API_KEY_1") or os.getenv("OPENROUTER_API_KEY"))


@pytest.mark.real_agents
@pytest.mark.asyncio
async def test_real_llm():
    if not _openrouter_configured():
        pytest.skip("OPENROUTER_API_KEY_1 or OPENROUTER_API_KEY not set")

    client = get_llm_client()
    if getattr(client, "client", None) is None:
        pytest.skip("LLM client not configured")

    content = await client.chat_completions_create(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a Geometry Expert. Give a short step-by-step reasoning for the distance "
                    "between midpoints M of AB and N of AD in rectangle ABCD with AB=10 and AD=20."
                ),
            },
            {"role": "user", "content": "Solve briefly."},
        ]
    )
    assert isinstance(content, str) and len(content.strip()) > 20


if __name__ == "__main__":
    asyncio.run(test_real_llm())
