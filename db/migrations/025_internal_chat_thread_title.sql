-- 025_internal_chat_thread_title.sql — optional generated or renamed chat title.

ALTER TABLE internal_chat_threads
    ADD COLUMN IF NOT EXISTS title VARCHAR(255);
