ALTER TABLE users
    ADD COLUMN email VARCHAR(200),
    ADD COLUMN name VARCHAR(200),
    ADD COLUMN phone VARCHAR(30),
    ADD COLUMN position VARCHAR(120);

CREATE UNIQUE INDEX uq_users_lower_email
    ON users (lower(email)) WHERE email IS NOT NULL;

-- Rollback: DROP INDEX IF EXISTS uq_users_lower_email;
-- Rollback: ALTER TABLE users DROP COLUMN IF EXISTS position;
-- Rollback: ALTER TABLE users DROP COLUMN IF EXISTS phone;
-- Rollback: ALTER TABLE users DROP COLUMN IF EXISTS name;
-- Rollback: ALTER TABLE users DROP COLUMN IF EXISTS email;
