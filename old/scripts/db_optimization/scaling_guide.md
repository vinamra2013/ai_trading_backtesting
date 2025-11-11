
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
