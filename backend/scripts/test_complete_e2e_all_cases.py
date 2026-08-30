"""
Complete End-to-End Benchmark across ALL Test Cases:
Part 1: Math OCR Vision Pipeline on Test Images (2D_easy, 3D_easy, 2D_hard, 3D_hard)
Part 2: 3D Geometry Reasoning & Deterministic Solver (3 Difficulty Levels)
Part 3: End-to-End Image -> OCR -> AI Core Solver -> VisualizationSpec -> Manim API
"""
import asyncio
import os
import sys
import time
import json
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
logger = logging.getLogger(__name__)

from agents.orchestrator import Orchestrator
from agents.ocr_agent import OCRAgent
from manim_client.client import ManimClient

OCR_DATA_DIR = "/Volumes/WorkSpace/Project/MathSolver/backend/tests/data"

OCR_TEST_CASES = [
    {"id": "2D_easy", "path": os.path.join(OCR_DATA_DIR, "2D_easy.png")},
    {"id": "3D_easy", "path": os.path.join(OCR_DATA_DIR, "3D_easy.png")},
    {"id": "2D_hard", "path": os.path.join(OCR_DATA_DIR, "2D_hard.png")},
    {"id": "3D_hard", "path": os.path.join(OCR_DATA_DIR, "3D_hard.png")},
]

MATH_BENCHMARK_CASES = [
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


async def run_ocr_tests(ocr_agent: OCRAgent) -> List[Dict[str, Any]]:
    print("\n" + "=" * 90, flush=True)
    print("      PHẦN 1: KIỂM THỬ MATH OCR VISION PIPELINE (Pix2Text Engine)", flush=True)
    print("=" * 90, flush=True)

    ocr_results = []
    for tc in OCR_TEST_CASES:
        start_t = time.time()
        res = await ocr_agent.process_image_canonical(tc["path"])
        elapsed = time.time() - start_t

        print(f"\n📸 Image: {tc['id']} ({tc['path']})", flush=True)
        print(f"⏱ OCR Time: {elapsed:.2f}s | Confidence: {res.confidence:.2f} | Elements: {len(res.elements)}", flush=True)
        print(f"📄 Extracted Text:\n{res.text.strip()}\n", flush=True)

        ocr_results.append({
            "id": tc["id"],
            "elapsed": round(elapsed, 2),
            "confidence": res.confidence,
            "elements_count": len(res.elements),
            "text": res.text.strip(),
        })

    return ocr_results


async def run_math_benchmark(orchestrator: Orchestrator) -> List[Dict[str, Any]]:
    print("\n" + "=" * 90, flush=True)
    print("      PHẦN 2: KIỂM THỬ TOÁN HÌNH HỌC & SANDBOX SYMPY (3 ĐỘ KHÓ)", flush=True)
    print("=" * 90, flush=True)

    math_results = []
    for tc in MATH_BENCHMARK_CASES:
        print(f"\n" + "-" * 90, flush=True)
        print(f"🔥 TEST CASE: {tc['name']}", flush=True)
        print(f"📄 Đề bài: {tc['text']}", flush=True)
        print(f"🎯 Kỳ vọng: {tc['expected_answer']}", flush=True)
        print("-" * 90, flush=True)

        start_t = time.time()
        res = await orchestrator.run(
            text=tc["text"],
            job_id=f"benchmark_{tc['id']}",
            generate_video=True,
        )
        elapsed = time.time() - start_t

        coords = res.get("coordinates", {})
        sol = res.get("solution", {})
        ans = sol.get("answer") if sol else "N/A"
        vars_eval = sol.get("evaluated_variables", {}) if sol else {}
        steps = sol.get("steps", []) if sol else []
        viz = res.get("visualization", {}) or {}

        print(f"⏱ Tổng thời gian: {elapsed:.2f}s | Trạng thái: {res.get('status')}", flush=True)
        print(f"📐 Tọa độ đỉnh ({len(coords)}): {list(coords.keys())}", flush=True)
        print(f"🐍 Biến số giải qua SymPy Sandbox: {vars_eval}", flush=True)
        print(f"🏆 Kết quả tính toán: {ans}", flush=True)
        print(f"🎬 Visualization Spec: {len(viz.get('spec', {}).get('geometry', []))} objs, {len(viz.get('spec', {}).get('animations', []))} beats | Manim Job: {viz.get('job_id')}", flush=True)

        math_results.append({
            "id": tc["id"],
            "name": tc["name"],
            "elapsed": round(elapsed, 2),
            "status": res.get("status"),
            "n_coords": len(coords),
            "answer": ans,
            "vars": vars_eval,
            "steps": steps,
            "viz_job_id": viz.get("job_id"),
            "viz_status": viz.get("status"),
        })

    return math_results


async def run_image_to_video_e2e(ocr_agent: OCRAgent, orchestrator: Orchestrator) -> Dict[str, Any]:
    print("\n" + "=" * 90, flush=True)
    print("      PHẦN 3: KIỂM THỬ TOÀN TRÌNH E2E (IMAGE -> OCR -> AI SOLVE -> MANIM)", flush=True)
    print("=" * 90, flush=True)

    img_path = os.path.join(OCR_DATA_DIR, "3D_easy.png")
    print(f"📷 Đang nạp ảnh đề bài: {img_path}", flush=True)

    start_t = time.time()
    # 1. Direct OCR from image
    ocr_res = await ocr_agent.process_image_canonical(img_path)
    ocr_text = ocr_res.text.strip()
    print(f"📄 OCR Text trích xuất từ ảnh ({time.time() - start_t:.2f}s):\n{ocr_text}\n", flush=True)

    # 2. Run Orchestrator with extracted OCR text
    res = await orchestrator.run(
        text=ocr_text,
        job_id="e2e_image_to_video",
        generate_video=True,
    )

    elapsed = time.time() - start_t
    sol = res.get("solution", {})
    viz = res.get("visualization", {}) or {}

    print(f"⏱ Tổng thời gian E2E: {elapsed:.2f}s | Trạng thái: {res.get('status')}", flush=True)
    print(f"🏆 Kết quả tính toán: {sol.get('answer')}", flush=True)
    print(f"🎬 Manim Render Job ID: {viz.get('job_id')} | Status: {viz.get('status')}", flush=True)

    return {
        "image": "3D_easy.png",
        "elapsed": round(elapsed, 2),
        "status": res.get("status"),
        "answer": sol.get("answer"),
        "viz_job_id": viz.get("job_id"),
        "viz_status": viz.get("status"),
    }


async def main():
    print("=" * 90, flush=True)
    print("      CHƯƠNG TRÌNH KIỂM THỬ END-TO-END TOÀN BỘ CÁC TEST CASES", flush=True)
    print(f"      Manim Endpoint: {os.getenv('MANIM_SERVICE_URL')}", flush=True)
    print("=" * 90, flush=True)

    ocr_agent = OCRAgent()
    orchestrator = Orchestrator()

    # Part 1: OCR Tests
    ocr_results = await run_ocr_tests(ocr_agent)

    # Part 2: Math Benchmark Tests
    math_results = await run_math_benchmark(orchestrator)

    # Part 3: Image-to-Video E2E Test
    e2e_result = await run_image_to_video_e2e(ocr_agent, orchestrator)

    # Summary Table
    print("\n" + "=" * 90, flush=True)
    print("                         TỔNG HỢP KẾT QUẢ BENCHMARK E2E", flush=True)
    print("=" * 90, flush=True)

    print("\n1. KẾT QUẢ OCR:")
    for o in ocr_results:
        print(f"   • [{o['id']}]: Time={o['elapsed']}s | Confidence={o['confidence']:.2f} | Elements={o['elements_count']}")

    print("\n2. KẾT QUẢ GIẢI TOÁN & HÌNH HỌC (3 ĐỘ KHÓ):")
    for m in math_results:
        print(f"   • [{m['id']}] {m['name']}:")
        print(f"     - Status: {m['status']} | Time: {m['elapsed']}s | Coords: {m['n_coords']} pts")
        print(f"     - Verified Answer: {m['answer']}")
        print(f"     - SymPy Vars: {m['vars']}")
        print(f"     - Manim Job: {m['viz_job_id']} ({m['viz_status']})")

    print("\n3. KẾT QUẢ TOÀN TRÌNH ẢNH -> VIDEO:")
    print(f"   • Image: {e2e_result['image']} | Total Time: {e2e_result['elapsed']}s | Ans: {e2e_result['answer']} | Manim Job: {e2e_result['viz_job_id']}")
    print("=" * 90, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
