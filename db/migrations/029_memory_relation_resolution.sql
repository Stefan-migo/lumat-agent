-- 029_memory_relation_resolution.sql — relation judge provenance and resolution.

ALTER TABLE memory_relations
  ADD COLUMN source VARCHAR(20) NOT NULL DEFAULT 'judge',
  ADD COLUMN human_resolved_at TIMESTAMPTZ;

CREATE INDEX idx_memory_relations_pending
  ON memory_relations (confidence)
  WHERE source = 'judge' AND human_resolved_at IS NULL;
