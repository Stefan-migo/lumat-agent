-- 048_technician_weekly_schedule.sql — normalized weekly technician availability.

CREATE TABLE technician_weekly_schedule (
    id BIGSERIAL PRIMARY KEY,
    technician_id BIGINT NOT NULL REFERENCES users (id),
    weekday SMALLINT NOT NULL,
    opens_at TIME NOT NULL,
    closes_at TIME NOT NULL,
    CONSTRAINT uq_technician_weekly_schedule_technician_weekday
        UNIQUE (technician_id, weekday)
);

GRANT SELECT, INSERT, UPDATE, DELETE ON technician_weekly_schedule TO app;
GRANT USAGE, SELECT ON SEQUENCE technician_weekly_schedule_id_seq TO app;
