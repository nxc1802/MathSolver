import os
import subprocess
from fastapi import FastAPI
import uvicorn
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start Celery worker in the background
    print("🚀 Starting Celery worker in background...")
    # Using subprocess.Popen to avoid blocking the main thread
    process = subprocess.Popen([
        "celery", 
        "-A", "worker.celery_app", 
        "worker", 
        "--loglevel=info",
        "--concurrency=1"  # Set to 1 to minimize RAM spikes on HF Spaces
    ])
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
