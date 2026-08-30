import json
import re
import ast

def robust_json_decode(text: str) -> dict:
    clean = text.strip()
    if clean.startswith("```"):
        m = re.search(r"```(?:json)?\s*(.*?)\s*```", clean, re.DOTALL)
        if m:
            clean = m.group(1).strip()

    try:
        return json.loads(clean, strict=False)
    except Exception:
        pass

    # Escape raw backslashes
    try:
        # Replace unescaped backslashes
        fixed = re.sub(r'\\(?![/\"\\bfnrtu]|u[0-9a-fA-F]{4})', r'\\\\', clean)
        return json.loads(fixed, strict=False)
    except Exception:
        pass

    # Try regex fallback extraction
    steps = re.findall(r'"([^"]*Bước[^"]*)"', clean)
    if not steps:
        steps = re.findall(r'"([^"]+)"', clean)
        steps = [s for s in steps if any(kw in s.lower() for kw in ['diện tích', 'thể tích', 'chiều cao', 'công thức', 'bước', 'ta có', '='])]

    ans_m = re.search(r'"final_answer"\s*:\s*"?([^"}\n]+)"?', clean)
    return {
        "step_by_step_solution": steps,
        "final_answer": ans_m.group(1).strip() if ans_m else ""
    }

test_str = r'{"step_by_step_solution": ["Bước 1: S = \frac{6^2\sqrt{3}}{4} = 9\sqrt{3}", "Bước 2: SO = 8", "Bước 3: V = \frac{1}{3} \times 9\sqrt{3} \times 8 = 24\sqrt{3}"], "final_answer": "24\sqrt{3}"}'

d = robust_json_decode(test_str)
print("Decoded steps count:", len(d["step_by_step_solution"]))
print("Decoded step 1:", d["step_by_step_solution"][0])
print("Decoded final_answer:", d["final_answer"])
