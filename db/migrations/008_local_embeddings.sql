-- 008_local_embeddings.sql — kb_chunks.embedding vector(1536) -> vector(384).
--
-- Local fastembed embeddings replaced OpenAI text-embedding-3-small (1536d)
-- with the multilingual paraphrase-multilingual-MiniLM-L12-v2 (384d). A
-- vector(1536) column cannot be resized to vector(384) while holding 1536-d
-- values, and re-embedding old rows against the new local model would be a
-- second full pass over the old (OpenAI) provider.
--
-- Pre-production data reset (documented decision): this project has no real
-- deployed data, so the clean migration is TRUNCATE the KB tables (chunks +
-- documents; audit_log is untouched) then resize the column. Prod upgrade
-- path (when data exists): back up, truncate KB, migrate, full re-ingest via
-- the panel KB manager — the re-ingest re-embeds everything locally.
--
-- The HNSW index is dropped and recreated because it was built for the 1536-d
-- column; ALTER COLUMN TYPE on a vector column with a live HNSW index fails.
-- Idempotency is handled by db/migrate.sh via schema_migrations (runs once).

TRUNCATE kb_chunks, kb_documents RESTART IDENTITY CASCADE;
DROP INDEX IF EXISTS idx_kb_chunks_embedding_hnsw;
ALTER TABLE kb_chunks ALTER COLUMN embedding TYPE vector(384);
CREATE INDEX idx_kb_chunks_embedding_hnsw
    ON kb_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
