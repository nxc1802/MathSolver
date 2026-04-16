from __future__ import annotations

import logging
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from agents.orchestrator import Orchestrator
from app.chat_image_upload import upload_session_chat_image, validate_chat_image_bytes
from app.ocr_celery import ocr_celery_enabled
from app.ocr_local_file import ocr_from_local_image_path
from app.dependencies import get_current_user_id
from app.errors import format_error_for_user
from app.logutil import log_pipeline_failure, log_pipeline_success, log_step
from app.models.schemas import (
    OcrPreviewResponse,
    RenderVideoRequest,
    RenderVideoResponse,
    SolveRequest,
    SolveResponse,
)
from app.ocr_text_merge import build_combined_ocr_preview_draft
from app.session_cache import invalidate_for_user, session_owned_by_user
from app.supabase_client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["Solve"])

# Eager init: all agents and models load at import time (also run in Docker build via scripts/prewarm_models.py).
ORCHESTRATOR = Orchestrator()


def get_orchestrator() -> Orchestrator:
    return ORCHESTRATOR


_OCR_PREVIEW_MAX_BYTES = 10 * 1024 * 1024


def _assert_session_owner(supabase, session_id: str, user_id, uid: str, op: str) -> None:
    def owns() -> bool:
        res = (
            supabase.table("sessions")
            .select("id")
            .eq("id", session_id)
            .eq("user_id", user_id)
            .execute()
        )
        log_step("db_select", table="sessions", op=op, session_id=session_id)
        return bool(res.data)

    if not session_owned_by_user(session_id, uid, owns):
        log_pipeline_failure("solve_request", error="forbidden", session_id=session_id)
        raise HTTPException(
            status_code=403, detail="Forbidden: You do not own this session."
        )


def _enqueue_solve_common(
    supabase,
    background_tasks: BackgroundTasks,
    session_id: str,
    user_id,
    uid: str,
    request: SolveRequest,
    message_metadata: dict,
    job_id: str,
) -> SolveResponse:
    """Insert user message, job row, enqueue pipeline; update title when first message."""
    supabase.table("messages").insert(
        {
            "session_id": session_id,
            "role": "user",
            "type": "text",
            "content": request.text,
            "metadata": message_metadata,
        }
    ).execute()
    log_step("db_insert", table="messages", op="user_message", session_id=session_id)

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

    background_tasks.add_task(process_session_job, job_id, session_id, request, str(user_id))

    title_check = supabase.table("sessions").select("title").eq("id", session_id).execute()
    if title_check.data and title_check.data[0]["title"] == "Bài toán mới":
        new_title = request.text[:50] + ("..." if len(request.text) > 50 else "")
        supabase.table("sessions").update({"title": new_title}).eq("id", session_id).execute()
        log_step("db_update", table="sessions", op="title_from_first_message")
        invalidate_for_user(uid)

    log_pipeline_success("solve_accepted", job_id=job_id, session_id=session_id)
    return SolveResponse(job_id=job_id, status="processing")


@router.post("/{session_id}/ocr_preview", response_model=OcrPreviewResponse)
async def ocr_preview(
    session_id: str,
    user_id=Depends(get_current_user_id),
    file: UploadFile = File(...),
    user_message: str | None = Form(None),
):
    """
    Run OCR on an uploaded image and merge with optional user_message into combined_draft.
    Does not insert messages or start a solve job. After user confirms, call POST .../solve
    with text=combined_draft (edited) and omit image_url to avoid double OCR.
    """
    supabase = get_supabase()
    uid = str(user_id)
    _assert_session_owner(supabase, session_id, user_id, uid, "owner_check_ocr_preview")

    body = await file.read()
    if len(body) > _OCR_PREVIEW_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large (max {_OCR_PREVIEW_MAX_BYTES // (1024 * 1024)} MB).",
        )
    if not body:
        raise HTTPException(status_code=400, detail="Empty file.")

    if ocr_celery_enabled():
        validate_chat_image_bytes(file.filename, body, file.content_type)

    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ""):
        suffix = ".png"
    temp_path = f"temp_ocr_preview_{uuid.uuid4()}{suffix or '.png'}"
    try:
        with open(temp_path, "wb") as f:
            f.write(body)
        ocr_text = await ocr_from_local_image_path(
            temp_path, file.filename, get_orchestrator().ocr_agent
        )
        if ocr_text is None:
            ocr_text = ""
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    um = (user_message or "").strip()
    combined = build_combined_ocr_preview_draft(user_message, ocr_text)
    log_step("ocr_preview_done", session_id=session_id, ocr_len=len(ocr_text), user_len=len(um))
    return OcrPreviewResponse(
        ocr_text=ocr_text,
        user_message=um,
        combined_draft=combined,
    )


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
    _assert_session_owner(supabase, session_id, user_id, uid, "owner_check")

    message_metadata = {"image_url": request.image_url} if request.image_url else {}
    job_id = str(uuid.uuid4())
    return _enqueue_solve_common(
        supabase,
        background_tasks,
        session_id,
        user_id,
        uid,
        request,
        message_metadata,
        job_id,
    )


@router.post("/{session_id}/solve_multipart", response_model=SolveResponse)
async def solve_multipart(
    session_id: str,
    background_tasks: BackgroundTasks,
    user_id=Depends(get_current_user_id),
    text: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Gửi text + file ảnh trong một request multipart: validate, upload bucket `image`,
    ghi session_assets, lưu message kèm metadata (URL, size, type), rồi enqueue solve
    (image_url trỏ public URL để orchestrator OCR).
    """
    supabase = get_supabase()
    uid = str(user_id)
    _assert_session_owner(supabase, session_id, user_id, uid, "owner_check_solve_multipart")

    t = (text or "").strip()
    if not t:
        raise HTTPException(status_code=400, detail="text must not be empty.")

    body = await file.read()
    ext, content_type = validate_chat_image_bytes(file.filename, body, file.content_type)

    job_id = str(uuid.uuid4())
    up = upload_session_chat_image(session_id, job_id, body, ext, content_type)
    public_url = up["public_url"]

    message_metadata = {
        "image_url": public_url,
        "attachment": {
            "public_url": public_url,
            "storage_path": up["storage_path"],
            "size_bytes": len(body),
            "content_type": content_type,
            "original_filename": file.filename or "",
            "session_asset_id": up.get("session_asset_id"),
        },
    }
    request = SolveRequest(text=t, image_url=public_url)
    return _enqueue_solve_common(
        supabase,
        background_tasks,
        session_id,
        user_id,
        uid,
        request,
        message_metadata,
        job_id,
    )


@router.post("/{session_id}/render_video", response_model=RenderVideoResponse)
async def render_video(
    session_id: str,
    request: RenderVideoRequest,
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

    # 2. Tìm tin nhắn assistant có metadata hình học (cụ thể job_id hoặc mới nhất trong 10 tin nhắn gần nhất)
    msg_res = (
        supabase.table("messages")
        .select("metadata")
        .eq("session_id", session_id)
        .eq("role", "assistant")
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    
    latest_geometry = None
    if msg_res.data:
        for msg in msg_res.data:
            meta = msg.get("metadata", {})
            # Nếu có yêu cầu job_id cụ thể, phải khớp job_id
            if request.job_id and meta.get("job_id") != request.job_id:
                continue
            
            # Phải có dữ liệu hình học
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
        await notify_status(job_id, {"status": status, "job_id": job_id})

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

        await notify_status(job_id, {"status": status, "job_id": job_id, "result": result})

    except Exception as e:
        logger.exception("Error processing session job %s", job_id)
        error_msg = format_error_for_user(e)
        supabase = get_supabase()
        supabase.table("jobs").update(
            {"status": "error", "result": {"error": str(e)}}
        ).eq("id", job_id).execute()
        supabase.table("messages").insert(
            {
                "session_id": session_id,
                "role": "assistant",
                "type": "error",
                "content": error_msg,
                "metadata": {"job_id": job_id},
            }
        ).execute()
        await notify_status(job_id, {"status": "error", "job_id": job_id, "error": error_msg})

async def process_render_job(job_id: str, session_id: str, geometry_data: dict):
    """Tiến trình render video từ metadata có sẵn."""
    from app.websocket_manager import notify_status
    from worker.tasks import render_geometry_video
    
    await notify_status(job_id, {"status": "rendering_queued", "job_id": job_id})
    
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
        logger.info(f"[RenderJob] Attempting to dispatch Celery task for job {job_id}...")
        render_geometry_video.delay(job_id, result_payload)
        logger.info(f"[RenderJob] SUCCESS: Dispatched Celery task for job {job_id}")
    except Exception as e:
        logger.exception(f"[RenderJob] FAILED to dispatch Celery task: {e}")
        supabase = get_supabase()
        supabase.table("jobs").update({"status": "error", "result": {"error": f"Task dispatch failed: {str(e)}"}}).eq("id", job_id).execute()
        await notify_status(job_id, {"status": "error", "job_id": job_id, "error": str(e)})
