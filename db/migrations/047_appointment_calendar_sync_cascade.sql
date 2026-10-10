-- 047_appointment_calendar_sync_cascade.sql — remove calendar sync rows with their appointment.

ALTER TABLE appointment_calendar_sync DROP CONSTRAINT IF EXISTS appointment_calendar_sync_appointment_id_fkey;
-- Rollback: ALTER TABLE appointment_calendar_sync ADD CONSTRAINT appointment_calendar_sync_appointment_id_fkey FOREIGN KEY (appointment_id) REFERENCES appointments (id);
ALTER TABLE appointment_calendar_sync ADD CONSTRAINT appointment_calendar_sync_appointment_id_fkey
    FOREIGN KEY (appointment_id) REFERENCES appointments (id) ON DELETE CASCADE;
-- Rollback: ALTER TABLE appointment_calendar_sync DROP CONSTRAINT IF EXISTS appointment_calendar_sync_appointment_id_fkey;
