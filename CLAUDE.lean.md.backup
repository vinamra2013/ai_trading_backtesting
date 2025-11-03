# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Algorithmic trading platform built on QuantConnect's LEAN engine with Interactive Brokers integration. This is a Python-based backtesting and live trading system using Docker for containerized deployment.

**Architecture**: LEAN-Native - All trading logic runs inside LEAN algorithms, with risk management as an integrated library. LEAN handles positions, orders, and execution natively.

## Environment Management

**CRITICAL**: This project uses a Python virtual environment. ALWAYS activate it before running Python commands:

```bash
source venv/bin/activate
```

All Python commands (pip, lean, python scripts) MUST run within the virtual environment.

## Docker Architecture

The platform uses a 4-service Docker architecture orchestrated via docker-compose.yml:

1. **lean**: LEAN trading engine (Python 3.12)
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
docker compose logs lean
docker compose logs ib-gateway

# Restart specific service
docker compose restart lean
```

## Interactive Brokers Integration

### Credentials Setup

IB credentials are managed through `.env` file and Docker secrets:
- Username/password stored in `.env` (gitignored)
- Password also mounted as Docker secret at `/run/secrets/ib_password`
- Trading mode: `paper` (default) or `live`

### Connection Architecture

`scripts/ib_connection.py` provides `IBConnectionManager` class with:
- Exponential backoff retry (3 attempts: 1s, 2s, 4s)
- Health checks every 30 seconds
- Context manager support for automatic connection lifecycle
- Port 4001 for paper trading, 4002 for live (default: 4001)

Note: Current implementation is a framework placeholder awaiting `ib_insync` integration when algorithms are deployed.

## LEAN Engine Commands

All LEAN CLI commands require virtual environment activation:

```bash
source venv/bin/activate

# Create new algorithm
lean create-python-algorithm my_algorithm

# Run backtest
lean backtest algorithms/my_algorithm

# Optimize parameters
lean optimize algorithms/my_algorithm

# Deploy to live trading
lean live deploy algorithms/my_algorithm
```

## Data Management

### Download Historical Data

Use `scripts/download_data.py` wrapper around LEAN CLI:

```bash
source venv/bin/activate
python scripts/download_data.py --symbols SPY AAPL \
  --start 2020-01-01 --end 2024-12-31 \
  --resolution Daily --data-type Trade
```

The script:
- Requires IB credentials in `.env` file
- Converts YYYY-MM-DD to YYYYMMDD format
- Supports multiple symbols (comma-separated)
- Data types: Trade, Quote
- Resolutions: Daily, Hour, Minute, Second
- Markets: USA (default)

### Data Storage Structure

```
data/
├── raw/        # Downloaded market data
├── processed/  # Cleaned/transformed data
├── lean/       # LEAN-formatted data
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
- Check algorithm exists
- Deploy via `lean live deploy` with IB integration
- Run in detached mode

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
- Liquidate each position via `lean live liquidate`
- Stop the algorithm
- Log emergency event

### LEAN Algorithm Structure

Live trading algorithms live in `algorithms/live_strategy/`:
- `main.py` - Main algorithm with trading logic
- `risk_manager.py` - Risk management library (position/loss/concentration limits)
- `db_logger.py` - Database logging for monitoring

The algorithm uses LEAN's native features:
- `self.Portfolio` for position tracking
- `self.MarketOrder()` / `self.LimitOrder()` for orders
- `self.Schedule.On()` for EOD liquidation at 3:55 PM
- Risk checks before every order

## Backtesting

### Run Backtest

Use `scripts/run_backtest.py` for programmatic execution:

```bash
source venv/bin/activate
python scripts/run_backtest.py \
  --algorithm algorithms/my_strategy \
  --start 2020-01-01 --end 2024-12-31 \
  --cost-model ib_standard
```

Results saved to `results/backtests/{uuid}.json` with:
- Backtest ID (UUID)
- Algorithm path
- Time period
- Cost model used
- Full stdout from LEAN
- Completion status

### Cost Models

Configured in `config/cost_config.yaml`:

**ib_standard** (default):
- Commission: $0.005/share, $1.00 minimum
- SEC fees: $27.80 per $1M (sells only)
- Slippage: 5 bps market orders, 0 bps limit orders
- Spread: 2 bps typical

**ib_pro** (tiered pricing):
- Commission: $0.0035/share, $0.35 minimum
- Same fees/slippage as standard

### Backtest Configuration

`config/backtest_config.yaml`:
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

## Configuration Files

Critical config files in `config/`:
- `backtest_config.yaml` - Backtest runner settings
- `cost_config.yaml` - IB commission/slippage models
- `data_config.yaml` - Data download settings
- `optimization_config.yaml` - Parameter optimization
- `walkforward_config.yaml` - Walk-forward analysis

## Project Rules

**Environment**: Always use `source venv/bin/activate` before Python commands

**Docker Logs**: NEVER use `-f` flag with `docker compose logs` or `docker logs`

**Git**: `.env` file is gitignored - never commit credentials

**Trading Mode**: Default is `paper` - thoroughly test before switching to `live`

**Results**: All backtest results auto-saved to `results/backtests/` with UUID

## Current Implementation Status

**Completed** (Epic 1-6):
- Development environment with LEAN CLI v1.0.221
- Full Docker orchestration (4 services)
- IB Gateway connection framework (credentials-ready)
- Data download pipeline via LEAN CLI
- Backtest execution with IB cost models
- Monitoring dashboard infrastructure
- **Live trading LEAN algorithm** (`algorithms/live_strategy/main.py`)
- **Risk management library** (position limits, loss limits, concentration)
- **Database logging** (orders, positions, P&L, risk events)
- **Emergency stop capability** (`./scripts/emergency_stop.sh`)
- **Deployment scripts** (`start_live_trading.sh`, `stop_live_trading.sh`)

See `stories/epic-5-stories.md` and `stories/epic-6-stories.md` for details.

## Architecture Notes

### Service Dependencies

```
monitoring → sqlite
lean → ib-gateway, sqlite
```

All services restart automatically (`restart: unless-stopped`) unless explicitly stopped.

### Volume Mounts

- `lean` service mounts: algorithms/, config/, data/, results/, logs/
- `monitoring` service has read-only access to data/, results/, logs/
- `sqlite` service mounts data/sqlite/ for persistence

### IB Gateway Health Checks

Health check runs every 30s via `nc -z localhost 4001`:
- Timeout: 10s
- Retries: 3
- Tests API port availability (not authentication)

## Claude Skills

Two specialized skills available for automation:

**data-manager**: Download and validate market data from IB
**backtest-runner**: Execute backtests with performance analysis

These auto-invoke when Claude detects related natural language requests.
