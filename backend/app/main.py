from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from solver.dsl_parser import DSLParser
from solver.engine import GeometryEngine
import uuid

app = FastAPI(title="Visual Math Solver API")

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

@app.post("/api/v1/solve", response_model=SolveResponse)
async def create_solve_job(request: SolveRequest):
    job_id = str(uuid.uuid4())
    # In Phase 2, we run it directly for demo purposes
    try:
        result = await orchestrator.run(request.text, request.image_url)
        jobs[job_id] = {
            "status": "success",
            "input": request.text,
            "result": result
        }
    except Exception as e:
        jobs[job_id] = {
            "status": "error",
            "error": str(e)
        }
    return SolveResponse(job_id=job_id, status=jobs[job_id]["status"])

@app.get("/api/v1/solve/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]
