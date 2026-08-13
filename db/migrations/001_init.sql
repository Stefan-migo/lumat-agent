-- 001_init.sql — LumatAgent initial schema (design Data Model, 10 tables).
--
-- Applied by db/migrate.sh as the ADMIN role (superuser in compose dev/test).
-- The runner creates the least-privilege `app` role first (password from env,
-- never committed) and records this file's version in schema_migrations, so
-- this script runs exactly once per database.
--
-- Grants (SH-5): app role gets INSERT+SELECT only on audit_log (append-only
-- enforced by grants), full CRUD on business tables.

-- pgvector extension (HNSW index on kb_chunks.embedding)
CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------

-- customers.state (CR-3 lifecycle: nuevo … postventa)
CREATE TYPE customer_state AS ENUM (
    'nuevo', 'contactado', 'pendiente', 'agendado', 'en_evaluacion',
    'finalizado', 'cancelado', 'postventa'
);

-- users.role (AP-2)
CREATE TYPE user_role AS ENUM ('admin', 'operador');

-- conversations.state (HH-1)
CREATE TYPE conversation_state AS ENUM ('bot', 'human', 'closed');

-- messages.direction (WH-4)
CREATE TYPE message_direction AS ENUM ('inbound', 'outbound');

-- messages.msg_type (WH-4: text/media from Meta webhook)
CREATE TYPE message_type AS ENUM (
    'text', 'image', 'video', 'audio', 'document', 'sticker',
    'location', 'contacts', 'other'
);

-- messages.status (webhook pipeline: received → processing → processed|failed)
CREATE TYPE message_status AS ENUM ('received', 'processing', 'processed', 'failed');

-- kb_documents.format (KB-1)
CREATE TYPE document_format AS ENUM ('pdf', 'md', 'csv');

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------

-- customers: one record per person, dedup by E.164 phone (CR-1, CR-2)
CREATE TABLE customers (
    id             BIGSERIAL PRIMARY KEY,
    phone_e164     VARCHAR(20)  NOT NULL UNIQUE,
    name           VARCHAR(200),
    email          VARCHAR(200),
    comuna         VARCHAR(100),
    address        TEXT,
    state          customer_state NOT NULL DEFAULT 'nuevo',
    consent_status BOOLEAN NOT NULL DEFAULT FALSE,
    consent_at     TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- users: panel accounts (AP-1, AP-2)
CREATE TABLE users (
    id            BIGSERIAL PRIMARY KEY,
    username      VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,          -- bcrypt
    role          user_role NOT NULL DEFAULT 'operador',
    active        BOOLEAN NOT NULL DEFAULT TRUE,
    failed_logins INTEGER NOT NULL DEFAULT 0,
    locked_until  TIMESTAMPTZ
);

-- conversations: one per customer contact thread (HH-1)
CREATE TABLE conversations (
    id              BIGSERIAL PRIMARY KEY,
    customer_id     BIGINT NOT NULL REFERENCES customers (id),
    wa_phone        VARCHAR(20) NOT NULL,          -- business WhatsApp number
    state           conversation_state NOT NULL DEFAULT 'bot',
    summary         TEXT,
    last_message_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at       TIMESTAMPTZ
);
CREATE INDEX idx_conversations_customer_id ON conversations (customer_id);

-- messages: inbound + outbound, dedup by wamid (inbound only, WH-5)
CREATE TABLE messages (
    id              BIGSERIAL PRIMARY KEY,
    wamid           VARCHAR(255),
    conversation_id BIGINT NOT NULL REFERENCES conversations (id),
    direction       message_direction NOT NULL,
    msg_type        message_type NOT NULL DEFAULT 'text',
    text            TEXT,
    media_url       TEXT,
    status          message_status NOT NULL DEFAULT 'received',
    payload         JSONB,                          -- raw webhook payload (WH-4)
    cost_llm        NUMERIC(12, 6),                 -- D6 cost tracking
    cost_meta       NUMERIC(12, 6),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_messages_conversation_id ON messages (conversation_id);
-- partial unique index: inbound dedup by wamid; outbound rows are not guarded
CREATE UNIQUE INDEX uq_messages_wamid_inbound
    ON messages (wamid) WHERE direction = 'inbound' AND wamid IS NOT NULL;

-- cases: service/priority/status per classification (CM-3, HH-2, AP-5)
CREATE TABLE cases (
    id              BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES conversations (id),
    customer_id     BIGINT NOT NULL REFERENCES customers (id),
    service         VARCHAR(100),
    priority        VARCHAR(20),
    status          VARCHAR(50),
    responsible_id  BIGINT REFERENCES users (id),
    summary         TEXT,
    escalated_at    TIMESTAMPTZ,
    closed_at       TIMESTAMPTZ
);
CREATE INDEX idx_cases_conversation_id ON cases (conversation_id);
CREATE INDEX idx_cases_customer_id ON cases (customer_id);

-- conversation_events: state transitions + escalations (HH-1, operador-visible)
CREATE TABLE conversation_events (
    id              BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES conversations (id),
    event           VARCHAR(100) NOT NULL,
    cause           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_conversation_events_conversation_id
    ON conversation_events (conversation_id);

-- kb_documents: versioned KB documents (KB-1, KB-3, KB-4, D8)
CREATE TABLE kb_documents (
    id             BIGSERIAL PRIMARY KEY,
    title          VARCHAR(255) NOT NULL,
    format         document_format NOT NULL,
    content        TEXT NOT NULL,
    version        INTEGER NOT NULL DEFAULT 1,
    active_version INTEGER NOT NULL DEFAULT 1,
    active         BOOLEAN NOT NULL DEFAULT TRUE,
    provider       VARCHAR(100),                    -- KB-1: embedding provider
    model          VARCHAR(100),                    -- KB-1: embedding model
    cost_meta      NUMERIC(12, 6),                  -- KB-1: cost recorded
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- kb_chunks: chunked + embedded content (KB-1; HNSW index below)
CREATE TABLE kb_chunks (
    id           BIGSERIAL PRIMARY KEY,
    document_id  BIGINT NOT NULL REFERENCES kb_documents (id),
    version      INTEGER NOT NULL,
    chunk_index  INTEGER NOT NULL,
    content      TEXT NOT NULL,
    source_meta  JSONB,
    embedding    VECTOR(1536) NOT NULL,
    UNIQUE (document_id, version, chunk_index)
);
CREATE INDEX idx_kb_chunks_document_id ON kb_chunks (document_id);
-- HNSW index per design: vector_cosine_ops, m=16, ef_construction=64
CREATE INDEX idx_kb_chunks_embedding_hnsw
    ON kb_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- settings: single KV store (D5)
CREATE TABLE settings (
    key        VARCHAR(100) PRIMARY KEY,
    value      JSONB NOT NULL,
    updated_by BIGINT REFERENCES users (id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- audit_log: append-only, INSERT+SELECT only for app role (SH-5)
CREATE TABLE audit_log (
    id         BIGSERIAL PRIMARY KEY,
    actor      VARCHAR(100) NOT NULL,
    action     VARCHAR(100) NOT NULL,
    entity     VARCHAR(100) NOT NULL,
    entity_id  VARCHAR(100),
    before     JSONB,
    after      JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Grants (app role, least privilege — SH-2/SH-5)
-- ---------------------------------------------------------------------------

GRANT USAGE ON SCHEMA public TO app;

-- business tables: full CRUD (webhook ingest, customer/case state, settings)
GRANT SELECT, INSERT, UPDATE, DELETE
    ON customers, users, conversations, messages, cases,
       conversation_events, kb_documents, kb_chunks, settings
    TO app;

-- audit_log: append-only enforced by grants — INSERT + SELECT only
GRANT SELECT, INSERT ON audit_log TO app;

-- sequences for the app role's INSERTs
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app;
