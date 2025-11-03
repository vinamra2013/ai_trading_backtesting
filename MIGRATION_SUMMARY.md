# LEAN → Backtrader Migration Summary

**Migration Date:** November 3, 2025
**Status:** Epic 11 & 12 Core Implementation Complete (75%)

---

## 🎯 Migration Overview

Successfully migrated from QuantConnect LEAN (paid API keys required) to Backtrader (open-source) trading platform. This eliminates external dependencies and provides full control over the backtesting infrastructure.

---

## ✅ Completed Components

### Epic 11: Migration Foundation & Docker Architecture (100%)

#### US-11.1: Custom Backtrader Docker Image ✅
- **Created:** `Dockerfile` with Python 3.12-slim base
- **Installed:** Backtrader 1.9.78.123, ib_insync, pandas, numpy, scipy, scikit-learn, matplotlib, plotly
- **Validated:** All libraries import successfully, container runs

#### US-11.2: Update docker-compose.yml Architecture ✅
- **Migrated:** `lean` service → `backtrader` service
- **Preserved:** `ib-gateway`, `sqlite`, `monitoring` services unchanged
- **Updated:** Volume mounts for new directory structure
- **Validated:** All 4 services start successfully

#### US-11.3: IB Connection with ib_insync ✅
- **File:** `scripts/ib_connection.py` (completely rewritten)
- **Features:**
  - ib_insync-based connection manager
  - Exponential backoff retry (3 attempts: 1s, 2s, 4s)
  - Health checks every 30 seconds
  - Context manager support
  - Support for paper (4001) and live (4002) trading

#### US-11.4: Data Download Pipeline ✅
- **File:** `scripts/download_data.py` (rewritten for ib_insync)
- **Features:**
  - Direct IB API integration via `ib_insync.IB.reqHistoricalData()`
  - Multi-symbol support with progress tracking
  - CSV output format compatible with Backtrader
  - Data quality validation (OHLC consistency, gaps, duplicates)
  - Rate limiting to avoid IB restrictions

- **File:** `scripts/backtrader_data_feeds.py` (NEW)
- **Features:**
  - `IBCSVData`: Load CSV files
  - `IBPandasData`: Load pandas DataFrames
  - `IBLiveData`: Real-time data streaming from IB

#### US-11.5: Infrastructure Scripts ✅
- **Updated:** `scripts/start.sh` - New directory structure
- **Updated:** `scripts/stop.sh` - Service name changes
- **Validated:** Start/stop cycle works correctly

#### US-11.6: Environment Configuration ✅
- **Updated:** `.env.example` with Backtrader variables
- **Removed:** LEAN-specific environment variables
- **Added:** `BACKTRADER_ENGINE`, `BACKTRADER_ENGINE_PATH`, `BACKTRADER_DATA_FOLDER`

#### US-11.7: Data Directory Restructure ✅
- **Created:**
  - `data/csv/` - CSV files for Backtrader feeds
  - `data/cache/` - IB download cache
  - `strategies/` - Backtrader strategy files
- **Preserved:**
  - `data/sqlite/` - Trade database
  - `data/processed/` - Cleaned data

---

### Epic 12: Core Backtesting Engine (75%)

#### US-12.1: Cerebro Framework Setup ✅
- **File:** `scripts/cerebro_engine.py` (NEW)
- **Features:**
  - YAML-based configuration loading
  - Automatic broker setup with commission models
  - Analyzer management (7 built-in analyzers)
  - Data feed management (single/multiple symbols)
  - Performance summary extraction

#### US-12.2: Performance Analyzers ✅
- **File:** `scripts/backtrader_analyzers.py` (NEW)
- **Analyzers:**
  1. `IBPerformanceAnalyzer` - Comprehensive metrics (trades, P&L, Sharpe, drawdown)
  2. `CommissionAnalyzer` - Detailed commission tracking
  3. `EquityCurveAnalyzer` - Portfolio value over time
  4. `MonthlyReturnsAnalyzer` - Monthly performance heatmap
  5. `TradeLogAnalyzer` - Trade-by-trade logging

#### US-12.3: IB Commission Models ✅
- **File:** `scripts/ib_commissions.py` (NEW)
- **Models:**
  - `IBCommissionStandard`: $0.005/share, $1.00 minimum
  - `IBCommissionPro`: $0.0035/share, $0.35 minimum
  - SEC fees on sells: $27.80 per $1M
  - Slippage modeling: 5 bps market orders, 0 bps limit orders

#### US-12.4: Backtest Execution Script ✅
- **File:** `scripts/run_backtest.py` (rewritten for Backtrader)
- **Features:**
  - Dynamic strategy loading from file path
  - Multi-symbol backtesting
  - Custom analyzer integration
  - JSON result output with UUID
  - Performance summary reporting

#### US-12.5: Result Parser ⏳
- **Status:** Partially complete
- **Note:** JSON format standardized, monitoring dashboard integration pending

#### US-12.6: Monitoring Dashboard Updates ⏳
- **Status:** Pending
- **Required:** Update `monitoring/app.py` backtest tab to load Backtrader results

#### US-12.7: Configuration Management ✅
- **Updated:** `config/backtest_config.yaml` for Backtrader
- **Sections:**
  - Cerebro engine settings
  - Data settings (resolution, feed type, data dir)
  - Broker settings (commission scheme, slippage, cash)
  - Execution settings
  - Analyzer list
  - Benchmark settings
  - Results storage

#### US-12.8: Benchmark Comparison ⏳
- **Status:** Pending
- **Required:** Update `scripts/compare_strategies.py` for Backtrader format

---

## 📁 New Files Created

### Core Infrastructure
1. `Dockerfile` - Backtrader Docker image
2. `docker-compose.yml` - Updated service configuration
3. `.env.example` - Updated environment variables

### Scripts
4. `scripts/ib_connection.py` - ib_insync connection manager
5. `scripts/download_data.py` - IB data downloader
6. `scripts/backtrader_data_feeds.py` - Custom data feeds
7. `scripts/cerebro_engine.py` - Cerebro engine wrapper
8. `scripts/ib_commissions.py` - IB commission models
9. `scripts/backtrader_analyzers.py` - Custom analyzers
10. `scripts/run_backtest.py` - Backtest runner

### Strategies
11. `strategies/sma_crossover.py` - Sample SMA crossover strategy

### Configuration
12. `config/backtest_config.yaml` - Updated for Backtrader

### Backup Files (for rollback)
- `docker-compose.lean.yml.backup`
- `Dockerfile.lean.backup`
- `scripts/ib_connection.lean.py.backup`
- `scripts/download_data.lean.py.backup`
- `scripts/run_backtest.lean.py.backup`

---

## 🔄 Migration Comparison

| Component | LEAN | Backtrader | Status |
|-----------|------|------------|--------|
| Docker Image | `quantconnect/lean:latest` | Custom `backtrader:local` | ✅ Migrated |
| Service Name | `lean` | `backtrader` | ✅ Migrated |
| IB Connection | LEAN native | `ib_insync` library | ✅ Migrated |
| Data Download | `lean data download` CLI | Direct `ib_insync` API | ✅ Migrated |
| Data Format | LEAN proprietary | CSV (OHLCV) | ✅ Migrated |
| Backtesting Engine | LEAN Launcher | Backtrader Cerebro | ✅ Migrated |
| Commission Models | LEAN config | Backtrader `CommissionInfo` | ✅ Migrated |
| Strategy Format | LEAN `QCAlgorithm` | Backtrader `Strategy` | ✅ Created Sample |
| Result Format | LEAN JSON | Backtrader JSON | ✅ Migrated |
| Analyzers | LEAN native | Custom Backtrader | ✅ Created |
| Monitoring Dashboard | Streamlit (LEAN data) | Streamlit (Backtrader data) | ⏳ Pending |

---

## 🚀 How to Use the New System

### 1. Start the Platform
```bash
./scripts/start.sh
```

### 2. Download Historical Data
```bash
docker exec backtrader-engine python /app/scripts/download_data.py \
  --symbols SPY AAPL \
  --start 2023-01-01 \
  --end 2024-12-31 \
  --resolution Daily \
  --validate
```

### 3. Run a Backtest
```bash
docker exec backtrader-engine python /app/scripts/run_backtest.py \
  --strategy strategies/sma_crossover.py \
  --symbols SPY \
  --start 2023-01-01 \
  --end 2024-12-31 \
  --resolution Daily \
  --params '{"fast_period": 10, "slow_period": 30}'
```

### 4. View Results
Results saved to: `results/backtests/{uuid}.json`

Format:
- `backtest_id`: UUID
- `performance`: Returns, Sharpe, drawdown
- `trading`: Trade count, win rate, profit factor
- `costs`: Commission breakdown
- `equity_curve`: Time-series portfolio value
- `trades`: Trade-by-trade log

### 5. Stop the Platform
```bash
./scripts/stop.sh
```

---

## 📊 Test Results

### Docker Validation
- ✅ Image builds successfully (Python 3.12 + Backtrader 1.9.78.123)
- ✅ All 4 services start (backtrader, ib-gateway, sqlite, monitoring)
- ✅ Backtrader container accessible
- ✅ Libraries import correctly (backtrader, ib_insync, pandas, numpy)

### Component Validation
- ✅ Commission models calculate correctly
- ✅ Cerebro engine initializes with config
- ✅ Sample strategy loads and validates
- ✅ Data feeds created successfully

---

## ⏳ Remaining Work (25%)

### Epic 12 Completion
1. **US-12.5: Result Parser** - Create standardized parser (4 hours)
2. **US-12.6: Monitoring Dashboard** - Update backtest tab (12 hours)
3. **US-12.8: Benchmark Comparison** - Update comparison script (4 hours)

### Testing & Validation
4. **End-to-End Test** - Run backtest with real/sample data (2 hours)
5. **Performance Validation** - Compare results with benchmarks (4 hours)

### Documentation
6. **CLAUDE.md Update** - Reflect Backtrader changes (2 hours)
7. **README.md Update** - New usage instructions (2 hours)

**Total Remaining:** ~30 hours

---

## 🎓 Key Learnings

### Technical Decisions
1. **ib_insync over IBStore**: Modern, actively maintained, better documentation
2. **CSV over proprietary formats**: Portable, debuggable, Backtrader-native
3. **Custom analyzers over defaults**: Match LEAN metrics for comparison
4. **YAML configuration**: Flexible, human-readable, version-controllable

### Migration Strategy
1. **Preserve infrastructure**: IB Gateway, SQLite, Monitoring unchanged
2. **Backup before replace**: All LEAN files backed up for rollback
3. **Incremental validation**: Test each component independently
4. **Maintain compatibility**: JSON result format similar to LEAN

---

## 🔧 Troubleshooting

### Issue: IB Gateway Connection Fails
```bash
# Check IB Gateway status
docker compose ps ib-gateway

# View IB Gateway logs
docker compose logs ib-gateway

# Verify credentials in .env
cat .env | grep IB_
```

### Issue: Data Download Fails
```bash
# Test IB connection
docker exec backtrader-engine python /app/scripts/ib_connection.py

# Check IB rate limits (60 requests/10 min)
# Add delays between symbol downloads
```

### Issue: Backtest Fails to Load Strategy
```bash
# Verify strategy file exists
docker exec backtrader-engine ls /app/strategies/

# Test strategy import
docker exec backtrader-engine python /app/strategies/sma_crossover.py
```

---

## 📝 Notes for Future Development

### Epic 13-16: Next Steps
- **Epic 13:** Algorithm Migration (port LEAN strategies to Backtrader)
- **Epic 14:** Live Trading Integration (adapt for Backtrader live mode)
- **Epic 15:** Parameter Optimization (grid search, walk-forward)
- **Epic 16:** Testing & Validation (comprehensive test suite)

### Potential Enhancements
- Multi-timeframe analysis support
- Portfolio-level backtesting (multiple strategies)
- Advanced order types (trailing stop, bracket orders)
- Real-time performance monitoring during backtests
- Integration with external data sources (Alpha Vantage, Polygon.io)

---

**Migration Lead:** Claude (Anthropic)
**Project:** AI Trading Backtesting Platform
**Repository:** `/home/vbhatnagar/code/ai_trading_backtesting`
