import os
import httpx
import time
import pytest
import logging

# Configuration from environment
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
USER_ID = os.getenv("TEST_USER_ID")
SESSION_ID = os.getenv("TEST_SESSION_ID")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_api_e2e_flow():
    if not USER_ID or not SESSION_ID:
        pytest.fail("TEST_USER_ID and TEST_SESSION_ID must be set")

    auth_headers = {"Authorization": f"Test {USER_ID}"}
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Health check
        print("\n[1/3] Checking API Health...")
        res = await client.get("/")
        assert res.status_code == 200
        assert "running" in res.json()["message"].lower()
        print("   ✅ Health check passed")

        # 2. Submit Solve Request
        print(f"\n[2/3] Submitting solve request for session {SESSION_ID}...")
        payload = {
            "text": "Cho hình chữ nhật ABCD có AB=5, AD=10. Tính diện tích.",
            "request_video": False
        }
        res = await client.post(f"/api/v1/sessions/{SESSION_ID}/solve", json=payload, headers=auth_headers)
        
        if res.status_code != 200:
            print(f"   ❌ FAILED: {res.text}")
            assert res.status_code == 200
            
        data = res.json()
        job_id = data["job_id"]
        assert job_id is not None
        print(f"   ✅ Request accepted. Job ID: {job_id}")

        # 3. Polling Job Status
        print("\n[3/3] Polling job status...")
        max_attempts = 15
        for i in range(max_attempts):
            time.sleep(2) # Simple sleep between polls
            res = await client.get(f"/api/v1/solve/{job_id}", headers=auth_headers)
            assert res.status_code == 200
            job_data = res.json()
            status = job_data["status"]
            print(f"   Attempt {i+1}: Status = {status}")
            
            if status == "success":
                print("   ✅ SUCCESS: API pipeline completed successfully.")
                result = job_data.get("result", {})
                assert "coordinates" in result
                assert "geometry_dsl" in result
                return
            
            if status == "error":
                error_msg = job_data.get("result", {}).get("error", "Unknown error")
                pytest.fail(f"Job failed with error: {error_msg}")
            
            if i == max_attempts - 1:
                pytest.fail("Timeout waiting for job completion")

if __name__ == "__main__":
    # This allows running the script directly if needed
    import asyncio
    asyncio.run(test_api_e2e_flow())
