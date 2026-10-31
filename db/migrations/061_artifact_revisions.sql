-- 061_artifact_revisions.sql — S1/S12: an artifact gets an append-only revision chain.
--
-- Until now every `artifact.save` inserted a row, so "editing" an artifact created a second file
-- beside the first. A revision is a new row with the same `root_id` and the next `version`; the
-- previous row is never updated and never deleted, so its blob and its sha256 stay verifiable.
--
-- The chain is additive: no existing column is dropped, renamed or rewritten. `root_id` is an
-- identity, not a parent pointer — the row where `root_id = id` is version 1 of that artifact and is
-- never deleted on its own, so no self-referencing foreign key is needed.
--
-- The unique index is the correctness half of S11: two concurrent edits of the same artifact must
-- produce distinct versions, never two rows claiming the same one.

ALTER TABLE assistant_artifacts
    ADD COLUMN root_id BIGINT,
    ADD COLUMN version INTEGER;

-- Every artifact stored before this migration is its own root at version 1.
UPDATE assistant_artifacts
SET root_id = id,
    version = 1
WHERE root_id IS NULL;

ALTER TABLE assistant_artifacts
    ALTER COLUMN root_id SET NOT NULL,
    ALTER COLUMN version SET NOT NULL,
    ALTER COLUMN version SET DEFAULT 1,
    ADD CONSTRAINT assistant_artifacts_version_positive CHECK (version >= 1);

CREATE UNIQUE INDEX uq_assistant_artifacts_root_version
    ON assistant_artifacts (root_id, version);

-- Rollback: DROP INDEX uq_assistant_artifacts_root_version;
--           ALTER TABLE assistant_artifacts
--               DROP CONSTRAINT assistant_artifacts_version_positive,
--               DROP COLUMN version,
--               DROP COLUMN root_id;
-- The rollback keeps every row: revisions become indistinguishable siblings again, which is exactly
-- the pre-061 behaviour, and no stored blob is deleted.
