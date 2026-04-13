import sys
import os
import time
import asyncio
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

# Add the parent directory to sys.path to allow importing from 'app'
# This assumes the script is inside 'backend/scripts' and we want to import from 'backend/app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.url_utils import openai_compatible_api_key
from openai import AsyncOpenAI

# Set up logger
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# List of models to benchmark
MODELS_TO_TEST = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "openai/gpt-oss-120b:free",
    "z-ai/glm-4.5-air:free",
    "minimax/minimax-m2.5:free",
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-4-31b-it:free",
    "arcee-ai/trinity-large-preview:free",
    "openai/gpt-oss-20b:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "nvidia/nemotron-nano-9b-v2:free",
]

DEFAULT_QUERY = "Giải hệ phương trình sau: x + y = 10, 2x - y = 2. Trả về kết quả cuối cùng x và y."

async def test_model(client: AsyncOpenAI, model: str, query: str) -> Dict[str, Any]:
    """Test a single model and return performance metrics."""
    start_time = time.time()
    result = {
        "model": model,
        "status": "success",
        "duration": 0,
        "content": "",
        "error": None
    }
    
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": query}],
            timeout=60.0
        )
        result["duration"] = time.time() - start_time
        result["content"] = response.choices[0].message.content.strip()
    except Exception as e:
        result["status"] = "failed"
        result["duration"] = time.time() - start_time
        result["error"] = str(e)
    
    return result

async def main():
    # Load configuration from .env file inside backend directory
    # If starting from root, backend/.env might be needed. If starting from backend/, .env is enough.
    load_dotenv()
    
    # Try multiple common env keys for api key
    api_key = os.getenv("OPENROUTER_API_KEY_1") or os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        logger.error("❌ Error: NO OPENROUTER_API_KEY found in environment variables.")
        logger.info("Check your .env file in the backend directory.")
        return

    # Using the project's url_utils to maintain consistency with the main app
    sanitized_key = openai_compatible_api_key(api_key)

    client = AsyncOpenAI(
        api_key=sanitized_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://mathsolver.ai",
            "X-Title": "MathSolver LLM Benchmarker",
        }
    )

    query = DEFAULT_QUERY
    logger.info("=" * 80)
    logger.info(f"🚀 LLM PERFORMANCE BENCHMARK")
    logger.info(f"Query: {query}")
    logger.info("=" * 80)
    logger.info(f"Testing {len(MODELS_TO_TEST)} models sequentially with 30s delay...\n")

    results = []
    for i, model in enumerate(MODELS_TO_TEST):
        if i > 0:
            logger.info(f"⏳ Waiting 30s before testing next model...")
            await asyncio.sleep(30)
        
        logger.info(f"[{i+1}/{len(MODELS_TO_TEST)}] Testing: {model}...")
        res = await test_model(client, model, query)
        results.append(res)
        
        # Immediate feedback
        status_str = "✅ SUCCESS" if res["status"] == "success" else "❌ FAILED"
        logger.info(f"   Status: {status_str} | Time: {res['duration']:.2f}s")

    # Report Summary Table
    logger.info("\n" + "=" * 80)
    logger.info("📊 FINAL BENCHMARK SUMMARY")
    logger.info("=" * 80)
    header = f"{'MODEL':<45} | {'STATUS':<10} | {'TIME (s)':<10}"
    logger.info(header)
    logger.info("-" * len(header))
    
    for res in results:
        status_str = "✅ SUCCESS" if res["status"] == "success" else "❌ FAILED"
        duration_str = f"{res['duration']:.2f}s"
        logger.info(f"{res['model']:<45} | {status_str:<10} | {duration_str:<10}")

    logger.info("-" * len(header))

    # Detailed report for successful ones
    logger.info("\n📝 FULL RESPONSES:")
    for res in results:
        logger.info(f"\n{'='*20} [{res['model']}] {'='*20}")
        if res["status"] == "success":
            logger.info(res["content"])
        else:
            logger.info(f"❌ Error: {res['error']}")
    
    logger.info("\n" + "=" * 80)
    logger.info(f"Benchmark finished.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nBenchmark cancelled by user.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
