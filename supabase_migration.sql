-- ============================================================
-- AI Meeting Summarizer - Supabase Database Migration
-- ============================================================
-- Run this ENTIRE script in your Supabase SQL Editor:
--   Dashboard → SQL Editor → New Query → Paste → Run
-- ============================================================

-- 1. Create the "meetings" table
CREATE TABLE IF NOT EXISTS public.meetings (
  id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  title         TEXT NOT NULL,
  session_date  TEXT,
  executive_summary TEXT,
  decisions     JSONB DEFAULT '[]'::jsonb,
  action_items  JSONB DEFAULT '[]'::jsonb,
  key_points    JSONB DEFAULT '[]'::jsonb,
  speaker_mapping JSONB DEFAULT '{}'::jsonb,
  segments      JSONB DEFAULT '[]'::jsonb,
  slides_count  INTEGER DEFAULT 0,
  slides        JSONB DEFAULT '[]'::jsonb,
  report_path   TEXT,
  created_at    TIMESTAMPTZ DEFAULT now()
);

-- 2. Enable Row Level Security
ALTER TABLE public.meetings ENABLE ROW LEVEL SECURITY;

-- 3. Create a permissive policy for the anon role
--    (allows read/write from the frontend using the anon key)
DROP POLICY IF EXISTS "Allow anon full access on meetings" ON public.meetings;
CREATE POLICY "Allow anon full access on meetings"
  ON public.meetings
  FOR ALL
  TO anon
  USING (true)
  WITH CHECK (true);

-- 4. Create the storage bucket for Word document uploads
INSERT INTO storage.buckets (id, name, public)
VALUES ('meeting-summaries', 'meeting-summaries', true)
ON CONFLICT (id) DO NOTHING;

-- 5. Allow anonymous uploads and reads on the storage bucket
DROP POLICY IF EXISTS "Allow anon upload to meeting-summaries" ON storage.objects;
CREATE POLICY "Allow anon upload to meeting-summaries"
  ON storage.objects
  FOR INSERT
  TO anon
  WITH CHECK (bucket_id = 'meeting-summaries');

DROP POLICY IF EXISTS "Allow anon read from meeting-summaries" ON storage.objects;
CREATE POLICY "Allow anon read from meeting-summaries"
  ON storage.objects
  FOR SELECT
  TO anon
  USING (bucket_id = 'meeting-summaries');

-- ============================================================
-- Done! Your database is now ready for the AI Meeting Summarizer.
-- ============================================================
