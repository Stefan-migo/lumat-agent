CREATE TABLE IF NOT EXISTS automation_installations (
    id BIGSERIAL PRIMARY KEY,
    recipe_id VARCHAR(100) NOT NULL UNIQUE,
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE automation_rules
    ADD COLUMN IF NOT EXISTS installation_id BIGINT REFERENCES automation_installations(id) UNIQUE;

GRANT SELECT, INSERT, UPDATE ON automation_installations TO app;
GRANT USAGE, SELECT ON SEQUENCE automation_installations_id_seq TO app;

-- Rollback: ALTER TABLE automation_rules DROP COLUMN IF EXISTS installation_id; DROP TABLE IF EXISTS automation_installations;
