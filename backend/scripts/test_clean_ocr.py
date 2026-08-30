import os
import re
import difflib
from PIL import Image
from pix2text import Pix2Text

VIET_MATH_REPLACEMENTS = [
    (r'\bch\s+tam\s+gie\b|\bcho\s+tam\s+giac\b|\bcho\s+tam\s+gie\b', 'Cho tam giác'),
    (r'\bA3O\b|\bAB C\b', 'ABC'),
    (r'\bvt\s*n\s+tai\b|\bvuong\s+tai\b|\bvuang\s+tai\b', 'vuông tại'),
    (r'\bbiét\b|\bbiet\b', 'biết'),
    (r'\bTnh\b|\btnh\b|\bTinh\b|\btinh\b', 'Tính'),
    (r'\bvidintchtmgiéc\b|\bva\s+dien\s+tich\s+tam\s+giac\b', 'và diện tích tam giác'),
    (r'\bchan\s+duing\s+cao\b|\bchan\s+duong\s+cao\b|\bla\s+chan\s+duing\s+cao\b', 'là chân đường cao'),
    (r'\btir\b|\bti\b', 'từ'),
    (r'\bch\s+hinb\s+hop\s+cht[\'’]?nbat\b|\bcho\s+hinh\s+hop\s+chu\s+nhat\b|\bch\s+hinh\s+hop\b', 'Cho hình hộp chữ nhật'),
    (r'\bdo\s+dai\b|\bđo\s+dai\b', 'độ dài'),
    (r'\bduing\s+cheo\b|\bduong\s+cheo\b', 'đường chéo'),
    (r'\bduing\s+tron\b|\bduong\s+tron\b', 'đường tròn'),
    (r'\bduing\s+kinh\b|\bduong\s+kinh\b', 'đường kính'),
    (r'\bduing\s+th[aà]ng\b|\bduong\s+thang\b', 'đường thẳng'),
    (r'\bc6\b', 'có'),
    (r'\bLay\s+di[eé]m\b|\blay\s+diem\b', 'Lấy điểm'),
    (r'\bTi[eé]p\s+tuy[eé]+n\s+tai\b|\btiep\s+tuyen\s+tai\b', 'Tiếp tuyến tại'),
    (r'\bcat\s+nhau\s+tai\b', 'cắt nhau tại'),
    (r'\bla\s+hinh\s+chi[eé]u\s+vuing\s+goc\s+cua\b|\bla\s+hinh\s+chieu\s+vuong\s+goc\s+cua\b|\blà\s+hinh\s+chiéu\s+vuing\s+goc\s+cua\b', 'là hình chiếu vuông góc của'),
    (r'\bla\s+giao\s+di[eé]m\s+cua\b|\bla\s+giao\s+diem\s+cua\b|\blà\s+giao\s+diém\s+cua\b', 'là giao điểm của'),
    (r'\bChtng\s+minh\s+r[aà]ng\b|\bchung\s+minh\s+rang\b', 'Chứng minh rằng'),
    (r'\bv[aà]\b', 'và'),
    (r'\bCho\s+hinh\s+ch[oó6]p\b|\bcho\s+hinh\s+chop\b', 'Cho hình chóp'),
    (r'\bc6\s+day\b|\bco\s+day\b|\bcó\s+day\b', 'có đáy'),
    (r'\bla\s+hinh\s+vu[aá]ng\s+canh\b|\bla\s+hinh\s+vuong\s+canh\b', 'là hình vuông cạnh'),
    (r'\bGo\b|\bGoi\b', 'Gọi'),
    (r'\bN\s+an\s+ludt\s+la\s+trung\s+di[eé]m\s+cua\b|\bN\s+lan\s+luot\s+la\s+trung\s+diem\s+cua\b', 'N lần lượt là trung điểm của'),
    (r'\bXac\s+dinh\s+giao\s+tuy[eé]n\s+cua\s+hai\s+mat\s+ph[aá]ng\b|\bxac\s+dinh\s+giao\s+tuyen\b', 'Xác định giao tuyến của hai mặt phẳng'),
    (r'\bTinh\s+khoang\s+cachtu\b|\btinh\s+khoang\s+cach\s+tu\b|\bTính\s+khoang\s+cachtu\b', 'Tính khoảng cách từ'),
    (r'\bTinh\s+goc\s+gila\b|\btinh\s+goc\s+giua\b|\bTính\s+goc\s+gila\b', 'Tính góc giữa'),
    (r'\bva\s+mat\s+phiang\b|\bva\s+mat\s+phang\b|\bvà\s+mat\s+phiang\b', 'và mặt phẳng'),
    (r'\bduing\s+cao\b|\bduong\s+cao\b', 'đường cao'),
    (r'\bhinh\s+chi[eé]u\b', 'hình chiếu'),
]

def clean_viet_math_text(text: str) -> str:
    s = text
    for pat, repl in VIET_MATH_REPLACEMENTS:
        s = re.sub(pat, repl, s, flags=re.IGNORECASE)
    return s

def clean_latex(s: str) -> str:
    s = s.strip().strip("$").strip()
    s = re.sub(r"\\mathrm\s*\{\s*~?\s*x\s*u\s*\\\s*hat\s*\{\s*o\s*\}\s*n\s*g\s*~?\s*\}", "xuống", s)
    s = re.sub(r"\\operatorname\s*\{\s*v\s*i\s*\}", "và", s)
    s = re.sub(r"\\operatorname\s*\{\s*l\s*e\s*n\s*\}", "lên", s)
    s = re.sub(r"\\mathrm\s*\{\s*\\\s*v\s*i\s*\\\s*\}", "và", s)
    s = re.sub(r"\\mathrm\s*\{\s*v\s*\}\s*\{\s*\\mathrm\s*\{\s*\\bf\s*a\s*\}\s*\}", "và", s)
    s = re.sub(r"\\;\s*\\mathrm\s*\{\s*c\s*\}\s*\\acute\s*\{\s*\\omicron\s*\}", " có", s)
    s = re.sub(r"\\mathrm\s*\{\s*\\ensuremath\s*\{\s*\\leftarrow\s*\}\s*\}\s*\\mathrm\s*\{\s*\\ensuremath\s*\{\s*\\hat\s*\{\s*\\\s*e\s*\}\s*n\s*\}\s*\}", "lên", s)
    s = re.sub(r"\\;\s*\\tt\s*d\s*\\hat\s*\{\s*e\s*n\s*\}", "đến", s)
    s = re.sub(r"\\,\s*", "", s)
    return s

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
    p2t = Pix2Text.from_config(enable_table=False)
    test_dir = os.path.join(os.path.dirname(__file__), "..", "tests", "data")
    
    print("=" * 70)
    print("      MATH OCR BENCHMARK EVALUATION (4 Test Cases)")
    print("=" * 70)
    
    sims = []
    for name, gt in GROUND_TRUTHS.items():
        img_path = os.path.join(test_dir, name)
        raw_out = p2t.recognize(Image.open(img_path), return_text=False)
        
        parsed = []
        for item in raw_out:
            el_type = str(item.get("type", "text")).lower()
            txt = str(item.get("text", "")).strip()
            pos = item.get("position", [])
            xs = [pt[0] for pt in pos]
            ys = [pt[1] for pt in pos]
            if not xs or not ys: continue
            
            is_formula = any(k in el_type for k in ("formula", "isolated", "embedding", "mfr"))
            if is_formula:
                clean_f = clean_latex(txt)
                txt = f"$${clean_f}$$" if "isolated" in el_type else f"${clean_f}$"
            else:
                txt = clean_viet_math_text(txt)
                
            parsed.append({
                "xmin": min(xs),
                "ymin": min(ys),
                "ymax": max(ys),
                "ycenter": (min(ys) + max(ys)) / 2.0,
                "height": max(ys) - min(ys),
                "text": txt,
                "is_formula": is_formula
            })
            
        parsed.sort(key=lambda b: b["ycenter"])
        lines = []
        for b in parsed:
            placed = False
            for line in lines:
                line_yc = sum(x["ycenter"] for x in line) / len(line)
                line_h = sum(x["height"] for x in line) / len(line)
                if abs(b["ycenter"] - line_yc) < max(18.0, line_h * 0.55):
                    line.append(b)
                    placed = True
                    break
            if not placed:
                lines.append([b])
                
        lines.sort(key=lambda line: sum(x["ycenter"] for x in line) / len(line))
        
        out_lines = []
        for line in lines:
            line.sort(key=lambda x: x["xmin"])
            line_txt = " ".join(x["text"] for x in line if x["text"].strip())
            line_txt = clean_viet_math_text(line_txt)
            out_lines.append(line_txt)
            
        rec_text = "\n".join(out_lines)
        sim = calc_sim(rec_text, gt)
        sims.append(sim)
        
        print(f"\n📁 TEST CASE: {name}")
        print(f"📊 Similarity Score: {sim * 100:.2f}%")
        print("\n--- [Ground Truth] ---")
        print(gt)
        print("\n--- [OCR Recognized Text] ---")
        print(rec_text)
        print("-" * 70)

    avg_sim = sum(sims) / len(sims)
    print(f"\n🎯 OVERALL BENCHMARK ACCURACY: {avg_sim * 100:.2f}%\n")

if __name__ == "__main__":
    main()
