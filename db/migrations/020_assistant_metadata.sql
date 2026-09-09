-- 020_assistant_metadata.sql — durable panel assistant state on internal threads.

ALTER TABLE internal_chat_threads
    ADD COLUMN assistant_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN current_plan JSONB,
    ADD COLUMN active_run_id VARCHAR(100);

ALTER TABLE internal_chat_messages
    ADD COLUMN assistant_metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX idx_internal_chat_threads_active_run
    ON internal_chat_threads (active_run_id)
    WHERE active_run_id IS NOT NULL;

GRANT SELECT, INSERT, UPDATE, DELETE ON internal_chat_threads TO app;
