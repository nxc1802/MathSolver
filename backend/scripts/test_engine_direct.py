import asyncio
import os
import json
import logging
import sys

# Add root directory to path to import app and agents
sys.path.append("/Volumes/WorkSpace/Project/MathSolver/backend")

# Configure logging to stdout
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from agents.orchestrator import Orchestrator

async def main():
    orch = Orchestrator()
    text = "Vẽ tam giác đều cạnh 5."
    job_id = "test_direct_equilateral"
    
    print(f"\n--- Testing Orchestrator Direct: {text} ---")
    
    async def status_cb(status):
        print(f"  [STATUS] {status}")
        
    try:
        result = await orch.run(text, job_id=job_id, status_callback=status_cb, request_video=False)
        print("\n--- Final Result ---")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"\n--- ERROR ---")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
