import os
import re
import difflib

from vision_ocr.pix2text_engine import Pix2TextOCREngine

def normalize_eval(s: str) -> str:
    s = s.replace("$", "").replace("\\", "").replace("{", "").replace("}", "").replace(" ", "").lower()
    for rm in [",", ".", ";", ":", "-", "_", "(", ")", "^", "*", "+", "=", "'", "prime"]:
        s = s.replace(rm, "")
    return s

def calc_sim(a: str, b: str) -> float:
    na = normalize_eval(a)
    nb = normalize_eval(b)
    return difflib.SequenceMatcher(None, na, nb).ratio()

GROUND_TRUTHS = {
    "2D_easy.png": (
        "Cho tam giác ABC vuông tại A, biết AB=6, AC=8.\n"
        "Gọi H là chân đường cao từ A xuống BC.\n"
        "Tính BC, AH và diện tích tam giác ABC."
    ),
    "3D_easy.png": (
        "Cho hình hộp chữ nhật ABCD.A'B'C'D' có AB=4, AD=3, AA'=5.\n"
        "Tính độ dài đường chéo AC'."
    ),
    "2D_hard.png": (
        "Cho đường tròn (O) có đường kính AB.\n"
        "Lấy điểm C trong (O), C khác A, B. Tiếp tuyến tại A và C cắt nhau tại M.\n"
        "Gọi H là hình chiếu vuông góc của C lên AB, N là giao điểm của CM và AB.\n"
        "Chứng minh rằng MA^2 = MH * MN và góc AMC = 2 * góc ABC."
    ),
    "3D_hard.png": (
        "Cho hình chóp S.ABCD có đáy ABCD là hình vuông cạnh a, SA vuông góc (ABCD), SA=a.\n"
        "Gọi M, N lần lượt là trung điểm của AB, CD.\n"
        "Gọi H là hình chiếu vuông góc của A lên SM.\n"
        "1. Xác định giao tuyến của hai mặt phẳng (SMN) và (SAD).\n"
        "2. Tính khoảng cách từ A đến đường thẳng SM.\n"
        "3. Tính góc giữa SM và mặt phẳng (ABCD)."
    ),
}

def main():
    engine = Pix2TextOCREngine.get_instance()
    test_dir = os.path.join(os.path.dirname(__file__), "..", "tests", "data")
    
    print("=" * 70)
    print("      MATH OCR BENCHMARK EVALUATION (4 Test Cases)")
    print("=" * 70)
    
    sims = []
    for name, gt in GROUND_TRUTHS.items():
        img_path = os.path.join(test_dir, name)
        res = engine.recognize(img_path)
        sim = calc_sim(res.text, gt)
        sims.append((name, sim, res, gt))
        
        print(f"\n📁 TEST CASE: {name}")
        print(f"📊 Similarity Score: {sim * 100:.2f}% | Elements: {len(res.elements)} | Conf: {res.confidence:.4f}")
        print(f"📐 Extracted LaTeX ({len(res.latex)}): {res.latex}")
        print("\n--- [Ground Truth] ---")
        print(gt)
        print("\n--- [OCR Canonical Output Text] ---")
        print(res.text)
        print("-" * 70)

    avg_sim = sum(s[1] for s in sims) / len(sims)
    print(f"\n🎯 OVERALL BENCHMARK ACCURACY: {avg_sim * 100:.2f}%\n")

if __name__ == "__main__":
    main()
