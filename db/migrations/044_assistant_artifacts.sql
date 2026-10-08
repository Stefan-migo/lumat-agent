CREATE TABLE assistant_artifacts (
    id BIGSERIAL PRIMARY KEY,
    thread_id BIGINT NOT NULL REFERENCES internal_chat_threads(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    size INTEGER NOT NULL CHECK (size > 0),
    sha256 VARCHAR(64) NOT NULL,
    stored_path TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_assistant_artifacts_thread ON assistant_artifacts(thread_id);
GRANT SELECT, INSERT, UPDATE, DELETE ON assistant_artifacts TO app;
GRANT USAGE, SELECT ON SEQUENCE assistant_artifacts_id_seq TO app;

-- Rollback: DROP TABLE IF EXISTS assistant_artifacts;
