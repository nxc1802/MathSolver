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
    }
]

# Q10-Step2 is a follow-up to Q10-Step1
Q10_FOLLOW_UP = {
    "id": "Q10-Step2",
    "text": "Vẽ thêm đường chéo AC.", 
    "expect_pts": ["A", "B", "C", "D"],
    "expect_phases": 2, # Main polygon + diagonal segment
}

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

async def run_query(orchestrator, q, history=None):
    print(f"\n{'='*60}")
    print(f"[{q['id']}] {q['text']}")
    if history:
        print(f"  (With history context of {len(history)} messages)")
    print('='*60)
    try:
        result = await orchestrator.run(
            text=q["text"],
            job_id=f"test-{q['id']}",
            request_video=False,
            history=history,
        )

        if "error" in result:
            print(f"  ❌ PIPELINE ERROR: {result['error']}")
            return None

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

        # Check 4: drawing_phases
        phases = result.get("drawing_phases", [])
        if len(phases) >= q["expect_phases"]:
            print(f"  ✅ drawing_phases: {len(phases)} phase(s)")
        else:
            print(f"  ❌ FAIL: expected {q['expect_phases']} drawing phase(s), got {len(phases)}")

        dsl = result.get('geometry_dsl', '')
        print(f"  DSL ({len(dsl.splitlines())} lines):\n{dsl}")
        
        # Specific check for Q10-Step2: must contain BOTH ABCD and AC segment
        if q["id"] == "Q10-Step2":
            if "POLYGON_ORDER(A, B, C, D)" in dsl and "SEGMENT(A, C)" in dsl:
                 print(f"  ✅ Multi-turn Success: DSL merged correctly.")
            else:
                 print(f"  ❌ Multi-turn Fail: DSL missing component.")

        return result

    except Exception as e:
        import traceback
        print(f"  ❌ EXCEPTION: {type(e).__name__}: {e}")
        traceback.print_exc()
        return None


async def main():
    load_dotenv()
    orchestrator = Orchestrator()

    results = []
    # Run Q1 to Q9
    for q in QUERIES[:-1]:
        res = await run_query(orchestrator, q)
        results.append((q["id"], res is not None))

    # Run Q10 Flow (Multi-turn)
    print("\n--- Starting Multi-turn Flow (Q10) ---")
    q10_1 = QUERIES[-1]
    res10_1 = await run_query(orchestrator, q10_1)
    results.append((q10_1["id"], res10_1 is not None))

    if res10_1:
        # Construct message history to pass to step 2
        history = [
            {"role": "user", "content": q10_1["text"]},
            {
                "role": "assistant", 
                "content": res10_1["semantic_analysis"],
                "metadata": {
                    "geometry_dsl": res10_1["geometry_dsl"],
                    "coordinates": res10_1["coordinates"]
                }
            }
        ]
        res10_2 = await run_query(orchestrator, Q10_FOLLOW_UP, history=history)
        results.append((Q10_FOLLOW_UP["id"], res10_2 is not None))

    print(f"\n{'='*60}")
    print("SUMMARY:")
    for qid, ok in results:
        print(f"  [{qid}] {'✅ PASS' if ok else '❌ FAIL'}")

if __name__ == "__main__":
    asyncio.run(main())
