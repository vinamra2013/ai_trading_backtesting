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
source venv/bin/activate
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
source venv/bin/activate
python scripts/run_backtest.py \
  --strategy strategies.sma_crossover.SMACrossover \
  --symbols SPY --start 2020-01-01 --end 2024-12-31 \
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

# Optimize parameters (Epic 14 - pending)
python scripts/optimize_strategy.py \
  --strategy strategies.sma_crossover.SMACrossover \
  --param-ranges "sma_short:10-30,sma_long:40-80"

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

### Data Storage Structure

```
data/
├── raw/        # Downloaded market data
├── processed/  # Cleaned/transformed data
└── sqlite/     # Trade history database
```

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

Streamlit dashboard runs on port 8501:

```bash
# Access at http://localhost:8501
```

Dashboard has read-only access to:
- `data/` - Historical data
- `results/` - Backtest outputs
- `logs/` - Application logs

**Note**: Dashboard integration with Backtrader backtest results is pending (US-12.6 from Epic 12).

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
- Run backtest: `python scripts/run_backtest.py --strategy strategies.sma_crossover.SMACrossover --symbols SPY --start 2020-01-01 --end 2024-12-31`
- Live trading: `./scripts/start_live_trading.sh`
- Emergency stop: `./scripts/emergency_stop.sh`
- View dashboard: `http://localhost:8501`
