-- 002_customer_notes.sql — internal staff notes per customer (CR-4).
--
-- The design Data Model (10 tables, 001_init.sql) had no notes table, but
-- spec CR-4 requires notes stored with author and timestamp, visible only to
-- staff (admin/operador). Notes are never exposed on the customer-facing
-- record — they live in their own table (CR-4: "shown to staff only").
--
-- Applied by db/migrate.sh (idempotent per-file), same grants pattern as
-- 001_init.sql (full CRUD on business tables for the `app` role).

CREATE TABLE customer_notes (
    id          BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers (id),
    note        TEXT NOT NULL,
    author      VARCHAR(100) NOT NULL,          -- panel user (admin/operador)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_customer_notes_customer_id ON customer_notes (customer_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON customer_notes TO app;
-- sequences created after 001 (which granted "ALL SEQUENCES") need their own grant
GRANT USAGE, SELECT ON SEQUENCE customer_notes_id_seq TO app;
