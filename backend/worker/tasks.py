import os
from .celery_app import celery_app
from agents.renderer_agent import RendererAgent
from app.supabase_client import get_supabase

@celery_app.task(name="worker.tasks.render_geometry_video")
def render_geometry_video(job_id: str, data: dict):
    renderer = RendererAgent()
    supabase = get_supabase()
    
    # 1. Generate Manim script
    script = renderer.generate_manim_script(data)
    
    # 2. Run Manim and get video file path
    video_path = renderer.run_manim(script, job_id)
    
    if not video_path or not os.path.exists(video_path):
        raise Exception(f"Manim rendering failed for job {job_id}")

    with open(video_path, "rb") as f:
        video_content = f.read()
    
    # 3. Upload to Supabase
    bucket_name = os.getenv("SUPABASE_BUCKET", "video")
    file_name = f"{job_id}.mp4"
    
    supabase.storage.from_(bucket_name).upload(
        path=file_name,
        file=video_content,
        file_options={"content-type": "video/mp4"}
    )
    
    # 4. Cleanup local file
    if os.path.exists(video_path):
        os.remove(video_path)
    
    # 5. Get Public URL
    video_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
    
    # 5. Update Job status and Final Result in Supabase Database
    final_result = data.copy()
    final_result["video_url"] = video_url
    
    supabase.table("jobs").update({
        "status": "success",
        "result": final_result
    }).eq("id", job_id).execute()
    
    # 6. Lưu tin nhắn vào history (nếu có session_id)
    session_id = data.get("session_id")
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
                "geometry_dsl": data.get("geometry_dsl")
            }
        }).execute()
    
    return video_url
