-- 031_internal_chat_thread_project.sql — bind each internal chat thread to a project namespace.
--
-- MEM-9 requires global agent memory to be project-qualified, but threads had no
-- persisted project binding. Without this column, a thread could silently use
-- the default namespace and cross-project memory isolation could not hold.
-- ponytail: the DEFAULT is the complete backfill for existing rows; proyecto is
-- a stable namespace slug and deliberately has no foreign key to projects.

ALTER TABLE internal_chat_threads
    ADD COLUMN IF NOT EXISTS proyecto VARCHAR(100) NOT NULL DEFAULT 'default';
