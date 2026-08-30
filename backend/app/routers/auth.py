from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_current_user_id
from app.supabase_client import get_supabase
from app.models.schemas import UserProfile
import uuid

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

@router.get("/me")
async def get_me(user_id=Depends(get_current_user_id)):
    """Lấy thông tin profile người dùng hiện tại (Retrieve current user profile)."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database service currently unavailable.")
    
    res = supabase.table("profiles").select("*").eq("id", user_id).execute()
    if res.data:
        return res.data[0]
    
    # Auto-provision basic profile if trigger didn't run or dev test user
    try:
        insert_res = (
            supabase.table("profiles")
            .insert({"id": str(user_id), "display_name": "Người dùng", "avatar_url": None})
            .execute()
        )
        if insert_res.data:
            return insert_res.data[0]
    except Exception:
        pass

    raise HTTPException(status_code=404, detail="Profile not found.")

@router.patch("/me")
async def update_me(data: dict, user_id=Depends(get_current_user_id)):
    """Cập nhật profile hiện tại (Update current profile)."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database service currently unavailable.")
    
    # Sanitize and only allow updating safe profile fields
    allowed_fields = {"display_name", "avatar_url"}
    update_data = {k: v for k, v in data.items() if k in allowed_fields}
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields provided for update (allowed: display_name, avatar_url).")
    
    res = supabase.table("profiles").update(update_data).eq("id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Profile not found to update.")
    return res.data[0]
