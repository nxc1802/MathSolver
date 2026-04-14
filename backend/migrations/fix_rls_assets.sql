-- ============================================================
-- FIX RLS & SESSION ASSETS (MathSolver v5.1 Worker Fix)
-- ============================================================

-- 1. Ensure session_assets table exists
CREATE TABLE IF NOT EXISTS public.session_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES public.sessions(id) ON DELETE CASCADE,
    job_id UUID NOT NULL,
    asset_type TEXT NOT NULL CHECK (asset_type IN ('video', 'image')),
    storage_path TEXT NOT NULL,
    public_url TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for session_assets
CREATE INDEX IF NOT EXISTS idx_session_assets_session_id ON public.session_assets(session_id);
CREATE INDEX IF NOT EXISTS idx_session_assets_type ON public.session_assets(session_id, asset_type);

-- 2. Enable RLS for all tables
ALTER TABLE public.session_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;


-- 3. Fix Table Policies to allow SERVICE ROLE
-- In Supabase, service_role usually bypasses RLS, but we add explicit policies for safety
-- especially for path-based checks or when SECURITY DEFINER functions are used.

-- [Session Assets]
DROP POLICY IF EXISTS "Users view own assets" ON public.session_assets;
CREATE POLICY "Users view own assets" ON public.session_assets 
    FOR SELECT USING (
        session_id IN (SELECT id FROM public.sessions WHERE user_id = auth.uid())
    );

DROP POLICY IF EXISTS "Service role manages assets" ON public.session_assets;
CREATE POLICY "Service role manages assets" ON public.session_assets 
    FOR ALL USING (true) 
    WITH CHECK (true);


-- [Messages] - Allow Worker to insert assistant messages
DROP POLICY IF EXISTS "Users manage own messages" ON public.messages;
CREATE POLICY "Users manage own messages" ON public.messages 
    FOR ALL USING (
        session_id IN (SELECT id FROM public.sessions WHERE user_id = auth.uid())
        OR 
        (auth.jwt() ->> 'role' = 'service_role')
    );


-- [Jobs] - Allow Worker to update job status
DROP POLICY IF EXISTS "Users manage own jobs" ON public.jobs;
CREATE POLICY "Users manage own jobs" ON public.jobs 
    FOR ALL USING (
        auth.uid() = user_id 
        OR user_id IS NULL
        OR (auth.jwt() ->> 'role' = 'service_role')
    );


-- 4. Storage Policies (Bucket: video)
-- Ensure 'video' bucket exists
INSERT INTO storage.buckets (id, name, public)
VALUES ('video', 'video', true)
ON CONFLICT (id) DO UPDATE SET public = true;

-- [Storage: Worker / Service Role] - Allow all in video bucket
DROP POLICY IF EXISTS "Service Role manage videos" ON storage.objects;
CREATE POLICY "Service Role manage videos" ON storage.objects
    FOR ALL 
    TO service_role
    USING (bucket_id = 'video');

-- [Storage: Users] - Allow users to view their session videos
DROP POLICY IF EXISTS "Users view session videos" ON storage.objects;
CREATE POLICY "Users view session videos" ON storage.objects
    FOR SELECT 
    TO authenticated
    USING (
        bucket_id = 'video' 
        AND (storage.foldername(name))[2] IN (
            SELECT id::text FROM public.sessions WHERE user_id = auth.uid()
        )
    );

-- [Storage: Public] - Allow public read access to videos
DROP POLICY IF EXISTS "Public read videos" ON storage.objects;
CREATE POLICY "Public read videos" ON storage.objects
    FOR SELECT 
    TO public
    USING (bucket_id = 'video');
