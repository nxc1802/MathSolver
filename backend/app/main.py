from __future__ import annotations

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import uuid
import os
import logging
import warnings
from dotenv import load_dotenv

# Routers
from app.routers import auth, sessions, solve
from app.supabase_client import get_supabase
from app.websocket_manager import register_websocket_routes
from agents.ocr_agent import OCRAgent

# ── Environment & Warnings ───────────────────────────────────────────────────
load_dotenv()
os.environ["NO_ALBUMENTATIONS_UPDATE"] = "1"
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", category=UserWarning, module="albumentations")

# ── Logging Configuration ──────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.DEBUG),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)

logger = logging.getLogger("app.main")
logger.info(f"🚀 [App] System v4.0 starting - Logging level: {LOG_LEVEL}")

app = FastAPI(title="Visual Math Solver API v4.0")

# Confirm Redis config on startup
from worker.celery_app import BROKER_URL
logger.info(f"📍 [Backend] Redis Configuration: {BROKER_URL.split('@')[-1] if '@' in BROKER_URL else BROKER_URL}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include Routers ──────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(solve.router)

register_websocket_routes(app)

# ── Shared Instances ──────────────────────────────────────────────────────────
_ocr_agent: OCRAgent | None = None


def get_ocr_agent() -> OCRAgent:
    """Lazy init: OCR loads YOLO/Paddle/Pix2Tex and is heavy; defer until first use."""
    global _ocr_agent
    if _ocr_agent is None:
        _ocr_agent = OCRAgent()
    return _ocr_agent


supabase_client = get_supabase()

# ── Routes ───────────────────────────────────────────────────────────────────

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
