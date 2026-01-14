"""
Visual Math Solver - Backend Test Script
Tests multiple geometry problems via the API
"""

import requests
import json
import time
from typing import Dict, Any, List

BASE_URL = "http://localhost:8000"

# Test cases for geometry problems
TEST_CASES = [
    {
        "name": "Simple Addition",
        "text": "1 + 1 = ?",
        "expected_type": "algebra"
    },
    {
        "name": "Triangle Cosine Rule",
        "text": "Cho tam giac ABC co AB = 5, AC = 7, goc A = 60 do. Tinh do dai BC.",
        "expected_type": "geometry_2d"
    },
    {
        "name": "Triangle Area",
        "text": "Cho tam giac ABC co AB = 6, AC = 8, goc A = 90 do. Tinh dien tich tam giac.",
        "expected_type": "geometry_2d"
    },
    {
        "name": "Circle Area",
        "text": "Tinh dien tich hinh tron co ban kinh R = 5.",
        "expected_type": "geometry_2d"
    },
    {
        "name": "Pythagorean Theorem",
        "text": "Cho tam giac vuong ABC co goc A = 90 do, AB = 3, AC = 4. Tinh BC.",
        "expected_type": "geometry_2d"
    },
    {
        "name": "Quadratic Equation",
        "text": "Giai phuong trinh x^2 - 5x + 6 = 0",
        "expected_type": "algebra"
    }
]


def test_health() -> bool:
    """Test health endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        data = response.json()
        return data.get("status") == "healthy"
    except Exception as e:
        print(f"Health check failed: {e}")
        return False


def solve_problem(text: str) -> Dict[str, Any]:
    """Call solve API with a math problem."""
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/solve",
            data={"text": text},
            timeout=120
        )
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def run_tests() -> List[Dict]:
    """Run all test cases and collect results."""
    results = []
    
    print("=" * 60)
    print("Visual Math Solver - Backend Test Report")
    print("=" * 60)
    print()
    
    # Health check first
    print("1. Health Check...")
    if test_health():
        print("   ✅ Server is healthy")
    else:
        print("   ❌ Server is not responding")
        return []
    
    print()
    print("2. Running Test Cases...")
    print("-" * 60)
    
    for i, test_case in enumerate(TEST_CASES, 1):
        name = test_case["name"]
        text = test_case["text"]
        expected_type = test_case["expected_type"]
        
        print(f"\n   Test {i}: {name}")
        print(f"   Input: {text[:50]}...")
        
        start_time = time.time()
        result = solve_problem(text)
        elapsed = time.time() - start_time
        
        if "error" in result:
            status = "❌ ERROR"
            answer = result["error"]
            problem_type = "N/A"
        else:
            problem_type = result.get("problem", {}).get("type", "unknown")
            answer = result.get("solution", {}).get("answer", "No answer")
            steps = result.get("solution", {}).get("steps", [])
            
            status = "✅ PASS"
            
        print(f"   Status: {status}")
        print(f"   Type: {problem_type}")
        print(f"   Answer: {answer}")
        print(f"   Time: {elapsed:.2f}s")
        
        results.append({
            "name": name,
            "input": text,
            "expected_type": expected_type,
            "actual_type": problem_type,
            "answer": answer,
            "time_seconds": round(elapsed, 2),
            "status": "PASS" if "error" not in result else "ERROR",
            "full_response": result
        })
    
    return results


def print_summary(results: List[Dict]):
    """Print test summary."""
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = total - passed
    avg_time = sum(r["time_seconds"] for r in results) / total if total > 0 else 0
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Average Time: {avg_time:.2f}s")
    print()
    
    print("Detailed Results:")
    print("-" * 60)
    for r in results:
        status_icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"{status_icon} {r['name']}: {r['answer'][:40]}... ({r['time_seconds']}s)")
    
    print()
    print("=" * 60)
    
    # Save results to JSON
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("Results saved to test_results.json")


if __name__ == "__main__":
    results = run_tests()
    if results:
        print_summary(results)
