import os
import httpx
import json
import time
from dotenv import load_dotenv

# Load môi trường từ backend/.env
load_dotenv(dotenv_path="./backend/.env")

MODELS = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "openai/gpt-oss-120b:free",
    "z-ai/glm-4.5-air:free",
    "minimax/minimax-m2.5:free",
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-4-31b-it:free",
]

PROMPT = "Cho hình chữ nhật ABCD có AB bằng 5 và AD bằng 10. Gọi E là điểm nằm trong đoạn CD sao cho CE = 2ED. Vẽ đoạn thẳng AE. Vẽ thêm P là điểm nằm trên đường thẳng BC sao cho BP = 2PC, tính chu vi tam giác PEA"

def test_models():
    api_key = os.getenv("OPENROUTER_API_KEY_1")
    base_url = "https://openrouter.ai/api/v1/chat/completions"

    if not api_key:
        print("❌ Lỗi: Không tìm thấy OPENROUTER_API_KEY trong file .env")
        return

    print("🚀 Bắt đầu benchmark các model OpenRouter...")
    print(f"📝 Prompt: {PROMPT}\n")
    
    results = []

    for model in MODELS:
        print(f"📡 Đang gọi model: {model}...", end="", flush=True)
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://mathsolver.io",
            "X-Title": "MathSolver Benchmark Tool"
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": PROMPT}]
        }

        start_time = time.time()
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(base_url, headers=headers, json=payload)
                response.raise_for_status()
                
                duration = time.time() - start_time
                data = response.json()
                answer = data['choices'][0]['message']['content']
                
                results.append({
                    "model": model,
                    "duration": duration,
                    "answer": answer,
                    "status": "success"
                })
                print(f" ✅ DONE ({duration:.2f}s)")
                
        except Exception as e:
            duration = time.time() - start_time
            print(f" ❌ FAILED ({duration:.2f}s)")
            results.append({
                "model": model,
                "duration": duration,
                "error": str(e),
                "status": "error"
            })

    print("\n" + "="*80)
    print("📊 BÁO CÁO CHI TIẾT BENCHMARK")
    print("="*80)

    for res in results:
        print(f"\n🔹 MODEL: {res['model']}")
        print(f"⏱ Thời gian: {res['duration']:.2f} giây")
        if res['status'] == "success":
            print(f"🤖 Phản hồi:\n{res['answer']}")
        else:
            print(f"❌ Lỗi: {res.get('error')}")
        print("-" * 40)

if __name__ == "__main__":
    test_models()
