-- 007_case_created_at.sql — cases.created_at (panel KPIs + ordering, T5.3/T5.5).
--
-- The cases table (001_init.sql) had no creation timestamp: escalation used
-- escalated_at and pending cases had no usable window anchor. The dashboard
-- KPIs (AP-8) count motivos / visit requests over a settings time window,
-- which needs a case creation time, and the cases view (HH-4) benefits from
-- a stable created ordering for pending rows.
--
-- Existing rows get now() (backfill default); new rows use the server default.

ALTER TABLE cases ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT now();
