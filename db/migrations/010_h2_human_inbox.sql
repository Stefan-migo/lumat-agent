-- 010_h2_human_inbox.sql — durable H2 ownership and outbound contracts.
--
-- Existing rows remain readable: ownership and delivery metadata are nullable,
-- while new conversations start at optimistic-concurrency version zero.

CREATE TYPE delivery_status AS ENUM ('pending', 'sending', 'sent', 'failed', 'unknown');

ALTER TABLE conversations
    ADD COLUMN responsible_id BIGINT REFERENCES users (id),
    ADD COLUMN version INTEGER NOT NULL DEFAULT 0;

ALTER TABLE messages
    ADD COLUMN author_id BIGINT REFERENCES users (id),
    ADD COLUMN request_id VARCHAR(255),
    ADD COLUMN delivery_status delivery_status,
    ADD COLUMN delivery_error TEXT,
    ADD COLUMN delivery_attempts INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN last_attempt_at TIMESTAMPTZ,
    ADD COLUMN delivered_at TIMESTAMPTZ;

ALTER TABLE conversations
    ADD CONSTRAINT conversations_version_nonnegative CHECK (version >= 0);

ALTER TABLE messages
    ADD CONSTRAINT messages_delivery_attempts_nonnegative
        CHECK (delivery_attempts >= 0);

CREATE INDEX idx_conversations_responsible_id
    ON conversations (responsible_id);

CREATE UNIQUE INDEX uq_messages_outbound_request_id
    ON messages (request_id)
    WHERE direction = 'outbound' AND request_id IS NOT NULL;
