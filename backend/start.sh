#!/bin/bash

# Start Celery worker in the background
echo "👷 Starting Celery Worker..."
celery -A worker.celery_app worker --loglevel=info &

# Start FastAPI backend in the foreground
echo "🚀 Starting FastAPI Backend on port 7860..."
uvicorn app.main:app --host 0.0.0.0 --port 7860
