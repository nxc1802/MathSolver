#!/bin/bash

# Start Celery worker in the background (Limiting concurrency to 1 to prevent OOM on HF)
echo "👷 Starting Celery Worker (concurrency=1)..."
celery -A worker.celery_app worker --loglevel=info --concurrency=1 &

# Start FastAPI backend in the foreground
echo "🚀 Starting FastAPI Backend on port 7860..."
uvicorn app.main:app --host 0.0.0.0 --port 7860
