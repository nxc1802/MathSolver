from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class SolveRequest(BaseModel):
    """Request model for solving a math problem."""
    text: Optional[str] = None
    image_base64: Optional[str] = None


class SolutionStep(BaseModel):
    """A single step in the solution."""
    step_number: int
    description: str
    formula: Optional[str] = None
    result: Optional[str] = None


class Visualization(BaseModel):
    """Visualization outputs."""
    static_image: Optional[str] = None
    animation_gif: Optional[str] = None
    video_mp4: Optional[str] = None


class SolveResponse(BaseModel):
    """Response model for a solved problem."""
    id: str
    status: str
    problem: Dict[str, Any]
    solution: Dict[str, Any]
    visualization: Visualization
    metadata: Dict[str, Any]


class OCRResult(BaseModel):
    """Result from OCR processing."""
    text: str
    latex: Optional[str] = None
    diagram_detected: bool = False
    confidence: float = 0.0


class GeometryObject(BaseModel):
    """A geometry object definition."""
    type: str  # point, line, segment, triangle, circle, etc.
    name: str
    properties: Dict[str, Any] = {}


class ProblemStructure(BaseModel):
    """Parsed problem structure."""
    problem_type: str
    objects: List[GeometryObject] = []
    relations: List[Dict[str, Any]] = []
    requirements: List[Dict[str, Any]] = []
