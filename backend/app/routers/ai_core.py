from __future__ import annotations

import base64
import logging
import os
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from agents.orchestrator import Orchestrator
from agents.ocr_agent import OCRAgent
from manim_client.client import ManimClient
from manim_client.schemas import MathRenderResponse
from vision_ocr.canonical_schema import CanonicalOCRResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ai", tags=["AI Core (Standalone)"])

# Shared in-memory instances
_orchestrator = Orchestrator()
_ocr_agent = OCRAgent()
_manim_client = ManimClient()


class AISolveRequest(BaseModel):
    text: Optional[str] = None
    image_url: Optional[str] = None
    image_path: Optional[str] = None
    generate_video: bool = True


class AIOCRRequest(BaseModel):
    image_url: Optional[str] = None
    image_path: Optional[str] = None
    image_base64: Optional[str] = None


@router.post("/ocr", response_model=CanonicalOCRResult)
async def ocr_direct_ai(request: AIOCRRequest) -> CanonicalOCRResult:
    """
    Direct Math OCR Endpoint (Pix2Text Engine).
    Converts geometry problem images into canonical structured format:
    - text: Reconstructed Markdown with LaTeX math formulas
    - latex: List of isolated and embedded LaTeX equations
    - elements: Classified layout regions (text, formulas, bboxes)
    - reading_order: Document reading sequence
    - confidence: Extraction accuracy confidence
    """
    if request.image_url:
        logger.info("==[AI Core OCR] Processing image_url: %s==", request.image_url)
        return await _ocr_agent.process_url_canonical(request.image_url)

    if request.image_path:
        logger.info("==[AI Core OCR] Processing local image_path: %s==", request.image_path)
        return await _ocr_agent.process_image_canonical(request.image_path)

    if request.image_base64:
        logger.info("==[AI Core OCR] Processing image_base64==")
        temp_path = f"temp_ocr_b64_{uuid.uuid4().hex}.png"
        try:
            b64_data = request.image_base64
            if "," in b64_data:
                b64_data = b64_data.split(",", 1)[1]
            img_bytes = base64.b64decode(b64_data)
            with open(temp_path, "wb") as f:
                f.write(img_bytes)
            return await _ocr_agent.process_image_canonical(temp_path)
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    raise HTTPException(status_code=400, detail="Must provide 'image_url', 'image_path', or 'image_base64'.")


@router.post("/solve")
async def solve_direct_ai(request: AISolveRequest) -> Dict[str, Any]:
    """
    Direct Standalone AI Core Solve Endpoint.
    - Runs OCR (Pix2Text) -> GeometryParser -> GeometryEngine -> DeepMath -> VisualizationSpec -> Manim Module.
    - 100% In-Memory: No Supabase DB or Redis connection required.
    - No authentication token required (Ideal for AI development & curl testing).
    """
    text = (request.text or "").strip()
    image_url = request.image_url

    if not text and request.image_path and os.path.exists(request.image_path):
        # Run OCR on local image directly
        ocr_res = await _ocr_agent.process_image_canonical(request.image_path)
        text = ocr_res.text
        logger.info("[AI Core Solve] Extracted OCR text from %s: '%s'", request.image_path, text[:80])

    if not text and not image_url:
        raise HTTPException(status_code=400, detail="Either 'text', 'image_url', or valid 'image_path' must be provided.")

    logger.info("==[AI Core Direct Solve] Received problem: %s==", text[:80] if text else f"Image: {image_url}")
    try:
        result = await _orchestrator.run(
            text=text,
            image_url=image_url,
            job_id="direct_ai_run",
            generate_video=request.generate_video,
        )
        return result
    except Exception as e:
        logger.exception("AI Core execution error: %s", e)
        raise HTTPException(status_code=500, detail=f"AI Core processing failed: {str(e)}")


@router.get("/visualization/jobs/{job_id}", response_model=MathRenderResponse)
async def get_visualization_job_status(job_id: str) -> MathRenderResponse:
    """
    Query the status of a Manim video generation job.
    Proxies request to the Manim Video Generation Module.
    """
    logger.info(f"==[AI Core Visualization] Fetching status for job {job_id}==")
    resp = await _manim_client.get_job_status(job_id)
    return resp
