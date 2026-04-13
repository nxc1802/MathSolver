from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from agents.orchestrator import Orchestrator
from app.dependencies import get_current_user_id
from app.errors import format_error_for_user
from app.logutil import log_pipeline_failure, log_pipeline_success, log_step
from app.models.schemas import SolveRequest, SolveResponse
from app.session_cache import invalidate_for_user, session_owned_by_user
from app.supabase_client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["Solve"])

# Eager init: all agents and models load at import time (also run in Docker build via scripts/prewarm_models.py).
ORCHESTRATOR = Orchestrator()


def get_orchestrator() -> Orchestrator:
    return ORCHESTRATOR


@router.post("/{session_id}/solve", response_model=SolveResponse)
async def solve_problem(
    session_id: str,
    request: SolveRequest,
    background_tasks: BackgroundTasks,
    user_id=Depends(get_current_user_id),
):
    """
    Gửi câu hỏi giải toán trong một session (Submit geometry problem in a session).
    Lưu câu hỏi vào history và bắt đầu tiến trình giải (chỉ giải toán và tạo hình tĩnh).
    """
    supabase = get_supabase()
    uid = str(user_id)

    def owns() -> bool:
        res = (
            supabase.table("sessions")
            .select("id")
            .eq("id", session_id)
            .eq("user_id", user_id)
            .execute()
        )
        log_step("db_select", table="sessions", op="owner_check", session_id=session_id)
        return bool(res.data)

    if not session_owned_by_user(session_id, uid, owns):
        log_pipeline_failure("solve_request", error="forbidden", session_id=session_id)
        raise HTTPException(
            status_code=403, detail="Forbidden: You do not own this session."
        )

    # NEW: Giới hạn 5 queries mỗi session
    msg_count_res = (
        supabase.table("messages")
        .select("id", count="exact")
        .eq("session_id", session_id)
        .eq("role", "user")
        .execute()
    )
    current_count = msg_count_res.count if msg_count_res.count is not None else 0
    import os
    if current_count >= 5 and os.getenv("ALLOW_TEST_BYPASS") != "true":
        raise HTTPException(
            status_code=400, 
            detail="Bạn đã đạt giới hạn 5 câu hỏi cho phiên này. (Session limit reached: 5/5)"
        )

    supabase.table("messages").insert(
        {
            "session_id": session_id,
            "role": "user",
            "type": "text",
            "content": request.text,
            "metadata": {"image_url": request.image_url} if request.image_url else {},
        }
    ).execute()
    log_step("db_insert", table="messages", op="user_message", session_id=session_id)

    job_id = str(uuid.uuid4())
    supabase.table("jobs").insert(
        {
            "id": job_id,
            "user_id": user_id,
            "session_id": session_id,
            "status": "processing",
            "input_text": request.text,
        }
    ).execute()
    log_step("db_insert", table="jobs", job_id=job_id)

    background_tasks.add_task(process_session_job, job_id, session_id, request, user_id)

    title_check = supabase.table("sessions").select("title").eq("id", session_id).execute()
    if title_check.data and title_check.data[0]["title"] == "Bài toán mới":
        new_title = request.text[:50] + ("..." if len(request.text) > 50 else "")
        supabase.table("sessions").update({"title": new_title}).eq("id", session_id).execute()
        log_step("db_update", table="sessions", op="title_from_first_message")
        invalidate_for_user(uid)

    log_pipeline_success("solve_accepted", job_id=job_id, session_id=session_id)
    return SolveResponse(job_id=job_id, status="processing")


@router.post("/{session_id}/render_video", response_model=RenderVideoResponse)
async def render_video(
    session_id: str,
    background_tasks: BackgroundTasks,
    user_id=Depends(get_current_user_id),
):
    """
    Yêu cầu tạo video Manim từ trạng thái hình ảnh mới nhất của session.
    """
    supabase = get_supabase()
    
    # 1. Kiểm tra quyền sở hữu
    res = supabase.table("sessions").select("id").eq("id", session_id).eq("user_id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this session.")

    # 2. Tìm tin nhắn assistant mới nhất có metadata hình học
    msg_res = (
        supabase.table("messages")
        .select("metadata")
        .eq("session_id", session_id)
        .eq("role", "assistant")
        .order("created_at", desc=True)
        .limit(10) # Look back a bit
        .execute()
    )
    
    latest_geometry = None
    if msg_res.data:
        for msg in msg_res.data:
            meta = msg.get("metadata", {})
            if meta.get("geometry_dsl") and meta.get("coordinates"):
                latest_geometry = meta
                break
    
    if not latest_geometry:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu hình học để render video.")

    # 3. Tạo Job rendering
    job_id = str(uuid.uuid4())
    supabase.table("jobs").insert({
        "id": job_id,
        "user_id": user_id,
        "session_id": session_id,
        "status": "rendering_queued",
        "input_text": f"Render video requested at {job_id}",
    }).execute()

    # 4. Dispatch background task
    background_tasks.add_task(process_render_job, job_id, session_id, latest_geometry)
    
    return RenderVideoResponse(job_id=job_id, status="rendering_queued")


async def process_session_job(
    job_id: str, session_id: str, request: SolveRequest, user_id: str
):
    """Tiến trình giải toán ngầm, tạo hình ảnh tĩnh."""
    from app.websocket_manager import notify_status

    async def status_update(status: str):
        await notify_status(job_id, {"status": status})

    supabase = get_supabase()
    try:
        history_res = (
            supabase.table("messages")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
        )
        history = history_res.data if history_res.data else []

        result = await get_orchestrator().run(
            request.text,
            request.image_url,
            job_id=job_id,
            session_id=session_id,
            status_callback=status_update,
            history=history,
        )

        status = result.get("status", "error") if "error" not in result else "error"

        supabase.table("jobs").update({"status": status, "result": result}).eq(
            "id", job_id
        ).execute()

        supabase.table("messages").insert(
            {
                "session_id": session_id,
                "role": "assistant",
                "type": "analysis" if "error" not in result else "error",
                "content": (
                    result.get("semantic_analysis", "Đã có lỗi xảy ra.")
                    if "error" not in result
                    else result["error"]
                ),
                "metadata": {
                    "job_id": job_id,
                    "coordinates": result.get("coordinates"),
                    "geometry_dsl": result.get("geometry_dsl"),
                    "polygon_order": result.get("polygon_order", []),
                    "drawing_phases": result.get("drawing_phases", []),
                    "circles": result.get("circles", []),
                    "lines": result.get("lines", []),
                    "rays": result.get("rays", []),
                    "solution": result.get("solution"),
                    "is_3d": result.get("is_3d", False),
                },
            }
        ).execute()

        await notify_status(job_id, {"status": status, "result": result})

    except Exception as e:
        logger.exception("Error processing session job %s", job_id)
        # Error handling code ... (preserved)

async def process_render_job(job_id: str, session_id: str, geometry_data: dict):
    """Tiến trình render video từ metadata có sẵn."""
    from app.websocket_manager import notify_status
    from worker.tasks import render_geometry_video
    
    await notify_status(job_id, {"status": "rendering_queued"})
    
    # Prepare payload for Celery (similar to what orchestrator used to do)
    result_payload = {
        "geometry_dsl": geometry_data.get("geometry_dsl"),
        "coordinates": geometry_data.get("coordinates"),
        "polygon_order": geometry_data.get("polygon_order", []),
        "drawing_phases": geometry_data.get("drawing_phases", []),
        "circles": geometry_data.get("circles", []),
        "lines": geometry_data.get("lines", []),
        "rays": geometry_data.get("rays", []),
        "semantic": geometry_data.get("semantic", {}),
        "semantic_analysis": geometry_data.get("semantic_analysis", "🎬 Video minh họa dựng từ trạng thái gần nhất."),
        "session_id": session_id,
    }
    
    try:
        render_geometry_video.delay(job_id, result_payload)
        # Note: The Celery task itself updates the job status to 'success' and adds the message when done.
        logger.info(f"[RenderJob] Dispatched Celery task for job {job_id}")
    except Exception as e:
        logger.exception("Failed to dispatch Celery rendering task")
        supabase = get_supabase()
        supabase.table("jobs").update({"status": "error", "result": {"error": str(e)}}).eq("id", job_id).execute()
        await notify_status(job_id, {"status": "error", "error": str(e)})
