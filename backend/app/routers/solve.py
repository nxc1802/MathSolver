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
    Lưu câu hỏi vào history và bắt đầu tiến trình giải.
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


async def process_session_job(
    job_id: str, session_id: str, request: SolveRequest, user_id: str
):
    """Tiến trình giải toán ngầm, cập nhật cả bảng jobs và bảng messages (history)."""
    from app.websocket_manager import notify_status

    async def status_update(status: str):
        await notify_status(job_id, {"status": status})

    supabase = get_supabase()
    try:
        # Fetch full history for the session
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
            request_video=request.request_video,
            history=history,
        )

        status = result.get("status", "error") if "error" not in result else "error"

        supabase.table("jobs").update({"status": status, "result": result}).eq(
            "id", job_id
        ).execute()
        log_step("db_update", table="jobs", job_id=job_id, status=status)

        if status != "rendering_queued":
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
                    },
                }
            ).execute()
            log_step("db_insert", table="messages", op="assistant", job_id=job_id)

        await notify_status(job_id, {"status": status, "result": result})

        if "error" in result:
            log_pipeline_failure(
                "solve_job", error=result.get("error"), job_id=job_id, session_id=session_id
            )
        else:
            log_pipeline_success(
                "solve_job", job_id=job_id, session_id=session_id, status=status
            )

    except Exception as e:
        logger.exception("Error processing session job %s", job_id)
        safe = format_error_for_user(e)
        supabase.table("jobs").update(
            {"status": "error", "result": {"error": safe}}
        ).eq("id", job_id).execute()

        supabase.table("messages").insert(
            {
                "session_id": session_id,
                "role": "assistant",
                "type": "error",
                "content": f"Lỗi hệ thống: {safe}",
                "metadata": {"job_id": job_id},
            }
        ).execute()

        await notify_status(job_id, {"status": "error", "message": safe})
        log_pipeline_failure("solve_job", error=safe, job_id=job_id, session_id=session_id)
