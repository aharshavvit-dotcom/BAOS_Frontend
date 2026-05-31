-- Migration 004: Add training_runs table for model version history.

CREATE TABLE IF NOT EXISTS baos.training_runs (
  id               SERIAL PRIMARY KEY,
  model_name       VARCHAR(100) NOT NULL,
  version          INTEGER NOT NULL DEFAULT 1,
  trained_at       TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  train_score      DOUBLE PRECISION,
  val_score        DOUBLE PRECISION,
  data_rows        INTEGER,
  feature_hash     VARCHAR(64),
  hyperparameters  JSONB,
  status           VARCHAR(20) DEFAULT 'completed',
  error_message    TEXT,
  created_at       TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_training_runs_model_name
  ON baos.training_runs(model_name);

CREATE INDEX IF NOT EXISTS idx_training_runs_trained_at
  ON baos.training_runs(trained_at DESC);

COMMENT ON TABLE baos.training_runs IS
  'Audit log of every model training run. One row per train call.';
