from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_current_user_id
from app.supabase_client import get_supabase
from app.models.schemas import UserProfile
import uuid

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

@router.get("/me")
async def get_me(user_id=Depends(get_current_user_id)):
    """获取当前登录用户的信息 (Retrieve current user profile)"""
    supabase = get_supabase()
    res = supabase.table("profiles").select("*").eq("id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return res.data[0]

@router.patch("/me")
async def update_me(data: dict, user_id=Depends(get_current_user_id)):
    """Cập nhật profile hiện tại (Update current profile)"""
    supabase = get_supabase()
    res = supabase.table("profiles").update(data).eq("id", user_id).execute()
    return res.data[0]
