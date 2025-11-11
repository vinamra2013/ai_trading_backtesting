
-- MLflow Performance Monitoring
-- Epic 17: US-17.14 - Performance Benchmarking

-- Connect to mlflow database
\c mlflow;

-- Query performance metrics
SELECT
    schemaname,
    tablename,
    n_tup_ins AS inserts,
    n_tup_upd AS updates,
    n_tup_del AS deletes,
    n_live_tup AS live_rows,
    n_dead_tup AS dead_rows
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- Index usage statistics
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- Table size information
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS index_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Experiment and run counts
SELECT
    'experiments' AS table_name,
    COUNT(*) AS total_count,
    COUNT(CASE WHEN lifecycle_stage = 'active' THEN 1 END) AS active_count,
    COUNT(CASE WHEN lifecycle_stage = 'archived' THEN 1 END) AS archived_count
FROM experiments
UNION ALL
SELECT
    'runs' AS table_name,
    COUNT(*) AS total_count,
    COUNT(CASE WHEN status = 'FINISHED' THEN 1 END) AS finished_count,
    COUNT(CASE WHEN status != 'FINISHED' THEN 1 END) AS other_status_count
FROM runs;

-- Log monitoring completion
DO $$
BEGIN
    RAISE NOTICE 'Performance monitoring completed at %', NOW();
END $$;
