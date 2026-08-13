-- 005_case_emergency_ack.sql — notification/ack state on cases (EM-4, T4.3).
--
-- T4.3.1: notified_at marks when the owner/technician emergency notification
-- was delivered on ANY channel (WhatsApp `emergency_alert` template or the
-- email fallback). The reminder sweep keys off it: unacked + notified >15 min
-- + fewer than 2 reminders -> reminder email.
-- T4.3.2: acknowledged_at + ack_by record the ack (reply-keyword ack from the
-- webhook ingest flow; the panel ack button lands in T5.3 on the same columns).
--
-- Applied by db/migrate.sh (idempotent per-file). Same grants pattern as 004 —
-- ALTER TABLE needs no new grant for the `app` role.

ALTER TABLE cases ADD COLUMN notified_at TIMESTAMPTZ;
ALTER TABLE cases ADD COLUMN acknowledged_at TIMESTAMPTZ;
ALTER TABLE cases ADD COLUMN ack_by VARCHAR(100);
ALTER TABLE cases ADD COLUMN reminder_count INTEGER NOT NULL DEFAULT 0;
