-- 067_message_transcript.sql — retain local audio transcription beside its message.
--
-- New inbound audio is processed asynchronously, outside the webhook path. The
-- transcript is separate from the original message text, while the timestamp
-- and bounded attempt counter let a future sweep find unfinished work safely.
-- The partial index keeps that sweep focused on inbound audio that still lacks
-- a transcript, ordered by arrival time rather than scanning message history.

ALTER TABLE messages
    ADD COLUMN transcript text,
    ADD COLUMN transcript_at timestamptz,
    ADD COLUMN transcript_attempts integer NOT NULL DEFAULT 0,
    ADD CONSTRAINT messages_transcript_attempts_check
        CHECK (transcript_attempts >= 0);

CREATE INDEX idx_messages_audio_transcript_pending
    ON messages (created_at)
    WHERE msg_type = 'audio' AND direction = 'inbound' AND transcript IS NULL;

-- Rollback: DROP INDEX idx_messages_audio_transcript_pending; ALTER TABLE messages DROP CONSTRAINT messages_transcript_attempts_check, DROP COLUMN transcript_attempts, DROP COLUMN transcript_at, DROP COLUMN transcript;
