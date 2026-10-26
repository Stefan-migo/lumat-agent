-- Persist inbound WhatsApp media metadata and bounded download attempts.
ALTER TABLE messages
    ADD COLUMN stored_path text,
    ADD COLUMN content_type varchar(255),
    ADD COLUMN filename text,
    ADD COLUMN size_bytes bigint,
    ADD COLUMN caption text,
    ADD COLUMN media_attempts integer NOT NULL DEFAULT 0,
    ADD CONSTRAINT messages_media_attempts_nonnegative
        CHECK (media_attempts >= 0);

-- Rollback: ALTER TABLE messages DROP COLUMN media_attempts, DROP COLUMN caption, DROP COLUMN size_bytes, DROP COLUMN filename, DROP COLUMN content_type, DROP COLUMN stored_path;
