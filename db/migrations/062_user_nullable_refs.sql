-- 062_user_nullable_refs.sql — S6: let a user be hard-deleted without losing the records that
-- reference them.
--
-- `appointments.technician_id` and `project_files.owner_id` are the two "who did it" references that
-- could not be nulled when their user leaves: an appointment and a project file are business records
-- that must survive the user. Making the column nullable means deletion nulls the attribution instead
-- of deleting the record or blocking forever.
--
-- Additive and reversible; no row is deleted or rewritten here.

ALTER TABLE appointments ALTER COLUMN technician_id DROP NOT NULL;
ALTER TABLE project_files ALTER COLUMN owner_id DROP NOT NULL;

-- Rollback: ALTER TABLE project_files ALTER COLUMN owner_id SET NOT NULL;
--           ALTER TABLE appointments ALTER COLUMN technician_id SET NOT NULL;
-- (The rollback requires no NULL values remain in those columns.)
