#!/usr/bin/env python3
"""
MegaLLM smoke test — same wiring as official docs (sync OpenAI client).

Docs pattern:
  client = OpenAI(base_url="https://ai.megallm.io/v1", api_key=os.environ.get("MEGALLM_API_KEY"))
  client.chat.completions.create(model="gpt-5", messages=[...])

This script uses the same URL/model/key resolution as the app (app.url_utils).

Usage:
  cd backend && PYTHONPATH=. python scripts/test_megallm.py
  PYTHONPATH=. python scripts/test_megallm.py gpt-5
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.url_utils import (  # noqa: E402
    megallm_base_url,
    megallm_model,
    openai_compatible_api_key,
    sanitize_env,
)


def main() -> int:
    from openai import OpenAI

    if not sanitize_env(os.getenv("MEGALLM_API_KEY")):
        print("ERROR: MEGALLM_API_KEY is missing or empty in .env", file=sys.stderr)
        return 1

    base_url = megallm_base_url()
    api_key = openai_compatible_api_key(os.getenv("MEGALLM_API_KEY"))
    model = sys.argv[1] if len(sys.argv) >= 2 else megallm_model()

    print("base_url:", base_url)
    print("model:", model)
    print("api_key: set")

    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hello, world!"}],
            max_tokens=64,
        )
        text = (response.choices[0].message.content or "").strip()
        print("SUCCESS")
        print("reply:", text[:800])
        return 0
    except Exception as e:
        print("FAILED:", e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
