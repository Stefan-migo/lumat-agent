-- 051_cases_archived_at.sql — soft-archive closed cases without deleting them.
ALTER TABLE cases ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;
-- Rollback: ALTER TABLE cases DROP COLUMN IF EXISTS archived_at;
