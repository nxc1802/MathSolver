import pytest
import asyncio
import uuid
import time
from app.routers.solve import process_session_job
from app.models.schemas import SolveRequest
from app.supabase_client import get_supabase

@pytest.mark.asyncio
async def test_metadata_persistence():
    session_id = "81f87517-88f2-40bd-96a9-7b34f1d14b6a"
    user_id = "8cd3adb0-7964-4575-949c-d0cadcd8b679"
    job_id = str(uuid.uuid4())
    
    print(f"🚀 Starting sub-pipeline test for job {job_id}...")
    
    request = SolveRequest(
        text="Cho hình chữ nhật ABCD có AB=10, AD=20. Vẽ đường thẳng d đi qua A và B.",
        request_video=False
    )
    
    # Trigger the process_session_job directly
    await process_session_job(job_id, session_id, request, user_id)
    
    print("⏳ Waiting for database sync (3s)...")
    await asyncio.sleep(3)
    
    # Verify the results in Supabase
    supabase = get_supabase()
    res = supabase.table("messages") \
        .select("metadata, created_at") \
        .eq("session_id", session_id) \
        .eq("role", "assistant") \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()
    
    if not res.data:
        print("❌ FAIL: No assistant message found in database.")
        return
    
    metadata = res.data[0].get("metadata", {})
    required_fields = ["job_id", "coordinates", "polygon_order", "drawing_phases", "circles", "lines", "rays"]
    missing = [f for f in required_fields if f not in metadata]
    
    if not missing:
        print("✅ SUCCESS: All metadata fields (including lines/rays) persisted correctly.")
        print(f"   job_id: {metadata.get('job_id')}")
        print(f"   polygon_order: {metadata.get('polygon_order')}")
        print(f"   lines: {metadata.get('lines')}")
        print(f"   phases: {len(metadata.get('drawing_phases', []))}")
    else:
        print(f"❌ FAIL: Missing fields in metadata: {missing}")

if __name__ == "__main__":
    asyncio.run(test_metadata_persistence())
