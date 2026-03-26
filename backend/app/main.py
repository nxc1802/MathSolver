from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uuid
import asyncio
import os
import logging
import warnings
from dotenv import load_dotenv
from app.supabase_client import get_supabase

# ── Environment & Warnings ───────────────────────────────────────────────────
load_dotenv()
os.environ["NO_ALBUMENTATIONS_UPDATE"] = "1"
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", category=UserWarning, module="albumentations")

# ── Logging Configuration ──────────────────────────────────────────────────────
# Set to logging.DEBUG for full agent traces, logging.INFO for production.
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.DEBUG),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
# Quiet down noisy 3rd-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)

logger = logging.getLogger("app.main")
logger.info(f"🚀 [App] Logging configured at level: {LOG_LEVEL}")

app = FastAPI(title="Visual Math Solver API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for production (Vercel/HuggingFace)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SolveRequest(BaseModel):
    text: str
    image_url: Optional[str] = None
    request_video: bool = False

class SolveResponse(BaseModel):
    job_id: str
    status: str

supabase_client = get_supabase()

@app.get("/")
def read_root():
    return {"message": "Visual Math Solver API v3.0 is running"}

from agents.orchestrator import Orchestrator
from agents.ocr_agent import OCRAgent

orchestrator = Orchestrator()
ocr_agent = OCRAgent()

@app.post("/api/v1/ocr")
async def upload_ocr(file: UploadFile = File(...)):
    # Save temp file
    temp_path = f"temp_{uuid.uuid4()}.png"
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())
    
    try:
        text = await ocr_agent.process_image(temp_path)
        return {"text": text}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/api/v1/solve", response_model=SolveResponse)
async def create_solve_job(request: SolveRequest):
    job_id = str(uuid.uuid4())
    # Create job in Supabase
    supabase_client.table("jobs").insert({
        "id": job_id,
        "status": "processing",
        "input_text": request.text
    }).execute()
    
    asyncio.create_task(process_job(job_id, request))
    return SolveResponse(job_id=job_id, status="processing")

async def process_job(job_id: str, request: SolveRequest):
    async def status_update(status: str):
        await notify_status(job_id, {"status": status})

    try:
        result = await orchestrator.run(
            request.text, 
            request.image_url, 
            job_id=job_id, 
            status_callback=status_update,
            request_video=request.request_video
        )
        status = result.get("status", "error") if "error" not in result else "error"
        
        # Update status in Supabase
        supabase_client.table("jobs").update({
            "status": status,
            "result": result
        }).eq("id", job_id).execute()
        
        await notify_status(job_id, {"status": status, "result": result})
    except Exception as e:
        supabase_client.table("jobs").update({
            "status": "error",
            "result": {"error": str(e)}
        }).eq("id", job_id).execute()

# WebSocket Management
active_connections: Dict[str, List[WebSocket]] = {}

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await websocket.accept()
    if job_id not in active_connections:
        active_connections[job_id] = []
    active_connections[job_id].append(websocket)
    try:
        while True:
            await websocket.receive_text() # Keep connection alive
    except WebSocketDisconnect:
        active_connections[job_id].remove(websocket)

async def notify_status(job_id: str, data: dict):
    if job_id in active_connections:
        for connection in active_connections[job_id]:
            await connection.send_json(data)

@app.get("/api/v1/solve/{job_id}")
async def get_job_status(job_id: str):
    response = supabase_client.table("jobs").select("*").eq("id", job_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return response.data[0]
