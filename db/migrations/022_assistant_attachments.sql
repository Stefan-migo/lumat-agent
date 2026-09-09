CREATE TABLE assistant_attachments (
    id BIGSERIAL PRIMARY KEY,
    thread_id BIGINT NOT NULL REFERENCES internal_chat_threads(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    kind VARCHAR(20) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    size INTEGER NOT NULL CHECK (size > 0 AND size <= 5242880),
    sha256 VARCHAR(64) NOT NULL,
    stored_path TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_assistant_attachments_thread ON assistant_attachments(thread_id, deleted_at);
GRANT SELECT, INSERT, UPDATE, DELETE ON assistant_attachments TO app;
GRANT USAGE, SELECT ON SEQUENCE assistant_attachments_id_seq TO app;
