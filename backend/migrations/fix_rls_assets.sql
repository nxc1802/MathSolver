-- ============================================================
-- FIX: Row Level Security for session_assets
-- Run this in your Supabase SQL Editor if you get Error 42501
-- ============================================================

-- 1. Ensure the table exists (in case it was deleted)
CREATE TABLE IF NOT EXISTS public.session_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES public.sessions(id) ON DELETE CASCADE,
    job_id UUID,
    asset_type TEXT NOT NULL DEFAULT 'video',
    storage_path TEXT NOT NULL,
    public_url TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Indices for performance
CREATE INDEX IF NOT EXISTS idx_session_assets_session_id ON public.session_assets(session_id);
CREATE INDEX IF NOT EXISTS idx_session_assets_job_id ON public.session_assets(job_id);

-- 3. Enable RLS
ALTER TABLE public.session_assets ENABLE ROW LEVEL SECURITY;

-- 4. Clean up policies to avoid duplication
DROP POLICY IF EXISTS "Users can view own session assets" ON public.session_assets;
DROP POLICY IF EXISTS "Service role can manage all assets" ON public.session_assets;

-- 5. Create Policies
-- Users can only view assets if they own the related session
CREATE POLICY "Users can view own session assets" ON public.session_assets
    FOR SELECT USING (
        session_id IN (SELECT id FROM public.sessions WHERE user_id = auth.uid())
    );

-- The Worker (Service Role) must have full permission to insert/update/query
CREATE POLICY "Service role can manage all assets" ON public.session_assets
    FOR ALL USING (true) WITH CHECK (true);

-- 6. Grant Permissions
GRANT ALL ON public.session_assets TO service_role;
GRANT SELECT ON public.session_assets TO authenticated;

COMMIT;
