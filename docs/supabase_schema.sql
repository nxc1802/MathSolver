-- ============================================================
-- SQL Schema for Visual Math Solver v4.0 (Multi-Session)
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

CREATE INDEX IF NOT EXISTS idx_messages_session_id ON public.messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON public.messages(session_id, created_at);

-- 4. Jobs Table
CREATE TABLE IF NOT EXISTS public.jobs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    session_id UUID REFERENCES public.sessions(id),
    status TEXT NOT NULL DEFAULT 'processing',
    input_text TEXT,
    result JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Session Assets Table (For Video Versioning)
CREATE TABLE IF NOT EXISTS public.session_assets (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id   UUID NOT NULL REFERENCES public.sessions(id) ON DELETE CASCADE,
    job_id       UUID NOT NULL REFERENCES public.jobs(id) ON DELETE CASCADE,
    asset_type   TEXT NOT NULL CHECK (asset_type IN ('video')),
    storage_path TEXT NOT NULL,
    public_url   TEXT NOT NULL,
    version      INTEGER NOT NULL DEFAULT 1,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_session_assets_session_id ON public.session_assets(session_id);
CREATE INDEX IF NOT EXISTS idx_session_assets_job_id ON public.session_assets(job_id);

-- ============================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.session_assets ENABLE ROW LEVEL SECURITY;

-- Profiles: Users view own profile
CREATE POLICY "Users view own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- Sessions: Users manage own sessions
CREATE POLICY "Users manage own sessions" ON public.sessions FOR ALL USING (auth.uid() = user_id);

-- Messages: Users view own messages
CREATE POLICY "Users view own messages" ON public.messages FOR ALL USING (
    session_id IN (SELECT id FROM public.sessions WHERE user_id = auth.uid())
);

-- Jobs: Users view own jobs
CREATE POLICY "Users view own jobs" ON public.jobs FOR ALL USING (auth.uid() = user_id OR user_id IS NULL);

-- Session Assets: Users view own assets
CREATE POLICY "Users view own assets" ON public.session_assets FOR SELECT USING (
    session_id IN (SELECT id FROM public.sessions WHERE user_id = auth.uid())
);
