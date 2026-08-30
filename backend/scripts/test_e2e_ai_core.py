import asyncio
import os
import sys
import time
import json
import logging
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")

from agents.orchestrator import Orchestrator

TEST_CASES = [
    {
        "id": "case_1_easy",
        "name": "Bài 1 (Dễ): Hình chóp tứ giác đều",
        "text": "Cho hình chóp S.ABCD có đáy ABCD là hình vuông cạnh 10. Chiều cao SO vuông góc với đáy tại tâm O, SO=15. Tính thể tích khối chóp S.ABCD.",
        "expected_answer": "500",
    },
    {
        "id": "case_2_medium",
        "name": "Bài 2 (Trung bình): Hình chóp tam giác đều",
        "text": "Cho hình chóp tam giác đều S.ABC có cạnh đáy bằng 6, chiều cao SO = 8 vuông góc với đáy tại trọng tâm O của tam giác ABC. Tính thể tích khối chóp S.ABC.",
        "expected_answer": "24*sqrt(3) ≈ 41.57",
    },
    {
        "id": "case_3_hard",
        "name": "Bài 3 (Khó): Hình chóp cụt tứ giác đều",
        "text": "Cho hình chóp cụt tứ giác đều ABCD.A1B1C1D1 có cạnh đáy dưới bằng 8, cạnh đáy trên bằng 4, chiều cao giữa hai đáy h=6. Tính thể tích khối chóp cụt.",
        "expected_answer": "224",
    },
]

async def main():
    print("=" * 80, flush=True)
    print("      END-TO-END AI CORE BENCHMARK (v6.0 Unified Architecture)", flush=True)
    print("      GeometryParserAgent + GeometryEngine + DeepMathSolverAgent", flush=True)
    print("=" * 80, flush=True)

    orchestrator = Orchestrator()
    results = []

    for tc in TEST_CASES:
        print(f"\n" + "=" * 80, flush=True)
        print(f"🔥 TEST CASE: {tc['name']}", flush=True)
        print(f"📄 Đề bài: {tc['text']}", flush=True)
        print(f"🎯 Kỳ vọng kết quả: {tc['expected_answer']}", flush=True)
        print("=" * 80, flush=True)

        start_time = time.time()
        try:
            res = await orchestrator.run(
                text=tc["text"],
                job_id=f"e2e_{tc['id']}",
            )
            elapsed = time.time() - start_time

            status = res.get("status")
            is_3d = res.get("is_3d")
            dsl = res.get("geometry_dsl")
            coords = res.get("coordinates", {})
            solution = res.get("solution", {})
            answer = solution.get("answer") if solution else "N/A"
            steps = solution.get("steps", []) if solution else []
            vars_eval = solution.get("evaluated_variables", {}) if solution else {}

            print(f"\n⏱ Tổng thời gian chạy: {elapsed:.2f}s", flush=True)
            print(f"📊 Trạng thái: {status} | Không gian 3D: {is_3d} | Tọa độ điểm ({len(coords)}): {list(coords.keys())}", flush=True)
            print(f"\n📐 Generated Geometry DSL:\n{dsl}", flush=True)
            print(f"\n🐍 Evaluated Variables via SymPy Sandbox: {vars_eval}", flush=True)
            print(f"🏆 Kết quả tính toán cuối cùng: {answer}", flush=True)
            print(f"\n📋 Các bước giải chi tiết ({len(steps)} bước):", flush=True)
            for s in steps:
                print(f"   • {s}", flush=True)

            results.append({
                "id": tc["id"],
                "name": tc["name"],
                "elapsed": round(elapsed, 2),
                "status": status,
                "n_coords": len(coords),
                "answer": answer,
                "vars": vars_eval,
            })
        except Exception as e:
            print(f"❌ Error during test: {e}", flush=True)
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80, flush=True)
    print("                    E2E BENCHMARK SUMMARY TABLE", flush=True)
    print("=" * 80, flush=True)
    for r in results:
        print(f"[{r['id']}] {r['name']}: Status={r['status']}, Coords={r['n_coords']} pts, Time={r['elapsed']}s, Ans={r['answer']}, Vars={r['vars']}", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    asyncio.run(main())
