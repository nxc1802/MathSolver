import os
from supabase import Client, ClientOptions, create_client
from supabase_auth import SyncMemoryStorage
from dotenv import load_dotenv

load_dotenv()


def get_supabase() -> Client:
    """Service-role client for server-side operations (bypasses RLS when policies expect service role)."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY) must be set"
        )
    return create_client(url, key)


def get_supabase_for_user_jwt(access_token: str) -> Client:
    """
    Client scoped to the logged-in user: PostgREST sends the user's JWT so RLS applies.
    Use SUPABASE_ANON_KEY (publishable), not the service role key.
    """
    url = os.getenv("SUPABASE_URL")
    anon = os.getenv("SUPABASE_ANON_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if not url or not anon:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_ANON_KEY (or NEXT_PUBLIC_SUPABASE_ANON_KEY) must be set "
            "for user-scoped Supabase access"
        )
    base_opts = ClientOptions(storage=SyncMemoryStorage())
    merged_headers = {**dict(base_opts.headers), "Authorization": f"Bearer {access_token}"}
    opts = ClientOptions(storage=SyncMemoryStorage(), headers=merged_headers)
    return create_client(url, anon, opts)
