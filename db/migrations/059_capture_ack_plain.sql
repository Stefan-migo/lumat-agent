-- 059_capture_ack_plain.sql — S1: stop thanking the customer before they gave anything.
--
-- The shipped default for `reply.texts.capture_ack` was `Gracias {{nombre}}. `, and production
-- keeps an explicit copy of it in `settings`. `db/seed.sh` is idempotent (it inserts missing rows and
-- leaves present ones alone), so changing the Python default never reaches a deployed database: the
-- conversation would keep saying "Gracias Stefan." forever.
--
-- The rewrite is guarded by equality with the OLD shipped default, so a text the owner edited by hand
-- in the panel is never overwritten.

UPDATE settings
SET value = jsonb_set(value, '{capture_ack}', to_jsonb('Entiendo. '::text), true)
WHERE key = 'reply.texts'
  AND value ->> 'capture_ack' = 'Gracias {{nombre}}. ';

-- Rollback: UPDATE settings
--             SET value = jsonb_set(value, '{capture_ack}', to_jsonb('Gracias {{nombre}}. '::text), true)
--           WHERE key = 'reply.texts'
--             AND value ->> 'capture_ack' = 'Entiendo. ';
