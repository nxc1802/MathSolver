from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import uuid
import time

from app.schemas.problem import (
    SolveRequest,
    SolveResponse,
    SolutionStep,
    Visualization,
)
from app.services.llm import LLMService
from app.services.ocr import OCRService
from app.services.geometry import GeometryEngine
from app.config import get_settings

router = APIRouter()
settings = get_settings()


# Sample problems for demo/testing
SAMPLE_PROBLEMS = {
    "triangle_cosine": {
        "text": "Cho tam giác ABC có AB = 5, AC = 7, góc A = 60°. Tính độ dài BC và diện tích tam giác ABC.",
        "type": "geometry_2d",
        "steps": [
            {
                "step_number": 1,
                "description": "Xác định các dữ kiện: AB = 5, AC = 7, góc A = 60°",
                "formula": None,
                "result": "Đây là bài toán tam giác biết 2 cạnh và góc xen giữa (SAS)"
            },
            {
                "step_number": 2,
                "description": "Áp dụng định lý cosine để tính BC",
                "formula": "BC² = AB² + AC² - 2·AB·AC·cos(A)",
                "result": "BC² = 25 + 49 - 2·5·7·cos(60°) = 74 - 35 = 39"
            },
            {
                "step_number": 3,
                "description": "Tính độ dài BC",
                "formula": "BC = √39",
                "result": "BC ≈ 6.24"
            },
            {
                "step_number": 4,
                "description": "Tính diện tích tam giác bằng công thức",
                "formula": "S = (1/2)·AB·AC·sin(A)",
                "result": "S = (1/2)·5·7·sin(60°) = 17.5·(√3/2) ≈ 15.16"
            }
        ],
        "answer": "BC ≈ 6.24, Diện tích S ≈ 15.16",
        "geometry_dsl": """# Tam giác ABC với AB=5, AC=7, góc A=60°
POINT(A, 0, 0)
POINT(B, 5, 0)
POINT(C, 3.5, 6.06)
TRIANGLE(ABC, A, B, C)
STEP("Vẽ điểm A tại gốc tọa độ")
STEP("Vẽ điểm B trên trục Ox với AB = 5")
STEP("Vẽ điểm C sao cho AC = 7 và góc A = 60°")
STEP("Nối các điểm tạo thành tam giác ABC")
ANIMATE_DRAW(ABC, 2s)"""
    }
}


@router.post("/solve")
async def solve_problem(
    image: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
):
    """
    Solve a math problem from image or text.
    
    - **image**: Upload an image of the math problem
    - **text**: Or provide the problem as text
    
    Returns solution steps and visualization URLs.
    """
    start_time = time.time()
    
    if not image and not text:
        raise HTTPException(
            status_code=400,
            detail="Either image or text must be provided"
        )
    
    problem_id = str(uuid.uuid4())
    problem_text = text
    
    # If image provided, run OCR
    if image:
        ocr_service = OCRService()
        problem_text = await ocr_service.extract_text(image)
    
    # Check if API key is configured
    if not settings.megallm_api_key or settings.megallm_api_key == "your_megallm_api_key_here":
        # Use sample solution for demo
        sample = SAMPLE_PROBLEMS["triangle_cosine"]
        processing_time = int((time.time() - start_time) * 1000)
        
        return JSONResponse(content={
            "id": problem_id,
            "status": "completed",
            "problem": {
                "text": problem_text or sample["text"],
                "type": sample["type"],
            },
            "solution": {
                "steps": sample["steps"],
                "answer": sample["answer"],
            },
            "visualization": {
                "static_image": None,
                "animation_gif": None,
                "video_mp4": None,
            },
            "metadata": {
                "model": "demo-mode",
                "processing_time_ms": processing_time,
            },
            "geometry_dsl": sample["geometry_dsl"],
        })
    
    # Solve using LLM
    llm_service = LLMService()
    solution = await llm_service.solve(problem_text)
    
    # Generate geometry DSL if it's a geometry problem
    geometry_dsl = solution.get("geometry_dsl", None)
    if not geometry_dsl and solution.get("problem_type", "").startswith("geometry"):
        geometry_dsl = await llm_service.generate_geometry_dsl({
            "problem_type": solution.get("problem_type"),
            "steps": solution.get("steps", []),
            "answer": solution.get("answer", ""),
        })
    
    # Validate geometry if DSL exists
    if geometry_dsl:
        engine = GeometryEngine()
        commands = engine.parse_dsl(geometry_dsl)
        validation = engine.validate_geometry(commands)
        if not validation["valid"]:
            # Log validation errors but don't fail
            print(f"Geometry validation warnings: {validation}")
    
    processing_time = int((time.time() - start_time) * 1000)
    
    return JSONResponse(content={
        "id": problem_id,
        "status": "completed",
        "problem": {
            "text": problem_text,
            "type": solution.get("problem_type", "unknown"),
        },
        "solution": {
            "steps": solution.get("steps", []),
            "answer": solution.get("answer", ""),
        },
        "visualization": {
            "static_image": None,
            "animation_gif": None,
            "video_mp4": None,
        },
        "metadata": {
            "model": settings.megallm_model,
            "processing_time_ms": processing_time,
        },
        "geometry_dsl": geometry_dsl,
    })


@router.get("/solve/{solution_id}")
async def get_solution(solution_id: str):
    """Get a previously computed solution by ID."""
    # TODO: Implement solution storage and retrieval
    raise HTTPException(
        status_code=404,
        detail=f"Solution {solution_id} not found"
    )


@router.get("/sample")
async def get_sample():
    """Get a sample problem for testing."""
    sample = SAMPLE_PROBLEMS["triangle_cosine"]
    return {
        "text": sample["text"],
        "expected_type": sample["type"],
    }
