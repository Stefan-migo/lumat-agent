-- Preserve merged customer identities as archived tombstones.
ALTER TABLE customers ADD COLUMN IF NOT EXISTS merged_into_customer_id BIGINT REFERENCES customers (id);

-- Rollback: ALTER TABLE customers DROP COLUMN IF EXISTS merged_into_customer_id;
