import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    # Sử dụng Service Role Key cho Backend để có toàn quyền quản lý DB (Bypass RLS)
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    return create_client(url, key)
