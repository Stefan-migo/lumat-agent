-- 014_h4_automations_chat_pwa.sql — transactional domain event outbox.

CREATE TABLE domain_events (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    available_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    leased_until TIMESTAMPTZ,
    lease_owner VARCHAR(100),
    processed_at TIMESTAMPTZ,
    error TEXT,
    dedupe_key VARCHAR(255) NOT NULL UNIQUE
);

ALTER TABLE notification_operations
    ADD COLUMN event_id BIGINT REFERENCES domain_events (id),
    ADD COLUMN user_id BIGINT REFERENCES users (id);

CREATE INDEX idx_domain_events_claim
    ON domain_events (status, available_at, leased_until, id);
CREATE INDEX idx_domain_events_entity
    ON domain_events (entity_type, entity_id);
CREATE INDEX idx_notification_operations_event_id
    ON notification_operations (event_id);
CREATE INDEX idx_notification_operations_user_id
    ON notification_operations (user_id);

GRANT SELECT, INSERT, UPDATE ON domain_events TO app;
GRANT USAGE, SELECT ON SEQUENCE domain_events_id_seq TO app;
