-- ============================================================
-- BAOS Performance Indexes
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_port_call_port_time
    ON baos.port_call(port_id, eosp_ts);

CREATE INDEX IF NOT EXISTS idx_port_call_berth
    ON baos.port_call(berth_id);

CREATE INDEX IF NOT EXISTS idx_port_call_vessel_type
    ON baos.port_call(vessel_type);

CREATE INDEX IF NOT EXISTS idx_port_call_valid
    ON baos.port_call(port_id, is_valid_for_training);

CREATE INDEX IF NOT EXISTS idx_port_call_source_hash
    ON baos.port_call(port_id, source_hash);

CREATE INDEX IF NOT EXISTS idx_berth_port
    ON baos.berth(port_id);

CREATE INDEX IF NOT EXISTS idx_capability_berth
    ON baos.berth_capability(berth_id);

CREATE INDEX IF NOT EXISTS idx_optimization_run_port
    ON baos.optimization_run(port_id, started_at);

CREATE INDEX IF NOT EXISTS idx_assumption_port
    ON baos.assumption_config(port_id);

CREATE INDEX IF NOT EXISTS idx_model_registry_port
    ON baos.ml_model_registry(port_id, is_active);

CREATE INDEX IF NOT EXISTS idx_ingestion_batch_file
    ON baos.ingestion_batch(source_file_hash);

CREATE INDEX IF NOT EXISTS idx_stg_port_call_batch
    ON baos.stg_port_call_raw(source_batch_id);
