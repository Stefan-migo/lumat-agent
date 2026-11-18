-- 069_panel_sessions.sql — a revocable, per-device credential refills the signed panel session.
--
-- The existing signed `session` cookie remains the only authorization source.
-- This table stores hashes of opaque remember tokens so a device can silently
-- restore that signed session after its twelve-hour idle window, and a copied
-- token can be detected when its predecessor is presented after rotation.
--
-- Tokens have an absolute ninety-day lifetime; successful restoration rotates
-- the credential instead of extending its expiry. Revocation is per device,
-- while the partial index keeps the active-session lookup scoped to one user.

CREATE TABLE panel_sessions (
    id bigserial PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash text NOT NULL UNIQUE,
    user_agent text,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_used_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    replaced_by_hash text
);

CREATE INDEX idx_panel_sessions_active_user
    ON panel_sessions (user_id)
    WHERE revoked_at IS NULL;

GRANT SELECT, INSERT, UPDATE, DELETE ON panel_sessions TO app;
GRANT USAGE, SELECT ON SEQUENCE panel_sessions_id_seq TO app;

-- Rollback: DROP INDEX idx_panel_sessions_active_user; DROP TABLE panel_sessions;
