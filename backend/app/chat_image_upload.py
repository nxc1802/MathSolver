"""Validate and upload chat/solve attachment images to Supabase Storage (image bucket)."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Tuple

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def _get_next_image_version(session_id: str) -> int:
    """Same logic as worker.asset_manager.get_next_version for asset_type image."""
    from app.supabase_client import get_supabase

    supabase = get_supabase()
    try:
        res = (
            supabase.table("session_assets")
            .select("version")
            .eq("session_id", session_id)
            .eq("asset_type", "image")
            .order("version", desc=True)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]["version"] + 1
        return 1
    except Exception as e:
        logger.error("Error fetching image version: %s", e)
        return 1

_MAX_BYTES_DEFAULT = 10 * 1024 * 1024

_EXT_TO_MIME: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
}


def _max_bytes() -> int:
    raw = os.getenv("CHAT_IMAGE_MAX_BYTES")
    if raw and raw.isdigit():
        return min(int(raw), 50 * 1024 * 1024)
    return _MAX_BYTES_DEFAULT


def _magic_ok(ext: str, body: bytes) -> bool:
    if len(body) < 12:
        return False
    if ext == ".png":
        return body.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in (".jpg", ".jpeg"):
        return body.startswith(b"\xff\xd8\xff")
    if ext == ".webp":
        return body.startswith(b"RIFF") and body[8:12] == b"WEBP"
    if ext == ".gif":
        return body.startswith(b"GIF87a") or body.startswith(b"GIF89a")
    if ext == ".bmp":
        return body.startswith(b"BM")
    return False


def validate_chat_image_bytes(
    filename: str | None,
    body: bytes,
    declared_content_type: str | None,
) -> Tuple[str, str]:
    """
    Validate size, extension, and magic bytes.
    Returns (extension_with_dot, content_type).
    """
    max_b = _max_bytes()
    if not body:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(body) > max_b:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large (max {max_b // (1024 * 1024)} MB).",
        )

    ext = os.path.splitext(filename or "")[1].lower()
    if not ext:
        ext = ".png"
    if ext not in _EXT_TO_MIME:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: {ext}. Allowed: {', '.join(sorted(_EXT_TO_MIME))}",
        )

    if not _magic_ok(ext, body):
        raise HTTPException(
            status_code=400,
            detail="File content does not match declared image type.",
        )

    mime = _EXT_TO_MIME[ext]
    if declared_content_type:
        decl = declared_content_type.split(";")[0].strip().lower()
        if decl and decl not in ("application/octet-stream", mime) and decl != mime:
            logger.warning(
                "Content-Type mismatch (declared=%s, inferred=%s); using inferred.",
                declared_content_type,
                mime,
            )
    return ext, mime


def upload_session_chat_image(
    session_id: str,
    job_id: str,
    file_bytes: bytes,
    ext_with_dot: str,
    content_type: str,
) -> Dict[str, Any]:
    """
    Upload to SUPABASE_IMAGE_BUCKET (default: image), insert session_assets row.
    Returns dict with public_url, storage_path, version, session_asset_id (if returned).
    """
    from app.supabase_client import get_supabase

    supabase = get_supabase()
    bucket_name = os.getenv("SUPABASE_IMAGE_BUCKET", "image")
    raw_ext = ext_with_dot.lstrip(".").lower()
    version = _get_next_image_version(session_id)
    file_name = f"image_v{version}_{job_id}.{raw_ext}"
    storage_path = f"sessions/{session_id}/{file_name}"

    supabase.storage.from_(bucket_name).upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": content_type},
    )
    public_url = supabase.storage.from_(bucket_name).get_public_url(storage_path)
    if isinstance(public_url, dict):
        public_url = public_url.get("publicUrl") or public_url.get("public_url") or str(public_url)

    row = {
        "session_id": session_id,
        "job_id": job_id,
        "asset_type": "image",
        "storage_path": storage_path,
        "public_url": public_url,
        "version": version,
    }
    ins = supabase.table("session_assets").insert(row).select("id").execute()
    asset_id = None
    if ins.data and len(ins.data) > 0:
        asset_id = ins.data[0].get("id")

    log_data = {
        "public_url": public_url,
        "storage_path": storage_path,
        "version": version,
        "session_asset_id": str(asset_id) if asset_id else None,
    }
    logger.info("Uploaded chat image: %s", log_data)
    return {
        "public_url": public_url,
        "storage_path": storage_path,
        "version": version,
        "session_asset_id": str(asset_id) if asset_id else None,
    }
