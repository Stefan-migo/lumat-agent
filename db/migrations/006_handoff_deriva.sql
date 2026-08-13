-- 006_handoff_deriva.sql — handoff state model + deriva bundle (T4.4).
--
-- HH-1: every bot/human/closed transition must be recorded with timestamp,
-- cause and actor (system | bot | rule). The `conversation_events` table
-- already carries timestamp + cause; `actor` names the trigger source so the
-- transition log is auditable without parsing the cause string. Existing
-- rows stay NULL (events written before this migration have no actor).
--
-- HH-2: the deriva bundle snapshots the full conversation history, summary,
-- customer ficha data and captured fields onto the case row, so an escalated
-- case is self-contained for the panel (HH-4) and survives later edits to the
-- conversation/customer. One JSONB column; the panel renders the snapshot.

ALTER TABLE conversation_events ADD COLUMN actor VARCHAR(100);
ALTER TABLE cases ADD COLUMN bundle JSONB;
