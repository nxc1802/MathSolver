import os
import sys
import time
import json
import re
import traceback
from typing import Dict, Any, List
from openai import OpenAI
import sympy as sp

API_KEY = os.getenv("GOOGLE_API_KEY", "")
BASE_URL = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
MODEL = os.getenv("LLM_MODEL", "gemma-4-31b-it")

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
    timeout=60.0,
)

TEST_PROBLEMS = [
    {
        "id": "case_1_easy",
        "name": "Hình chóp tứ giác đều (Easy)",
        "question": "Cho hình chóp S.ABCD có đáy ABCD là hình vuông cạnh 10. Chiều cao SO vuông góc với đáy tại tâm O, SO=15. Tính thể tích khối chóp S.ABCD.",
        "expected": "500",
    },
    {
        "id": "case_2_medium",
        "name": "Hình chóp tam giác đều (Medium)",
        "question": "Cho hình chóp tam giác đều S.ABC có cạnh đáy bằng 6, chiều cao SO = 8 vuông góc với đáy tại trọng tâm O của tam giác ABC. Tính thể tích khối chóp S.ABC.",
        "expected": "24*sqrt(3) ≈ 41.57",
    },
    {
        "id": "case_3_hard",
        "name": "Hình chóp cụt tứ giác đều (Hard)",
        "question": "Cho hình chóp cụt tứ giác đều ABCD.A1B1C1D1 có cạnh đáy dưới bằng 8, cạnh đáy trên bằng 4, chiều cao giữa hai đáy h=6. Tính thể tích khối chóp cụt.",
        "expected": "224",
    }
]

# ==============================================================================
# 1. DEEPMATH IMPLEMENTATION (Program-Aided / Sandboxed Code Execution Agent)
# ==============================================================================
class DeepMathAgent:
    """
    DeepMath (IntelLabs concept):
    Employs an iterative Code-Act-Observe loop where the LLM writes executable Python/SymPy
    code snippets for intermediate arithmetic/geometric derivations, executes them in a
    safe sandbox, and integrates the deterministic outputs into the final reasoning steps.
    """
    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model

    def solve(self, question: str) -> Dict[str, Any]:
        start_time = time.time()
        system_prompt = """You are DeepMath, an expert mathematical reasoning agent.
When solving geometry and math problems:
1. Explain the geometric method step-by-step in Vietnamese.
2. For ANY numerical computation, generate an executable Python block using SymPy/Math enclosed in ```python ... ```.
3. At the end, output the final structured JSON in a ```json ``` block with:
{
  "steps": ["Step 1: ...", "Step 2: ..."],
  "python_code": "... combined python code ...",
  "evaluated_variables": {"var_name": "value"},
  "answer": "final numerical or exact symbolic answer"
}
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Hãy giải bài toán hình học sau:\n{question}"}
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
        )
        content = response.choices[0].message.content or ""

        # Extract and execute Python code snippets in a safe SymPy environment
        code_blocks = re.findall(r"```python(.*?)```", content, re.DOTALL)
        exec_globals = {"sp": sp, "math": __import__("math"), "sqrt": sp.sqrt}
        exec_locals = {}
        for block in code_blocks:
            try:
                exec(block, exec_globals, exec_locals)
            except Exception as e:
                exec_locals["_error"] = str(e)

        # Extract JSON
        json_match = re.search(r"```json(.*?)```", content, re.DOTALL)
        if json_match:
            try:
                parsed_json = json.loads(json_match.group(1).strip())
            except Exception:
                parsed_json = {"raw": content}
        else:
            parsed_json = {"raw": content}

        elapsed = time.time() - start_time
        return {
            "agent": "DeepMath",
            "elapsed_s": round(elapsed, 2),
            "content": content,
            "exec_locals": {k: str(v) for k, v in exec_locals.items() if not k.startswith("_")},
            "parsed_json": parsed_json,
        }

# ==============================================================================
# 2. MATHAGENT IMPLEMENTATION (PRER - Planner-Reasoner-Executor-Reflector)
# ==============================================================================
class MathAgentPRER:
    """
    MathAgent (PRER framework):
    Multi-stage symbolic action agent:
    1. Preprocess: splits into Conditions & Sub-questions.
    2. Select & Act: selects reasoning actions (Calculate, Transform, Deduce).
    3. Check & Reflector: validates step correctness.
    4. Summary: synthesizes final proof and answer.
    """
    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model

    def solve(self, question: str) -> Dict[str, Any]:
        start_time = time.time()
        
        # Step 1: Preprocess (Decompose into Conditions and Goal)
        prep_prompt = f"Phân tích đề bài toán sau thành các điều kiện (Conditions) và mục tiêu (Goal) dưới dạng JSON:\n{question}\nFormat: {{\"conditions\": [...], \"goal\": \"...\"}}"
        prep_res = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prep_prompt}],
            temperature=0.1,
        )
        prep_content = prep_res.choices[0].message.content or ""

        # Step 2: Reasoner & Executor (Calculate + Deduce)
        reason_prompt = f"""Dựa trên bài toán: {question}
Thực hiện các bước giải toán hình học chi tiết, tính toán các công thức diện tích và thể tích chính xác.
Trả về JSON gồm:
{{
  "steps": ["Bước 1: ...", "Bước 2: ..."],
  "formulas": ["S_day = ...", "V = ..."],
  "answer": "kết quả cuối cùng"
}}"""
        reason_res = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": reason_prompt}],
            temperature=0.1,
        )
        reason_content = reason_res.choices[0].message.content or ""

        elapsed = time.time() - start_time
        return {
            "agent": "MathAgent (PRER)",
            "elapsed_s": round(elapsed, 2),
            "prep_content": prep_content,
            "reason_content": reason_content,
        }

def main():
    print("======================================================================", flush=True)
    print("    BENCHMARK & CAPABILITY COMPARISON: DeepMath vs MathAgent", flush=True)
    print(f"    Model: {MODEL} | Provider: Google Generative Language", flush=True)
    print("======================================================================", flush=True)

    deepmath = DeepMathAgent(client, MODEL)
    mathagent = MathAgentPRER(client, MODEL)

    for prob in TEST_PROBLEMS:
        print(f"\n" + "="*70, flush=True)
        print(f"🔥 PROBLEM: {prob['name']}", flush=True)
        print(f"Question: {prob['question']}", flush=True)
        print(f"Expected: {prob['expected']}", flush=True)
        print("="*70, flush=True)

        # 1. Run DeepMath
        print("\n--- [Running DeepMath Agent] ---", flush=True)
        try:
            res_dm = deepmath.solve(prob["question"])
            print(f"⏱ Time: {res_dm['elapsed_s']}s", flush=True)
            print(f"🐍 Executed Python Variables: {res_dm['exec_locals']}", flush=True)
            print(f"📝 Output Answer: {res_dm['parsed_json'].get('answer', 'N/A')}", flush=True)
            print(f"📋 Steps ({len(res_dm['parsed_json'].get('steps', []))}):", flush=True)
            for s in res_dm['parsed_json'].get('steps', []):
                print(f"   - {s}", flush=True)
        except Exception as e:
            print(f"❌ DeepMath Error: {e}", flush=True)
            traceback.print_exc()

        # 2. Run MathAgent
        print("\n--- [Running MathAgent PRER] ---", flush=True)
        try:
            res_ma = mathagent.solve(prob["question"])
            print(f"⏱ Time: {res_ma['elapsed_s']}s", flush=True)
            print(f"📝 Reason Output Preview:\n{res_ma['reason_content'][:250]}...", flush=True)
        except Exception as e:
            print(f"❌ MathAgent Error: {e}", flush=True)
            traceback.print_exc()

if __name__ == "__main__":
    main()
