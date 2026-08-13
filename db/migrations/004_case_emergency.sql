-- 004_case_emergency.sql: emergency flag on cases (EM-2/EM-4, T4.2).
--
-- Strong emergency hits mark the case row so the panel (T5.3) can list and
-- acknowledge emergencies; the flag survives the per-message state rebuild
-- (design D2). Defaults false — only the emergency node sets it true.
ALTER TABLE cases ADD COLUMN emergency BOOLEAN NOT NULL DEFAULT false;
