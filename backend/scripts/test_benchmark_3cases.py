import urllib.request
import json
import time

CASES = [
    {
        "level": "1. Easy (Cơ bản)",
        "name": "Hình chóp tứ giác đều S.ABCD",
        "text": "Cho hình chóp S.ABCD có đáy ABCD là hình vuông cạnh 10. Chiều cao SO vuông góc với đáy tại tâm O, SO=15. Tính thể tích khối chóp S.ABCD.",
        "expected_answer": "500",
        "expected_formula": "V = 1/3 * S_day * h = 1/3 * 100 * 15 = 500"
    },
    {
        "level": "2. Medium (Trung bình - Căn thức & Tam giác đều)",
        "name": "Hình chóp tam giác đều S.ABC",
        "text": "Cho hình chóp tam giác đều S.ABC có cạnh đáy bằng 6, chiều cao SO = 8 vuông góc với mặt phẳng đáy (ABC) tại tâm O. Tính thể tích khối chóp S.ABC.",
        "expected_answer": "24*sqrt(3) (≈ 41.57) hoặc 41.57",
        "expected_formula": "S_ABC = (6^2 * sqrt(3)) / 4 = 9*sqrt(3), V = 1/3 * 9*sqrt(3) * 8 = 24*sqrt(3) ≈ 41.57"
    },
    {
        "level": "3. Hard (Nâng cao - Hình chóp cụt)",
        "name": "Hình chóp cụt tứ giác đều",
        "text": "Cho hình chóp cụt tứ giác đều ABCD.A1B1C1D1 có cạnh đáy dưới bằng 8, cạnh đáy trên bằng 4, chiều cao h=6. Tính thể tích khối chóp cụt.",
        "expected_answer": "224",
        "expected_formula": "S1 = 64, S2 = 16, V = (6/3) * (64 + 16 + sqrt(64*16)) = 2 * (80 + 32) = 224"
    }
]

def run_test():
    print("\n" + "="*75)
    print("🎯 BẮT ĐẦU TEST BỘ 3 BÀI TOÁN HÌNH HỌC VỚI SYMPY CALCULATE ENGINE & GEMMA 4 31B")
    print("="*75)

    results = []
    for idx, c in enumerate(CASES, 1):
        print(f"\n📌 TEST CASE {idx}: [{c['level']}] - {c['name']}")
        print(f"📝 Đề bài: {c['text']}")
        print(f"🎯 Kỳ vọng: {c['expected_formula']}")
        print("-" * 60)

        start_t = time.time()
        payload = json.dumps({"text": c["text"]}).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/v1/ai/solve",
            data=payload,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                elapsed = time.time() - start_t
                data = json.loads(resp.read().decode("utf-8"))
                
                status = data.get("status")
                solution = data.get("solution") or {}
                dsl = data.get("geometry_dsl")
                coords = data.get("coordinates")
                answer = solution.get("answer")
                steps = solution.get("steps", [])
                sym_expr = solution.get("symbolic_expression")
                context = solution.get("evaluated_context")

                print(f"⏱️ Thời gian xử lý: {elapsed:.2f}s | Trạng thái: {status}")
                print(f"\n📐 DSL sinh ra:\n{dsl}")
                print(f"\n📍 Toạ độ giải được:\n{json.dumps(coords, indent=2)}")
                print(f"\n🧮 Lời giải tính toán tự động qua SymPy Calculator:")
                for step in steps:
                    print(f"  {step}")
                print(f"\n👉 Đáp số cuối cùng (Đã qua SymPy): {answer}")
                if sym_expr:
                    print(f"👉 Biểu thức LaTeX: {sym_expr}")
                if context:
                    print(f"👉 Context các biến tính toán: {context}")

                results.append({
                    "case": c["level"],
                    "status": "PASS" if status == "success" and answer else "FAIL",
                    "answer": answer,
                    "elapsed": f"{elapsed:.2f}s"
                })
        except Exception as e:
            print(f"❌ Lỗi thực thi: {e}")
            results.append({
                "case": c["level"],
                "status": "ERROR",
                "error": str(e)
            })

    print("\n" + "="*75)
    print("📊 TỔNG KẾT KẾT QUẢ BENCHMARK 3 BÀI TOÁN:")
    print("="*75)
    for r in results:
        print(f"• {r['case']}: [{r['status']}] Đáp số: {r.get('answer', 'N/A')} (Thời gian: {r.get('elapsed', 'N/A')})")
    print("="*75 + "\n")

if __name__ == "__main__":
    run_test()
