-- 050_kb_chunks_cascade.sql — remove document chunks with their KB document.

ALTER TABLE kb_chunks DROP CONSTRAINT IF EXISTS kb_chunks_document_id_fkey;
-- Rollback: ALTER TABLE kb_chunks ADD CONSTRAINT kb_chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES kb_documents (id);
ALTER TABLE kb_chunks ADD CONSTRAINT kb_chunks_document_id_fkey
    FOREIGN KEY (document_id) REFERENCES kb_documents (id) ON DELETE CASCADE;
-- Rollback: ALTER TABLE kb_chunks DROP CONSTRAINT IF EXISTS kb_chunks_document_id_fkey;
