import pytest
import asyncio
import os
import logging
from dotenv import load_dotenv
from app.llm_client import get_llm_client

# Setup logging to see the fallback process
logging.basicConfig(level=logging.INFO)
load_dotenv()

@pytest.mark.asyncio
async def test_real_llm():
    client = get_llm_client()
    
    print("\n--- Testing LLM Call (Complex Prompt) ---")
    try:
        content = await client.chat_completions_create(
            messages=[
                {"role": "system", "content": "You are a Geometry Expert. Formulate a step-by-step reasoning for calculating the distance between two points M and N where M is the midpoint of AB (len=10) and N is the midpoint of AD (len=20) in a rectangle ABCD. Use LaTeX for formulas."},
                {"role": "user", "content": "Solve it carefully."}
            ]
        )
        print(f"\nResponse: {content}")
        print("\n--- Test Completed Successfully ---")
    except Exception as e:
        print(f"\n--- Test Failed: {type(e).__name__}: {e} ---")

if __name__ == "__main__":
    asyncio.run(test_real_llm())
