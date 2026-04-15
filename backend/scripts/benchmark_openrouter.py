"""Benchmark several OpenRouter models (manual tool; not part of pytest)."""

from __future__ import annotations

import json
import os
import time

import httpx
from dotenv import load_dotenv

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_BACKEND_ROOT, ".env"))

MODELS = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "openai/gpt-oss-120b:free",
    "z-ai/glm-4.5-air:free",
    "minimax/minimax-m2.5:free",
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-4-31b-it:free",
]

PROMPT = (
    "Cho hình chữ nhật ABCD có AB bằng 5 và AD bằng 10. Gọi E là điểm nằm trong đoạn CD sao cho CE = 2ED. "
    "Vẽ đoạn thẳng AE. Vẽ thêm P là điểm nằm trên đường thẳng BC sao cho BP = 2PC, tính chu vi tam giác PEA"
)


def main() -> None:
    api_key = os.getenv("OPENROUTER_API_KEY_1") or os.getenv("OPENROUTER_API_KEY")
    base_url = "https://openrouter.ai/api/v1/chat/completions"

    if not api_key:
        print("Missing OPENROUTER_API_KEY_1 or OPENROUTER_API_KEY in .env")
        return

    print("Benchmark OpenRouter models\nPrompt:", PROMPT, "\n")
    results = []

    for model in MODELS:
        print(f"Calling {model}...", end="", flush=True)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://mathsolver.io",
            "X-Title": "MathSolver Benchmark Tool",
        }
        payload = {"model": model, "messages": [{"role": "user", "content": PROMPT}]}
        start = time.time()
        try:
            with httpx.Client(timeout=120.0) as client:
                r = client.post(base_url, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
                answer = data["choices"][0]["message"]["content"]
                duration = time.time() - start
                results.append(
                    {"model": model, "duration": duration, "answer": answer, "status": "success"}
                )
                print(f" OK ({duration:.2f}s)")
        except Exception as e:
            duration = time.time() - start
            results.append(
                {"model": model, "duration": duration, "error": str(e), "status": "error"}
            )
            print(f" FAIL ({duration:.2f}s) {e}")

    print("\n" + "=" * 80)
    for res in results:
        print(json.dumps(res, ensure_ascii=False, indent=2)[:2000])
        print("-" * 40)


if __name__ == "__main__":
    main()
