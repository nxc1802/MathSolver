import os
import uuid
import logging
from typing import Tuple
from app.supabase_client import get_supabase

logger = logging.getLogger(__name__)

def get_next_version(session_id: str, asset_type: str = "video") -> int:
    """
    Query session_assets to find the latest version for this session/type.
    """
    supabase = get_supabase()
    try:
        res = (
            supabase.table("session_assets")
            .select("version")
            .eq("session_id", session_id)
            .eq("asset_type", asset_type)
            .order("version", desc=True)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]["version"] + 1
        return 1
    except Exception as e:
        logger.error(f"Error fetching version: {e}")
        return 1

def upload_session_asset(
    session_id: str, 
    job_id: str, 
    file_bytes: bytes, 
    asset_type: str, 
    ext: str
) -> Tuple[str, str]:
    """
    Upload file to Supabase Storage with versioned path and record in session_assets.
    Returns (storage_path, public_url).
    """
    supabase = get_supabase()
    if not supabase:
        logger.error("[AssetManager] Failed to initialize Supabase client")
        raise RuntimeError("Supabase client internal error")
        
    bucket_name = os.getenv("SUPABASE_BUCKET", "video")
    
    version = get_next_version(session_id, asset_type)
    
    # Structure: sessions/{session_id}/{asset_type}_v{version}_{job_id}.{ext}
    file_name = f"{asset_type}_v{version}_{job_id}.{ext}"
    storage_path = f"sessions/{session_id}/{file_name}"
    
    # 1. Upload to Storage
    content_type = "video/mp4" if ext == "mp4" else "image/png"
    supabase.storage.from_(bucket_name).upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": content_type}
    )
    
    # 2. Get Public URL
    public_url = supabase.storage.from_(bucket_name).get_public_url(storage_path)
    
    # 3. Record in DB
    supabase.table("session_assets").insert({
        "session_id": session_id,
        "job_id": job_id,
        "asset_type": asset_type,
        "storage_path": storage_path,
        "public_url": public_url,
        "version": version
    }).execute()
    
    return storage_path, public_url
