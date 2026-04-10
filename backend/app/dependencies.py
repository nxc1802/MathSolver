from fastapi import HTTPException, Header

from app.supabase_client import get_supabase, get_supabase_for_user_jwt


async def get_current_user_id(authorization: str = Header(...)):
    """
    Authenticate user using Supabase JWT.
    Expected Header: Authorization: Bearer <token>
    """
    import os
    if os.getenv("ALLOW_TEST_BYPASS") == "true" and authorization.startswith("Test "):
        return authorization.split(" ")[1]

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing or invalid. Use 'Bearer <token>'",
        )

    token = authorization.split(" ")[1]
    supabase = get_supabase()

    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid session or token.")

        return user_response.user.id
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


async def get_authenticated_supabase(authorization: str = Header(...)):
    """
    Supabase client that carries the user's JWT (anon key + Authorization header).
    Use for routes that should respect Row Level Security; pair with app logic as needed.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing or invalid. Use 'Bearer <token>'",
        )

    token = authorization.split(" ")[1]
    supabase = get_supabase()

    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid session or token.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

    try:
        return get_supabase_for_user_jwt(token)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
