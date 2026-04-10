from __future__ import annotations

import logging
import os
import time
import uuid
import warnings

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

load_dotenv()

from app.runtime_env import apply_runtime_env_defaults

apply_runtime_env_defaults()

os.environ["NO_ALBUMENTATIONS_UPDATE"] = "1"
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", category=UserWarning, module="albumentations")

from app.logging_setup import ACCESS_LOGGER_NAME, get_log_level, setup_application_logging

setup_application_logging()

# Routers (after logging)
from app.routers import auth, sessions, solve
from agents.ocr_agent import OCRAgent
from app.routers.solve import get_orchestrator
from app.supabase_client import get_supabase
from app.websocket_manager import register_websocket_routes

logger = logging.getLogger("app.main")
_access = logging.getLogger(ACCESS_LOGGER_NAME)

app = FastAPI(title="Visual Math Solver API v5.1")


@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    """LOG_LEVEL=info/debug: mọi request; warning: chỉ 4xx/5xx; error: chỉ 4xx/5xx ở mức error."""
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    mode = get_log_level()
    method = request.method
    path = request.url.path
    status = response.status_code

    if mode in ("debug", "info"):
        _access.info("%s %s -> %s (%.0fms)", method, path, status, ms)
    elif mode == "warning":
        if status >= 500:
            _access.error("%s %s -> %s (%.0fms)", method, path, status, ms)
        elif status >= 400:
            _access.warning("%s %s -> %s (%.0fms)", method, path, status, ms)
    elif mode == "error":
        if status >= 400:
            _access.error("%s %s -> %s", method, path, status)

    return response


from worker.celery_app import BROKER_URL

_broker_tail = BROKER_URL.split("@")[-1] if "@" in BROKER_URL else BROKER_URL
if get_log_level() in ("debug", "info"):
    logger.info("App starting LOG_LEVEL=%s | Redis: %s", get_log_level(), _broker_tail)
else:
    logger.warning(
        "App starting LOG_LEVEL=%s | Redis: %s", get_log_level(), _broker_tail
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(solve.router)

register_websocket_routes(app)


def get_ocr_agent() -> OCRAgent:
    """Same OCR instance as the solve pipeline (no duplicate model load)."""
    return get_orchestrator().ocr_agent


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
