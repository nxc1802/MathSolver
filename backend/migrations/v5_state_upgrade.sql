-- ============================================================
-- MATHSOLVER v5.0 - State Architecture Upgrade Migration
-- ============================================================

-- 1. Auto-update `sessions.updated_at` function
CREATE OR REPLACE FUNCTION public.update_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.sessions
    SET updated_at = NOW()
    WHERE id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. Triggers for session timestamp updates
DROP TRIGGER IF EXISTS trg_update_session_on_message ON public.messages;
CREATE TRIGGER trg_update_session_on_message
    AFTER INSERT ON public.messages
    FOR EACH ROW
    EXECUTE FUNCTION public.update_session_timestamp();

DROP TRIGGER IF EXISTS trg_update_session_on_job ON public.jobs;
CREATE TRIGGER trg_update_session_on_job
    AFTER INSERT OR UPDATE ON public.jobs
    FOR EACH ROW
    EXECUTE FUNCTION public.update_session_timestamp();

DROP TRIGGER IF EXISTS trg_update_session_on_asset ON public.session_assets;
CREATE TRIGGER trg_update_session_on_asset
    AFTER INSERT ON public.session_assets
    FOR EACH ROW
    EXECUTE FUNCTION public.update_session_timestamp();

-- 3. Idempotency Support: client_message_id on messages
ALTER TABLE public.messages 
ADD COLUMN IF NOT EXISTS client_message_id UUID;

CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_session_client_id 
ON public.messages(session_id, client_message_id) 
WHERE client_message_id IS NOT NULL;

-- 4. Atomic Asset Versioning: Unique version per session and asset type
CREATE UNIQUE INDEX IF NOT EXISTS idx_session_assets_unique_version 
ON public.session_assets(session_id, asset_type, version);
