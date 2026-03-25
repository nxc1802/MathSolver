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
    
    # 2. Run Manim and get paths (video and image)
    paths = renderer.run_manim(script, job_id)
    video_path = paths.get("video")
    image_path = paths.get("image")
    
    if not video_path or not os.path.exists(video_path):
        raise Exception(f"Manim rendering failed for job {job_id}")

    # 3. Upload to Supabase
    bucket_name = os.getenv("SUPABASE_BUCKET", "video")
    
    # Upload Video
    with open(video_path, "rb") as f:
        supabase.storage.from_(bucket_name).upload(
            path=f"{job_id}.mp4",
            file=f.read(),
            file_options={"content-type": "video/mp4"}
        )
    video_url = supabase.storage.from_(bucket_name).get_public_url(f"{job_id}.mp4")

    # Upload Image (if exists)
    image_url = ""
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            supabase.storage.from_(bucket_name).upload(
                path=f"{job_id}.png",
                file=f.read(),
                file_options={"content-type": "image/png"}
            )
        image_url = supabase.storage.from_(bucket_name).get_public_url(f"{job_id}.png")

    # 4. Cleanup local files
    for p in [video_path, image_path]:
        if p and os.path.exists(p):
            os.remove(p)
    
    # 5. Update Job status and Final Result in Supabase Database
    final_result = data.copy()
    final_result["video_url"] = video_url
    final_result["image_url"] = image_url
    
    supabase.table("jobs").update({
        "status": "success",
        "result": final_result
    }).eq("id", job_id).execute()
    
    return {"video_url": video_url, "image_url": image_url}
