-- 003_conversation_captured_data.sql — per-conversation capture state (CM-2).
--
-- The conversation state is rebuilt from the DB per message (design D2), so
-- the progressive capture fields (identification, location, equipment,
-- failure, evidence, availability, consent) must persist on the conversation.
-- `captured_data` holds the captured{field: value} dict (internal marker
-- "_pending" tracks which field is currently being asked).
--
-- Applied by db/migrate.sh (idempotent per-file). conversations already has
-- full CRUD grants for the app role (001_init.sql) — no new grant needed.

ALTER TABLE conversations ADD COLUMN captured_data JSONB;
