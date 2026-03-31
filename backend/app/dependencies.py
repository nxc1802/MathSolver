from fastapi import Depends, HTTPException, Header
from app.supabase_client import get_supabase
from typing import Optional

async def get_current_user_id(authorization: str = Header(...)):
    """
    Authenticate user using Supabase JWT.
    Expected Header: Authorization: Bearer <token>
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, 
            detail="Authorization header missing or invalid. Use 'Bearer <token>'"
        )

    token = authorization.split(" ")[1]
    supabase = get_supabase()

    try:
        # Verify the JWT with Supabase Auth
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid session or token.")
        
        return user_response.user.id
    except Exception as e:
        # Potentially log the error
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

async def get_authenticated_supabase(authorization: str = Header(...)):
    """
    Return a supabase client for the current user session (optional, 
    usually backend uses service role but RLS requires user context).
    Note: Supabase-py doesn't easily 'proxy' the user token for all calls automatically
    like the JS client without re-initializing or setting headers.
    """
    # For now, we use the global service role client but check UID in logic.
    return get_supabase()
