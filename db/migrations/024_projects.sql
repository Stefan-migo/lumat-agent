-- 024_projects.sql — agent-owned project namespace registry.

CREATE TABLE IF NOT EXISTS projects (
    id BIGSERIAL PRIMARY KEY,
    slug VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    purpose VARCHAR(500) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'archived')),
    purpose_embedding vector(384) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_projects_normalized_slug
    ON projects (lower(btrim(slug)));

CREATE TABLE IF NOT EXISTS project_aliases (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(id),
    alias VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_project_aliases_alias UNIQUE (alias)
);

CREATE TABLE IF NOT EXISTS project_audit (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT REFERENCES projects(id),
    actor VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    before JSONB,
    after JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO projects (slug, name, purpose, purpose_embedding)
VALUES ('default', 'Default', 'Default project namespace', ('[' || repeat('0,', 383) || '0]')::vector)
ON CONFLICT DO NOTHING;

GRANT SELECT, INSERT, UPDATE, DELETE ON projects, project_aliases, project_audit TO app;
GRANT USAGE, SELECT ON SEQUENCE projects_id_seq, project_aliases_id_seq, project_audit_id_seq TO app;
