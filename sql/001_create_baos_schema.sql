-- ============================================================
-- BAOS Core Schema — Phase 1
-- PostgreSQL 13+
-- Creates the 'baos' schema with all domain tables
-- ============================================================

CREATE SCHEMA IF NOT EXISTS baos;

-- ── 1. Ingestion Batch ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS baos.ingestion_batch (
    batch_id            UUID PRIMARY KEY,
    source_file_name    TEXT NOT NULL,
    source_file_hash    TEXT NOT NULL,
    source_file_type    TEXT,
    port_code           TEXT,
    load_status         TEXT NOT NULL DEFAULT 'PENDING',
    total_rows          INTEGER DEFAULT 0,
    inserted_rows       INTEGER DEFAULT 0,
    updated_rows        INTEGER DEFAULT 0,
    rejected_rows       INTEGER DEFAULT 0,
    error_message       TEXT,
    started_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at        TIMESTAMP
);

-- ── 2. Port ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS baos.port (
    port_id     UUID PRIMARY KEY,
    port_code   TEXT UNIQUE NOT NULL,
    port_name   TEXT NOT NULL,
    country     TEXT DEFAULT 'India',
    timezone    TEXT DEFAULT 'Asia/Kolkata',
    latitude    DOUBLE PRECISION,
    longitude   DOUBLE PRECISION,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── 3. Berth ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS baos.berth (
    berth_id            UUID PRIMARY KEY,
    port_id             UUID NOT NULL REFERENCES baos.port(port_id),
    berth_code          TEXT NOT NULL,
    berth_name          TEXT,
    terminal_name       TEXT,
    berth_class         TEXT,
    max_loa_m           DOUBLE PRECISION,
    max_beam_m          DOUBLE PRECISION,
    max_draft_m         DOUBLE PRECISION,
    depth_m             DOUBLE PRECISION,
    length_m            DOUBLE PRECISION,
    is_active           BOOLEAN DEFAULT TRUE,
    data_quality_level  TEXT DEFAULT 'SPEC',
    source_batch_id     UUID REFERENCES baos.ingestion_batch(batch_id),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(port_id, berth_code)
);

-- ── 4. Berth Capability ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS baos.berth_capability (
    capability_id               UUID PRIMARY KEY,
    berth_id                    UUID NOT NULL REFERENCES baos.berth(berth_id),
    vessel_type                 TEXT,
    cargo_type                  TEXT,
    equipment_type              TEXT,
    equipment_count             INTEGER,
    handling_rate_tons_per_hour  DOUBLE PRECISION,
    priority_level              INTEGER DEFAULT 0,
    is_preferred                BOOLEAN DEFAULT FALSE,
    capability_score            DOUBLE PRECISION,
    data_quality_level          TEXT DEFAULT 'SPEC',
    source_batch_id             UUID REFERENCES baos.ingestion_batch(batch_id),
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── 5. Port Call (Historical) ───────────────────────────────
CREATE TABLE IF NOT EXISTS baos.port_call (
    port_call_id        UUID PRIMARY KEY,
    port_id             UUID NOT NULL REFERENCES baos.port(port_id),

    vessel_name         TEXT,
    vessel_imo          TEXT,
    vessel_type         TEXT,
    cargo_type          TEXT,

    berth_id            UUID REFERENCES baos.berth(berth_id),
    berth_code_raw      TEXT,

    loa_m               DOUBLE PRECISION,
    beam_m              DOUBLE PRECISION,
    arrival_draft_m     DOUBLE PRECISION,
    departure_draft_m   DOUBLE PRECISION,
    dwt                 DOUBLE PRECISION,
    cargo_tons          DOUBLE PRECISION,

    eosp_ts             TIMESTAMP,
    pob_ts              TIMESTAMP,
    all_fast_ts         TIMESTAMP,
    last_line_ts        TIMESTAMP,
    cosp_ts             TIMESTAMP,

    pilot_wait_hours            DOUBLE PRECISION,
    pilot_to_berth_hours        DOUBLE PRECISION,
    berth_occupancy_hours       DOUBLE PRECISION,
    unberth_outbound_hours      DOUBLE PRECISION,
    total_port_stay_hours       DOUBLE PRECISION,

    is_valid_for_training       BOOLEAN DEFAULT TRUE,
    validation_status           TEXT DEFAULT 'VALID',
    validation_notes            TEXT,

    source_batch_id     UUID REFERENCES baos.ingestion_batch(batch_id),
    source_file_name    TEXT,
    source_sheet_name   TEXT,
    source_row_number   INTEGER,
    source_hash         TEXT,

    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(port_id, source_hash)
);

-- ── 6. Assumption Configuration ─────────────────────────────
CREATE TABLE IF NOT EXISTS baos.assumption_config (
    assumption_id           UUID PRIMARY KEY,
    port_id                 UUID REFERENCES baos.port(port_id),
    assumption_key          TEXT NOT NULL,
    assumption_value        DOUBLE PRECISION NOT NULL,
    unit                    TEXT,
    source_quality          TEXT DEFAULT 'ASSUMPTION',
    confidence_multiplier   DOUBLE PRECISION DEFAULT 0.80,
    description             TEXT,
    used_in_decision        BOOLEAN DEFAULT TRUE,
    is_active               BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(port_id, assumption_key)
);

-- ── 7. ML Model Registry ────────────────────────────────────
CREATE TABLE IF NOT EXISTS baos.ml_model_registry (
    model_id            UUID PRIMARY KEY,
    port_id             UUID NOT NULL REFERENCES baos.port(port_id),
    model_name          TEXT NOT NULL,
    model_type          TEXT NOT NULL,
    target_name         TEXT NOT NULL,
    model_version       TEXT NOT NULL,
    artifact_path       TEXT,
    feature_schema      JSONB,
    metrics             JSONB,
    baseline_metrics    JSONB,
    training_start_ts   TIMESTAMP,
    training_end_ts     TIMESTAMP,
    training_rows       INTEGER,
    validation_rows     INTEGER,
    test_rows           INTEGER,
    split_strategy      TEXT,
    data_start_ts       TIMESTAMP,
    data_end_ts         TIMESTAMP,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(port_id, model_name, model_version)
);

-- ── 8. Optimization Run ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS baos.optimization_run (
    optimization_run_id UUID PRIMARY KEY,
    port_id             UUID NOT NULL REFERENCES baos.port(port_id),
    scenario_name       TEXT,
    solver_status       TEXT,
    objective_value     DOUBLE PRECISION,
    total_wait_hours    DOUBLE PRECISION,
    total_cost_usd      DOUBLE PRECISION,
    assigned_count      INTEGER,
    unassigned_count    INTEGER,
    config              JSONB,
    assumptions_used    JSONB,
    request_payload     JSONB,
    result_summary      JSONB,
    started_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at        TIMESTAMP
);

-- ── 9. Optimization Assignment ──────────────────────────────
CREATE TABLE IF NOT EXISTS baos.optimization_assignment (
    assignment_id           UUID PRIMARY KEY,
    optimization_run_id     UUID NOT NULL REFERENCES baos.optimization_run(optimization_run_id),
    vessel_temp_id          TEXT NOT NULL,
    vessel_name             TEXT,
    berth_id                UUID REFERENCES baos.berth(berth_id),
    berth_code              TEXT,
    assigned                BOOLEAN DEFAULT TRUE,
    start_ts                TIMESTAMP,
    end_ts                  TIMESTAMP,
    wait_hours              DOUBLE PRECISION,
    service_hours           DOUBLE PRECISION,
    service_time_source     TEXT,
    cost_usd                DOUBLE PRECISION,
    confidence_score        DOUBLE PRECISION,
    risk_level              TEXT,
    explanation             JSONB,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── 10. Recommendation Log ──────────────────────────────────
CREATE TABLE IF NOT EXISTS baos.recommendation_log (
    recommendation_id   UUID PRIMARY KEY,
    port_id             UUID NOT NULL REFERENCES baos.port(port_id),
    vessel_payload      JSONB NOT NULL,
    recommendations     JSONB NOT NULL,
    assumptions_used    JSONB,
    model_versions      JSONB,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── Staging Tables ──────────────────────────────────────────

CREATE TABLE IF NOT EXISTS baos.stg_berth_config_raw (
    id                  BIGSERIAL PRIMARY KEY,
    raw_payload         JSONB NOT NULL,
    source_file_name    TEXT,
    source_sheet_name   TEXT,
    source_row_number   INTEGER,
    source_batch_id     UUID REFERENCES baos.ingestion_batch(batch_id),
    source_hash         TEXT,
    loaded_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS baos.stg_berth_capability_raw (
    id                  BIGSERIAL PRIMARY KEY,
    raw_payload         JSONB NOT NULL,
    source_file_name    TEXT,
    source_sheet_name   TEXT,
    source_row_number   INTEGER,
    source_batch_id     UUID REFERENCES baos.ingestion_batch(batch_id),
    source_hash         TEXT,
    loaded_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS baos.stg_port_call_raw (
    id                  BIGSERIAL PRIMARY KEY,
    raw_payload         JSONB NOT NULL,
    source_file_name    TEXT,
    source_sheet_name   TEXT,
    source_row_number   INTEGER,
    source_batch_id     UUID REFERENCES baos.ingestion_batch(batch_id),
    source_hash         TEXT,
    loaded_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
