-- 056_appointment_technician_state.sql — technician field quick-action state (S5/S6).

-- A new axis for the field quick actions, deliberately NOT folded into
-- appointment_status: `en_route` and `arrived` describe where the technician is
-- relative to the visit, not the visit's own lifecycle.
CREATE TYPE technician_visit_state AS ENUM ('en_route', 'arrived');

ALTER TABLE appointments
    ADD COLUMN technician_state technician_visit_state,
    ADD COLUMN technician_state_at TIMESTAMPTZ;
-- Rollback: ALTER TABLE appointments DROP COLUMN IF EXISTS technician_state, DROP COLUMN IF EXISTS technician_state_at; DROP TYPE IF EXISTS technician_visit_state;
