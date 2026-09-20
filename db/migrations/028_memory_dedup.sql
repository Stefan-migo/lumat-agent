-- 028_memory_dedup.sql — deterministic content-level memory deduplication.

ALTER TABLE memories
  ADD COLUMN normalized_hash VARCHAR(64),
  ADD COLUMN duplicate_count INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE UNIQUE INDEX uq_memories_normalized_content
  ON memories (proyecto, scope, entity_id, normalized_hash)
  WHERE normalized_hash IS NOT NULL;
