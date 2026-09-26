-- 033_customer_archived_at.sql — mark customer records as archived without deleting them.

ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;
