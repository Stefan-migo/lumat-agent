-- 015_h4_automations.sql — deterministic rules and execution audit.

CREATE TABLE automation_rules (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    conditions JSONB NOT NULL DEFAULT '{}'::jsonb,
    channel VARCHAR(30) NOT NULL,
    template_event VARCHAR(100) NOT NULL,
    cooldown_seconds INTEGER NOT NULL DEFAULT 0 CHECK (cooldown_seconds BETWEEN 0 AND 2592000),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE automation_executions (
    id BIGSERIAL PRIMARY KEY,
    rule_id BIGINT NOT NULL REFERENCES automation_rules (id),
    event_id BIGINT NOT NULL REFERENCES domain_events (id),
    execution_key VARCHAR(255) NOT NULL UNIQUE,
    outcome VARCHAR(30) NOT NULL,
    reason TEXT,
    operation_id BIGINT REFERENCES notification_operations (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_automation_rules_event ON automation_rules (event_type, enabled);
CREATE INDEX idx_automation_executions_rule_time ON automation_executions (rule_id, created_at);
CREATE INDEX idx_automation_executions_event ON automation_executions (event_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON automation_rules, automation_executions TO app;
GRANT USAGE, SELECT ON SEQUENCE automation_rules_id_seq, automation_executions_id_seq TO app;
