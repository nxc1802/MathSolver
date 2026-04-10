import uuid
import sys
import os

# Add parent dir to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.supabase_client import get_supabase

def prepare():
    supabase = get_supabase()
    # Use existing valid user to avoid foreign key violation on sessions.user_id
    user_id = "8cd3adb0-7964-4575-949c-d0cadcd8b679"
    session_id = str(uuid.uuid4())
    
    print(f"Using existing test user: {user_id}")
    
    print(f"Creating fresh test session: {session_id}")
    # Insert session
    supabase.table("sessions").insert({
        "id": session_id,
        "user_id": user_id,
        "title": f"Fresh API Test {session_id[:8]}"
    }).execute()
    
    # Return IDs for the test script
    print(f"RESULT:USER_ID={user_id}")
    print(f"RESULT:SESSION_ID={session_id}")

if __name__ == "__main__":
    prepare()
