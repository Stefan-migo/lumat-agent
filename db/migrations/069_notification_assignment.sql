-- 069_notification_assignment.sql — explicit ownership for conversations and cases.
BEGIN;

ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS assigned_user_id bigint;
ALTER TABLE cases
    ADD COLUMN IF NOT EXISTS assigned_user_id bigint;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'conversations_assigned_user_id_fkey'
          AND conrelid = 'conversations'::regclass
    ) THEN
        ALTER TABLE conversations
            ADD CONSTRAINT conversations_assigned_user_id_fkey
            FOREIGN KEY (assigned_user_id) REFERENCES users(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'cases_assigned_user_id_fkey'
          AND conrelid = 'cases'::regclass
    ) THEN
        ALTER TABLE cases
            ADD CONSTRAINT cases_assigned_user_id_fkey
            FOREIGN KEY (assigned_user_id) REFERENCES users(id) ON DELETE SET NULL;
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_conversations_assigned_user_id
    ON conversations (assigned_user_id);
CREATE INDEX IF NOT EXISTS idx_cases_assigned_user_id
    ON cases (assigned_user_id);

COMMIT;

-- Rollback (run in this order; the last statement is not optional): the tracking row must go, or
-- `migrate.sh` will skip the file on the next run and leave a database without these columns
-- believing it is already at 069.
--   DELETE FROM schema_migrations WHERE version = '069_notification_assignment';
--   DROP INDEX IF EXISTS idx_cases_assigned_user_id; DROP INDEX IF EXISTS idx_conversations_assigned_user_id; ALTER TABLE cases DROP CONSTRAINT IF EXISTS cases_assigned_user_id_fkey, DROP COLUMN IF EXISTS assigned_user_id; ALTER TABLE conversations DROP CONSTRAINT IF EXISTS conversations_assigned_user_id_fkey, DROP COLUMN IF EXISTS assigned_user_id;
