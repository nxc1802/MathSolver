import os
import logging
from supabase import Client, ClientOptions, create_client
from supabase_auth import SyncMemoryStorage
from dotenv import load_dotenv

load_dotenv()

from app.url_utils import sanitize_env

logger = logging.getLogger(__name__)

_supabase_client = None


def get_supabase() -> Client:
    """Service-role client for server-side operations with lazy init."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    url = sanitize_env(os.getenv("SUPABASE_URL"))
    key = sanitize_env(os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY"))
    if not url or not key:
        logger.warning("[Supabase] SUPABASE_URL or key not configured. Cloud DB operations will be unavailable.")
        return None

    try:
        _supabase_client = create_client(url, key)
        return _supabase_client
    except Exception as e:
        logger.warning("[Supabase] Failed to initialize Supabase client: %s", e)
        return None


def get_supabase_for_user_jwt(access_token: str) -> Client:
    """Client scoped to the logged-in user."""
    url = sanitize_env(os.getenv("SUPABASE_URL"))
    anon = sanitize_env(os.getenv("SUPABASE_ANON_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY"))
    if not url or not anon:
        raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set for user-scoped Supabase access")
    base_opts = ClientOptions(storage=SyncMemoryStorage())
    merged_headers = {**dict(base_opts.headers), "Authorization": f"Bearer {access_token}"}
    opts = ClientOptions(storage=SyncMemoryStorage(), headers=merged_headers)
    return create_client(url, anon, opts)
