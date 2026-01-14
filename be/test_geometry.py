"""
Test script for Visual Math Solver Backend
Tests multiple geometry problems with DeepSeek V3.1 model
"""

import requests
import json
import time
from typing import Dict, Any, List

API_URL = "http://localhost:8000/api/v1/solve"

# Geometry test cases
TEST_CASES: List[Dict[str, Any]] = [
    {
        "name": "Triangle - Law of Cosines",
        "text": "Cho tam giac ABC co AB = 5, AC = 7, goc A = 60 do. Tinh do dai BC.",
        "expected_type": "geometry_2d",
        "expected_answer_contains": ["6.24", "sqrt(39)", "căn 39"],
    },
    {
        "name": "Triangle - Area",
        "text": "Tinh dien tich tam giac ABC biet AB = 6, AC = 8, goc A = 30 do.",
        "expected_type": "geometry_2d",
        "expected_answer_contains": ["12", "24/2"],
    },
    {
        "name": "Pythagorean Theorem",
        "text": "Cho tam giac ABC vuong tai A co AB = 3, AC = 4. Tinh BC.",
        "expected_type": "geometry_2d",
        "expected_answer_contains": ["5"],
    },
    {
        "name": "Circle - Circumference",
        "text": "Tinh chu vi hinh tron co ban kinh R = 7.",
        "expected_type": "geometry_2d",
        "expected_answer_contains": ["14", "pi", "43.98", "44"],
    },
    {
        "name": "Circle - Area",
        "text": "Tinh dien tich hinh tron co duong kinh d = 10.",
        "expected_type": "geometry_2d",
        "expected_answer_contains": ["25", "pi", "78.5"],
    },
]


def test_solve_api(text: str) -> Dict[str, Any]:
    """Call the solve API with given text."""
    try:
        response = requests.post(
            API_URL,
            data={"text": text},
            timeout=120  # 2 minutes timeout for complex problems
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def check_answer(result: Dict, expected_contains: List[str]) -> bool:
    """Check if answer contains any of the expected values."""
    answer = str(result.get("solution", {}).get("answer", "")).lower()
    steps_text = json.dumps(result.get("solution", {}).get("steps", []), ensure_ascii=False).lower()
    full_text = answer + " " + steps_text
    
    for expected in expected_contains:
        if expected.lower() in full_text:
            return True
    return False


def run_tests():
    """Run all test cases and report results."""
    print("=" * 60)
    print("Visual Math Solver - Backend Test Report")
    print("Model: deepseek-ai/deepseek-v3.1-terminus")
    print("=" * 60)
    print()
    
    # Check health first
    try:
        health = requests.get("http://localhost:8000/api/health").json()
        print(f"✅ Server Status: {health['status']}")
        print(f"   Environment: {health['environment']}")
    except Exception as e:
        print(f"❌ Server not reachable: {e}")
        return
    
    print()
    print("-" * 60)
    print("Running Test Cases...")
    print("-" * 60)
    print()
    
    results = []
    total_time = 0
    
    for i, test in enumerate(TEST_CASES, 1):
        print(f"[{i}/{len(TEST_CASES)}] {test['name']}")
        print(f"    Input: {test['text'][:50]}...")
        
        start_time = time.time()
        result = test_solve_api(test["text"])
        elapsed = time.time() - start_time
        total_time += elapsed
        
        if "error" in result:
            status = "❌ ERROR"
            answer = result["error"]
            passed = False
        else:
            answer = result.get("solution", {}).get("answer", "N/A")
            problem_type = result.get("problem", {}).get("type", "unknown")
            passed = check_answer(result, test["expected_answer_contains"])
            status = "✅ PASS" if passed else "⚠️ CHECK"
            
            # Show steps count
            steps = result.get("solution", {}).get("steps", [])
            print(f"    Type: {problem_type}")
            print(f"    Steps: {len(steps)}")
        
        print(f"    Answer: {answer[:80]}...")
        print(f"    Time: {elapsed:.2f}s")
        print(f"    Status: {status}")
        print()
        
        results.append({
            "name": test["name"],
            "passed": passed,
            "time": elapsed,
            "answer": answer,
            "full_result": result
        })
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed_count = sum(1 for r in results if r["passed"])
    print(f"Total Tests: {len(TEST_CASES)}")
    print(f"Passed: {passed_count}/{len(TEST_CASES)}")
    print(f"Total Time: {total_time:.2f}s")
    print(f"Avg Time: {total_time/len(TEST_CASES):.2f}s per test")
    print()
    
    # Detailed results table
    print("-" * 60)
    print(f"{'Test Name':<30} {'Status':<10} {'Time':<10}")
    print("-" * 60)
    for r in results:
        status = "✅ PASS" if r["passed"] else "⚠️ CHECK"
        print(f"{r['name']:<30} {status:<10} {r['time']:.2f}s")
    print("-" * 60)
    
    # Save detailed results to JSON
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nDetailed results saved to: test_results.json")
    
    return results


if __name__ == "__main__":
    run_tests()
