import asyncio
import os
import logging
from dotenv import load_dotenv
from app.llm_client import get_llm_client

# Setup logging to see the fallback process
logging.basicConfig(level=logging.INFO)
load_dotenv()

async def test_real_llm():
    client = get_llm_client()
    
    print("\n--- Testing LLM Call ---")
    try:
        content = await client.chat_completions_create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'LLM is working' if you can read this."}
            ]
        )
        print(f"\nResponse: {content}")
        print("\n--- Test Completed Successfully ---")
    except Exception as e:
        print(f"\n--- Test Failed: {e} ---")

if __name__ == "__main__":
    asyncio.run(test_real_llm())
