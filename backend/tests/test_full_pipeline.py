import asyncio
import logging
import json
import os
import math
from dotenv import load_dotenv

from app.logging_setup import setup_application_logging
setup_application_logging()
logging.getLogger("agents").setLevel(logging.DEBUG)
logging.getLogger("solver").setLevel(logging.DEBUG)
logging.getLogger("app").setLevel(logging.DEBUG)

from agents.orchestrator import Orchestrator

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
        "text": "Cho hình chữ nhật ABCD có AB bằng 10 và AD bằng 20. Vẽ điểm M là trung điểm của AB và N là trung điểm của AD, tính MN.",
        "expect_pts": ["A", "B", "C", "D", "M", "N"],
        "expect_phases": 2,
    },
]

def dist(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

def validate_rectangle(coords):
    a, b = coords.get("A"), coords.get("B")
    d = coords.get("D")
    if not (a and b and d):
        return False, "Missing A or B or D"
    ab = dist(a, b)
    ad = dist(a, d)
    return True, f"AB={ab:.2f}, AD={ad:.2f}"

async def run_query(orchestrator, q):
    print(f"\n{'='*60}")
    print(f"[{q['id']}] {q['text']}")
    print('='*60)
    try:
        result = await orchestrator.run(
            text=q["text"],
            job_id=f"test-{q['id']}",
            request_video=False,
        )

        if "error" in result:
            print(f"  ❌ PIPELINE ERROR: {result['error']}")
            return False

        # Check 1: semantic_analysis != original query
        analysis = result.get("semantic_analysis", "")
        if analysis.strip() == q["text"].strip():
            print(f"  ❌ FAIL: semantic_analysis is identical to input query")
        else:
            print(f"  ✅ semantic_analysis: {analysis[:100]}...")

        # Check 2: all expected points are in coordinates
        coords = result.get("coordinates", {})
        missing = [pt for pt in q["expect_pts"] if pt not in coords]
        if missing:
            print(f"  ❌ FAIL: Missing points in coordinates: {missing}")
        else:
            print(f"  ✅ All expected points present: {list(coords.keys())}")

        # Check 3: polygon_order
        polygon_order = result.get("polygon_order", [])
        print(f"  📐 polygon_order: {polygon_order}")

        # Check 4: drawing_phases
        phases = result.get("drawing_phases", [])
        if len(phases) >= q["expect_phases"]:
            print(f"  ✅ drawing_phases: {len(phases)} phase(s)")
            for ph in phases:
                print(f"     Phase {ph['phase']}: {ph['label']} | pts={ph['points']} | segs={ph['segments']}")
        else:
            print(f"  ❌ FAIL: expected {q['expect_phases']} drawing phase(s), got {len(phases)}")

        # Shape-specific validation
        if q["id"] == "Q1" and coords:
            ok, info = validate_rectangle(coords)
            print(f"  {'✅' if ok else '❌'} Rectangle validation: {info}")
        
        if q["id"] == "Q3" and "M" in coords and "N" in coords:
            mn = dist(coords["M"], coords["N"])
            expected_mn = math.sqrt(5**2 + 10**2)  # 5√5 ≈ 11.18
            ok = abs(mn - expected_mn) < 0.1
            print(f"  {'✅' if ok else '❌'} MN = {mn:.3f} (expected ≈ {expected_mn:.3f})")

        print(f"\n  Coordinates:\n{json.dumps(coords, indent=4)}")
        print(f"  DSL:\n{result.get('geometry_dsl', '')}")
        return True

    except Exception as e:
        import traceback
        print(f"  ❌ EXCEPTION: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


async def main():
    load_dotenv()
    orchestrator = Orchestrator()

    results = []
    for q in QUERIES:
        ok = await run_query(orchestrator, q)
        results.append((q["id"], ok))

    print(f"\n{'='*60}")
    print("SUMMARY:")
    for qid, ok in results:
        print(f"  [{qid}] {'✅ PASS' if ok else '❌ FAIL'}")

if __name__ == "__main__":
    asyncio.run(main())
