"""Celery Tasks & Async Worker Handlers for MathSolver Solve & Render Pipeline."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from typing import Any, Dict, Optional

from app.celery_app import celery_app
from app.errors import format_error_for_user
from app.logutil import log_pipeline_failure, log_pipeline_success, log_step
from app.models.job_state import JobStatus, JobStage, JobStateMachine
from app.supabase_client import get_supabase
from app.websocket_manager import notify_status

logger = logging.getLogger(__name__)


async def async_solve_session_job(
    job_id: str,
    session_id: str,
    text: str,
    image_url: Optional[str] = None,
    user_id: Optional[str] = None,
    client_message_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute the full geometry solve pipeline for a session job."""
    from app.routers.solve import get_orchestrator

    supabase = get_supabase()

    async def status_callback(status: str, stage: Optional[str] = None, progress: Optional[int] = None):
        norm_status = JobStateMachine.normalize_status(status)
        norm_stage = JobStateMachine.normalize_stage(stage or status)
        update_data = {"status": norm_status.value}
        if norm_stage:
            update_data["stage"] = norm_stage.value
        if progress is not None:
            update_data["progress"] = progress

        if supabase:
            try:
                supabase.table("jobs").update(update_data).eq("id", job_id).execute()
            except Exception as e:
                logger.debug("Failed updating job status in DB: %s", e)

        await notify_status(job_id, {
            "status": norm_status.value,
            "stage": norm_stage.value if norm_stage else None,
            "progress": progress,
            "job_id": job_id,
        })

    try:
        # Initial status update
        await status_callback("processing", stage="ocr", progress=15)

        history = []
        if supabase and session_id:
            try:
                history_res = (
                    supabase.table("messages")
                    .select("*")
                    .eq("session_id", session_id)
                    .order("created_at", desc=False)
                    .execute()
                )
                history = history_res.data if history_res.data else []
            except Exception as e:
                logger.warning("Could not fetch message history: %s", e)

        result = await get_orchestrator().run(
            text,
            image_url,
            job_id=job_id,
            session_id=session_id,
            status_callback=lambda st: status_callback(st),
            history=history,
        )

        has_error = "error" in result and result.get("error")
        final_status = JobStatus.FAILED if has_error else JobStatus.COMPLETED

        if supabase:
            supabase.table("jobs").update({
                "status": final_status.value,
                "stage": None,
                "progress": 100 if final_status == JobStatus.COMPLETED else 0,
                "result": result,
            }).eq("id", job_id).execute()

            # Idempotency check: Ensure assistant message for this job is not inserted twice
            existing_msg = (
                supabase.table("messages")
                .select("id")
                .eq("session_id", session_id)
                .filter("metadata->>job_id", "eq", job_id)
                .execute()
            )

            if not existing_msg.data or len(existing_msg.data) == 0:
                supabase.table("messages").insert({
                    "session_id": session_id,
                    "role": "assistant",
                    "type": "error" if has_error else "analysis",
                    "content": (
                        result.get("error", "Đã có lỗi xảy ra.")
                        if has_error
                        else result.get("semantic_analysis", "Giải bài toán hoàn tất.")
                    ),
                    "metadata": {
                        "job_id": job_id,
                        "client_message_id": client_message_id,
                        "coordinates": result.get("coordinates"),
                        "geometry_dsl": result.get("geometry_dsl"),
                        "polygon_order": result.get("polygon_order", []),
                        "drawing_phases": result.get("drawing_phases", []),
                        "circles": result.get("circles", []),
                        "solids": result.get("solids", []),
                        "faces": result.get("faces", []),
                        "lines": result.get("lines", []),
                        "rays": result.get("rays", []),
                        "visualization_graph": result.get("visualization_graph"),
                        "auxiliary": result.get("auxiliary", []),
                        "solution": result.get("solution"),
                        "is_3d": result.get("is_3d", False),
                    },
                }).execute()

        await notify_status(job_id, {
            "status": final_status.value,
            "stage": None,
            "progress": 100 if final_status == JobStatus.COMPLETED else 0,
            "job_id": job_id,
            "result": result,
        })
        log_pipeline_success("job_complete", job_id=job_id, session_id=session_id)
        return result

    except Exception as e:
        logger.exception("Error in async_solve_session_job for job %s: %s", job_id, e)
        error_msg = format_error_for_user(e)
        if supabase:
            try:
                supabase.table("jobs").update({
                    "status": JobStatus.FAILED.value,
                    "progress": 0,
                    "result": {"error": str(e)},
                }).eq("id", job_id).execute()

                supabase.table("messages").insert({
                    "session_id": session_id,
                    "role": "assistant",
                    "type": "error",
                    "content": error_msg,
                    "metadata": {"job_id": job_id, "client_message_id": client_message_id},
                }).execute()
            except Exception as dbe:
                logger.error("DB error recording failure for job %s: %s", job_id, dbe)

        await notify_status(job_id, {
            "status": JobStatus.FAILED.value,
            "job_id": job_id,
            "error": error_msg,
            "progress": 0,
        })
        log_pipeline_failure("job_failed", job_id=job_id, error=str(e))
        return {"status": "error", "error": error_msg}


async def async_render_video_job(job_id: str, session_id: str, geometry_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Manim video rendering job for a session."""
    from manim_client import ManimClient, build_visualization_spec
    from manim_client.schemas import ErrorCode

    await notify_status(job_id, {
        "status": JobStatus.QUEUED.value,
        "stage": JobStage.RENDERING.value,
        "job_id": job_id,
        "progress": 10,
    })
    supabase = get_supabase()

    try:
        manim_url = os.getenv("MANIM_SERVICE_URL", "https://cuong2004-manim-agent.hf.space")
        manim_token = os.getenv("MANIM_INTERNAL_TOKEN")
        client = ManimClient(base_url=manim_url, internal_token=manim_token)

        vis_spec = build_visualization_spec(geometry_data)
        resp = await client.submit_render_job(vis_spec)

        if resp.status == "failed":
            err_code = resp.get_error_code() or ErrorCode.MANIM_REQUEST_FAILED
            err_msg = resp.get_error_message() or "Không thể gửi yêu cầu tạo video tới máy chủ Manim."
            if supabase:
                supabase.table("jobs").update({
                    "status": JobStatus.FAILED.value,
                    "result": {"error": {"code": err_code, "message": err_msg}},
                }).eq("id", job_id).execute()
                if session_id:
                    supabase.table("messages").insert({
                        "session_id": session_id,
                        "role": "assistant",
                        "type": "error",
                        "content": f"Không thể tạo video: {err_msg}",
                        "metadata": {"job_id": job_id, "error_code": err_code},
                    }).execute()
            await notify_status(job_id, {
                "status": JobStatus.FAILED.value,
                "job_id": job_id,
                "error": err_msg,
                "error_code": err_code,
            })
            return {"status": "error", "error": err_msg}

        manim_job_id = resp.job_id
        if supabase:
            supabase.table("jobs").update({
                "status": JobStatus.PROCESSING.value,
                "stage": JobStage.RENDERING.value,
                "progress": 40,
                "result": {"manim_job_id": str(manim_job_id)},
            }).eq("id", job_id).execute()

        await notify_status(job_id, {
            "status": JobStatus.PROCESSING.value,
            "stage": JobStage.RENDERING.value,
            "job_id": job_id,
            "progress": 40,
            "manim_job_id": str(manim_job_id),
        })

        poll_timeout = float(os.getenv("MANIM_POLL_TIMEOUT", "600.0"))
        status_resp = await client.wait_for_completion(manim_job_id, poll_interval=3.0, max_wait=poll_timeout)
        video_url = status_resp.video_url

        if status_resp.status == "failed" or not video_url:
            err_code = status_resp.get_error_code() or ErrorCode.MANIM_RENDER_FAILED
            err_msg = status_resp.get_error_message() or "Tiến trình dựng video Manim thất bại."
            if supabase:
                supabase.table("jobs").update({
                    "status": JobStatus.FAILED.value,
                    "result": {"error": {"code": err_code, "message": err_msg}},
                }).eq("id", job_id).execute()
                if session_id:
                    supabase.table("messages").insert({
                        "session_id": session_id,
                        "role": "assistant",
                        "type": "error",
                        "content": f"Không thể tạo video: {err_msg}",
                        "metadata": {"job_id": job_id, "error_code": err_code},
                    }).execute()
            await notify_status(job_id, {
                "status": JobStatus.FAILED.value,
                "job_id": job_id,
                "error": err_msg,
                "error_code": err_code,
            })
            return {"status": "error", "error": err_msg}

        final_result = geometry_data.copy()
        final_result["video_url"] = video_url
        final_result["manim_job_id"] = str(manim_job_id)

        if supabase:
            supabase.table("jobs").update({
                "status": JobStatus.COMPLETED.value,
                "progress": 100,
                "result": final_result,
            }).eq("id", job_id).execute()

            # Versioned asset recording
            try:
                asset_version = 1
                v_res = supabase.table("session_assets").select("version").eq("session_id", session_id).eq("asset_type", "video").order("version", desc=True).limit(1).execute()
                if v_res.data and len(v_res.data) > 0:
                    asset_version = v_res.data[0]["version"] + 1

                supabase.table("session_assets").insert({
                    "session_id": session_id,
                    "job_id": job_id,
                    "asset_type": "video",
                    "storage_path": video_url,
                    "public_url": video_url,
                    "version": asset_version,
                }).execute()
            except Exception as e:
                logger.warning("Could not record session_asset video row: %s", e)

            if session_id:
                supabase.table("messages").insert({
                    "session_id": session_id,
                    "role": "assistant",
                    "type": "analysis",
                    "content": geometry_data.get("semantic_analysis", "🎬 Video minh họa hình học đã hoàn tất."),
                    "metadata": {
                        "job_id": job_id,
                        "video_url": video_url,
                        "coordinates": geometry_data.get("coordinates"),
                        "geometry_dsl": geometry_data.get("geometry_dsl"),
                        "polygon_order": geometry_data.get("polygon_order", []),
                        "drawing_phases": geometry_data.get("drawing_phases", []),
                        "circles": geometry_data.get("circles", []),
                        "solids": geometry_data.get("solids", []),
                        "faces": geometry_data.get("faces", []),
                        "lines": geometry_data.get("lines", []),
                        "rays": geometry_data.get("rays", []),
                        "visualization_graph": geometry_data.get("visualization_graph"),
                        "auxiliary": geometry_data.get("auxiliary", []),
                        "is_3d": geometry_data.get("is_3d", False),
                    },
                }).execute()

        await notify_status(job_id, {
            "status": JobStatus.COMPLETED.value,
            "job_id": job_id,
            "result": final_result,
            "video_url": video_url,
            "progress": 100,
        })
        return final_result

    except Exception as e:
        logger.exception("Error rendering video for job %s: %s", job_id, e)
        safe_msg = format_error_for_user(e)
        if supabase:
            try:
                supabase.table("jobs").update({
                    "status": JobStatus.FAILED.value,
                    "result": {"error": {"message": safe_msg}},
                }).eq("id", job_id).execute()
                if session_id:
                    supabase.table("messages").insert({
                        "session_id": session_id,
                        "role": "assistant",
                        "type": "error",
                        "content": f"Lỗi render video: {safe_msg}",
                        "metadata": {"job_id": job_id},
                    }).execute()
            except Exception as dbe:
                logger.error("DB error recording render failure: %s", dbe)
        await notify_status(job_id, {"status": JobStatus.FAILED.value, "job_id": job_id, "error": safe_msg})
        return {"status": "error", "error": safe_msg}


@celery_app.task(name="tasks.solve_session_job", bind=True, acks_late=True, max_retries=1)
def solve_session_job_task(
    self,
    job_id: str,
    session_id: str,
    text: str,
    image_url: Optional[str] = None,
    user_id: Optional[str] = None,
    client_message_id: Optional[str] = None,
):
    """Celery task entry point for solve pipeline."""
    return asyncio.run(
        async_solve_session_job(
            job_id=job_id,
            session_id=session_id,
            text=text,
            image_url=image_url,
            user_id=user_id,
            client_message_id=client_message_id,
        )
    )


@celery_app.task(name="tasks.render_video_job", bind=True, acks_late=True, max_retries=1)
def render_video_job_task(self, job_id: str, session_id: str, geometry_data: Dict[str, Any]):
    """Celery task entry point for video render pipeline."""
    return asyncio.run(async_render_video_job(job_id=job_id, session_id=session_id, geometry_data=geometry_data))


def recover_stale_jobs(timeout_seconds: int = 900) -> int:
    """Detect and mark jobs stuck in 'processing' longer than timeout as failed."""
    supabase = get_supabase()
    if not supabase:
        return 0
    try:
        # Note: in production, run via cron or worker startup
        from datetime import datetime, timezone, timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)).isoformat()
        res = (
            supabase.table("jobs")
            .update({
                "status": JobStatus.FAILED.value,
                "result": {"error": "Worker timeout or crash detected. Job marked failed by recovery agent."},
            })
            .eq("status", JobStatus.PROCESSING.value)
            .lt("created_at", cutoff)
            .execute()
        )
        count = len(res.data) if res.data else 0
        if count > 0:
            logger.warning("Recovered %d stale jobs", count)
        return count
    except Exception as e:
        logger.error("Error running recover_stale_jobs: %s", e)
        return 0
