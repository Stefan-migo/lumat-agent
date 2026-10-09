ALTER TABLE automation_rules ADD COLUMN IF NOT EXISTS recipient_target VARCHAR(30) NOT NULL DEFAULT 'customer';
ALTER TABLE automation_rules ADD COLUMN IF NOT EXISTS content TEXT;

-- Rollback: ALTER TABLE automation_rules DROP COLUMN IF EXISTS content; ALTER TABLE automation_rules DROP COLUMN IF EXISTS recipient_target;
