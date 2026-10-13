-- 051_memory_handoff.sql — mark memories for handoff.

ALTER TABLE memories ADD COLUMN handoff boolean NOT NULL DEFAULT false;
