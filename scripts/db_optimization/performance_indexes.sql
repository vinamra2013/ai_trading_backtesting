
-- MLflow PostgreSQL Performance Indexes
-- Epic 17: US-17.14 - Database Performance Optimization

-- Connect to mlflow database
\c mlflow;

-- Index on experiments table for faster lookups
CREATE INDEX IF NOT EXISTS idx_experiments_name ON experiments (name);
CREATE INDEX IF NOT EXISTS idx_experiments_lifecycle_stage ON experiments (lifecycle_stage);
CREATE INDEX IF NOT EXISTS idx_experiments_creation_time ON experiments (creation_time);

-- Index on runs table for faster queries
CREATE INDEX IF NOT EXISTS idx_runs_experiment_id ON runs (experiment_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs (status);
CREATE INDEX IF NOT EXISTS idx_runs_start_time ON runs (start_time);
CREATE INDEX IF NOT EXISTS idx_runs_end_time ON runs (end_time);

-- Index on metrics table for metric-based queries
CREATE INDEX IF NOT EXISTS idx_metrics_run_uuid ON metrics (run_uuid);
CREATE INDEX IF NOT EXISTS idx_metrics_key ON metrics (key);
CREATE INDEX IF NOT EXISTS idx_metrics_value ON metrics (value);

-- Index on params table for parameter queries
CREATE INDEX IF NOT EXISTS idx_params_run_uuid ON params (run_uuid);
CREATE INDEX IF NOT EXISTS idx_params_key ON params (key);

-- Index on tags table for tag-based filtering
CREATE INDEX IF NOT EXISTS idx_tags_run_uuid ON tags (run_uuid);
CREATE INDEX IF NOT EXISTS idx_tags_key ON tags (key);
CREATE INDEX IF NOT EXISTS idx_tags_value ON tags (value);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_runs_experiment_status ON runs (experiment_id, status);
CREATE INDEX IF NOT EXISTS idx_metrics_run_key ON metrics (run_uuid, key);
CREATE INDEX IF NOT EXISTS idx_tags_key_value ON tags (key, value);

-- Index for time-based queries (last 30 days performance)
CREATE INDEX IF NOT EXISTS idx_runs_recent ON runs (start_time) WHERE start_time > NOW() - INTERVAL '30 days';

-- Index for experiment creation time queries
CREATE INDEX IF NOT EXISTS idx_experiments_recent ON experiments (creation_time) WHERE creation_time > NOW() - INTERVAL '90 days';

-- Analyze tables to update statistics
ANALYZE experiments;
ANALYZE runs;
ANALYZE metrics;
ANALYZE params;
ANALYZE tags;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'MLflow performance indexes created successfully at %', NOW();
END $$;
