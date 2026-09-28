-- 036_case_amount.sql — optional CLP service value for a case.

ALTER TABLE cases ADD COLUMN IF NOT EXISTS amount NUMERIC;
