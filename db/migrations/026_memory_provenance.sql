-- 026_memory_provenance.sql — memory provenance and declared visibility.
--
-- The true producer of rows created before this migration is unrecoverable.
-- `system` is a conservative placeholder for those pre-existing rows.
--
-- `visibility` is intentionally recorded even though it is currently
-- functionally determined by `scope`: it preserves the declaration that was
-- audited at write time and lets the database enforce the axis mapping.
-- ponytail: redundancy ceiling is the visibility column; if the mapping
-- widens, keep the audited declaration while extending the coherence rule.

CREATE TYPE memory_producer AS ENUM ('user', 'system', 'agent', 'pipeline');
CREATE TYPE memory_visibility AS ENUM ('thread', 'project');

ALTER TABLE memories
  ADD COLUMN producer memory_producer NOT NULL DEFAULT 'system',
  ADD COLUMN origin_thread_id VARCHAR(100),
  ADD COLUMN visibility memory_visibility NOT NULL DEFAULT 'thread',
  ADD CONSTRAINT memories_visibility_scope_coherence
    CHECK ((visibility = 'project') = (scope = 'agent'));
