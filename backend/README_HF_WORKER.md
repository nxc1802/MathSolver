---
title: Math Solver Render Worker
emoji: 👷
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# Math Solver — Render worker (Manim)

This Space runs **Celery** via `worker_health.py` and consumes **only** queue **`render`** (`render_geometry_video`). Image sets `CELERY_WORKER_QUEUES=render` by default (`Dockerfile.worker`).

**Solve** (orchestrator, agents, OCR-in-request when `OCR_USE_CELERY` is off) runs on the **API** Space, not on this worker.

## OCR offload (separate Space)

Queue **`ocr`** is handled by a **dedicated OCR worker** (`Dockerfile.worker.ocr`, `README_HF_WORKER_OCR.md`, workflow `deploy-worker-ocr.yml`). On the API, set `OCR_USE_CELERY=true` and deploy an OCR Space that listens on `ocr`.

## Secrets

Same broker as the API: `REDIS_URL` / `CELERY_BROKER_URL`, Supabase, OpenRouter (renderer may use LLM paths), etc.

**GitHub Actions:** repository secrets `HF_TOKEN` and `HF_WORKER_REPO` (`owner/space-name`) for this workflow (`deploy-worker.yml`).
