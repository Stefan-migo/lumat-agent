-- 009_memory.sql — persistent, domain-aware memory layer over pgvector.
--
-- MEM-1: typed memories per (proyecto, scope, entity_id) keyed by topic_key,
-- hybrid semantic+FTS recall, typed observations, and a schema-only relations
-- table (deferred worker; design "Ponytail explicit deferrals").
--
-- Single-agent: only proyecto='default' is writable (MEM-2, enforced in the
-- service layer). Embeddings reuse the local fastembed model (384d) via
-- kb.embed_texts() — same model as kb_chunks (008_local_embeddings.sql).
--
-- Idempotency is handled by db/migrate.sh via schema_migrations (runs once).

-- MEM-3 hybrid search fuses pgvector cosine with pg_trgm FTS on content, so the
-- trigram extension is a hard dependency of this migration.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TYPE memory_type AS ENUM ('decision','discovery','pattern','preference','customer_memo','summary','session','prompt');
CREATE TYPE memory_status AS ENUM ('active','needs_review','archived');
CREATE TYPE observation_type AS ENUM ('recurrencia','sin_respuesta','riesgo','oportunidad');

CREATE TABLE memories (
  id BIGSERIAL PRIMARY KEY,
  proyecto VARCHAR(100) NOT NULL DEFAULT 'default',
  scope VARCHAR(100) NOT NULL,
  entity_id VARCHAR(100) NOT NULL,
  tipo memory_type NOT NULL DEFAULT 'decision',
  titulo VARCHAR(255) NOT NULL,
  contenido TEXT NOT NULL,
  embedding vector(384) NOT NULL,
  topic_key VARCHAR(255) NOT NULL DEFAULT 'general',
  pin BOOLEAN NOT NULL DEFAULT FALSE,
  review_after TIMESTAMPTZ,
  status memory_status NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (proyecto, scope, entity_id, topic_key)
);

CREATE INDEX idx_memories_embedding_hnsw ON memories USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);
CREATE INDEX idx_memories_entity ON memories (scope, entity_id);

CREATE TABLE memory_relations (
  id BIGSERIAL PRIMARY KEY,
  id_a BIGINT NOT NULL REFERENCES memories(id),
  id_b BIGINT NOT NULL REFERENCES memories(id),
  relation VARCHAR(50) NOT NULL,        -- supersedes|conflicts|related|compatible|scoped|not_conflict
  confidence REAL NOT NULL DEFAULT 1.0,
  reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (id_a <> id_b)
);

CREATE TABLE memory_observations (
  id BIGSERIAL PRIMARY KEY,
  memory_id BIGINT REFERENCES memories(id),
  scope VARCHAR(100) NOT NULL,
  entity_id VARCHAR(100) NOT NULL,
  tipo observation_type NOT NULL,
  detalle JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_memory_observations_entity ON memory_observations (scope, entity_id);

GRANT SELECT,INSERT,UPDATE,DELETE ON memories,memory_relations,memory_observations TO app;
GRANT USAGE,SELECT ON SEQUENCE memories_id_seq,memory_relations_id_seq,memory_observations_id_seq TO app;
