import os
import sys
import uuid

from dotenv import load_dotenv

# Add parent dir to path to import app modules
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(_BACKEND_ROOT)
load_dotenv(os.path.join(_BACKEND_ROOT, ".env"))

from app.supabase_client import get_supabase

# Default UUID matches historical dev DB; override with TEST_SUPABASE_USER_ID in .env
_DEFAULT_TEST_USER = "8cd3adb0-7964-4575-949c-d0cadcd8b679"


def prepare():
    supabase = get_supabase()
    user_id = os.environ.get("TEST_SUPABASE_USER_ID", _DEFAULT_TEST_USER).strip()
    session_id = str(uuid.uuid4())
    
    print(f"Using test user (TEST_SUPABASE_USER_ID or default): {user_id}")
    
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
