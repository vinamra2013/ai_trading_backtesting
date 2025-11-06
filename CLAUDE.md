# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Algorithmic trading platform built on **Backtrader** (open-source) with Interactive Brokers integration. This is a Python-based backtesting and live trading system using Docker for containerized deployment.

**Migration Status**: ✅ Successfully migrated from LEAN to Backtrader (Nov 2025)
**Architecture**: Backtrader-Native - All trading logic runs inside Backtrader strategies with IB integration via ib_insync.

**See**: [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md) for complete migration details.

## Environment Management

**CRITICAL**: This project uses a Python virtual environment. ALWAYS activate it before running Python commands:

```bash
source venv/bin/activate.fish
```

All Python commands (pip, python scripts) MUST run within the virtual environment.

## Docker Architecture

The platform uses a 4-service Docker architecture orchestrated via [docker-compose.yml](docker-compose.yml):

1. **backtrader**: Backtrader trading engine (Python 3.12 + Backtrader 1.9.78.123)
2. **ib-gateway**: Interactive Brokers Gateway (headless) - handles broker connectivity
3. **sqlite**: Trade history database
4. **monitoring**: Streamlit dashboard on port 8501

All services communicate via `trading-network` bridge network.

### Service Startup/Shutdown

```bash
# Start all services (preferred method)
./scripts/start.sh

# Stop all services
./scripts/stop.sh

# View logs (NEVER use -f flag as per project rules)
docker compose logs backtrader
docker compose logs ib-gateway

# Restart specific service
docker compose restart backtrader
```

## Interactive Brokers Integration

### Credentials Setup

IB credentials are managed through `.env` file and Docker secrets:
- Username/password stored in `.env` (gitignored)
- Password also mounted as Docker secret at `/run/secrets/ib_password`
- Trading mode: `paper` (default) or `live`

### Connection Architecture

[scripts/ib_connection.py](scripts/ib_connection.py) provides `IBConnectionManager` class with:
- **ib_insync-based** connection manager (fully implemented)
- Exponential backoff retry (3 attempts: 1s, 2s, 4s)
- Health checks every 30 seconds
- Context manager support for automatic connection lifecycle
- Port 4001 for paper trading, 4002 for live (default: 4001)

## Backtrader Commands

All Backtrader operations run via Python scripts inside or outside Docker:

```bash
# Test IB connection
docker exec backtrader-engine python /app/scripts/ib_connection.py

# Download historical data
source venv/bin/activate
python scripts/download_data.py \
  --symbols SPY AAPL --start 2024-01-01 --end 2024-12-31 --validate

# Run backtest
source venv/bin/activate
 python scripts/run_backtest.py \
   --strategy strategies.sma_crossover.SMACrossover \
   --symbols SPY --start 2024-01-01 --end 2024-12-31
```

### MLflow Experiment Tracking (Epic 17)

**Status**: ✅ Implemented - AI-Native Research Lab with centralized experiment tracking.

#### Enable MLflow Logging

```bash
# Run inside Docker container
docker exec -e PYTHONPATH=/app backtrader-engine python /app/scripts/run_backtest.py \
  --strategy strategies/sma_crossover.py \
  --symbols SPY \
  --start 2020-01-01 \
  --end 2024-12-31 \
  --mlflow \
  --project Q1_2025 \
  --asset-class Equities \
  --strategy-family MeanReversion
```

#### MLflow Features

- **Centralized Tracking**: All backtests logged to PostgreSQL-backed MLflow server
- **Project Hierarchy**: Dot notation organization (Project.AssetClass.StrategyFamily.Strategy)
- **Advanced Metrics**: 30+ metrics including Sortino, Calmar, regime analysis, alpha/beta
- **Artifact Storage**: Equity curves, trade logs, strategy plots, tearsheets
- **Experiment Comparison**: Compare strategies across projects and time periods

#### Access MLflow UI

```bash
# Start services (includes MLflow on port 5000)
./scripts/start.sh

# Open MLflow UI
open http://localhost:5000
```

#### Experiment Organization

**Naming Convention**: `{Project}.{AssetClass}.{StrategyFamily}.{Strategy}`
- `Q1_2025.Equities.MeanReversion.SMACrossover`
- `Q2_2025.Crypto.Momentum.RSIStrategy`

**Tags**: Comprehensive tagging for filtering and organization
- Project, Asset Class, Strategy Family, Team, Status
- Symbols, Time Period, Benchmark

#### Advanced Metrics (Epic 17)

Backtests now include:
- **QuantStats**: 30+ advanced metrics (Sortino, Calmar, Omega, VaR, CVaR)
- **Regime Analysis**: Bull/bear market performance breakdown
- **Alpha/Beta**: Benchmark comparison vs SPY
- **HTML Tearsheets**: Comprehensive performance reports

#### Bayesian Parameter Optimization (Epic 17)

**Status**: ✅ Implemented - Optuna-based intelligent optimization with MLflow integration.

```bash
# Run inside Docker container
docker exec -e PYTHONPATH=/app backtrader-engine python /app/scripts/optimize_strategy.py \
  --strategy strategies/sma_crossover.py \
  --param-space /app/scripts/sma_crossover_params.json \
  --symbols SPY \
  --start 2020-01-01 \
  --end 2024-12-31 \
  --metric sharpe_ratio \
  --n-trials 100 \
  --study-name sma_opt_v1
```

**Features**:
- **Bayesian Optimization**: Optuna TPE sampler for intelligent parameter search
- **Distributed Execution**: 4-worker parallel optimization
- **MLflow Integration**: Parent-child run structure for study tracking
- **Parameter Constraints**: Strategy-aware validation (SMA fast < slow)
- **Study Resumption**: Continue interrupted optimization studies

#### Project Management (Epic 17)

**Status**: ✅ Implemented - Intelligent experiment organization and querying.

```python
from scripts.project_manager import ProjectManager

pm = ProjectManager()

# Create organized experiments
exp_id = pm.create_experiment(
    project="Q1_2025",
    asset_class="Equities",
    strategy_family="MeanReversion",
    strategy="SMACrossover"
)

# Query experiments
equity_experiments = pm.query_by_asset_class("Equities")
research_projects = pm.query_by_status("research")

# Compare strategies
comparison = pm.compare_strategies("Q1_2025", "sharpe_ratio")
```

**Query Patterns**:
- `query_by_project("Q1_2025")` - All experiments in project
- `query_by_asset_class("Equities")` - All equity strategies
- `query_by_strategy_family("MeanReversion")` - All mean reversion strategies
- `query_recent_experiments(days=7)` - Recent experiments

# Deploy to live trading
./scripts/start_live_trading.sh
```

## Data Management

### Download Historical Data

Use [scripts/download_data.py](scripts/download_data.py) for data downloads via ib_insync:

```bash
source venv/bin/activate
python scripts/download_data.py --symbols SPY AAPL \
  --start 2020-01-01 --end 2024-12-31 \
  --resolution Daily --data-type Trade
```

The script:
- Requires IB credentials in `.env` file
- Connects to IB Gateway via ib_insync
- Downloads data directly from Interactive Brokers
- Supports multiple symbols (comma-separated)
- Data types: Trade, Quote
- Resolutions: Daily, Hour, Minute, Second
- Markets: USA (default)

### Symbol Discovery Engine (Epic 18)

**Status**: ✅ Implemented - Autonomous symbol discovery using IB API scanner functionality.

Use [scripts/symbol_discovery.py](scripts/symbol_discovery.py) for autonomous symbol discovery:

```bash
# Basic usage - discover high volume stocks
source venv/bin/activate
python scripts/symbol_discovery.py --scanner high_volume --output csv

# Advanced usage with filters
python scripts/symbol_discovery.py \
  --scanner volatility_leaders \
  --min-volume 2000000 \
  --atr-threshold 1.5 \
  --min-price 10.0 \
  --max-price 200.0 \
  --output json

# Dry run to see configuration
python scripts/symbol_discovery.py --scanner top_gainers --dry-run

# View discovery statistics
python scripts/symbol_discovery.py --stats

# Skip database operations (file output only)
python scripts/symbol_discovery.py --scanner most_active_stocks --no-db --output csv
```

#### Scanner Types

- `high_volume`: High volume stocks ($2M+ avg daily volume)
- `top_gainers`: Top percentage gainers (daily)
- `top_losers`: Top percentage losers (daily)
- `most_active_stocks`: Most active stocks by volume
- `most_active_etfs`: Most active ETFs by volume
- `volatility_leaders`: Highest volatility (ATR-based)

#### Filter Options

- `--min-volume`: Minimum average daily volume
- `--atr-threshold`: Minimum ATR (volatility) threshold
- `--min-price`: Minimum stock price
- `--max-price`: Maximum stock price
- `--exchanges`: Allowed exchanges (NYSE,NASDAQ,ARCA)

#### Output Formats

- `--output csv`: Comma-separated values (default)
- `--output json`: JSON array format
- `--output both`: Generate both CSV and JSON

#### Features

- **IB Scanner API Integration**: Direct connection to Interactive Brokers scanner
- **Intelligent Filtering**: Liquidity, volatility, price range, exchange validation
- **ATR Calculation**: Real-time volatility analysis using historical data
- **PostgreSQL Storage**: Historical symbol tracking and performance data
- **CLI Flexibility**: Full parameter override capability
- **Comprehensive Logging**: Detailed execution logs and error handling

#### Output Files

Results saved to `data/discovered_symbols/` with timestamped filenames:
```
data/discovered_symbols/high_volume_20251105_174142.csv
data/discovered_symbols/high_volume_20251105_174142.json
```

CSV format includes: symbol, exchange, sector, avg_volume, atr, price, pct_change, market_cap, volume, discovery_timestamp

### Data Storage Structure

```
data/
├── raw/        # Downloaded market data
├── processed/  # Cleaned/transformed data
├── sqlite/     # Trade history database
└── discovered_symbols/  # Symbol discovery outputs (Epic 18)
```

## Database Optimization (Epic 17)

**Status**: ✅ Implemented - PostgreSQL performance optimization and archival strategies.

### Performance Optimization

The platform includes automated database optimization scripts for MLflow PostgreSQL backend:

```bash
source venv/bin/activate
python scripts/db_optimizer.py
```

This generates:
- `scripts/db_optimization/performance_indexes.sql` - Index optimization
- `scripts/db_optimization/archive_data_90days.sql` - Data archival
- `scripts/db_optimization/cleanup_maintenance.sql` - Maintenance scripts
- `scripts/db_optimization/performance_monitoring.sql` - Monitoring queries
- `scripts/db_optimization/scaling_guide.md` - Scaling documentation

### Key Optimizations

- **Composite Indexes**: Optimized for common query patterns
- **Partial Indexes**: Efficient queries on recent data
- **Archival Strategy**: Automatic archiving of experiments >90 days old
- **Maintenance Scripts**: Automated cleanup and reindexing
- **Performance Monitoring**: Query performance tracking

### Scaling Guide

See `scripts/db_optimization/scaling_guide.md` for:
- Vertical scaling recommendations
- Connection pooling setup
- Backup strategies
- Troubleshooting common issues

## Live Trading

### Start Live Trading

```bash
source venv/bin/activate
./scripts/start_live_trading.sh
```

The script will:
- Validate IB credentials in `.env`
- Check strategy exists
- Deploy to Backtrader with IB integration
- Run in detached mode (or foreground based on config)

### Stop Live Trading

```bash
./scripts/stop_live_trading.sh
```

### Emergency Stop

If you need to immediately liquidate all positions and stop trading:

```bash
./scripts/emergency_stop.sh
```

This will:
- Query database for open positions
- Liquidate each position via Backtrader
- Stop the algorithm
- Log emergency event

### Backtrader Strategy Structure

Live trading strategies live in [strategies/](strategies/):
- `base_strategy.py` - Base strategy template with risk management
- `risk_manager.py` - Risk management library (position/loss/concentration limits)
- `db_logger.py` - Database logging for monitoring
- `sma_crossover.py` - Example strategy
- `sma_crossover_risk_managed.py` - Example with full risk management

Strategies use Backtrader's native features:
- `self.broker` for position tracking and cash management
- `self.buy()` / `self.sell()` / `self.close()` for orders
- `bt.Strategy` base class with `__init__()` and `next()` methods
- Risk checks via `BaseStrategy` inheritance

## Backtesting

### Run Backtest

Use [scripts/run_backtest.py](scripts/run_backtest.py) for programmatic execution:

```bash
source venv/bin/activate
python scripts/run_backtest.py \
  --strategy strategies.sma_crossover.SMACrossover \
  --start 2020-01-01 --end 2024-12-31 \
  --cash 100000 \
  --symbols SPY
```

Results saved to `results/backtests/{uuid}.json` with:
- Backtest ID (UUID)
- Strategy path
- Time period
- Commission model used
- Full performance metrics (Sharpe, drawdown, returns, etc.)
- Completion status

### Commission Models

Configured in [config/cost_config.yaml](config/cost_config.yaml):

**ib_standard** (default):
- Commission: $0.005/share, $1.00 minimum
- SEC fees: $27.80 per $1M (sells only)
- Slippage: 5 bps market orders, 0 bps limit orders
- Spread: 2 bps typical

**ib_pro** (tiered pricing):
- Commission: $0.0035/share, $0.35 minimum
- Same fees/slippage as standard

### Backtest Configuration

[config/backtest_config.yaml](config/backtest_config.yaml):
- Initial capital: $100,000
- Default resolution: Daily
- Benchmark: SPY
- Parallel execution: enabled (8 workers)
- Results caching: enabled

## Monitoring Dashboard

Streamlit dashboard runs on port 8501 with 9 tabs for comprehensive monitoring:

```bash
# Access at http://localhost:8501
```

### Dashboard Tabs

1. **📊 Dashboard**: Account summary, risk metrics, equity curve
2. **💼 Live Trading**: Active positions with P&L tracking
3. **📜 Trade Log**: Complete trade history with execution details
4. **📈 Performance**: Performance analytics and metrics
5. **🔬 Backtests**: Historical backtest results (JSON-based)
6. **⚙️ Optimization**: Parameter optimization history (JSON-based)
7. **🧪 MLflow**: Experiment tracking and comparison (Epic 17)
8. **🏥 Health**: System health monitoring and diagnostics
9. **⚙️ Settings**: Environment variables and configuration

### MLflow Integration (Epic 17)

The **🧪 MLflow** tab provides AI Research Lab features:

**Features**:
- **Real-time Metrics**: Total experiments, runs, recent activity, failed runs
- **Project Browser**: Filter experiments by project, asset class, strategy family
- **Experiment Listing**: View all experiments with best Sharpe, returns, drawdown
- **Experiment Comparison**: Select 2-5 experiments for side-by-side comparison
- **Performance Charts**:
  - Sharpe Ratio comparison (bar chart)
  - Total Returns comparison (bar chart)
  - Risk-Adjusted Returns scatter plot
- **Link to MLflow UI**: Direct link to full MLflow UI (http://localhost:5000)

**Usage**:
1. Start platform: `./scripts/start.sh`
2. Run backtests with MLflow: `--mlflow` flag
3. Access dashboard: http://localhost:8501
4. Navigate to MLflow tab
5. Use filters and comparison tools

**Note**: MLflow tab requires MLflow server running. If unavailable, dashboard shows warning with startup instructions.

### Data Access

Dashboard has read-only access to:
- `data/` - Historical data
- `results/` - Backtest outputs (JSON files)
- `logs/` - Application logs
- **MLflow Server**: Experiment tracking via http://mlflow:5000

## Configuration Files

Critical config files in [config/](config/):
- `backtest_config.yaml` - Backtest runner settings
- `cost_config.yaml` - IB commission/slippage models
- `data_config.yaml` - Data download settings
- `optimization_config.yaml` - Parameter optimization (Epic 14)
- `walkforward_config.yaml` - Walk-forward analysis (Epic 14)

## Project Rules

**Environment**: Always use `source venv/bin/activate` before Python commands

**Docker Logs**: NEVER use `-f` flag with `docker compose logs` or `docker logs`

**Git**: `.env` file is gitignored - never commit credentials

**Trading Mode**: Default is `paper` - thoroughly test before switching to `live`

**Results**: All backtest results auto-saved to `results/backtests/` with UUID

## Current Implementation Status

**Completed Epics**:
- ✅ **Epic 11**: Migration Foundation (100%)
  - Docker architecture migrated to Backtrader
  - IB connection framework via ib_insync
  - Data pipeline operational
  - Project structure established

- ✅ **Epic 18**: Symbol Discovery Engine (100%)
  - IB Scanner API integration
  - 6 scanner types (high_volume, top_gainers, volatility_leaders, etc.)
  - Intelligent filtering (liquidity, volatility, price range, exchange)
  - PostgreSQL database storage for historical tracking
  - CLI interface with filter overrides
  - CSV/JSON output formats

**Partially Completed Epics**:
- 🔄 **Epic 12**: Core Backtesting Engine (87.5%)
  - ✅ Cerebro engine configuration
  - ✅ Analyzers and performance metrics
  - ✅ Commission models (IB Standard, IB Pro)
  - ✅ Backtest execution script
  - ✅ Result parser
  - ⏳ US-12.6: Monitoring dashboard integration (pending)

- 🔄 **Epic 13**: Algorithm Migration & Risk (37.5%)
  - ✅ Base strategy template
  - ✅ Risk management framework
  - ✅ Example risk-managed strategy
  - ⏳ Additional strategy migrations (pending)
  - ⏳ Live trading deployment (pending)
  - ⏳ Database logger integration (pending)
  - ⏳ Strategy testing (pending)

**Pending Epics**:
- 📋 **Epic 14**: Advanced Features (0%)
  - Parameter optimization
  - Walk-forward analysis
  - Live trading enhancements
  - Claude Skills completion

- 📋 **Epic 15**: Testing & Validation (0%)
  - Unit tests
  - Integration tests
  - Paper trading validation
  - Performance validation

- 🔄 **Epic 16**: Documentation & Cleanup (In Progress)
  - Documentation updates
  - LEAN dependency removal
  - Code cleanup
  - Production cutover

See [stories/epic-12-stories.md](stories/epic-12-stories.md), [stories/epic-13-stories.md](stories/epic-13-stories.md), etc. for details.

## Architecture Notes

### Service Dependencies

```
monitoring → sqlite
backtrader → ib-gateway, sqlite
```

All services restart automatically (`restart: unless-stopped`) unless explicitly stopped.

### Volume Mounts

- `backtrader` service mounts: strategies/, scripts/, config/, data/, results/, logs/
- `monitoring` service has read-only access to data/, results/, logs/
- `sqlite` service mounts data/sqlite/ for persistence

### IB Gateway Health Checks

Health check runs every 30s via `nc -z localhost 4001`:
- Timeout: 10s
- Retries: 3
- Tests API port availability (not authentication)

## Claude Skills

Three specialized skills available for automation:

**data-manager**: Download and validate market data from IB via ib_insync
**backtest-runner**: Execute backtests with performance analysis
**parameter-optimizer**: Optimize strategy parameters (Epic 14)

These auto-invoke when Claude detects related natural language requests.

## AI Code Delegation (Gemini Integration)

For large-scale implementation tasks, Claude Code can delegate work to Gemini AI to leverage its long context window and code generation capabilities while maintaining project context and coding standards.

### When to Use Gemini Delegation

**Ideal Use Cases**:
- **Multi-File Implementations**: Implementing features across 5+ files simultaneously
- **Large-Scale Refactoring**: Applying consistent changes across entire directories (e.g., converting callback patterns to async/await)
- **Comprehensive Testing**: Writing unit tests for multiple modules at once
- **New Module Development**: Implementing complete modules from specifications

**Examples**:
```bash
# Multi-file feature implementation
"Implement authentication system across user service, auth middleware, and token validation modules"

# Large-scale refactoring
"Refactor entire data pipeline in strategies/ to use async/await patterns consistently"

# Comprehensive testing
"Write comprehensive unit tests for strategies/base_strategy.py and strategies/risk_manager.py"

# Module from spec
"Implement risk_calculator.py based on specifications in docs/risk_spec.md"
```

### How It Works

1. **Automatic Detection**: Claude Code detects when a task is better suited for Gemini (large scope, multi-file changes)
2. **Context Preservation**: Project context, coding standards, and architectural patterns are passed to Gemini
3. **Constrained Execution**: File boundaries and modification scope are strictly controlled
4. **Quality Assurance**: Generated code is validated against project standards

### Benefits

- **Long Context Window**: Handle larger codebases and more complex changes in a single pass
- **Parallel Processing**: Multi-file implementations without sequential bottlenecks
- **Consistency**: Apply patterns consistently across multiple files
- **Efficiency**: Faster turnaround for large-scale coding tasks

### Manual Invocation

While Claude Code automatically delegates when appropriate, you can explicitly request Gemini delegation:

```bash
# Explicit delegation request
"Use Gemini to implement the entire risk management module across these 8 files"
```

**Important Notes**:
- Gemini delegation is most effective for implementation tasks. For analysis, architecture design, or debugging, Claude Code's native capabilities are typically better suited.
- **Always use maximum bash timeout** (600000ms / 10 minutes) when delegating to Gemini, as large-scale code generation can take significant time to complete.

## Strategy Development Guide

### Creating a New Strategy

1. **Inherit from BaseStrategy** (recommended for risk management):
   ```python
   from strategies.base_strategy import BaseStrategy
   import backtrader as bt

   class MyStrategy(BaseStrategy):
       params = (
           ('param1', 20),
       )

       def __init__(self):
           # Initialize indicators
           self.sma = bt.indicators.SMA(self.data.close, period=self.params.param1)

       def next(self):
           # Strategy logic
           if not self.position:
               if self.data.close[0] > self.sma[0]:
                   self.buy()
           else:
               if self.data.close[0] < self.sma[0]:
                   self.sell()
   ```

2. **Test via backtest**:
   ```bash
   python scripts/run_backtest.py \
     --strategy strategies.my_strategy.MyStrategy \
     --symbols SPY --start 2020-01-01 --end 2024-12-31
   ```

3. **Deploy to live trading**:
   ```bash
   ./scripts/start_live_trading.sh
   ```

### Risk Management Integration

All strategies should inherit from [strategies/base_strategy.py](strategies/base_strategy.py:1) for automatic risk management:

- **Position Limits**: `max_position_size` parameter
- **Loss Limits**: `max_daily_loss`, `max_drawdown` parameters
- **Concentration Limits**: `max_concentration` parameter
- **Automatic Checks**: Pre-order risk validation
- **Database Logging**: Automatic trade/position logging

See [strategies/risk_manager.py](strategies/risk_manager.py:1) for full framework details.

## Migration from LEAN

This platform was migrated from QuantConnect LEAN to Backtrader in November 2025. Key changes:

**Framework Changes**:
- LEAN QCAlgorithm → Backtrader bt.Strategy
- LEAN CLI → Python scripts + ib_insync
- LEAN data → Direct IB data via ib_insync
- LEAN live trading → Backtrader live trading with IB broker

**Command Changes**:
- `lean backtest` → `python scripts/run_backtest.py`
- `lean live deploy` → `./scripts/start_live_trading.sh`
- `lean data download` → `python scripts/download_data.py`

**Benefits**:
- ✅ Zero vendor lock-in (100% open-source)
- ✅ Full control over execution and data
- ✅ More flexible strategy development
- ✅ Better integration with Python ecosystem
- ✅ Lower costs (no QuantConnect subscription)

See [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md) for complete migration details and [docs/MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md) for LEAN→Backtrader conceptual mapping.

## Troubleshooting

### Common Issues

**"ModuleNotFoundError: No module named 'backtrader'"**
- Activate virtual environment: `source venv/bin/activate`
- Reinstall: `pip install backtrader`

**"Connection refused to IB Gateway"**
- Check IB Gateway is running: `docker compose ps ib-gateway`
- Check credentials in `.env` file
- Verify port 4001 (paper) or 4002 (live) is accessible
- Test connection: `python scripts/ib_connection.py`

**"No data returned for symbol SPY"**
- Verify IB Gateway connection
- Check symbol is valid and market is open
- Verify date range is valid (not future dates)
- Check IB account has market data subscriptions

**"Backtest script fails with import error"**
- Ensure strategy file exists in `strategies/` directory
- Check strategy class name matches import path
- Verify all required indicators are imported

### Debug Mode

Enable debug logging in scripts:
```bash
# Set environment variable
export DEBUG=1

# Run with verbose output
python scripts/run_backtest.py --strategy strategies.my_strategy.MyStrategy --symbols SPY --start 2020-01-01 --end 2024-12-31 --verbose
```

## Performance Best Practices

1. **Use Daily Data**: Start with daily resolution, optimize to intraday only if needed
2. **Limit Symbols**: Start with 1-5 symbols, expand gradually
3. **Cache Results**: Backtest results are cached, reuse when possible
4. **Parallel Execution**: Use `--parallel` flag for multi-symbol backtests (Epic 14)
5. **Monitor Memory**: Large datasets can consume significant memory

## Security Considerations

- **Never commit credentials**: `.env` is gitignored, keep it that way
- **Use paper trading first**: Validate all strategies in paper mode
- **Review risk limits**: Set appropriate position/loss limits
- **Monitor logs**: Regularly check logs for unusual activity
- **Secure VNC**: Change default VNC password in production

---

**Quick Reference Card**:
- Start services: `./scripts/start.sh`
- Download data: `python scripts/download_data.py --symbols SPY --start 2020-01-01 --end 2024-12-31`
- Symbol discovery: `python scripts/symbol_discovery.py --scanner high_volume --output csv`
- Run backtest: `python scripts/run_backtest.py --strategy strategies.sma_crossover.SMACrossover --symbols SPY --start 2020-01-01 --end 2024-12-31`
- Live trading: `./scripts/start_live_trading.sh`
- Emergency stop: `./scripts/emergency_stop.sh`
- View dashboard: `http://localhost:8501`
