-- Persist inbound and outbound WhatsApp media metadata; migration 058 is the
-- feature's existing unmerged migration and is intentionally extended in place.
ALTER TABLE messages
    ADD COLUMN stored_path text,
    ADD COLUMN content_type varchar(255),
    ADD COLUMN filename text,
    ADD COLUMN size_bytes bigint,
    ADD COLUMN caption text,
    ADD COLUMN media_attempts integer NOT NULL DEFAULT 0,
    ADD COLUMN meta_media_id varchar(255),
    ADD CONSTRAINT messages_media_attempts_nonnegative
        CHECK (media_attempts >= 0);

-- Rollback: ALTER TABLE messages DROP COLUMN meta_media_id, DROP COLUMN media_attempts, DROP COLUMN caption, DROP COLUMN size_bytes, DROP COLUMN filename, DROP COLUMN content_type, DROP COLUMN stored_path;
