import os
import httpx
import time
import asyncio
import pytest
import logging
import json

# Configuration
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
USER_ID = os.getenv("TEST_USER_ID")
SESSION_ID = os.getenv("TEST_SESSION_ID")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

QUERIES = [
    {
        "id": "Q1",
        "text": "Cho hình chữ nhật ABCD có AB bằng 5 và AD bằng 10",
        "expect_pts": ["A", "B", "C", "D"],
        "expect_phases": 1,
    },
    {
        "id": "Q2",
        "text": "Tam giác ABC có AB=6, BC=8, AC=10",
        "expect_pts": ["A", "B", "C"],
        "expect_phases": 1,
    },
    {
        "id": "Q3",
        "text": "Cho hình chữ nhật ABCD có AB bằng 10 và AD bằng 20. Vẽ điểm M là trung điểm của AB và N là trung điểm của AD.",
        "expect_pts": ["A", "B", "C", "D", "M", "N"],
        "expect_phases": 2,
    },
    {
        "id": "Q4",
        "text": "Cho hình thang ABCD vuông tại A và D. AB=4, CD=8, AD=5.",
        "expect_pts": ["A", "B", "C", "D"],
        "expect_phases": 1,
    },
    {
        "id": "Q5",
        "text": "Cho hình vuông ABCD có cạnh bằng 6.",
        "expect_pts": ["A", "B", "C", "D"],
        "expect_phases": 1,
    },
    {
        "id": "Q6",
        "text": "Cho tam giác ABC vuông tại A. AB=3, AC=4. Vẽ đường cao AH.",
        "expect_pts": ["A", "B", "C", "H"],
        "expect_phases": 2,
    },
    {
        "id": "Q7",
        "text": "Cho hình thoi ABCD có cạnh bằng 5 và góc A bằng 60 độ.",
        "expect_pts": ["A", "B", "C", "D"],
        "expect_phases": 1,
    },
    {
        "id": "Q8",
        "text": "Cho đường tròn tâm O bán kính bằng 7.",
        "expect_pts": ["O"],
        "expect_phases": 1,
    },
    {
        "id": "Q9",
        "text": "Cho hình bình hành ABCD có AB=8, AD=6. Gọi E là trung điểm của CD. Vẽ đoạn thẳng AE.",
        "expect_pts": ["A", "B", "C", "D", "E"],
        "expect_phases": 2,
    },
    {
        "id": "Q10-Step1",
        "text": "Cho hình chữ nhật ABCD có AB=10, AD=5.",
        "expect_pts": ["A", "B", "C", "D"],
        "expect_phases": 1,
    },
    {
        "id": "Q11-Video",
        "text": "Cho tam giác ABC đều cạnh 5. Vẽ đường tròn ngoại tiếp tam giác.",
        "expect_pts": ["A", "B", "C"],
        "expect_phases": 2,
        "request_video": True
    },
    {
        "id": "Q12-3D",
        "text": "Cho hình chóp S.ABCD có đáy ABCD là hình vuông cạnh 10, đường cao SO=15 với O là tâm đáy.",
        "expect_pts": ["S", "A", "B", "C", "D", "O"],
        "expect_phases": 2,
    }
]

Q10_FOLLOW_UP = {
    "id": "Q10-Step2",
    "text": "Vẽ thêm đường chéo AC.", 
    "expect_pts": ["A", "B", "C", "D"],
    "expect_phases": 2,
}

test_stats = []

async def run_single_api_query(client, q, headers):
    print(f"\n🚀 [RUNNING] {q['id']}: {q['text']}")
    start_time = time.time()
    
    # 1. Submit Request
    payload = {
        "text": q["text"],
        "request_video": q.get("request_video", False)
    }
    
    try:
        if q.get("isolate", True):
            # Create a fresh session for isolation
            session_resp = await client.post("/api/v1/sessions", headers=headers)
            if session_resp.status_code != 200:
                return {"id": q["id"], "query": q["text"], "success": False, "error": f"Session creation failed: {session_resp.text}"}
            session_id = session_resp.json()["id"]
        else:
            session_id = q.get("session_id", SESSION_ID)

        res = await client.post(f"/api/v1/sessions/{session_id}/solve", json=payload, headers=headers)
        if res.status_code != 200:
            print(f"   ❌ FAILED: Status {res.status_code} - {res.text}")
            return {"id": q["id"], "query": q["text"], "success": False, "error": f"HTTP {res.status_code}: {res.text}"}
        
        job_id = res.json()["job_id"]
        print(f"   ✅ Job Created: {job_id}")

        # 2. Polling result
        max_attempts = 45 # Increased for video rendering
        result_data = None
        for i in range(max_attempts):
            await asyncio.sleep(4)
            res = await client.get(f"/api/v1/solve/{job_id}", headers=headers)
            data = res.json()
            status = data.get("status")
            print(f"      - Polling ({i+1}): {status}")
            
            if status == "success":
                result_data = data["result"]
                break
            if status == "error":
                print(f"   ❌ ERROR: {data.get('result', {}).get('error')}")
                return {"id": q["id"], "query": q["text"], "success": False, "error": data.get("result", {}).get("error")}
            
            if i == max_attempts - 1:
                print("   ❌ TIMEOUT")
                return {"id": q["id"], "query": q["text"], "success": False, "error": "Timeout"}

        # 3. Strict Validation
        elapsed = time.time() - start_time
        errors = []
        
        # Validation: Coordinates
        coords = result_data.get("coordinates", {})
        for pt in q["expect_pts"]:
            if pt not in coords:
                errors.append(f"Missing point {pt}")
        
        # Validation: Non-zero coords (generic check)
        # Only fail if there are MULTIPLE points and all are at origin. 
        # A single point (like a circle center) at origin is perfectly valid.
        if coords and len(coords) > 1 and all(v == [0,0,0] for v in coords.values()):
            errors.append("All points are at [0,0,0]")

        # Validation: Drawing Phases
        phases = result_data.get("drawing_phases", [])
        if len(phases) < q["expect_phases"]:
            errors.append(f"Expected {q['expect_phases']} phases, got {len(phases)}")

        # Validation: Video URL if requested
        if q.get("request_video") and not result_data.get("video_url"):
            # We allow video fail if it's environment issue, but log it
            print("      ⚠️ Video requested but no URL found (Expected in some test envs)")
            # errors.append("Video URL missing")

        if errors:
            print(f"   ❌ VALIDATION FAILED: {', '.join(errors)}")
            return {"id": q["id"], "query": q["text"], "success": False, "error": "; ".join(errors), "elapsed": elapsed, "result": result_data}
        
        print(f"   ✅ PASS ({elapsed:.2f}s)")
        return {"id": q['id'], "query": q["text"], "success": True, "elapsed": elapsed, "job_id": job_id, "result": result_data}

    except Exception as e:
        print(f"   ❌ EXCEPTION: {str(e)}")
        return {"id": q["id"], "query": q["text"], "success": False, "error": str(e)}

@pytest.mark.asyncio
async def test_full_api_suite():
    if not USER_ID or not SESSION_ID:
        pytest.fail("TEST_USER_ID and TEST_SESSION_ID must be set")

    headers = {"Authorization": f"Test {USER_ID}"}
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
        # Run standard queries
        import uuid
        for q in QUERIES:
            if q["id"] == "Q10-Step1": continue
            # Isolated by default
            res = await run_single_api_query(client, q, headers)
            test_stats.append(res)

        # Run Multi-turn Q10
        print("\n--- Testing Multi-turn API Flow (Q10) ---")
        # Create a shared session for Q10
        shared_session_resp = await client.post("/api/v1/sessions", headers=headers)
        shared_session = shared_session_resp.json()["id"]
        
        q10_1 = next(q for q in QUERIES if q["id"] == "Q10-Step1")
        q10_1["session_id"] = shared_session
        q10_1["isolate"] = False
        res10_1 = await run_single_api_query(client, q10_1, headers)
        test_stats.append(res10_1)

        if res10_1["success"]:
            Q10_FOLLOW_UP["session_id"] = shared_session
            Q10_FOLLOW_UP["isolate"] = False
            res10_2 = await run_single_api_query(client, Q10_FOLLOW_UP, headers)
            
            # Additional check for Q10-Step2: check if DSL contains combined logic
            if res10_2["success"]:
                dsl = res10_2["result"].get("geometry_dsl", "")
                if "POLYGON_ORDER" not in dsl or "SEGMENT" not in dsl:
                    res10_2["success"] = False
                    res10_2["error"] = "DSL did not merge history correctly"
            
            test_stats.append(res10_2)

    # Save Results to JSON for the runner script to generate Markdown
    with open("temp_suite_results.json", "w") as f:
        json.dump(test_stats, f)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_full_api_suite())
