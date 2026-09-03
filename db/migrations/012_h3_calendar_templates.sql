-- 012_h3_calendar_templates.sql — calendar identity and immutable templates.

CREATE TABLE appointment_calendar_sync (
    id BIGSERIAL PRIMARY KEY,
    appointment_id BIGINT NOT NULL UNIQUE REFERENCES appointments (id),
    provider VARCHAR(100) NOT NULL DEFAULT 'ics',
    uid VARCHAR(255) NOT NULL,
    idempotency_key VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    timezone VARCHAR(100) NOT NULL,
    cancelled BOOLEAN NOT NULL DEFAULT FALSE,
    external_id VARCHAR(255),
    payload TEXT,
    error TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TIMESTAMPTZ,
    synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, uid),
    UNIQUE (provider, idempotency_key)
);

CREATE TABLE notification_template_versions (
    id BIGSERIAL PRIMARY KEY,
    event VARCHAR(100) NOT NULL,
    channel VARCHAR(30) NOT NULL,
    locale VARCHAR(20) NOT NULL,
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    required_variables JSONB NOT NULL DEFAULT '[]',
    approved BOOLEAN NOT NULL DEFAULT FALSE,
    smtp_allowed BOOLEAN NOT NULL DEFAULT TRUE,
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (event, channel, locale, version)
);

CREATE INDEX idx_calendar_sync_status ON appointment_calendar_sync (status);
CREATE INDEX idx_template_lookup ON notification_template_versions (event, channel, locale, version);

GRANT SELECT, INSERT, UPDATE ON appointment_calendar_sync TO app;
GRANT SELECT, INSERT ON notification_template_versions TO app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app;
