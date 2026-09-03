-- 013_h3_notifications.sql — durable notification operations and attempts.

CREATE TABLE notification_operations (
    id BIGSERIAL PRIMARY KEY,
    recipient VARCHAR(255) NOT NULL,
    channel VARCHAR(30) NOT NULL,
    content TEXT NOT NULL,
    source_entity VARCHAR(100) NOT NULL,
    source_id VARCHAR(100) NOT NULL,
    idempotency_key VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_attempt_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE notification_attempts (
    id BIGSERIAL PRIMARY KEY,
    operation_id BIGINT NOT NULL REFERENCES notification_operations (id),
    attempt_number INTEGER NOT NULL,
    status VARCHAR(30) NOT NULL,
    error TEXT,
    external_id VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (operation_id, attempt_number)
);

CREATE INDEX idx_notification_operations_due
    ON notification_operations (status, next_attempt_at);
CREATE INDEX idx_notification_attempts_operation
    ON notification_attempts (operation_id, created_at);

GRANT SELECT, INSERT, UPDATE ON notification_operations, notification_attempts TO app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app;
