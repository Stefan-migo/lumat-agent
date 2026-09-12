-- 023_panel_cost_llm.sql — measured spend for internal assistant requests.

ALTER TABLE internal_chat_messages
    ADD COLUMN IF NOT EXISTS cost_llm NUMERIC(12, 6);

GRANT SELECT, INSERT, UPDATE, DELETE ON internal_chat_messages TO app;
GRANT USAGE, SELECT ON SEQUENCE internal_chat_messages_id_seq TO app;
