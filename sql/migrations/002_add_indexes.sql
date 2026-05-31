-- Migration 002: Add performance indexes on hot-path query columns.

CREATE INDEX IF NOT EXISTS idx_baos_port_call_port_id
  ON baos.port_call(port_id);

CREATE INDEX IF NOT EXISTS idx_baos_port_call_berth_id
  ON baos.port_call(berth_id);

CREATE INDEX IF NOT EXISTS idx_baos_port_call_eosp_ts
  ON baos.port_call(eosp_ts);

CREATE INDEX IF NOT EXISTS idx_baos_port_call_vessel_type
  ON baos.port_call(vessel_type);

CREATE INDEX IF NOT EXISTS idx_baos_port_call_port_berth
  ON baos.port_call(port_id, berth_id);

CREATE INDEX IF NOT EXISTS idx_baos_port_call_valid_training
  ON baos.port_call(port_id, is_valid_for_training);

CREATE INDEX IF NOT EXISTS idx_baos_berth_port_id
  ON baos.berth(port_id);

CREATE INDEX IF NOT EXISTS idx_baos_berth_port_code
  ON baos.berth(port_id, berth_code);

CREATE INDEX IF NOT EXISTS idx_baos_capability_berth_id
  ON baos.berth_capability(berth_id);

CREATE INDEX IF NOT EXISTS idx_baos_ml_model_registry_port_active
  ON baos.ml_model_registry(port_id, is_active);
