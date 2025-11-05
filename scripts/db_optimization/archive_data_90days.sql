
-- MLflow Data Archival Script
-- Epic 17: US-17.14 - Database Archival Strategy
-- Archives experiments and runs older than 90 days

-- Connect to mlflow database
\c mlflow;

-- Create archive schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS archive;

-- Create archive tables if they don't exist
CREATE TABLE IF NOT EXISTS archive.experiments_archived (LIKE experiments INCLUDING ALL);
CREATE TABLE IF NOT EXISTS archive.runs_archived (LIKE runs INCLUDING ALL);
CREATE TABLE IF NOT EXISTS archive.metrics_archived (LIKE metrics INCLUDING ALL);
CREATE TABLE IF NOT EXISTS archive.params_archived (LIKE params INCLUDING ALL);
CREATE TABLE IF NOT EXISTS archive.tags_archived (LIKE tags INCLUDING ALL);

-- Add archived timestamp columns
ALTER TABLE archive.experiments_archived ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP DEFAULT NOW();
ALTER TABLE archive.runs_archived ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP DEFAULT NOW();
ALTER TABLE archive.metrics_archived ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP DEFAULT NOW();
ALTER TABLE archive.params_archived ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP DEFAULT NOW();
ALTER TABLE archive.tags_archived ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP DEFAULT NOW();

-- Archive old experiments (creation time > 90 days ago)
INSERT INTO archive.experiments_archived
SELECT *, NOW() as archived_at FROM experiments
WHERE creation_time < NOW() - INTERVAL '90 days'
AND lifecycle_stage = 'active';

-- Archive associated runs
INSERT INTO archive.runs_archived
SELECT r.*, NOW() as archived_at FROM runs r
JOIN experiments e ON r.experiment_id = e.experiment_id
WHERE e.creation_time < NOW() - INTERVAL '90 days'
AND e.lifecycle_stage = 'active';

-- Archive associated metrics, params, and tags
INSERT INTO archive.metrics_archived
SELECT m.*, NOW() as archived_at FROM metrics m
JOIN runs r ON m.run_uuid = r.run_uuid
JOIN experiments e ON r.experiment_id = e.experiment_id
WHERE e.creation_time < NOW() - INTERVAL '90 days'
AND e.lifecycle_stage = 'active';

INSERT INTO archive.params_archived
SELECT p.*, NOW() as archived_at FROM params p
JOIN runs r ON p.run_uuid = r.run_uuid
JOIN experiments e ON r.experiment_id = e.experiment_id
WHERE e.creation_time < NOW() - INTERVAL '90 days'
AND e.lifecycle_stage = 'active';

INSERT INTO archive.tags_archived
SELECT t.*, NOW() as archived_at FROM tags t
JOIN runs r ON t.run_uuid = r.run_uuid
JOIN experiments e ON r.experiment_id = e.experiment_id
WHERE e.creation_time < NOW() - INTERVAL '90 days'
AND e.lifecycle_stage = 'active';

-- Update lifecycle stage to archived
UPDATE experiments
SET lifecycle_stage = 'archived'
WHERE creation_time < NOW() - INTERVAL '90 days'
AND lifecycle_stage = 'active';

-- Log archival completion
DO $$
DECLARE
    archived_experiments INTEGER;
    archived_runs INTEGER;
BEGIN
    SELECT COUNT(*) INTO archived_experiments FROM experiments WHERE lifecycle_stage = 'archived';
    SELECT COUNT(*) INTO archived_runs FROM runs r JOIN experiments e ON r.experiment_id = e.experiment_id WHERE e.lifecycle_stage = 'archived';

    RAISE NOTICE 'Archival completed at %. Archived % experiments and % runs older than 90 days.',
        NOW(), archived_experiments, archived_runs;
END $$;
