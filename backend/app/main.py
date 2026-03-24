from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uuid
import asyncio
from app.supabase_client import get_supabase

app = FastAPI(title="Visual Math Solver API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SolveRequest(BaseModel):
    text: str
    image_url: Optional[str] = None

class SolveResponse(BaseModel):
    job_id: str
    status: str

supabase_client = get_supabase()

@app.get("/")
def read_root():
    return {"message": "Visual Math Solver API v3.0 is running"}

from agents.orchestrator import Orchestrator

orchestrator = Orchestrator()

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
    try:
        result = await orchestrator.run(request.text, request.image_url, job_id=job_id)
        status = "rendering" if "error" not in result else "error"
        
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
