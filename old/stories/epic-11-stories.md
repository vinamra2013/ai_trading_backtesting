# Epic 11: Migration Foundation & Docker Architecture

**Epic Description:** Replace QuantConnect LEAN engine with Backtrader (open-source) to eliminate paid API key requirement. This epic establishes the foundational infrastructure including Docker architecture, IB connectivity, and basic data pipeline.

**Time Estimate:** 1 week (40 hours)
**Priority:** P0 (Critical - Foundation for Backtrader migration)
**Dependencies:** None (starts migration project)

---

## User Stories

### [✅] US-11.1: Custom Backtrader Docker Image
**As a developer, I need a Docker container with Backtrader and dependencies**

**Status:** ✅ Complete
**Estimate:** 6 hours
**Priority:** P0

**Acceptance Criteria:**
- [✅] New Dockerfile created for Backtrader (Python 3.12 base)
- [✅] Backtrader installed via pip (latest stable version 1.9.78.123)
- [✅] Dependencies installed: ib_insync, pandas, numpy, scipy, scikit-learn
- [✅] Additional libraries: matplotlib, plotly (for visualization)
- [✅] Image builds successfully and runs basic test
- [✅] Image tagged and documented in README

**Technical Notes:**
```dockerfile
FROM python:3.12-slim
RUN pip install backtrader ib_insync pandas numpy scipy \
    scikit-learn matplotlib plotly streamlit sqlalchemy
WORKDIR /app
```

**Risks:**
- Version compatibility issues between Backtrader and dependencies
- **Mitigation:** Pin versions in requirements.txt

---

### [✅] US-11.2: Update docker-compose.yml Architecture
**As a developer, I need docker-compose updated for Backtrader**

**Status:** ✅ Complete
**Estimate:** 4 hours
**Priority:** P0

**Acceptance Criteria:**
- [✅] Replace `lean` service with `backtrader` service
- [✅] Update service configuration (volumes, networks, environment)
- [✅] Keep `ib-gateway`, `sqlite`, `monitoring` services unchanged
- [✅] Update volume mounts for new directory structure
- [✅] Service dependencies correctly configured
- [✅] Health checks implemented for backtrader service
- [✅] Documentation updated with new service names

**Technical Notes:**
- Service name: `lean` → `backtrader`
- Image: `quantconnect/lean:latest` → `backtrader:local`
- Keep same network: `trading-network`
- Mount: algorithms/, config/, data/, results/, logs/
- Environment: IB credentials from .env
- Command: Run Python scripts (not LEAN CLI)

**Dependencies:**
- Requires US-11.1 (Docker image)

---

### [✅] US-11.3: IB Connection with ib_insync
**As a developer, I need IB Gateway connection using ib_insync**

**Status:** ✅ Complete
**Estimate:** 8 hours
**Priority:** P0

**Acceptance Criteria:**
- [✅] Rewrite `scripts/ib_connection.py` using ib_insync library
- [✅] Connection manager with retry logic (exponential backoff)
- [✅] Support for paper (port 4001) and live (port 4002) trading
- [✅] Health check method implemented
- [✅] Context manager support for automatic cleanup
- [✅] Error handling for connection failures
- [✅] Logging integrated with existing log infrastructure
- [✅] Unit tests for connection manager

**Technical Notes:**
```python
from ib_insync import IB, util

class IBConnectionManager:
    def __init__(self, host='ib-gateway', port=4001, client_id=1):
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id

    def connect(self, retries=3):
        # Exponential backoff: 1s, 2s, 4s
        # Return connection status

    def disconnect(self):
        # Clean shutdown
```

**Dependencies:**
- Requires US-11.1 (ib_insync installed)
- IB Gateway service must be running

**Risks:**
- IB Gateway connection timeout/failures
- **Mitigation:** Implement robust retry with logging

---

### [✅] US-11.4: Basic Data Download Pipeline
**As a developer, I need to download historical data for Backtrader**

**Status:** ✅ Complete
**Estimate:** 12 hours
**Priority:** P0

**Acceptance Criteria:**
- [✅] Rewrite `scripts/download_data.py` using ib_insync
- [✅] Support for multiple symbols (SPY, AAPL, etc.)
- [✅] Date range specification (start/end dates)
- [✅] Resolution support: Daily, Hourly, Minute
- [✅] Data type support: Trades, Quotes, Bid/Ask
- [✅] Save data in CSV format compatible with Backtrader
- [✅] Error handling for IB rate limits
- [✅] Progress logging and data validation
- [✅] Documentation updated with new CLI usage

**Technical Notes:**
```python
# Download via ib_insync
from ib_insync import IB, Stock

ib = IB()
ib.connect('ib-gateway', 4001, clientId=1)

contract = Stock('SPY', 'SMART', 'USD')
bars = ib.reqHistoricalData(
    contract,
    endDateTime='',
    durationStr='365 D',
    barSizeSetting='1 day',
    whatToShow='TRADES',
    useRTH=True
)

# Convert to DataFrame and save CSV
df = util.df(bars)
df.to_csv('data/raw/SPY_daily.csv')
```

**CSV Format for Backtrader:**
```csv
Date,Open,High,Low,Close,Volume
2020-01-02,324.87,325.18,323.34,324.34,100234567
```

**Dependencies:**
- Requires US-11.3 (IB connection)

**Risks:**
- IB historical data rate limits (60 requests/10 min)
- **Mitigation:** Implement rate limiting and caching

---

### [✅] US-11.5: Update Infrastructure Scripts
**As a developer, I need updated start/stop scripts for Backtrader**

**Status:** ✅ Complete
**Estimate:** 6 hours
**Priority:** P1

**Acceptance Criteria:**
- [✅] Update `scripts/start.sh` for Backtrader services
- [✅] Update `scripts/stop.sh` for graceful shutdown
- [✅] Remove LEAN-specific commands
- [✅] Add Backtrader service health checks
- [✅] Update logging output and status messages
- [✅] Test start/stop cycle multiple times
- [✅] Documentation updated in README.md

**Technical Notes:**
```bash
# start.sh updates
docker compose up -d backtrader ib-gateway sqlite monitoring
# Wait for IB Gateway health check
# Verify Backtrader container running
# Display access URLs (Streamlit on 8501)
```

**Dependencies:**
- Requires US-11.2 (docker-compose.yml)

---

### [✅] US-11.6: Environment Configuration
**As a developer, I need environment variables for Backtrader**

**Status:** ✅ Complete
**Estimate:** 2 hours
**Priority:** P1

**Acceptance Criteria:**
- [✅] Update `.env.example` with Backtrader variables
- [✅] Remove LEAN-specific environment variables
- [✅] Add Backtrader configuration variables
- [✅] Document all environment variables in README
- [✅] Validate .env file parsing in scripts
- [✅] Ensure .gitignore still excludes .env

**Technical Notes:**
```bash
# .env.example updates
# IB Gateway Configuration (unchanged)
IB_USER_NAME=your_username
IB_PASSWORD=your_password
IB_TRADING_MODE=paper

# Backtrader Configuration (new)
BACKTRADER_INITIAL_CASH=100000
BACKTRADER_COMMISSION=0.005
BACKTRADER_DATA_DIR=/app/data
BACKTRADER_RESULTS_DIR=/app/results
```

**Dependencies:**
- Requires US-11.2 (docker-compose.yml)

---

### [✅] US-11.7: Data Directory Restructure
**As a developer, I need updated data directory structure for Backtrader**

**Status:** ✅ Complete
**Estimate:** 2 hours
**Priority:** P2

**Acceptance Criteria:**
- [✅] Update data/ directory structure documentation
- [✅] Create subdirectories: csv/, pickle/, cache/
- [✅] Remove LEAN-specific directories if needed
- [✅] Update .gitkeep files
- [✅] Document data format conventions
- [✅] Update scripts to use new paths

**Technical Notes:**
```
data/
├── csv/           # CSV files for Backtrader feeds
├── pickle/        # Serialized Backtrader data objects
├── cache/         # Downloaded data cache
├── sqlite/        # Trade database (unchanged)
└── .gitkeep
```

**Dependencies:**
- Requires US-11.4 (data download)

---

## Epic Completion Checklist
- [ ] All user stories completed
- [ ] All acceptance criteria met
- [ ] Docker environment tested (build, start, stop)
- [ ] IB Gateway connection validated
- [ ] Sample data downloaded successfully
- [ ] Documentation updated (README.md, CLAUDE.md)
- [ ] Epic demo: Start services, download data, verify connectivity

## Validation Tests
1. **Docker Build:** `docker build -t backtrader:local -f Dockerfile .`
2. **Service Start:** `./scripts/start.sh` → All 4 services running
3. **IB Connection:** Python script connects to IB Gateway on port 4001
4. **Data Download:** Download SPY daily data for 2023
5. **Service Stop:** `./scripts/stop.sh` → Graceful shutdown

## Migration Notes
- **What's Changing:** LEAN Docker service → Backtrader Docker service
- **What's Staying:** IB Gateway, SQLite, Monitoring, network architecture
- **Rollback Plan:** Keep LEAN docker-compose in `docker-compose.lean.yml.backup`

---

**Next Epic:** Epic 12 - Core Backtesting Engine (implement Cerebro, analyzers, cost models)

---

## ✅ Epic 11 Completion Summary

**Status:** COMPLETE
**Completion Date:** November 3, 2025
**Total Time:** 40 hours (as estimated)

### All User Stories Completed:
- ✅ US-11.1: Backtrader Docker Image
- ✅ US-11.2: docker-compose.yml Architecture  
- ✅ US-11.3: IB Connection with ib_insync
- ✅ US-11.4: Data Download Pipeline
- ✅ US-11.5: Infrastructure Scripts
- ✅ US-11.6: Environment Configuration
- ✅ US-11.7: Data Directory Restructure

### Key Achievements:
- Backtrader 1.9.78.123 deployed in Docker
- ib_insync integration complete
- Data pipeline operational
- All services validated and running
- Full rollback capability maintained

**Migration to Epic 12:** Core Backtesting Engine
