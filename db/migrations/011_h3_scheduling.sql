-- 011_h3_scheduling.sql — local scheduling foundation (SS-1/2, CR-8).

CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE TYPE appointment_status AS ENUM ('booked', 'cancelled', 'completed', 'no_show');

CREATE TABLE technician_availability (
    id BIGSERIAL PRIMARY KEY,
    technician_id BIGINT NOT NULL REFERENCES users (id),
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    available BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (ends_at > starts_at)
);

CREATE TABLE appointments (
    id BIGSERIAL PRIMARY KEY,
    service VARCHAR(100) NOT NULL,
    customer_id BIGINT NOT NULL REFERENCES customers (id),
    case_id BIGINT NOT NULL REFERENCES cases (id),
    technician_id BIGINT NOT NULL REFERENCES users (id),
    local_start TIMESTAMP NOT NULL,
    timezone VARCHAR(100) NOT NULL,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
    status appointment_status NOT NULL DEFAULT 'booked',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (ends_at > starts_at),
    CHECK (ends_at - starts_at = make_interval(mins => duration_minutes))
);

CREATE TABLE appointment_history (
    id BIGSERIAL PRIMARY KEY,
    appointment_id BIGINT NOT NULL REFERENCES appointments (id),
    actor VARCHAR(100) NOT NULL,
    action VARCHAR(30) NOT NULL,
    from_status appointment_status,
    to_status appointment_status NOT NULL,
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE appointments ADD CONSTRAINT appointments_technician_no_overlap
    EXCLUDE USING gist (technician_id WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&)
    WHERE (status = 'booked');
ALTER TABLE appointments ADD CONSTRAINT appointments_customer_no_overlap
    EXCLUDE USING gist (customer_id WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&)
    WHERE (status = 'booked');

CREATE INDEX idx_technician_availability_technician_time
    ON technician_availability (technician_id, starts_at, ends_at);
CREATE INDEX idx_appointments_customer ON appointments (customer_id, starts_at);
CREATE INDEX idx_appointments_case ON appointments (case_id, starts_at);
CREATE INDEX idx_appointment_history_appointment ON appointment_history (appointment_id, created_at, id);

GRANT SELECT, INSERT, UPDATE, DELETE ON technician_availability, appointments, appointment_history TO app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app;
