# PostgreSQL Docker Setup - Complete ✅

**Status**: PostgreSQL configured and ready for trading framework

---

## What Was Done

### 1. PostgreSQL Container Configuration
- **Container**: `mlflow-postgres` (already running)
- **Image**: `postgres:16-alpine`
- **Network**: `trading-network` (Docker internal)
- **Port Mapping**: `5432:5432` (exposed to host) ✅
- **Volumes**: `./data/postgres:/var/lib/postgresql/data` (persistent)

### 2. Trading Database Created
```bash
docker exec mlflow-postgres psql -U mlflow -c "CREATE DATABASE trading;"
```

**Result**: ✅ Database `trading` created

### 3. Schema Deployed
```bash
docker exec -i mlflow-postgres psql -U mlflow -d trading < scripts/db_schema.sql
```

**Tables Created**:
- ✅ `strategies` (3 sample records)
- ✅ `optimization_runs`
- ✅ `backtest_results`

**Views Created**:
- ✅ `strategy_leaderboard`
- ✅ `parameter_performance`
- ✅ `fee_analysis`
- ✅ `daily_summary`

### 4. Connection Verified
```bash
venv/bin/python -c "import psycopg2; conn = psycopg2.connect(dbname='trading', user='mlflow', password='mlflow_secure_password', host='localhost', port='5432'); print('✅ Connected')"
```

**Result**: ✅ Scripts can connect from host to PostgreSQL container

---

## Configuration

### `.env` Settings
```bash
POSTGRES_DB=trading
POSTGRES_USER=mlflow
POSTGRES_PASSWORD=mlflow_secure_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

### `docker-compose.yml` Changes
```yaml
postgres:
  ports:
    - "5432:5432"  # Exposed to host for trading framework scripts
```

---

## How It Works

**Architecture**:
```
Host Machine (scripts run here)
    ↓ (localhost:5432)
Docker Container (mlflow-postgres)
    ↓
PostgreSQL Database (trading)
    ↓
Tables: strategies, optimization_runs, backtest_results
```

**Workflow**:
1. User runs: `venv/bin/python scripts/optimize_runner.py --config my_config.yaml`
2. Script (on host) connects to PostgreSQL via `localhost:5432`
3. Docker routes to container `mlflow-postgres`
4. PostgreSQL processes queries and stores results
5. User queries results via PostgreSQL or scripts

---

## Useful Commands

### Access PostgreSQL from Host
```bash
# Using Python scripts (recommended)
venv/bin/python scripts/optimize_runner.py --config configs/optimizations/rsi_etf_example.yaml

# Using psql directly (if installed)
psql -h localhost -p 5432 -U mlflow -d trading
```

### Access PostgreSQL from Inside Container
```bash
# Execute psql in container
docker exec -it mlflow-postgres psql -U mlflow -d trading

# Run SQL from file
docker exec -i mlflow-postgres psql -U mlflow -d trading < my_query.sql

# Check tables
docker exec mlflow-postgres psql -U mlflow -d trading -c "\dt"

# Query data
docker exec mlflow-postgres psql -U mlflow -d trading -c "SELECT * FROM strategies;"
```

### Container Management
```bash
# Restart PostgreSQL container
docker compose restart postgres

# Recreate container (if config changed)
docker compose up -d postgres

# Check logs
docker logs mlflow-postgres

# Check health
docker exec mlflow-postgres pg_isready -U mlflow
```

---

## Data Persistence

**PostgreSQL data is persistent** thanks to volume mounting:
```yaml
volumes:
  - ./data/postgres:/var/lib/postgresql/data
```

**What this means**:
- Database survives container restarts ✅
- Database survives container recreation ✅
- Database lost only if `./data/postgres/` deleted ❌

**Backup database**:
```bash
# Backup
docker exec mlflow-postgres pg_dump -U mlflow trading > backup_trading.sql

# Restore
docker exec -i mlflow-postgres psql -U mlflow -d trading < backup_trading.sql
```

---

## Troubleshooting

### "Connection refused" Error
**Cause**: PostgreSQL container not running or port not mapped

**Fix**:
```bash
# Check container status
docker ps | grep mlflow-postgres

# Check port mapping
docker port mlflow-postgres
# Should show: 5432/tcp -> 0.0.0.0:5432

# Restart if needed
docker compose up -d postgres
```

### "Database does not exist" Error
**Cause**: Trading database not created

**Fix**:
```bash
docker exec mlflow-postgres psql -U mlflow -c "CREATE DATABASE trading;"
docker exec -i mlflow-postgres psql -U mlflow -d trading < scripts/db_schema.sql
```

### "Tables not found" Error
**Cause**: Schema not deployed

**Fix**:
```bash
docker exec -i mlflow-postgres psql -U mlflow -d trading < scripts/db_schema.sql
```

### "Password authentication failed" Error
**Cause**: Wrong credentials in .env

**Fix**: Verify credentials match docker-compose.yml
```bash
# Check docker-compose.yml
grep -A 5 "postgres:" docker-compose.yml | grep POSTGRES_

# Update .env
POSTGRES_USER=mlflow
POSTGRES_PASSWORD=mlflow_secure_password
```

---

## Next Steps

✅ **PostgreSQL Setup Complete**

**Now Ready For**:
1. Create first optimizable strategy (see `AUTOMATION_SCRIPTS_COMPLETE.md`)
2. Run small test optimization (9 combinations)
3. Verify results in database
4. Run full optimization (50+ combinations)

**Quick Test**:
```bash
# Verify connection works
venv/bin/python -c "import psycopg2; conn = psycopg2.connect(dbname='trading', user='mlflow', password='mlflow_secure_password', host='localhost', port='5432'); print('✅ Ready!'); conn.close()"
```

---

## Summary

🎯 **PostgreSQL is ready for the trading framework!**

**What's Working**:
- ✅ PostgreSQL running in Docker
- ✅ Port exposed to host (localhost:5432)
- ✅ Trading database created
- ✅ Schema deployed (3 tables + 4 views)
- ✅ Connection from host verified
- ✅ Data persistence configured

**What's Next**:
- Create optimizable strategy with `get_parameter()`
- Run optimization via `scripts/optimize_runner.py`
- Query results from database
- Iterate and improve strategies
