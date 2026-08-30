import logging
import os
from .celery_app import celery_app
from geometry_render.renderer import RendererAgent
from app.supabase_client import get_supabase
from .asset_manager import upload_session_asset

logger = logging.getLogger(__name__)

@celery_app.task(name="worker.tasks.render_geometry_video")
def render_geometry_video(job_id: str, data: dict):
    renderer = RendererAgent()
    supabase = get_supabase()
    session_id = data.get("session_id")
    video_local_path = None
    
    try:
        # 1. Generate Manim script
        script = renderer.generate_manim_script(data)
        
        # 2. Run Manim and get local video file path
        video_local_path = renderer.run_manim(script, job_id)
        
        if not video_local_path or not os.path.exists(video_local_path):
            raise Exception(f"Manim rendering failed for job {job_id}")

        with open(video_local_path, "rb") as f:
            video_content = f.read()
        
        # 3. Upload to Supabase using Asset Manager (Versioning)
        if session_id:
            storage_path, video_url = upload_session_asset(
                session_id=session_id,
                job_id=job_id,
                file_bytes=video_content,
                asset_type="video",
                ext="mp4"
            )
        else:
            # Legacy fallback
            bucket_name = os.getenv("SUPABASE_BUCKET", "video")
            file_name = f"{job_id}.mp4"
            if supabase:
                supabase.storage.from_(bucket_name).upload(path=file_name, file=video_content)
                video_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
            else:
                video_url = f"local://{file_name}"
        
        # 4. Update Job status and Final Result in Supabase Database
        final_result = data.copy()
        final_result["video_url"] = video_url
        
        if supabase:
            supabase.table("jobs").update({
                "status": "success",
                "result": final_result
            }).eq("id", job_id).execute()
            
            # 5. Save message history (Assistant answer)
            if session_id:
                supabase.table("messages").insert({
                    "session_id": session_id,
                    "role": "assistant",
                    "type": "analysis",
                    "content": data.get("semantic_analysis", "🎬 Video minh họa đã sẵn sàng."),
                    "metadata": {
                        "job_id": job_id,
                        "video_url": video_url,
                        "coordinates": data.get("coordinates"),
                        "geometry_dsl": data.get("geometry_dsl"),
                        "polygon_order": data.get("polygon_order", []),
                        "drawing_phases": data.get("drawing_phases", []),
                        "circles": data.get("circles", []),
                        "lines": data.get("lines", []),
                        "rays": data.get("rays", []),
                    }
                }).execute()
        
        return video_url
    except Exception as e:
        logger.exception("Error rendering video for job %s: %s", job_id, e)
        if supabase:
            try:
                supabase.table("jobs").update({
                    "status": "error",
                    "result": {"error": f"Rendering error: {str(e)}"}
                }).eq("id", job_id).execute()
                if session_id:
                    supabase.table("messages").insert({
                        "session_id": session_id,
                        "role": "assistant",
                        "type": "error",
                        "content": f"Không thể dựng video minh họa: {str(e)}",
                        "metadata": {"job_id": job_id},
                    }).execute()
            except Exception as db_err:
                logger.error("Failed to record error in DB for job %s: %s", job_id, db_err)
        raise e
    finally:
        # 6. Cleanup local file
        if video_local_path and os.path.exists(video_local_path):
            try:
                os.remove(video_local_path)
            except Exception:
                pass
