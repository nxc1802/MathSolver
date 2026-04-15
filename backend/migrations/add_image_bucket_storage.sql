-- ============================================================
-- MathSolver: Supabase Storage bucket `image` (chat / OCR attachments)
-- Run after session_assets and storage.video policies exist.
-- ============================================================

INSERT INTO storage.buckets (id, name, public)
VALUES ('image', 'image', true)
ON CONFLICT (id) DO UPDATE SET public = true;

-- Service role: upload/delete/list for API + workers
DROP POLICY IF EXISTS "Service Role manage images" ON storage.objects;
CREATE POLICY "Service Role manage images" ON storage.objects
    FOR ALL
    TO service_role
    USING (bucket_id = 'image')
    WITH CHECK (bucket_id = 'image');

-- Authenticated: read only objects under sessions they own (path sessions/{session_id}/...)
DROP POLICY IF EXISTS "Users view session images" ON storage.objects;
CREATE POLICY "Users view session images" ON storage.objects
    FOR SELECT
    TO authenticated
    USING (
        bucket_id = 'image'
        AND (storage.foldername(name))[2] IN (
            SELECT id::text FROM public.sessions WHERE user_id = auth.uid()
        )
    );

-- Public read for get_public_url / FE img tags (same model as video bucket)
DROP POLICY IF EXISTS "Public read images" ON storage.objects;
CREATE POLICY "Public read images" ON storage.objects
    FOR SELECT
    TO public
    USING (bucket_id = 'image');
