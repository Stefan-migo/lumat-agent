-- 066_commitments.sql — D6: preserve the owner's explicit promises as durable work.
--
-- The corpus measured 58 owner messages containing a promise, including work that
-- was completed late, never completed, or left open. Conversation summaries and
-- events cannot preserve the exact promise text or its explicitly stated due date.
-- Each row therefore keeps the message verbatim and links it to its customer/thread.

CREATE TABLE commitments (
    id bigserial PRIMARY KEY,
    conversation_id bigint REFERENCES conversations(id),
    customer_id bigint NOT NULL REFERENCES customers(id),
    source_message_id bigint REFERENCES messages(id),
    promise_text text NOT NULL,
    actor varchar(20) NOT NULL CHECK (actor IN ('bot', 'operador')),
    due_at timestamptz,
    status varchar(20) NOT NULL DEFAULT 'pendiente'
        CHECK (status IN ('pendiente', 'cumplido', 'descartado')),
    resolved_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_commitments_conversation_id ON commitments (conversation_id);
CREATE INDEX idx_commitments_customer_id ON commitments (customer_id);
CREATE INDEX idx_commitments_status_due_at ON commitments (status, due_at);
CREATE UNIQUE INDEX uq_commitments_source_message_id ON commitments (source_message_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON commitments TO app;
GRANT USAGE, SELECT ON SEQUENCE commitments_id_seq TO app;

-- Rollback: DROP TABLE commitments;
