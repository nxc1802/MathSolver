"""Verify assistant message metadata after process_session_job (Supabase + LLM)."""

from __future__ import annotations

import os
import uuid

import pytest
from dotenv import load_dotenv

load_dotenv()

from app.models.schemas import SolveRequest
from app.routers.solve import process_session_job
from app.supabase_client import get_supabase


@pytest.mark.real_api
@pytest.mark.asyncio
async def test_metadata_persistence_after_solve():
    if not os.getenv("SUPABASE_SERVICE_ROLE_KEY") and not os.getenv("SUPABASE_KEY"):
        pytest.skip("Supabase credentials not configured")

    user_id = os.getenv("TEST_SUPABASE_USER_ID") or os.getenv("TEST_USER_ID")
    if not user_id:
        pytest.skip("TEST_SUPABASE_USER_ID or TEST_USER_ID required")

    supabase = get_supabase()
    session_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    supabase.table("sessions").insert(
        {
            "id": session_id,
            "user_id": user_id,
            "title": "pytest metadata session",
        }
    ).execute()

    request = SolveRequest(
        text="Cho hình chữ nhật ABCD có AB=10, AD=20. Vẽ đường thẳng d đi qua A và B.",
        request_video=False,
    )

    supabase.table("jobs").insert(
        {
            "id": job_id,
            "user_id": user_id,
            "session_id": session_id,
            "status": "processing",
            "input_text": request.text,
        }
    ).execute()
    supabase.table("messages").insert(
        {
            "session_id": session_id,
            "role": "user",
            "type": "text",
            "content": request.text,
            "metadata": {},
        }
    ).execute()

    try:
        await process_session_job(job_id, session_id, request, user_id)

        res = (
            supabase.table("messages")
            .select("metadata")
            .eq("session_id", session_id)
            .eq("role", "assistant")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        assert res.data, "Expected at least one assistant message"
        metadata = res.data[0].get("metadata") or {}
        required = [
            "job_id",
            "coordinates",
            "polygon_order",
            "drawing_phases",
            "circles",
            "lines",
            "rays",
        ]
        missing = [f for f in required if f not in metadata]
        assert not missing, f"Missing metadata fields: {missing}"
        assert metadata.get("job_id") == job_id
    finally:
        try:
            supabase.table("messages").delete().eq("session_id", session_id).execute()
        except Exception:
            pass
        try:
            supabase.table("jobs").delete().eq("session_id", session_id).execute()
        except Exception:
            pass
        try:
            supabase.table("sessions").delete().eq("id", session_id).execute()
        except Exception:
            pass
