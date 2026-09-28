-- Scope normalized-content deduplication to the memory owner namespace.
DROP INDEX IF EXISTS uq_memories_normalized_content;

CREATE UNIQUE INDEX uq_memories_normalized_content
  ON memories (owner_id, proyecto, scope, entity_id, normalized_hash) NULLS NOT DISTINCT
  WHERE normalized_hash IS NOT NULL;

-- Rollback: DROP INDEX IF EXISTS uq_memories_normalized_content;
-- Rollback: CREATE UNIQUE INDEX uq_memories_normalized_content
-- Rollback:   ON memories (proyecto, scope, entity_id, normalized_hash)
-- Rollback:   WHERE normalized_hash IS NOT NULL;
