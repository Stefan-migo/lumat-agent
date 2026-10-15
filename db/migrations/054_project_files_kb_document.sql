-- 054_project_files_kb_document.sql — link a project file to the KB document it indexed into.
--
-- Uploading a supported project file already ingests it into the project-scoped
-- KB (app/services/project_files.py -> ingest_project_file). Without a stored
-- link the panel cannot tell an indexed file from a skipped or failed one, so
-- the same document was listed both as a project file and as knowledge.
-- Null means "not indexed" (image or text-less payload); a failed ingestion
-- leaves project_files.status = 'failed' with this column null.
ALTER TABLE project_files
    ADD COLUMN kb_document_id BIGINT REFERENCES kb_documents(id) ON DELETE SET NULL;

CREATE INDEX idx_project_files_kb_document ON project_files (kb_document_id);

-- Backfill the link for files uploaded before this column existed. The link is
-- recoverable from the chunk provenance written by ingest_project_file.
UPDATE project_files pf
SET kb_document_id = c.document_id
FROM (
    SELECT (source_meta->>'project_file_id')::bigint AS project_file_id,
           min(document_id) AS document_id
    FROM kb_chunks
    WHERE source_meta->>'project_file_id' IS NOT NULL
    GROUP BY 1
) c
WHERE pf.id = c.project_file_id AND pf.kb_document_id IS NULL;

-- Rollback: DROP INDEX IF EXISTS idx_project_files_kb_document; ALTER TABLE project_files DROP COLUMN IF EXISTS kb_document_id;
