#!/usr/bin/env python3
"""
Database Optimization - Epic 17: US-17.14
PostgreSQL performance optimization and archival utilities.

This module provides database optimization utilities for the MLflow PostgreSQL backend,
including index creation, archival strategies, and performance monitoring.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """
    Database optimization utilities for MLflow PostgreSQL backend.
    """

    def __init__(self, db_url: str = "postgresql://mlflow:mlflow_secure_password@postgres:5432/mlflow"):
        """
        Initialize database optimizer.

        Args:
            db_url: PostgreSQL connection URL
        """
        self.db_url = db_url
        self.scripts_dir = Path(__file__).parent / "db_optimization"
        self.scripts_dir.mkdir(exist_ok=True)

    def create_performance_indexes(self) -> str:
        """
        Create SQL script for performance indexes.

        Returns:
            Path to the created SQL script
        """
        sql_script = """
-- MLflow PostgreSQL Performance Indexes
-- Epic 17: US-17.14 - Database Performance Optimization

-- Connect to mlflow database
\\c mlflow;

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
"""

        script_path = self.scripts_dir / "performance_indexes.sql"
        script_path.write_text(sql_script)
        logger.info(f"Created performance indexes script: {script_path}")
        return str(script_path)

    def create_archival_script(self, archive_days: int = 90) -> str:
        """
        Create SQL script for archiving old experiments and runs.

        Args:
            archive_days: Number of days after which to archive data

        Returns:
            Path to the created SQL script
        """
        sql_script = f"""
-- MLflow Data Archival Script
-- Epic 17: US-17.14 - Database Archival Strategy
-- Archives experiments and runs older than {archive_days} days

-- Connect to mlflow database
\\c mlflow;

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

-- Archive old experiments (creation time > {archive_days} days ago)
INSERT INTO archive.experiments_archived
SELECT *, NOW() as archived_at FROM experiments
WHERE creation_time < NOW() - INTERVAL '{archive_days} days'
AND lifecycle_stage = 'active';

-- Archive associated runs
INSERT INTO archive.runs_archived
SELECT r.*, NOW() as archived_at FROM runs r
JOIN experiments e ON r.experiment_id = e.experiment_id
WHERE e.creation_time < NOW() - INTERVAL '{archive_days} days'
AND e.lifecycle_stage = 'active';

-- Archive associated metrics, params, and tags
INSERT INTO archive.metrics_archived
SELECT m.*, NOW() as archived_at FROM metrics m
JOIN runs r ON m.run_uuid = r.run_uuid
JOIN experiments e ON r.experiment_id = e.experiment_id
WHERE e.creation_time < NOW() - INTERVAL '{archive_days} days'
AND e.lifecycle_stage = 'active';

INSERT INTO archive.params_archived
SELECT p.*, NOW() as archived_at FROM params p
JOIN runs r ON p.run_uuid = r.run_uuid
JOIN experiments e ON r.experiment_id = e.experiment_id
WHERE e.creation_time < NOW() - INTERVAL '{archive_days} days'
AND e.lifecycle_stage = 'active';

INSERT INTO archive.tags_archived
SELECT t.*, NOW() as archived_at FROM tags t
JOIN runs r ON t.run_uuid = r.run_uuid
JOIN experiments e ON r.experiment_id = e.experiment_id
WHERE e.creation_time < NOW() - INTERVAL '{archive_days} days'
AND e.lifecycle_stage = 'active';

-- Update lifecycle stage to archived
UPDATE experiments
SET lifecycle_stage = 'archived'
WHERE creation_time < NOW() - INTERVAL '{archive_days} days'
AND lifecycle_stage = 'active';

-- Log archival completion
DO $$
DECLARE
    archived_experiments INTEGER;
    archived_runs INTEGER;
BEGIN
    SELECT COUNT(*) INTO archived_experiments FROM experiments WHERE lifecycle_stage = 'archived';
    SELECT COUNT(*) INTO archived_runs FROM runs r JOIN experiments e ON r.experiment_id = e.experiment_id WHERE e.lifecycle_stage = 'archived';

    RAISE NOTICE 'Archival completed at %. Archived % experiments and % runs older than {archive_days} days.',
        NOW(), archived_experiments, archived_runs;
END $$;
"""

        script_path = self.scripts_dir / f"archive_data_{archive_days}days.sql"
        script_path.write_text(sql_script)
        logger.info(f"Created archival script: {script_path}")
        return str(script_path)

    def create_cleanup_script(self) -> str:
        """
        Create SQL script for database cleanup and maintenance.

        Returns:
            Path to the created SQL script
        """
        sql_script = """
-- MLflow Database Cleanup and Maintenance
-- Epic 17: US-17.14 - Database Maintenance

-- Connect to mlflow database
\\c mlflow;

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
"""

        script_path = self.scripts_dir / "cleanup_maintenance.sql"
        script_path.write_text(sql_script)
        logger.info(f"Created cleanup script: {script_path}")
        return str(script_path)

    def create_monitoring_script(self) -> str:
        """
        Create SQL script for performance monitoring.

        Returns:
            Path to the created SQL script
        """
        sql_script = """
-- MLflow Performance Monitoring
-- Epic 17: US-17.14 - Performance Benchmarking

-- Connect to mlflow database
\\c mlflow;

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
"""

        script_path = self.scripts_dir / "performance_monitoring.sql"
        script_path.write_text(sql_script)
        logger.info(f"Created monitoring script: {script_path}")
        return str(script_path)

    def generate_scaling_guide(self) -> str:
        """
        Generate scaling guide documentation.

        Returns:
            Path to the created guide
        """
        guide_content = """
# MLflow PostgreSQL Scaling Guide
# Epic 17: US-17.14 - Database Scaling Strategy

## Overview
This guide provides recommendations for scaling the MLflow PostgreSQL backend
to handle increasing experiment tracking and optimization workloads.

## Current Configuration
- Database: PostgreSQL 16 (Alpine Linux)
- Storage: Persistent volume at ./data/postgres/
- Connection Pooling: Default (can be enhanced)
- Indexes: Performance optimized for common query patterns

## Performance Benchmarks
Target performance metrics:
- Query time < 1 second for 10K runs
- Index creation time < 5 minutes
- Archival time < 10 minutes for 90-day windows

## Scaling Strategies

### 1. Vertical Scaling (Current Approach)
- Increase PostgreSQL container memory limits
- Add more CPU cores to database container
- Use faster storage (SSD recommended)

### 2. Index Optimization
- Composite indexes for common query patterns
- Partial indexes for recent data
- Regular reindexing during maintenance windows

### 3. Data Archival Strategy
- Archive experiments older than 90 days
- Move archived data to separate schema
- Compress archived data for storage efficiency

### 4. Connection Pooling
- Implement PgBouncer for connection pooling
- Configure appropriate pool sizes based on workload
- Monitor connection usage patterns

### 5. Query Optimization
- Use prepared statements for common queries
- Implement query result caching where appropriate
- Monitor slow queries and optimize as needed

## Maintenance Schedule
- Daily: Vacuum analyze tables
- Weekly: Reindex tables
- Monthly: Archive old data
- Quarterly: Full database maintenance

## Monitoring
- Track query performance metrics
- Monitor index usage statistics
- Alert on slow queries (>1 second)
- Monitor disk space usage

## Backup Strategy
- Daily automated backups
- Point-in-time recovery capability
- Test restore procedures regularly
- Store backups in separate location

## Troubleshooting
- High query latency: Check indexes and analyze tables
- Disk space issues: Implement archival strategy
- Connection issues: Review connection pooling configuration
- Slow imports: Optimize bulk insert operations

## Configuration Examples

### Docker Compose Scaling
```yaml
postgres:
  deploy:
    resources:
      limits:
        memory: 4G
        cpus: '2.0'
      reservations:
        memory: 2G
        cpus: '1.0'
```

### PostgreSQL Tuning
```sql
-- Increase work memory for complex queries
SET work_mem = '64MB';

-- Increase maintenance work memory for index creation
SET maintenance_work_mem = '256MB';

-- Enable autovacuum
ALTER SYSTEM SET autovacuum = on;
```

## Performance Testing
Use the included monitoring scripts to benchmark performance:
1. Run performance_monitoring.sql before optimization
2. Apply performance_indexes.sql
3. Run performance_monitoring.sql after optimization
4. Compare results and adjust as needed

## Contact
For scaling issues or performance concerns, refer to the database optimization scripts
in the `scripts/db_optimization/` directory.
"""

        guide_path = self.scripts_dir / "scaling_guide.md"
        guide_path.write_text(guide_content)
        logger.info(f"Created scaling guide: {guide_path}")
        return str(guide_path)

    def run_all_optimizations(self) -> Dict[str, str]:
        """
        Generate all optimization scripts and documentation.

        Returns:
            Dictionary mapping script types to file paths
        """
        scripts = {}

        # Create all optimization scripts
        scripts['performance_indexes'] = self.create_performance_indexes()
        scripts['archival'] = self.create_archival_script()
        scripts['cleanup'] = self.create_cleanup_script()
        scripts['monitoring'] = self.create_monitoring_script()
        scripts['scaling_guide'] = self.generate_scaling_guide()

        logger.info(f"Generated {len(scripts)} optimization scripts and guides")
        return scripts


def main():
    """Main function to run database optimization."""
    optimizer = DatabaseOptimizer()

    print("Generating MLflow PostgreSQL optimization scripts...")
    scripts = optimizer.run_all_optimizations()

    print("\nGenerated scripts:")
    for script_type, path in scripts.items():
        print(f"- {script_type}: {path}")

    print("\nNext steps:")
    print("1. Review and execute performance_indexes.sql on your PostgreSQL instance")
    print("2. Set up automated archival using archive_data_90days.sql")
    print("3. Schedule regular cleanup with cleanup_maintenance.sql")
    print("4. Monitor performance using performance_monitoring.sql")
    print("5. Refer to scaling_guide.md for capacity planning")


if __name__ == "__main__":
    main()