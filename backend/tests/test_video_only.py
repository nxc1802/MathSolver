import asyncio
import logging
import json
import time
from dotenv import load_dotenv
from agents.orchestrator import Orchestrator
from app.supabase_client import get_supabase

async def test_video_rendering():
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    orchestrator = Orchestrator()
    supabase = get_supabase()

    q = {
        "id": "VIDEO_TEST",
        "text": "Cho hình vuông ABCD cạnh 5.",
        "request_video": True
    }

    print(f"\n🚀 Starting Video Rendering Test...")
    job_id_override = f"test-video-{int(time.time())}"
    
    result = await orchestrator.run(
        text=q["text"],
        job_id=job_id_override,
        request_video=True
    )

    if "error" in result:
        print(f"❌ Pipeline Error: {result['error']}")
        return

    job_id = result.get("job_id")
    print(f"⏳ Job created: {job_id}. Waiting for worker...")

    # Poll Supabase
    max_retries = 30 # 2.5 minutes
    for i in range(max_retries):
        job_res = supabase.table("jobs").select("*").eq("id", job_id).execute()
        if job_res.data:
            job_data = job_res.data[0]
            status = job_data.get("status")
            print(f"  [{i+1}/{max_retries}] Job status: {status}")
            
            if status == "success":
                video_url = job_data.get("result", {}).get("video_url")
                if video_url:
                    print(f"✅ SUCCESS: Video URL: {video_url}")
                    return
                else:
                    print("❌ FAIL: Job success but no video_url")
                    return
            elif status == "failed":
                print(f"❌ FAIL: Job failed. Check worker logs.")
                return
        await asyncio.sleep(5)

    print("❌ FAIL: Timeout waiting for video rendering.")

if __name__ == "__main__":
    asyncio.run(test_video_rendering())
