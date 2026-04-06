import os
import sys
import json
from dotenv import load_dotenv

# Ensure we can import from backend
sys.path.append(os.getcwd())

from app.supabase_client import get_supabase
from worker.tasks import render_geometry_video

def test_celery_task_directly():
    load_dotenv()
    
    # Mock data for a square
    data = {
        "session_id": "88888888-8888-8888-8888-888888888888", # Fake uuid
        "coordinates": {
            "A": [0, 0],
            "B": [5, 0],
            "C": [5, 5],
            "D": [0, 5]
        },
        "polygon_order": ["A", "B", "C", "D"],
        "drawing_phases": [
            {
                "phase": 1,
                "label": "Base",
                "points": ["A", "B", "C", "D"],
                "segments": [["A","B"],["B","C"],["C","D"],["D","A"]]
            }
        ],
        "semantic_analysis": "Test squere video rendering."
    }
    
    job_id = f"manual-direct-test-{int(os.time.time()) if hasattr(os, 'time') else 123}"
    # Just use a static ID or similar
    import time
    job_id = f"manual-test-{int(time.time())}"

    print(f"🚀 Running render_geometry_video directly for job {job_id}...")
    
    try:
        # We need to mock Supabase calls if we don't want to actually hit the DB,
        # but here we WANT to test the real task logic.
        # This will fail on DB update if job_id doesn't exist in 'jobs' table.
        # So let's create a dummy job first.
        supabase = get_supabase()
        supabase.table("jobs").insert({
            "id": job_id,
            "user_id": None,
            "status": "processing",
            "type": "solve"
        }).execute()
        
        # Run the task function directly (not via .delay)
        video_url = render_geometry_video(job_id, data)
        
        if video_url:
            print(f"✅ SUCCESS! Video URL: {video_url}")
        else:
            print("❌ FAIL: No video URL returned.")
            
    except NameError as e:
        print(f"❌ NameError Caught: {e}")
    except Exception as e:
        print(f"❌ Error during manual task execution: {e}")

if __name__ == "__main__":
    test_celery_task_directly()
