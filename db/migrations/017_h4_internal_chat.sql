-- 017_h4_internal_chat.sql — owner/admin internal agent conversations.

CREATE TABLE internal_chat_threads (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users (id),
    status VARCHAR(30) NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_internal_chat_threads_user_updated
    ON internal_chat_threads (user_id, updated_at DESC, id DESC);

CREATE TABLE internal_chat_messages (
    id BIGSERIAL PRIMARY KEY,
    thread_id BIGINT NOT NULL REFERENCES internal_chat_threads (id) ON DELETE CASCADE,
    author VARCHAR(30) NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'processing',
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_internal_chat_messages_thread_created
    ON internal_chat_messages (thread_id, created_at, id);

GRANT SELECT, INSERT, UPDATE, DELETE ON internal_chat_threads, internal_chat_messages TO app;
GRANT USAGE, SELECT ON SEQUENCE internal_chat_threads_id_seq, internal_chat_messages_id_seq TO app;
