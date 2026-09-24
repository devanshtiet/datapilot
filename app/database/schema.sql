-- DataPilot — PostgreSQL schema
-- Apply with: psql -d datapilot -f schema.sql
-- (Mission 3+)

CREATE TABLE IF NOT EXISTS audit_log (
    id               SERIAL PRIMARY KEY,
    run_id           VARCHAR(64)  NOT NULL,
    dataset_version  VARCHAR(64)  NOT NULL,
    tool_name        VARCHAR(128) NOT NULL,
    input_summary    TEXT,
    output_summary   TEXT,
    success          BOOLEAN      NOT NULL DEFAULT TRUE,
    error_message    TEXT,
    duration_ms      FLOAT,
    created_at       TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_run_id          ON audit_log(run_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_dataset_version ON audit_log(dataset_version);

CREATE TABLE IF NOT EXISTS insight_feedback (
    id               SERIAL PRIMARY KEY,
    run_id           VARCHAR(64)  NOT NULL,
    dataset_version  VARCHAR(64)  NOT NULL,
    insight_id       VARCHAR(128) NOT NULL,
    feedback         VARCHAR(32)  NOT NULL CHECK (feedback IN ('correct','incorrect','unclear')),
    created_at       TIMESTAMP    NOT NULL DEFAULT NOW()
);
