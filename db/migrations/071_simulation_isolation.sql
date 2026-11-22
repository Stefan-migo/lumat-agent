-- 071_simulation_isolation.sql — persist simulation provenance for operational filtering.
-- Existing and ordinary rows remain operational by default.

ALTER TABLE conversations
    ADD COLUMN simulated boolean NOT NULL DEFAULT false;

ALTER TABLE cases
    ADD COLUMN simulated boolean NOT NULL DEFAULT false;

-- Rollback: ALTER TABLE cases DROP COLUMN simulated; ALTER TABLE conversations DROP COLUMN simulated;
