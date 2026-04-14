-- ============================================================
-- MATHSOLVER v4.0 - Migration Script (Multi-Session & History)
-- ============================================================

-- 1. Profiles Table (Extends Supabase Auth)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Function to handle new user signup and auto-create profile
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, display_name, avatar_url)
    VALUES (
        NEW.id, 
        COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.email),
        NEW.raw_user_meta_data->>'avatar_url'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger for profile creation
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- 2. Sessions Table
CREATE TABLE IF NOT EXISTS public.sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT DEFAULT 'Bài toán mới',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for sessions
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON public.sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON public.sessions(updated_at DESC);

-- 3. Messages Table
CREATE TABLE IF NOT EXISTS public.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES public.sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    type TEXT NOT NULL DEFAULT 'text',
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for messages
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON public.messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON public.messages(session_id, created_at);

-- 4. Session Assets Table (v5.1 Versioning)
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

-- 5. Update Jobs Table
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS session_id UUID REFERENCES public.sessions(id);

-- 6. Row Level Security (RLS)
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.session_assets ENABLE ROW LEVEL SECURITY;

-- Polices for public.profiles
DROP POLICY IF EXISTS "Users view own profile" ON public.profiles;
CREATE POLICY "Users view own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);
DROP POLICY IF EXISTS "Users update own profile" ON public.profiles;
CREATE POLICY "Users update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- Policies for public.sessions
DROP POLICY IF EXISTS "Users manage own sessions" ON public.sessions;
CREATE POLICY "Users manage own sessions" ON public.sessions FOR ALL USING (auth.uid() = user_id);

-- Policies for public.messages
DROP POLICY IF EXISTS "Users manage own messages" ON public.messages;
CREATE POLICY "Users manage own messages" ON public.messages FOR ALL USING (
    session_id IN (SELECT id FROM public.sessions WHERE user_id = auth.uid())
    OR (auth.jwt() ->> 'role' = 'service_role')
);

-- Policies for public.session_assets
DROP POLICY IF EXISTS "Users view own assets" ON public.session_assets;
CREATE POLICY "Users view own assets" ON public.session_assets FOR SELECT USING (
    session_id IN (SELECT id FROM public.sessions WHERE user_id = auth.uid())
);
DROP POLICY IF EXISTS "Service role manages assets" ON public.session_assets;
CREATE POLICY "Service role manages assets" ON public.session_assets FOR ALL USING (true);

-- Policies for public.jobs
DROP POLICY IF EXISTS "Users manage own jobs" ON public.jobs;
CREATE POLICY "Users manage own jobs" ON public.jobs FOR ALL USING (
    auth.uid() = user_id OR user_id IS NULL OR (auth.jwt() ->> 'role' = 'service_role')
);

-- 7. Storage Policies (Bucket: video)
-- (Run this in Supabase Dashboard if not allowed in migration)
-- INSERT INTO storage.buckets (id, name, public) VALUES ('video', 'video', true) ON CONFLICT (id) DO NOTHING;
-- CREATE POLICY "Service Role manage videos" ON storage.objects FOR ALL TO service_role USING (bucket_id = 'video');
-- CREATE POLICY "Public read videos" ON storage.objects FOR SELECT TO public USING (bucket_id = 'video');

-- Grant permissions to public/authenticated
GRANT ALL ON public.profiles TO authenticated;
GRANT ALL ON public.sessions TO authenticated;
GRANT ALL ON public.messages TO authenticated;
GRANT ALL ON public.jobs TO authenticated;
GRANT ALL ON public.session_assets TO authenticated;
GRANT ALL ON public.session_assets TO service_role;
