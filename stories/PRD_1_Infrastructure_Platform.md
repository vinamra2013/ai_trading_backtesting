# PRD: Algorithmic Trading Infrastructure & Application Platform

**Product Name:** LEAN Trading Infrastructure Platform  
**Version:** 1.0  
**Date:** 2025-10-31  
**Owner:** Trading Systems Team  
**Status:** Draft → Ready for Implementation

---

## Executive Summary

Build a production-grade algorithmic trading infrastructure using QuantConnect LEAN engine, deployed via Docker, with Interactive Brokers integration. The platform provides core services for backtesting, live trading, monitoring, and risk management that can support multiple trading strategies.

**Objective:** Create reusable, reliable trading infrastructure that separates concerns between platform operations and strategy logic.

**Timeline:** 3-4 weeks for MVP  
**Budget:** $0 (open source stack) + $20-50/month operational costs (optional VPS)

---

## Problem Statement

### Current State
- No algorithmic trading infrastructure exists
- Manual trading is time-consuming and emotion-driven
- Need systematic approach to test and deploy trading strategies
- Require professional-grade tools without enterprise costs

### Desired State
- Automated trading platform running 24/7
- Backtest strategies with historical data
- Deploy strategies to paper/live trading with one command
- Monitor performance in real-time
- Enforce risk management automatically
- Support multiple strategies simultaneously

### Success Metrics
- Platform uptime: >99%
- Deployment time: <5 minutes from code to live
- Backtest execution: <10 minutes for 1 year of data
- Order latency: <500ms from signal to broker
- Zero unhandled exceptions in production

---

## Goals & Objectives

### Primary Goals
1. **Infrastructure Foundation**: Docker-based LEAN deployment with IB connectivity
2. **Data Management**: Automated data ingestion, caching, and validation
3. **Execution Engine**: Reliable order placement and fill tracking
4. **Monitoring System**: Real-time visibility into system health and trades
5. **Risk Management**: Automated enforcement of position and loss limits

### Non-Goals (Out of Scope)
- Strategy development (covered in separate PRD)
- Mobile app
- Multi-broker support (IB only for v1)
- Historical data storage beyond 2 years
- Machine learning model training infrastructure

---

## User Personas

### Primary User: Solo Algorithmic Trader (You)
- **Background**: Technical knowledge, programming experience
- **Goals**: Automate day trading strategies, generate consistent returns
- **Pain Points**: Don't want to build everything from scratch, need reliability
- **Tech Comfort**: High - comfortable with Docker, Python, command line

### Secondary User: Strategy Developer (Also You)
- **Background**: Developing trading strategies
- **Goals**: Quick iteration, easy testing, reliable deployment
- **Pain Points**: Want to focus on strategy logic, not infrastructure
- **Tech Comfort**: High - Python proficient

---

## User Stories & Requirements

### Epic 1: Development Environment Setup

**US-1.1: As a developer, I need LEAN CLI installed locally**
- **Acceptance Criteria:**
  - LEAN CLI installed via pip
  - Version verification command works
  - Can initialize new LEAN project
  - Documentation on system requirements
- **Priority:** P0 (Critical)
- **Estimate:** 2 hours

**US-1.2: As a developer, I need a Docker environment for LEAN**
- **Acceptance Criteria:**
  - Dockerfile created for LEAN engine
  - docker-compose.yml with all services
  - Volumes configured for data persistence
  - Network configuration for IB Gateway
  - One-command start/stop
- **Priority:** P0 (Critical)
- **Estimate:** 4 hours

**US-1.3: As a developer, I need project structure organized**
- **Acceptance Criteria:**
  - Directory structure created per specification
  - README with setup instructions
  - .gitignore configured
  - Environment variable template (.env.example)
  - Scripts directory with helpers
- **Priority:** P0 (Critical)
- **Estimate:** 2 hours

---

### Epic 2: Interactive Brokers Integration

**US-2.1: As a trader, I need IB Gateway/TWS configured**
- **Acceptance Criteria:**
  - IB Gateway or TWS installed
  - API access enabled in settings
  - Paper trading account connected
  - Socket configuration documented
  - Connection test successful
- **Priority:** P0 (Critical)
- **Estimate:** 3 hours

**US-2.2: As a platform, I need IB connection management**
- **Acceptance Criteria:**
  - Automatic connection on startup
  - Reconnection logic (3 retries with backoff)
  - Connection health checks every 30 seconds
  - Graceful disconnection on shutdown
  - Error logging for connection issues
- **Priority:** P0 (Critical)
- **Estimate:** 6 hours

**US-2.3: As a platform, I need to retrieve account information**
- **Acceptance Criteria:**
  - Fetch account balance
  - Fetch buying power
  - Fetch current positions
  - Fetch open orders
  - Update frequency: real-time via callbacks
- **Priority:** P0 (Critical)
- **Estimate:** 4 hours

**US-2.4: As a platform, I need market data streaming**
- **Acceptance Criteria:**
  - Subscribe to real-time quotes
  - Receive bid/ask/last prices
  - Volume and timestamp included
  - Handle multiple symbols simultaneously
  - Graceful handling of data feed interruptions
- **Priority:** P0 (Critical)
- **Estimate:** 6 hours

**US-2.5: As a platform, I need order execution capabilities**
- **Acceptance Criteria:**
  - Place market orders
  - Place limit orders
  - Place stop orders
  - Cancel orders
  - Modify orders
  - Receive fill notifications
  - Track order status (pending, filled, cancelled)
- **Priority:** P0 (Critical)
- **Estimate:** 8 hours

---

### Epic 3: Data Management

**US-3.1: As a developer, I need to download historical data**
- **Acceptance Criteria:**
  - Script to download from Yahoo Finance (free)
  - Optional: Download from IB (with account)
  - Date range specification
  - Symbol list specification
  - Progress indication
  - Resume capability if interrupted
- **Priority:** P0 (Critical)
- **Estimate:** 6 hours

**US-3.2: As a platform, I need efficient data storage**
- **Acceptance Criteria:**
  - Data stored in HDF5 format (efficient)
  - Organized by symbol and timeframe
  - Fast retrieval (<1 second for 1 year)
  - Compression enabled
  - Data validation on storage
- **Priority:** P1 (High)
- **Estimate:** 4 hours

**US-3.3: As a platform, I need data quality checks**
- **Acceptance Criteria:**
  - Check for missing dates
  - Check for gaps in intraday data
  - Validate OHLCV relationships (O,H,L,C make sense)
  - Flag suspicious data (e.g., zero volume)
  - Report data quality metrics
- **Priority:** P1 (High)
- **Estimate:** 4 hours

**US-3.4: As a developer, I need to update historical data**
- **Acceptance Criteria:**
  - Incremental updates (only download new data)
  - Schedule: daily after market close
  - Automatic detection of last date in cache
  - Merge new data with existing
  - Verification of successful update
- **Priority:** P2 (Medium)
- **Estimate:** 4 hours

---

### Epic 4: Backtesting Infrastructure

**US-4.1: As a developer, I need to run backtests easily**
- **Acceptance Criteria:**
  - Single command to run backtest
  - Specify algorithm, date range, symbols
  - Progress indication during run
  - Results saved automatically
  - Multiple backtests can run sequentially
- **Priority:** P0 (Critical)
- **Estimate:** 4 hours

**US-4.2: As a developer, I need realistic cost modeling**
- **Acceptance Criteria:**
  - IB commission structure ($0.005/share, min $1)
  - SEC fees modeled
  - Bid-ask spread simulation
  - Slippage modeling (market orders)
  - Fill probability (limit orders)
  - Configurable parameters
- **Priority:** P0 (Critical)
- **Estimate:** 6 hours

**US-4.3: As a developer, I need backtest result analysis**
- **Acceptance Criteria:**
  - Equity curve chart
  - Trade-by-trade log (CSV export)
  - Performance metrics calculated:
    * Total return, annualized return
    * Sharpe ratio, Sortino ratio
    * Maximum drawdown, recovery time
    * Win rate, profit factor
    * Average win/loss
    * Trade count
  - HTML report generated
  - JSON results for programmatic access
- **Priority:** P0 (Critical)
- **Estimate:** 8 hours

**US-4.4: As a developer, I need parameter optimization**
- **Acceptance Criteria:**
  - Grid search implementation
  - Specify parameter ranges
  - Parallel execution (use all CPU cores)
  - Results sorted by metric (Sharpe, profit factor, etc.)
  - Optimization report with top 10 combinations
  - Overfitting detection (in-sample vs out-of-sample)
- **Priority:** P1 (High)
- **Estimate:** 12 hours

**US-4.5: As a developer, I need walk-forward analysis**
- **Acceptance Criteria:**
  - Configurable train/test split (e.g., 6mo/2mo)
  - Rolling window through dataset
  - Optimize on train, test on out-of-sample
  - Aggregate results across all periods
  - Detect parameter drift over time
  - Visualization of performance stability
- **Priority:** P1 (High)
- **Estimate:** 10 hours

---

### Epic 5: Live Trading Engine

**US-5.1: As a platform, I need to run algorithms live**
- **Acceptance Criteria:**
  - Load algorithm from configuration
  - Connect to IB live/paper account
  - Start trading on command
  - Graceful startup (check prerequisites)
  - Logging all decisions and actions
- **Priority:** P0 (Critical)
- **Estimate:** 6 hours

**US-5.2: As a platform, I need live order management**
- **Acceptance Criteria:**
  - Queue orders before market open
  - Execute orders during trading hours
  - Track order status to completion
  - Handle partial fills
  - Retry failed orders (with limits)
  - Alert on order errors
- **Priority:** P0 (Critical)
- **Estimate:** 8 hours

**US-5.3: As a platform, I need position tracking**
- **Acceptance Criteria:**
  - Real-time position updates
  - Unrealized P&L calculation
  - Realized P&L tracking
  - Cost basis tracking
  - Position reconciliation with IB
  - Automatic sync every 5 minutes
- **Priority:** P0 (Critical)
- **Estimate:** 6 hours

**US-5.4: As a platform, I need end-of-day procedures**
- **Acceptance Criteria:**
  - Liquidate all positions at 3:55 PM ET
  - Cancel all open orders
  - Log final daily P&L
  - Generate daily summary report
  - Prepare for next trading day
  - Automatic execution (no manual intervention)
- **Priority:** P0 (Critical)
- **Estimate:** 4 hours

---

### Epic 6: Risk Management System

**US-6.1: As a platform, I need position size limits**
- **Acceptance Criteria:**
  - Max position size: configurable (default 10% of portfolio)
  - Check before every trade
  - Reject orders exceeding limit
  - Log rejection reason
  - Alert trader of rejection
- **Priority:** P0 (Critical)
- **Estimate:** 4 hours

**US-6.2: As a platform, I need loss limits**
- **Acceptance Criteria:**
  - Daily loss limit: configurable (default 2%)
  - Real-time tracking of daily P&L
  - Stop trading when limit hit
  - Liquidate all positions when limit hit
  - Alert trader immediately
  - Require manual override to resume trading
- **Priority:** P0 (Critical)
- **Estimate:** 6 hours

**US-6.3: As a platform, I need concurrent position limits**
- **Acceptance Criteria:**
  - Max concurrent positions: configurable (default 5)
  - Check before every entry
  - Reject new entries if at limit
  - Allow exits even at limit
  - Track portfolio concentration
- **Priority:** P0 (Critical)
- **Estimate:** 3 hours

**US-6.4: As a platform, I need emergency stop capability**
- **Acceptance Criteria:**
  - Single command liquidates everything
  - Cancel all open orders
  - Disconnect from trading
  - Log emergency event
  - Send critical alert
  - Script: ./scripts/emergency_stop.sh
- **Priority:** P0 (Critical)
- **Estimate:** 4 hours

**US-6.5: As a platform, I need risk metrics tracking**
- **Acceptance Criteria:**
  - Portfolio heat (total exposure %)
  - Value at Risk (VaR) calculation
  - Correlation between positions
  - Leverage ratio
  - Margin usage
  - Update every position change
- **Priority:** P2 (Medium)
- **Estimate:** 8 hours

---

### Epic 7: Monitoring & Observability

**US-7.1: As a trader, I need a real-time dashboard**
- **Acceptance Criteria:**
  - Web interface (Flask or Streamlit)
  - Current positions table (symbol, size, entry, P&L)
  - Today's trades table (all executions)
  - Account summary (balance, buying power, P&L)
  - Risk metrics (portfolio heat, daily P&L vs limit)
  - System health (IB connection, last update time)
  - Auto-refresh every 5 seconds
  - Mobile-responsive design
- **Priority:** P0 (Critical)
- **Estimate:** 12 hours

**US-7.2: As a trader, I need alerts**
- **Acceptance Criteria:**
  - Email alerts for critical events
  - SMS alerts (optional, via Twilio)
  - Alert triggers:
    * Trade executed
    * Stop loss hit
    * Daily loss limit approaching (80%, 90%, 100%)
    * System errors
    * IB disconnection
    * Emergency stop triggered
  - Configurable alert preferences
- **Priority:** P1 (High)
- **Estimate:** 8 hours

**US-7.3: As a trader, I need comprehensive logging**
- **Acceptance Criteria:**
  - Log levels: DEBUG, INFO, WARNING, ERROR
  - Structured logging (JSON format)
  - Log files rotated daily
  - Separate logs for:
    * Application (general)
    * Trading (orders, fills)
    * Risk (limit checks, rejections)
    * System (connection, health)
  - Retention: 90 days
  - Search/filter capabilities
- **Priority:** P1 (High)
- **Estimate:** 6 hours

**US-7.4: As a trader, I need a trade journal**
- **Acceptance Criteria:**
  - Automatic logging of every trade
  - Fields captured:
    * Entry: time, price, size, reason
    * Exit: time, price, reason
    * P&L: gross, net (after costs)
    * Market conditions: volatility, volume
    * Technical indicators at entry/exit
  - Daily summary report
  - Weekly aggregation
  - Exportable to CSV/Excel
- **Priority:** P1 (High)
- **Estimate:** 8 hours

**US-7.5: As a developer, I need performance monitoring**
- **Acceptance Criteria:**
  - Order execution latency tracking
  - Data feed latency tracking
  - Backtest execution time
  - Memory usage monitoring
  - CPU usage tracking
  - Alert on performance degradation
- **Priority:** P2 (Medium)
- **Estimate:** 6 hours

---

### Epic 8: Deployment & Operations

**US-8.1: As a developer, I need automated deployment**
- **Acceptance Criteria:**
  - Script: ./scripts/deploy.sh
  - Build Docker images
  - Start all containers
  - Verify health checks pass
  - Display connection status
  - Rollback capability if deployment fails
- **Priority:** P0 (Critical)
- **Estimate:** 4 hours

**US-8.2: As a developer, I need configuration management**
- **Acceptance Criteria:**
  - Separate configs for: dev, paper, live
  - Environment variables for secrets
  - .env.example template provided
  - Validation of required variables
  - Clear error messages for missing config
- **Priority:** P0 (Critical)
- **Estimate:** 3 hours

**US-8.3: As a developer, I need database persistence**
- **Acceptance Criteria:**
  - SQLite for trade history (lightweight)
  - Schema for: trades, orders, positions, daily_summaries
  - Automatic backup daily
  - Retention policy (1 year)
  - Migration scripts for schema changes
- **Priority:** P1 (High)
- **Estimate:** 6 hours

**US-8.4: As an operator, I need health checks**
- **Acceptance Criteria:**
  - Endpoint: /health
  - Checks: IB connection, data feed, disk space, memory
  - Returns: JSON with status of each component
  - HTTP 200 if healthy, 503 if unhealthy
  - Used by monitoring/alerting systems
- **Priority:** P1 (High)
- **Estimate:** 4 hours

**US-8.5: As an operator, I need backup/restore**
- **Acceptance Criteria:**
  - Backup script: ./scripts/backup.sh
  - Backs up: database, configs, logs
  - Compressed archive with timestamp
  - Upload to S3 or local storage (configurable)
  - Restore script: ./scripts/restore.sh
  - Test backup/restore monthly
- **Priority:** P2 (Medium)
- **Estimate:** 6 hours

---

### Epic 9: AI Integration Layer

**US-9.1: As an AI agent, I need programmatic backtest execution**
- **Acceptance Criteria:**
  - Python API: `run_backtest(strategy_code, start_date, end_date, symbols, parameters)`
  - Returns structured results (JSON)
  - Async execution support
  - Progress callbacks
  - Error handling with meaningful messages
- **Priority:** P0 (Critical)
- **Estimate:** 6 hours

**US-9.2: As an AI agent, I need to read backtest results programmatically**
- **Acceptance Criteria:**
  - API: `get_backtest_results(backtest_id)`
  - Returns: metrics dict (Sharpe, win rate, trades, drawdown, etc.)
  - API: `get_trades(backtest_id)` returns trade list
  - API: `get_equity_curve(backtest_id)` returns time series
  - All data in machine-readable format (JSON/dict)
- **Priority:** P0 (Critical)
- **Estimate:** 4 hours

**US-9.3: As an AI agent, I need parameter optimization API**
- **Acceptance Criteria:**
  - API: `optimize_parameters(strategy_code, param_ranges, optimization_metric)`
  - Runs grid search or Bayesian optimization
  - Returns ranked results with top N parameter sets
  - Progress tracking
  - Can specify constraints (max drawdown, min win rate)
- **Priority:** P0 (Critical)
- **Estimate:** 8 hours

**US-9.4: As an AI agent, I need strategy deployment API**
- **Acceptance Criteria:**
  - API: `deploy_strategy(strategy_code, mode='paper'|'live', parameters)`
  - Validates strategy before deployment
  - Hot-swap capability (replace running strategy)
  - Rollback to previous strategy
  - Returns deployment status
- **Priority:** P0 (Critical)
- **Estimate:** 6 hours

**US-9.5: As an AI agent, I need live performance monitoring API**
- **Acceptance Criteria:**
  - API: `get_current_positions()` returns active positions
  - API: `get_today_trades()` returns today's executions
  - API: `get_performance_metrics()` returns live P&L, win rate, etc.
  - API: `get_system_health()` returns connection status, errors
  - WebSocket stream for real-time updates (optional)
- **Priority:** P1 (High)
- **Estimate:** 6 hours

**US-9.6: As an AI agent, I need data access API**
- **Acceptance Criteria:**
  - API: `get_historical_data(symbols, start_date, end_date, resolution)`
  - API: `download_data(symbols, date_range)` triggers download
  - API: `get_data_quality_report(symbols)` checks for gaps/issues
  - Caching handled transparently
- **Priority:** P1 (High)
- **Estimate:** 4 hours

**US-9.7: As an AI agent, I need strategy comparison API**
- **Acceptance Criteria:**
  - API: `compare_strategies([backtest_id1, backtest_id2, ...])`
  - Returns side-by-side metrics comparison
  - Generates comparison charts
  - Highlights winner by specified metric
  - Export to report format
- **Priority:** P1 (High)
- **Estimate:** 4 hours

**US-9.8: As a developer, I need Claude Skills for common tasks**
- **Acceptance Criteria:**
  - Skill: "data-manager" (download, cache, validate data)
  - Skill: "backtest-runner" (run backtest, get results)
  - Skill: "parameter-optimizer" (optimize and rank)
  - Skill: "strategy-deployer" (deploy to paper/live)
  - Skill: "performance-monitor" (get current status)
  - Each skill has clear interface and examples
  - Skills documented in /skills directory
- **Priority:** P1 (High)
- **Estimate:** 12 hours

---

### Epic 10: Testing & Quality

**US-10.1: As a developer, I need unit tests**
- **Acceptance Criteria:**
  - pytest framework
  - Test coverage for:
    * Data management functions
    * Order execution logic
    * Risk management checks
    * Position calculations
  - Coverage target: >70%
  - CI pipeline runs tests automatically
- **Priority:** P1 (High)
- **Estimate:** 12 hours

**US-9.2: As a developer, I need integration tests**
- **Acceptance Criteria:**
  - Test end-to-end flows:
    * Backtest execution
    * Order placement → fill
    * Risk limit enforcement
    * Emergency stop
  - Mock IB connection for tests
  - Test data fixtures
- **Priority:** P1 (High)
- **Estimate:** 10 hours

**US-9.3: As a developer, I need documentation**
- **Acceptance Criteria:**
  - README.md with setup instructions
  - Architecture diagram
  - API documentation (if exposing APIs)
  - Configuration guide
  - Troubleshooting guide
  - Deployment guide
- **Priority:** P1 (High)
- **Estimate:** 8 hours

---

## Technical Specifications

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Deployment Layer (Docker)                                       │
│  ├── LEAN Engine Container                                      │
│  ├── Monitoring Dashboard Container                             │
│  ├── IB Gateway Container (optional)                            │
│  └── Database Container (SQLite in volume)                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Application Layer                                                │
│  ├── LEAN Core Engine (backtesting + live trading)              │
│  ├── Order Management System                                    │
│  ├── Risk Management Engine                                     │
│  ├── Data Management Layer                                      │
│  └── Monitoring & Logging                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Integration Layer                                                │
│  ├── IB Gateway/TWS (broker connection)                         │
│  ├── Data Providers (Yahoo Finance, IB)                         │
│  └── Alert Services (Email, SMS)                                │
└─────────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Core Platform:**
- LEAN Engine: 2.5+ (QuantConnect open source)
- Python: 3.11+
- Docker: 20.10+
- Docker Compose: 2.0+

**Data:**
- HDF5 (via PyTables) for historical data
- SQLite for trade history
- Pandas for data manipulation

**Monitoring:**
- Streamlit or Flask for dashboard
- Python logging module
- Email via SMTP
- Twilio for SMS (optional)

**Broker:**
- Interactive Brokers TWS API 10.19+
- ib_insync or LEAN's native IB integration

**Testing:**
- pytest for unit/integration tests
- pytest-cov for coverage
- Mock for IB API testing

### System Requirements

**Development Machine:**
- OS: Windows 10/11, macOS 11+, or Linux (Ubuntu 20.04+)
- CPU: 4+ cores
- RAM: 8 GB minimum, 16 GB recommended
- Storage: 100 GB available (for data caching)
- Network: Stable internet connection

**Production (VPS - Optional):**
- CPU: 4+ cores
- RAM: 8 GB
- Storage: 50 GB SSD
- Network: Low latency to IB servers
- OS: Ubuntu 22.04 LTS
- Cost: $20-50/month

### Data Flow

**Backtesting:**
```
Historical Data (HDF5)
    ↓
LEAN Backtesting Engine
    ↓
Strategy Algorithm
    ↓
Order Simulation
    ↓
Results & Metrics
```

**Live Trading:**
```
IB Market Data Stream
    ↓
LEAN Live Engine
    ↓
Strategy Algorithm (generates signals)
    ↓
Risk Management (validates)
    ↓
Order Management (executes)
    ↓
IB Gateway (broker)
    ↓
Fill Notifications
    ↓
Position/P&L Updates
```

### Configuration Schema

**config.json** (LEAN configuration):
```json
{
  "environment": "paper",  // dev, paper, live
  
  "algorithm-type-name": "TradingAlgorithm",
  "algorithm-language": "Python",
  "algorithm-location": "../algorithms/strategy/main.py",
  
  "live-mode": false,
  "live-mode-brokerage": "InteractiveBrokers",
  
  "ib-host": "127.0.0.1",
  "ib-port": 4002,
  "ib-account": "",
  "ib-user-name": "",
  "ib-trading-mode": "paper",
  
  "data-folder": "../data/",
  "results-destination-folder": "../results/",
  
  "parameters": {}
}
```

**.env** (Environment variables):
```bash
# IB Credentials
IB_USERNAME=your_username
IB_ACCOUNT=DU123456
IB_PASSWORD=your_password  # If using automated login

# Alert Configuration
ALERT_EMAIL=your@email.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@email.com
SMTP_PASSWORD=app_password

# Optional: SMS Alerts
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
TWILIO_TO_NUMBER=

# Risk Management
MAX_POSITION_SIZE_PCT=10.0
MAX_DAILY_LOSS_PCT=2.0
MAX_CONCURRENT_POSITIONS=5

# Deployment
ENVIRONMENT=paper  # dev, paper, live
LOG_LEVEL=INFO
```

### Database Schema

**trades table:**
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME,
    symbol TEXT,
    direction TEXT,  -- BUY, SELL
    quantity INTEGER,
    price REAL,
    commission REAL,
    pnl REAL,
    strategy TEXT,
    entry_reason TEXT,
    exit_reason TEXT
);
```

**positions table:**
```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME,
    symbol TEXT,
    quantity INTEGER,
    entry_price REAL,
    current_price REAL,
    unrealized_pnl REAL,
    realized_pnl REAL
);
```

**daily_summary table:**
```sql
CREATE TABLE daily_summary (
    date DATE PRIMARY KEY,
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    gross_profit REAL,
    gross_loss REAL,
    net_pnl REAL,
    win_rate REAL,
    profit_factor REAL
);
```

### API Endpoints (Monitoring Dashboard)

```
GET  /                      # Dashboard home
GET  /positions             # Current positions (JSON)
GET  /trades/today          # Today's trades (JSON)
GET  /performance/daily     # Daily performance (JSON)
GET  /health                # System health check
POST /emergency-stop        # Trigger emergency liquidation
GET  /logs                  # View recent logs
```

---

## Dependencies

### Prerequisites
1. Python 3.11+ installed
2. Docker and Docker Compose installed
3. Interactive Brokers account (paper or live)
4. IB Gateway or TWS installed
5. Basic command line proficiency

### External Dependencies
- LEAN CLI (pip install lean)
- QuantConnect LEAN (git clone)
- IB TWS API (from IB)
- Yahoo Finance API (via yfinance library)

### Internal Dependencies
None (this is the foundation)

---

## Risks & Mitigations

### Technical Risks

**Risk: IB connection instability**
- Impact: High (can't trade)
- Mitigation: Reconnection logic, health checks, alerts
- Fallback: Manual trading via TWS

**Risk: Data feed issues**
- Impact: High (bad data = bad decisions)
- Mitigation: Data validation, multiple sources, staleness checks
- Fallback: Pause trading if data quality poor

**Risk: Docker container crashes**
- Impact: High (system down)
- Mitigation: Auto-restart policies, health checks, monitoring
- Fallback: Run LEAN natively (non-Docker)

**Risk: Order execution failures**
- Impact: High (can't enter/exit)
- Mitigation: Retry logic, manual override capability
- Fallback: Manual order placement

**Risk: Disk space fills up (logs/data)**
- Impact: Medium (system degradation)
- Mitigation: Log rotation, disk space monitoring, cleanup scripts
- Fallback: Manual cleanup

### Operational Risks

**Risk: Internet outage during trading**
- Impact: High (lose control)
- Mitigation: VPS with redundant internet, mobile hotspot backup
- Fallback: IB mobile app for manual control

**Risk: Power outage**
- Impact: High (if local)
- Mitigation: Use VPS, UPS for local machine
- Fallback: Mobile device trading

**Risk: Forgot to start system**
- Impact: Medium (missed trades)
- Mitigation: Automated startup scripts, calendar reminders
- Fallback: Manual start

### Security Risks

**Risk: IB credentials exposed**
- Impact: Critical (account compromise)
- Mitigation: Environment variables, never commit to git, file permissions
- Fallback: Change credentials immediately

**Risk: Unauthorized access to system**
- Impact: High (system manipulation)
- Mitigation: Firewall rules, SSH key auth, no public endpoints
- Fallback: Audit logs, emergency stop

---

## Success Criteria

### Phase 1: Infrastructure Complete (Week 2)
- [ ] LEAN CLI installed and working
- [ ] Docker environment running
- [ ] IB paper account connected
- [ ] Can download historical data
- [ ] Can run example LEAN algorithm
- [ ] All services healthy

### Phase 2: Backtesting Ready (Week 3)
- [ ] Historical data for 6 symbols cached
- [ ] Can run backtests with realistic costs
- [ ] Results generated with all metrics
- [ ] Parameter optimization working
- [ ] Walk-forward analysis implemented

### Phase 3: Live Trading Ready (Week 4)
- [ ] Can deploy to paper trading
- [ ] Orders execute correctly
- [ ] Positions tracked accurately
- [ ] Risk limits enforced
- [ ] Dashboard shows real-time data
- [ ] Alerts firing on events
- [ ] Emergency stop tested

### MVP Complete Criteria
- All P0 user stories completed
- All integration tests passing
- Documentation complete
- Successfully paper traded for 1 week
- Zero critical bugs
- Performance meets targets (latency, uptime)

---

## Timeline & Milestones

### Week 1: Foundation
- Day 1-2: Environment setup (LEAN CLI, Docker)
- Day 3-4: IB integration (connection, basic data)
- Day 5: Data management (download, cache)
- **Milestone:** Can connect to IB and retrieve data

### Week 2: Core Features
- Day 6-8: Backtesting infrastructure
- Day 9-10: Live trading engine basics
- Day 11-12: Risk management system
- **Milestone:** Can backtest and execute orders

### Week 3: Monitoring & Ops
- Day 13-15: Dashboard and alerts
- Day 16-17: Logging and trade journal
- Day 18: Deployment automation
- **Milestone:** Full observability

### Week 4: AI Integration & Testing
- Day 19-20: AI Integration Layer (APIs and Skills)
- Day 21-22: Unit and integration tests
- Day 23-24: Documentation
- Day 25: Bug fixes and improvements
- **Milestone:** Production-ready platform with AI capabilities

---

## Maintenance & Support

### Ongoing Maintenance
- **Daily:** Monitor system health, review logs
- **Weekly:** Check disk space, review performance
- **Monthly:** Update dependencies, review and optimize
- **Quarterly:** Full system audit, disaster recovery test

### Support Model
- Documentation in /docs folder
- GitHub issues for bug tracking
- Community: QuantConnect forums
- IB Support for broker issues

---

## Appendices

### Appendix A: Glossary
- **LEAN:** QuantConnect's open-source algorithmic trading engine
- **IB:** Interactive Brokers
- **TWS:** Trader Workstation (IB's desktop platform)
- **Paper Trading:** Simulated trading with fake money
- **HFT:** High-Frequency Trading
- **P&L:** Profit and Loss
- **VPS:** Virtual Private Server
- **PDT:** Pattern Day Trader

### Appendix B: References
- LEAN Documentation: https://www.lean.io/docs/
- IB API: https://interactivebrokers.github.io/
- Docker Docs: https://docs.docker.com/

### Appendix C: Cost Breakdown

**One-Time Costs:**
- Development time: 80-100 hours @ $0 (self-built)
- Total: $0

**Monthly Operational Costs:**
- VPS (optional): $20-50
- IB market data: $10-25
- SMS alerts (optional): $5-10
- **Total:** $0-85/month

**Live Trading Costs:**
- Per trade: $15-30 (1000 shares round trip)
- Varies with trading frequency

---

## Approval & Sign-Off

**Product Owner:** [Your Name]  
**Technical Lead:** Claude Code  
**Status:** Ready for Implementation  
**Approved Date:** [To be filled]

---

**Next Steps:**
1. Review and approve this PRD
2. Provide to Claude Code for story breakdown
3. Begin Sprint 1: Development Environment Setup
4. Track progress against user stories
5. Demo at end of each sprint

---

*This PRD serves as the source of truth for infrastructure platform development. All user stories derive from this document.*
