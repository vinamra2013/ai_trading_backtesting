# Epic 8: Deployment & Operations

**Epic Description:** Build deployment automation, configuration management, database persistence, health checks, and backup/restore capabilities. Most infrastructure already complete.

**Architecture Note:** Uses LEAN CLI (`lean live deploy`) with wrapper scripts for validation and lifecycle management.

**Time Estimate:** 8 hours (reduced from 23h - deployment scripts exist, config complete, database complete)
**Priority:** P0 (Critical)
**Dependencies:** Epic 1 (Dev Environment), Epic 5 (Live Trading)
**Completion Status:** 70% (4 of 5 stories complete or nearly complete)

---

## User Stories

### [X] US-8.1: Automated Deployment
**As a developer, I need automated deployment**

**Status:** Complete
**Estimate:** 0 hours (complete)
**Priority:** P0

**Acceptance Criteria:**
- [X] Script: ./scripts/start_live_trading.sh (143 lines with validation)
- [X] Pre-flight checks (IB credentials, config files, algorithm exists)
- [X] Executes `lean live deploy` with IB integration
- [X] Health checks (IB Gateway connectivity test)
- [X] Clear error messages for validation failures
- [X] Stop script: ./scripts/stop_live_trading.sh
- [X] Emergency stop: ./scripts/emergency_stop.sh

**Implementation Details:**
- `start_live_trading.sh`: Validates all prerequisites, deploys via LEAN CLI
- `stop_live_trading.sh`: Graceful shutdown of trading algorithm
- `emergency_stop.sh`: Immediate liquidation of all positions (queries DB for open positions)
- All scripts use venv activation and proper error handling
- Health checks validate IB Gateway connectivity before deployment

---

### [X] US-8.2: Configuration Management
**As a developer, I need configuration management**

**Status:** Complete
**Estimate:** 0 hours (complete)
**Priority:** P0

**Acceptance Criteria:**
- [X] Separate configs created:
  - config/live_trading_config.yaml (trading hours, EOD liquidation, algorithm settings)
  - config/risk_config.yaml (position limits, loss limits, concentration limits)
  - config/backtest_config.yaml (backtest settings, initial capital, resolution)
  - config/cost_config.yaml (IB commission models: ib_standard, ib_pro)
- [X] Environment variables for secrets (.env file)
- [X] .env.example template provided
- [X] Validation in start_live_trading.sh (checks all required variables)
- [X] Clear error messages for missing config

**Implementation Details:**
- All configuration files exist in config/ directory
- LEAN algorithm loads configs via risk_manager and db_logger
- Deployment script validates IB credentials and all required config files
- Supports paper and live trading modes via trading_mode variable

---

### [X] US-8.3: Database Persistence
**As a developer, I need database persistence**

**Status:** Complete
**Estimate:** 0 hours (complete)
**Priority:** P1 (High)

**Acceptance Criteria:**
- [X] SQLite for trade history (scripts/db_manager.py)
- [X] Complete schema (8 tables):
  - orders, positions, position_history
  - daily_summaries, risk_events, risk_metrics
  - emergency_stops, trading_state
- [X] WAL mode enabled for concurrent access
- [X] Foreign key constraints and indexes
- [X] Database logger (algorithms/live_strategy/db_logger.py)
- [X] Docker volume mount (data/sqlite/ persisted across restarts)

**Implementation Details:**
- `scripts/db_manager.py`: Complete schema creation and query utilities
- `algorithms/live_strategy/db_logger.py`: Integrates with LEAN algorithm
- All queries logged with timestamps for audit trail
- Data persists across container restarts via Docker volume mount
- Tables have proper foreign key relationships and indexes

---

### [~] US-8.4: Health Monitoring
**As an operator, I need health monitoring**

**Status:** Partially Complete
**Estimate:** 4 hours (remaining work)
**Priority:** P1 (High)

**Acceptance Criteria:**
- [X] IB Gateway health check in docker-compose.yml (nc -z localhost 4001)
- [X] Pre-deployment health check in start_live_trading.sh
- [X] Docker auto-restart on failure (restart: unless-stopped)
- [X] Log health check results
- [ ] Runtime health monitoring endpoint (/health)
- [ ] Health check dashboard page in Streamlit
- [ ] HTTP 200 if healthy, 503 if unhealthy
- [ ] Checks: IB connection, disk space, memory, database connectivity

**Completed:**
- Docker Compose health checks for IB Gateway (every 30s)
- Pre-deployment IB Gateway connectivity validation
- Container restart policies

**Remaining Work:**
- Add /health endpoint to monitoring app
- Create Streamlit health dashboard page
- Add system metrics monitoring (disk, memory)

---

### [ ] US-8.5: Backup & Restore
**As an operator, I need backup & restore**

**Status:** Not Started
**Estimate:** 4 hours
**Priority:** P2 (Medium)

**Acceptance Criteria:**
- [ ] Backup script: ./scripts/backup.sh
- [ ] Backs up:
  - Database (data/sqlite/trades.db)
  - Configuration files (config/*.yaml, .env)
  - Algorithm code (algorithms/)
- [ ] Automated daily backups
- [ ] Restore script: ./scripts/restore.sh
- [ ] Backup retention: 30 days
- [ ] Compression support (tar.gz)

**Implementation Approach:**
- Simple file copy to backup directory with timestamp
- Daily cron job trigger (if needed)
- Consider S3/cloud storage for production deployments
- Validation that restore completes successfully

---

## Epic Completion Checklist
- [X] US-8.1: Automated deployment (complete)
- [X] US-8.2: Configuration management (complete)
- [X] US-8.3: Database persistence (complete)
- [~] US-8.4: Health monitoring (4h remaining)
- [ ] US-8.5: Backup/restore (4h remaining)
- [X] Deployment scripts tested and functional
- [X] Configuration management verified
- [X] Database schema created and tested
- [~] Health checks partially functional (Docker level, need app level)
- [ ] Backup/restore validated
- [X] Documentation complete for completed items
- [ ] Epic demo completed

**Completion Status:** 70% (17 of 24 items complete)
