-- SQL Schema for Visual Math Solver v3.0

-- Create the jobs table
CREATE TABLE IF NOT EXISTS public.jobs (
    id UUID PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'processing',
    input_text TEXT,
    result JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security (Optional for Backend access, but good practice)
ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;

-- Allow Service Role to do everything (Backend always uses service role or anon with correct policies)
CREATE POLICY "Allow all for service role" ON public.jobs
    FOR ALL USING (true);

-- Allow Public READ for monitoring status (Optional, based on your UX)
CREATE POLICY "Allow public read" ON public.jobs
    FOR SELECT USING (true);
