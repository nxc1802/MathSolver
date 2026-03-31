from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_current_user_id
from app.supabase_client import get_supabase
from typing import List
import uuid

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions"])

@router.get("", response_model=List[dict])
async def list_sessions(user_id=Depends(get_current_user_id)):
    """Danh sách các phiên chat của người dùng (List user's chat sessions)"""
    supabase = get_supabase()
    res = supabase.table("sessions").select("*") \
        .eq("user_id", user_id) \
        .order("updated_at", desc=True) \
        .execute()
    return res.data

@router.post("", response_model=dict)
async def create_session(user_id=Depends(get_current_user_id)):
    """Tạo một phiên chat mới (Create a new chat session)"""
    supabase = get_supabase()
    res = supabase.table("sessions").insert({
        "user_id": user_id,
        "title": "Bài toán mới"
    }).execute()
    return res.data[0]

@router.get("/{session_id}/messages", response_model=List[dict])
async def get_session_messages(session_id: str, user_id=Depends(get_current_user_id)):
    """Lấy toàn bộ lịch sử tin nhắn của một phiên (Get chat history for a session)"""
    supabase = get_supabase()
    # Kiểm tra quyền sở hữu session
    check = supabase.table("sessions").select("id").eq("id", session_id).eq("user_id", user_id).execute()
    if not check.data:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this session.")

    res = supabase.table("messages").select("*") \
        .eq("session_id", session_id) \
        .order("created_at", desc=False) \
        .execute()
    return res.data

@router.delete("/{session_id}")
async def delete_session(session_id: str, user_id=Depends(get_current_user_id)):
    """Xóa một phiên chat (Delete a chat session)"""
    supabase = get_supabase()
    res = supabase.table("sessions").delete() \
        .eq("id", session_id) \
        .eq("user_id", user_id) \
        .execute()
    return {"status": "ok", "deleted_id": session_id}

@router.patch("/{session_id}/title")
async def update_session_title(title: str, session_id: str, user_id=Depends(get_current_user_id)):
    """Cập nhật tiêu đề phiên chat (Rename a chat session)"""
    supabase = get_supabase()
    res = supabase.table("sessions").update({"title": title}) \
        .eq("id", session_id) \
        .eq("user_id", user_id) \
        .execute()
    return res.data[0]
