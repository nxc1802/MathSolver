import os
import subprocess
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn

load_dotenv()
from app.runtime_env import apply_runtime_env_defaults

apply_runtime_env_defaults()

from app.logging_setup import setup_application_logging

setup_application_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start Celery worker in the background
    print("🚀 Starting Celery worker in background...")
    # Using subprocess.Popen to avoid blocking the main thread
    # Must match task_routes in worker/celery_app.py (queues: render, ocr). No Celery "solve" queue — solve runs on the API.
    queues = os.environ.get("CELERY_WORKER_QUEUES", "render").strip() or "render"
    print(f"🧵 Celery consuming queues: {queues}", flush=True)
    process = subprocess.Popen(
        [
            "celery",
            "-A",
            "worker.celery_app",
            "worker",
            "--loglevel=info",
            "--concurrency=1",  # minimize RAM spikes on HF Spaces
            "-Q",
            queues,
        ]
    )
    yield
    # Cleanup
    print("🛑 Shutting down Celery worker...")
    process.terminate()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def health_check():
    return {"status": "ok", "worker": "running"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"📡 Starting Health Check API on port {port}...", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
