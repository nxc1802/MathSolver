---
title: Math Solver OCR Worker
emoji: 👁️
colorFrom: gray
colorTo: blue
sdk: docker
app_port: 7860
---

# Math Solver — OCR-only worker

This Space runs **Celery** (`worker_health.py`) consuming **only** the `ocr` queue.

Set environment:

- `CELERY_WORKER_QUEUES=ocr` (default in `Dockerfile.worker.ocr`)
- Same `REDIS_URL` / `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` as the API

This Space runs **raw OCR only** (YOLO, PaddleOCR, Pix2Tex). **OpenRouter / LLM tinh chỉnh** không chạy ở đây; API Space gọi `refine_with_llm` sau khi nhận kết quả từ queue `ocr`.

On the **API** Space, set `OCR_USE_CELERY=true` so `run_ocr_from_url` tasks are sent to this worker instead of running Paddle/Pix2Tex on the API process.

Optional: `OCR_CELERY_TIMEOUT_SEC` (default `180`).

**Manim / video** uses a different Celery queue (`render`) and Space — see `README_HF_WORKER.md` and workflow `deploy-worker.yml`.

GitHub Actions: repository secrets `HF_TOKEN` and `HF_OCR_WORKER_REPO` (`owner/space-name`) enable workflow `deploy-worker-ocr.yml`.
