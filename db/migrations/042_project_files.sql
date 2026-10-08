CREATE TABLE project_files (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    owner_id BIGINT NOT NULL REFERENCES users(id),
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    size INTEGER NOT NULL CHECK (size > 0),
    sha256 VARCHAR(64) NOT NULL,
    stored_path TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ready',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_project_files_project ON project_files(project_id);
GRANT SELECT, INSERT, UPDATE, DELETE ON project_files TO app;
GRANT USAGE, SELECT ON SEQUENCE project_files_id_seq TO app;

-- Rollback: DROP TABLE IF EXISTS project_files;
