-- 064_conversation_turn_count.sql — chat-rafagas S3: count TURNS, not messages.
--
-- `ConversationState.from_db` derived the turn number from
-- `count(*.messages where direction = 'inbound')`, which counts messages the bot
-- never answered as one turn. A customer who writes "Hola" and "¿Cómo estás?"
-- before the first reply inflates that count to 2, so `receive` never treats the
-- conversation as a first contact (`state.turn <= 1`).
--
-- `turn_count` is incremented exactly once per graph run by `run_conversation`,
-- which is the only writer of a turn. Existing conversations are backfilled from
-- their persisted inbound history so the operator-facing turn number keeps
-- matching the transcript it was written next to.
--
-- Additive and reversible; no row is deleted.

ALTER TABLE conversations ADD COLUMN turn_count integer NOT NULL DEFAULT 0;

UPDATE conversations c
SET turn_count = inbound.total
FROM (
    SELECT conversation_id, count(*) AS total
    FROM messages
    WHERE direction = 'inbound'
    GROUP BY conversation_id
) AS inbound
WHERE inbound.conversation_id = c.id;

-- Rollback: ALTER TABLE conversations DROP COLUMN turn_count;
