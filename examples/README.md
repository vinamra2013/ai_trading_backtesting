# Claude Skills Usage Examples

Examples for using the `data-manager` and `backtest-runner` Claude Skills.

## Data Manager Skill Examples

### Download Historical Data

```bash
# Download daily data for multiple symbols
python scripts/download_data.py \
  --symbols SPY AAPL MSFT \
  --start 2020-01-01 \
  --end 2024-12-31 \
  --resolution Daily

# Download with resume capability (recommended)
python scripts/download_data.py \
  --symbols SPY AAPL MSFT GOOGL AMZN \
  --start 2020-01-01 \
  --end 2024-12-31 \
  --resume
```

### Validate Data Quality

```bash
# Check data quality for symbols
python scripts/data_quality_check.py \
  --symbols SPY AAPL MSFT \
  --report-format json \
  --output reports/quality_report.json

# Verbose validation
python scripts/data_quality_check.py \
  --symbols SPY AAPL \
  --verbose
```

### Incremental Data Updates

```bash
# Update data with auto-detection of last date
python scripts/update_data.py \
  --symbols SPY AAPL MSFT \
  --auto-detect-start

# Manual update for last 30 days
python scripts/update_data.py \
  --symbols SPY AAPL
```

## Backtest Runner Skill Examples

### Run a Backtest

```bash
# Basic backtest
python scripts/run_backtest.py \
  --algorithm algorithms/MyStrategy \
  --start 2020-01-01 \
  --end 2024-12-31

# Backtest with specific cost model
python scripts/run_backtest.py \
  --algorithm algorithms/MyStrategy \
  --start 2023-01-01 \
  --end 2024-12-31 \
  --cost-model ib_standard
```

### Using LEAN CLI Directly

```bash
# Run backtest with LEAN CLI
lean backtest algorithms/MyStrategy

# Create new algorithm
lean create-python-algorithm MyNewStrategy

# Optimize parameters
lean optimize algorithms/MyStrategy
```

## Configuration

All skills use YAML configuration files in `config/`:

- `data_config.yaml` - Data download and validation settings
- `backtest_config.yaml` - Backtest execution settings
- `cost_config.yaml` - Commission and slippage models
- `optimization_config.yaml` - Parameter optimization settings
- `walkforward_config.yaml` - Walk-forward analysis settings

## Interactive Brokers Setup

Ensure `.env` file contains:

```bash
IB_USERNAME=your_username
IB_ACCOUNT=your_account_id
IB_PASSWORD=your_password
IB_TRADING_MODE=paper  # or 'live'
```

## Claude Skills Invocation

When working with Claude, you can simply ask:

> "Download SPY data for the last 2 years and validate quality"

Claude will automatically invoke the `data-manager` skill and use the appropriate scripts.

> "Run a backtest on MyStrategy from 2020 to 2024"

Claude will use the `backtest-runner` skill to execute the backtest.

## Directory Structure

```
.claude/skills/
├── data-manager/
│   └── SKILL.md
└── backtest-runner/
    └── SKILL.md

scripts/
├── download_data.py          # US-3.1
├── data_quality_check.py     # US-3.3
├── update_data.py            # US-3.4
└── run_backtest.py           # US-4.1

config/
├── data_config.yaml
├── backtest_config.yaml
├── cost_config.yaml          # US-4.2
├── optimization_config.yaml   # US-4.4
└── walkforward_config.yaml   # US-4.5

results/
├── backtests/                # Backtest results
├── optimization/             # Optimization results
└── walkforward/              # Walk-forward results
```

## Next Steps

1. **Epic 3 Complete**: Data management infrastructure ready
2. **Epic 4 Partial**: Core backtesting ready, advanced features (optimization, walk-forward) have configuration but need full implementation
3. **Epic 5**: Live trading engine (next)
4. **Epic 6**: Risk management system (next)

See [stories/](../stories/) for detailed progress tracking.
