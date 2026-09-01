from __future__ import annotations

import logging
import time
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.chat_image_upload import cleanup_session_storage
from app.dependencies import get_current_user_id
from app.logutil import log_step
from app.session_cache import (
    invalidate_session_owner,
    session_owned_by_user,
)
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions"])
logger = logging.getLogger(__name__)


@router.get("", response_model=List[dict])
async def list_sessions(user_id=Depends(get_current_user_id)):
    """Danh sách các phiên chat của người dùng (List user's chat sessions)"""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database service currently unavailable.")
    t0 = time.perf_counter()
    res = (
        supabase.table("sessions")
        .select("id, user_id, title, created_at, updated_at")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .execute()
    )
    log_step("db_select", table="sessions", op="list", user_id=str(user_id))
    out = res.data or []
    logger.info(
        "sessions.list user=%s count=%d %.1fms",
        user_id,
        len(out),
        (time.perf_counter() - t0) * 1000,
    )
    return out


@router.post("", response_model=dict)
async def create_session(user_id=Depends(get_current_user_id)):
    """Tạo một phiên chat mới (Create a new chat session)"""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database service currently unavailable.")
    t0 = time.perf_counter()
    res = supabase.table("sessions").insert(
        {"user_id": user_id, "title": "Bài toán mới"}
    ).execute()
    log_step("db_insert", table="sessions", op="create")
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create session.")
    row = res.data[0]
    logger.info(
        "sessions.create user=%s id=%s %.1fms",
        user_id,
        row.get("id"),
        (time.perf_counter() - t0) * 1000,
    )
    return row


@router.get("/{session_id}/messages", response_model=List[dict])
async def get_session_messages(session_id: str, user_id=Depends(get_current_user_id)):
    """Lấy toàn bộ lịch sử tin nhắn của một phiên (Get chat history for a session)"""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database service currently unavailable.")

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

    if not session_owned_by_user(session_id, str(user_id), owns):
        raise HTTPException(
            status_code=403, detail="Forbidden: You do not own this session."
        )

    res = (
        supabase.table("messages")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .execute()
    )
    log_step("db_select", table="messages", op="list", session_id=session_id)
    return res.data or []


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    background_tasks: BackgroundTasks,
    user_id=Depends(get_current_user_id),
):
    """Xóa một phiên chat và toàn bộ tài nguyên liên quan (Delete a chat session & associated assets)"""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database service currently unavailable.")

    def owns() -> bool:
        res = (
            supabase.table("sessions")
            .select("id")
            .eq("id", session_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(res.data)

    if not session_owned_by_user(session_id, str(user_id), owns):
        raise HTTPException(
            status_code=403, detail="Forbidden: You do not own this session."
        )

    # 1. Authoritative DB deletion first (dependent rows before session)
    try:
        supabase.table("session_assets").delete().eq("session_id", session_id).execute()
        log_step("db_delete", table="session_assets", op="by_session", session_id=session_id)
    except Exception as e:
        logger.warning("Error deleting session_assets for session %s: %s", session_id, e)

    supabase.table("jobs").delete().eq("session_id", session_id).eq("user_id", user_id).execute()
    log_step("db_delete", table="jobs", op="by_session", session_id=session_id)
    supabase.table("messages").delete().eq("session_id", session_id).execute()
    log_step("db_delete", table="messages", op="by_session", session_id=session_id)
    
    res = (
        supabase.table("sessions")
        .delete()
        .eq("id", session_id)
        .eq("user_id", user_id)
        .execute()
    )
    log_step("db_delete", table="sessions", session_id=session_id)
    invalidate_session_owner(session_id, str(user_id))

    # 2. Async / non-blocking storage cleanup AFTER DB deletion succeeds
    background_tasks.add_task(cleanup_session_storage, session_id)

    return {"status": "ok", "deleted_id": session_id}


@router.patch("/{session_id}/title")
async def update_session_title(title: str, session_id: str, user_id=Depends(get_current_user_id)):
    """Cập nhật tiêu đề phiên chat (Rename a chat session)"""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database service currently unavailable.")
    
    res = (
        supabase.table("sessions")
        .update({"title": title})
        .eq("id", session_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Session not found or not owned by user.")
    log_step("db_update", table="sessions", op="title", session_id=session_id)
    return res.data[0]


@router.get("/{session_id}/assets", response_model=List[dict])
async def get_session_assets(session_id: str, user_id=Depends(get_current_user_id)):
    """Lấy danh sách video đã render trong session (Get versioned assets for a session)"""
    supabase = get_supabase()

    def owns() -> bool:
        res = (
            supabase.table("sessions")
            .select("id")
            .eq("id", session_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(res.data)

    if not session_owned_by_user(session_id, str(user_id), owns):
        raise HTTPException(
            status_code=403, detail="Forbidden: You do not own this session."
        )

    res = (
        supabase.table("session_assets")
        .select("*")
        .eq("session_id", session_id)
        .order("version", desc=True)
        .execute()
    )
    log_step("db_select", table="session_assets", op="list", session_id=session_id)
    return res.data
