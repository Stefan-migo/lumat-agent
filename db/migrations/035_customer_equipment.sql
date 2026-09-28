-- 035_customer_equipment.sql — customer equipment records and captured details (D5).

CREATE TABLE customer_equipment (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers (id),
    equipment_type VARCHAR(50),
    brand VARCHAR(100),
    model VARCHAR(100),
    age VARCHAR(100),
    details TEXT,
    source_conversation_id BIGINT REFERENCES conversations (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_customer_equipment_customer_id ON customer_equipment (customer_id);
CREATE UNIQUE INDEX uq_customer_equipment_source_conversation
    ON customer_equipment (source_conversation_id)
    WHERE source_conversation_id IS NOT NULL;

GRANT SELECT, INSERT, UPDATE, DELETE ON customer_equipment TO app;
GRANT USAGE, SELECT ON SEQUENCE customer_equipment_id_seq TO app;
