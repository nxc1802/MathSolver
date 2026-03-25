import requests
import time
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"

TEST_CASES = [
    {
        "name": "Equilateral Triangle",
        "payload": {"text": "Vẽ tam giác đều cạnh 5.", "request_video": True}
    },
    {
        "name": "Right Triangle (3-4-5)",
        "payload": {"text": "Cho tam giác ABC vuông tại A có AB=3, AC=4. Tính BC.", "request_video": True}
    },
    {
        "name": "Isosceles Triangle",
        "payload": {"text": "Cho tam giác ABC cân tại A có AB=5, BC=6.", "request_video": False}
    },
    {
        "name": "Square",
        "payload": {"text": "Vẽ hình vuông ABCD cạnh 4.", "request_video": True}
    },
    {
        "name": "Invalid Input",
        "payload": {"text": "abcxyz", "request_video": False}
    }
]

def run_test(test_case):
    print(f"\n[TEST] Running: {test_case['name']}...")
    try:
        start_time = time.time()
        # Create job
        response = requests.post(f"{BASE_URL}/solve", json=test_case['payload'])
        if response.status_code != 200:
            print(f"  [FAIL] Initial request failed: {response.text}")
            return False
        
        job_id = response.json().get("job_id")
        print(f"  [INFO] Job ID: {job_id}")
        
        # Poll for completion
        status = "processing"
        max_attempts = 40
        attempts = 0
        while status in ["processing", "solving", "rendering_queued", "rendering"] and attempts < max_attempts:
            time.sleep(5)
            res = requests.get(f"{BASE_URL}/solve/{job_id}")
            data = res.json()
            status = data.get("status")
            print(f"  [INFO] Status: {status} (Attempt {attempts+1})")
            if status == "success":
                duration = time.time() - start_time
                print(f"  [SUCCESS] Completed in {duration:.2f}s")
                if test_case['payload'].get('request_video'):
                    video_url = data.get("result", {}).get("video_url")
                    if video_url:
                        print(f"  [INFO] Video URL: {video_url}")
                    else:
                        print("  [WARNING] Video requested but no URL found in result.")
                return True
            if status == "error":
                print(f"  [FAIL] Solver error: {data.get('result', {}).get('error')}")
                return False
            attempts += 1
            
        if attempts >= max_attempts:
            print("  [FAIL] Timeout reached.")
            return False
            
    except Exception as e:
        print(f"  [ERROR] Exception: {str(e)}")
        return False

if __name__ == "__main__":
    results = []
    print("=== MathSolver Backend Test Suite ===")
    for tc in TEST_CASES:
        success = run_test(tc)
        results.append((tc['name'], success))
    
    print("\n" + "="*40)
    print("FINAL REPORT:")
    all_passed = True
    for name, success in results:
        status_str = "PASS" if success else "FAIL"
        print(f"- {name}: {status_str}")
        if not success: all_passed = False
    
    if all_passed:
        print("\nALL TESTS PASSED! 🎉")
        sys.exit(0)
    else:
        print("\nSOME TESTS FAILED. ❌")
        sys.exit(1)
