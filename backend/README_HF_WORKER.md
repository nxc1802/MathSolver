---
title: Math Solver Worker
emoji: 👷
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# Math Solver Worker
This Space runs **Celery** (via `worker_health.py`): video render queue `render` and solve/OCR queue `solve`.

## Queues (env `CELERY_WORKER_QUEUES`)
- **Default:** `render,solve` — one Space handles both (same as local `docker-compose`).
- **Solve-only Space:** set `CELERY_WORKER_QUEUES=solve` (pair with a render-only Space or keep one combined Space).
- **Render-only Space:** set `CELERY_WORKER_QUEUES=render`.

Copy the same secrets as the API: `REDIS_URL` / `CELERY_BROKER_URL`, Supabase, OpenRouter, etc. The API must share the same Redis broker so tasks reach this worker.

**GitHub Actions:** set secrets `HF_TOKEN` plus `HF_WORKER_REPO` (main Space, `owner/space`) for `deploy-worker.yml`. For a second solve-only Space, add `HF_SOLVE_WORKER_REPO` (`owner/space`); workflow `deploy-worker-solve.yml` runs only when that secret is set. Git remote uses the owner before `/` as the HF username for push.
