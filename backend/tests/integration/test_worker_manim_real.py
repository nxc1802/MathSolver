"""Real Manim render + Supabase upload via render_geometry_video (opt-in)."""

from __future__ import annotations

import os
import uuid

import pytest


@pytest.mark.real_worker_manim
@pytest.mark.slow
def test_render_geometry_video_uploads_and_updates_job():
    if os.getenv("MOCK_VIDEO", "").lower() == "true":
        pytest.skip("MOCK_VIDEO must be unset/false for real Manim")

    if os.getenv("RUN_REAL_WORKER_MANIM", "").lower() not in ("1", "true", "yes"):
        pytest.skip("Set RUN_REAL_WORKER_MANIM=1 to run Manim + storage integration")

    if not os.getenv("SUPABASE_SERVICE_ROLE_KEY") and not os.getenv("SUPABASE_KEY"):
        pytest.skip("Supabase credentials required")

    from app.supabase_client import get_supabase
    from worker.tasks import render_geometry_video

    supabase = get_supabase()
    # Same default as scripts/prepare_api_test.py when TEST_SUPABASE_USER_ID is unset.
    default_test_user = "8cd3adb0-7964-4575-949c-d0cadcd8b679"
    user_id = (
        os.getenv("TEST_SUPABASE_USER_ID") or os.getenv("TEST_USER_ID") or default_test_user
    ).strip()
    if not user_id:
        pytest.skip("TEST_SUPABASE_USER_ID or TEST_USER_ID required for session FK")

    session_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    supabase.table("sessions").insert(
        {
            "id": session_id,
            "user_id": user_id,
            "title": "pytest manim integration",
        }
    ).execute()

    supabase.table("jobs").insert(
        {
            "id": job_id,
            "user_id": user_id,
            "session_id": session_id,
            "status": "processing",
            "input_text": "pytest render_geometry_video",
        }
    ).execute()

    data = {
        "session_id": session_id,
        "coordinates": {
            "A": [0, 0],
            "B": [5, 0],
            "C": [5, 5],
            "D": [0, 5],
        },
        "polygon_order": ["A", "B", "C", "D"],
        "drawing_phases": [
            {
                "phase": 1,
                "label": "Base",
                "points": ["A", "B", "C", "D"],
                "segments": [["A", "B"], ["B", "C"], ["C", "D"], ["D", "A"]],
            }
        ],
        "semantic_analysis": "pytest square video",
        "geometry_dsl": "POINT(A)\nPOINT(B)\nLENGTH(AB,5)",
    }

    try:
        video_url = render_geometry_video.run(job_id, data)
        assert video_url and isinstance(video_url, str), "Expected public video URL"

        job_res = supabase.table("jobs").select("status, result").eq("id", job_id).execute()
        assert job_res.data and job_res.data[0].get("status") == "success"
        assert job_res.data[0].get("result", {}).get("video_url")
    finally:
        try:
            supabase.table("session_assets").delete().eq("job_id", job_id).execute()
        except Exception:
            pass
        try:
            supabase.table("messages").delete().eq("session_id", session_id).execute()
        except Exception:
            pass
        try:
            supabase.table("jobs").delete().eq("id", job_id).execute()
        except Exception:
            pass
        try:
            supabase.table("sessions").delete().eq("id", session_id).execute()
        except Exception:
            pass
