from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from solver.dsl_parser import DSLParser
from solver.engine import GeometryEngine
import uuid
import json
from dotenv import load_dotenv

load_dotenv()

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

# In-memory job store for PoC
jobs = {}

@app.get("/")
def read_root():
    return {"message": "Visual Math Solver API v3.0 is running"}

from agents.orchestrator import Orchestrator

orchestrator = Orchestrator()

# Store active websocket connections
active_connections: Dict[str, WebSocket] = {}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    active_connections[client_id] = websocket
    try:
        while True:
            await websocket.receive_text() # keepalive
    except WebSocketDisconnect:
        del active_connections[client_id]

@app.post("/api/v1/solve")
async def solve(request: SolveRequest, client_id: Optional[str] = None):
    # Run Orchestrator
    try:
        result = await orchestrator.run(request.text, request.image_url)
        
        # If client_id is provided via websocket, send result back directly
        if client_id and client_id in active_connections:
            await active_connections[client_id].send_json({
                "type": "result",
                "data": result
            })
        
        return {"status": "success", "data": result}
    except Exception as e:
        if client_id and client_id in active_connections:
            await active_connections[client_id].send_json({"type": "error", "message": str(e)})
        raise HTTPException(status_code=500, detail=str(e))
