"""Run solve pipeline (OCR + agents) for a session job — shared by Celery worker and tests."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.errors import format_error_for_user
from app.job_events import publish_job_ws_event
from app.models.schemas import SolveRequest
from app.supabase_client import get_supabase

if TYPE_CHECKING:
    from agents.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

_orch: "Orchestrator | None" = None


def get_job_orchestrator() -> "Orchestrator":
    global _orch
    if _orch is None:
        from agents.orchestrator import Orchestrator

        _orch = Orchestrator()
    return _orch


async def _emit_job_ws(job_id: str, data: dict) -> None:
    """Notify WS clients: Redis bridge when available, else in-process notify_status."""
    if publish_job_ws_event(job_id, data):
        return
    from app.websocket_manager import notify_status

    await notify_status(job_id, data)


async def run_solve_session_job(
    job_id: str,
    session_id: str,
    request: SolveRequest,
    user_id: str,
) -> None:
    """Load history, run orchestrator, update jobs/messages, emit WS events."""
    orchestrator = get_job_orchestrator()

    async def status_update(status: str):
        await _emit_job_ws(job_id, {"status": status})

    supabase = get_supabase()
    try:
        history_res = (
            supabase.table("messages")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
        )
        history = history_res.data if history_res.data else []

        result = await orchestrator.run(
            request.text,
            request.image_url,
            job_id=job_id,
            session_id=session_id,
            status_callback=status_update,
            history=history,
        )

        status = result.get("status", "error") if "error" not in result else "error"

        supabase.table("jobs").update({"status": status, "result": result}).eq(
            "id", job_id
        ).execute()

        supabase.table("messages").insert(
            {
                "session_id": session_id,
                "role": "assistant",
                "type": "analysis" if "error" not in result else "error",
                "content": (
                    result.get("semantic_analysis", "Đã có lỗi xảy ra.")
                    if "error" not in result
                    else result["error"]
                ),
                "metadata": {
                    "job_id": job_id,
                    "coordinates": result.get("coordinates"),
                    "geometry_dsl": result.get("geometry_dsl"),
                    "polygon_order": result.get("polygon_order", []),
                    "drawing_phases": result.get("drawing_phases", []),
                    "circles": result.get("circles", []),
                    "lines": result.get("lines", []),
                    "rays": result.get("rays", []),
                    "solution": result.get("solution"),
                    "is_3d": result.get("is_3d", False),
                },
            }
        ).execute()

        await _emit_job_ws(job_id, {"status": status, "result": result})

    except Exception as e:
        logger.exception("Error processing session job %s", job_id)
        error_msg = format_error_for_user(e)
        supabase = get_supabase()
        supabase.table("jobs").update(
            {"status": "error", "result": {"error": str(e)}}
        ).eq("id", job_id).execute()
        supabase.table("messages").insert(
            {
                "session_id": session_id,
                "role": "assistant",
                "type": "error",
                "content": error_msg,
                "metadata": {"job_id": job_id},
            }
        ).execute()
        await _emit_job_ws(job_id, {"status": "error", "error": error_msg})


def run_solve_session_job_sync(
    job_id: str,
    session_id: str,
    user_id: str,
    text: str,
    image_url: str | None,
) -> None:
    """Celery entrypoint (sync): build SolveRequest and asyncio.run the async job."""
    import asyncio

    req = SolveRequest(text=text, image_url=image_url)
    asyncio.run(run_solve_session_job(job_id, session_id, req, user_id))
