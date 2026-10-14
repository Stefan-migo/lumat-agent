-- 053_panel_secrets.sql — encrypted application-managed panel credentials.
CREATE TABLE panel_secrets (
    key TEXT PRIMARY KEY,
    ciphertext BYTEA NOT NULL,
    nonce BYTEA NOT NULL,
    updated_by INT REFERENCES users(id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- The app connects as the least-privilege `app` role; grant like the other
-- panel-managed tables (001_init.sql / 002_customer_notes.sql pattern).
GRANT SELECT, INSERT, UPDATE, DELETE ON panel_secrets TO app;
-- Rollback: DROP TABLE IF EXISTS panel_secrets;
