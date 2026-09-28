-- 036_case_amount.sql — optional CLP service value for a case.

ALTER TABLE cases ADD COLUMN amount NUMERIC;

GRANT SELECT, INSERT, UPDATE, DELETE ON cases TO app;
