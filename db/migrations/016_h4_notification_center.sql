-- 016_h4_notification_center.sql — panel read model and optional push.

ALTER TABLE notification_operations ADD COLUMN IF NOT EXISTS event_id BIGINT REFERENCES domain_events (id);
ALTER TABLE notification_operations ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES users (id);
CREATE INDEX IF NOT EXISTS idx_notification_operations_event ON notification_operations (event_id);
CREATE INDEX IF NOT EXISTS idx_notification_operations_user ON notification_operations (user_id);

CREATE TABLE panel_notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users (id),
    operation_id BIGINT NOT NULL REFERENCES notification_operations (id),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(100) NOT NULL,
    status VARCHAR(30) NOT NULL,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, operation_id)
);

CREATE INDEX idx_panel_notifications_user_created ON panel_notifications (user_id, created_at DESC);
CREATE INDEX idx_panel_notifications_filters ON panel_notifications (user_id, status, source, read_at, created_at DESC);

CREATE TABLE push_subscriptions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users (id),
    endpoint TEXT NOT NULL UNIQUE,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    user_agent TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_push_subscriptions_user_active ON push_subscriptions (user_id, active);
GRANT SELECT, INSERT, UPDATE, DELETE ON panel_notifications, push_subscriptions TO app;
GRANT USAGE, SELECT ON SEQUENCE panel_notifications_id_seq, push_subscriptions_id_seq TO app;
