import os
import subprocess
from fastapi import FastAPI
import uvicorn
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start Celery worker in the background
    print("🚀 [Health] Starting Celery worker in background...")
    # Using subprocess.Popen to avoid blocking the main thread
    # Redirect stderr to stdout to see errors in HF logs
    process = subprocess.Popen(
        ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info", "--concurrency=1"],
        stdout=None, 
        stderr=None
    )
    yield
    # Cleanup
    print("🛑 [Health] Shutting down Celery worker...")
    process.terminate()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def health_check():
    return {"status": "ok", "worker": "running"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"📡 Starting Health Check API on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
