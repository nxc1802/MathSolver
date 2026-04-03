from __future__ import annotations

import logging
import os
import uuid
import warnings

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
os.environ["NO_ALBUMENTATIONS_UPDATE"] = "1"
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", category=UserWarning, module="albumentations")

from app.logging_setup import setup_application_logging

setup_application_logging()

# Routers (after logging)
from app.routers import auth, sessions, solve
from app.supabase_client import get_supabase
from app.websocket_manager import register_websocket_routes
from agents.ocr_agent import OCRAgent

logger = logging.getLogger("app.main")
logger.info("App starting (APP_LOG_MODE=%s)", os.getenv("APP_LOG_MODE", "production"))

app = FastAPI(title="Visual Math Solver API v4.0")

from worker.celery_app import BROKER_URL

logger.info(
    "Redis broker: %s",
    BROKER_URL.split("@")[-1] if "@" in BROKER_URL else BROKER_URL,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(solve.router)

register_websocket_routes(app)

_ocr_agent: OCRAgent | None = None


def get_ocr_agent() -> OCRAgent:
    """Lazy init: OCR loads YOLO/Paddle/Pix2Tex and is heavy; defer until first use."""
    global _ocr_agent
    if _ocr_agent is None:
        _ocr_agent = OCRAgent()
    return _ocr_agent


supabase_client = get_supabase()


@app.get("/")
def read_root():
    return {"message": "Visual Math Solver API v4.0 is running"}


@app.post("/api/v1/ocr")
async def upload_ocr(file: UploadFile = File(...)):
    """Legacy OCR endpoint (retained for now as it's stateless)"""
    temp_path = f"temp_{uuid.uuid4()}.png"
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())

    try:
        text = await get_ocr_agent().process_image(temp_path)
        return {"text": text}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.get("/api/v1/solve/{job_id}")
async def get_job_status(job_id: str):
    """Retrieve job status (can be used for polling if WS fails)"""
    response = supabase_client.table("jobs").select("*").eq("id", job_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return response.data[0]
