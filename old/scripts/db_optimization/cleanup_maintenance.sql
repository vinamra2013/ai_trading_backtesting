
-- MLflow Database Cleanup and Maintenance
-- Epic 17: US-17.14 - Database Maintenance

-- Connect to mlflow database
\c mlflow;

-- Vacuum analyze for better query performance
VACUUM ANALYZE experiments;
VACUUM ANALYZE runs;
VACUUM ANALYZE metrics;
VACUUM ANALYZE params;
VACUUM ANALYZE tags;

-- Reindex for optimal performance
REINDEX TABLE experiments;
REINDEX TABLE runs;
REINDEX TABLE metrics;
REINDEX TABLE params;
REINDEX TABLE tags;

-- Clean up orphaned records (runs without experiments)
DELETE FROM metrics WHERE run_uuid NOT IN (SELECT run_uuid FROM runs);
DELETE FROM params WHERE run_uuid NOT IN (SELECT run_uuid FROM runs);
DELETE FROM tags WHERE run_uuid NOT IN (SELECT run_uuid FROM runs);

-- Update table statistics
ANALYZE;

-- Log cleanup completion
DO $$
BEGIN
    RAISE NOTICE 'Database cleanup completed at %. Tables vacuumed, reindexed, and analyzed.', NOW();
    RAISE NOTICE 'Removed orphaned records from metrics, params, and tags tables.';
END $$;
