---
name: backtest-runner
description: Run backtests programmatically using LEAN engine, analyze performance with realistic IB cost models, optimize parameters with grid search, and perform walk-forward validation.
---

# Backtest Runner Skill

Programmatic interface for running backtests, analyzing results, optimizing parameters, and validating strategies using LEAN.

## Capabilities

1. **Run Backtests**: Execute LEAN backtests programmatically
2. **Cost Modeling**: Apply realistic IB commission, slippage, and fees
3. **Performance Analysis**: Calculate metrics (Sharpe, Sortino, drawdown, etc.)
4. **Parameter Optimization**: Grid search with parallel execution
5. **Walk-Forward Analysis**: Rolling window train/test validation

## Usage

### Run a Backtest

```bash
# Using LEAN CLI directly
lean backtest algorithms/MyStrategy

# Using Claude helper (recommended for AI)
python scripts/claude_backtest_helper.py \
  --algorithm algorithms/MyStrategy \
  --start 2020-01-01 \
  --end 2024-12-31

# With parameters
python scripts/claude_backtest_helper.py \
  --algorithm algorithms/MyStrategy \
  --param sma_period 20 \
  --param rsi_threshold 30
```

### Natural Language Examples

When Claude receives requests like:
- "Run a backtest on MyStrategy from 2020 to 2024"
- "Test the algorithm with SMA period 50"
- "Compare results with different RSI thresholds"

Claude should:
1. Use `claude_backtest_helper.py` for simple runs
2. Parse LEAN output and extract metrics
3. Provide human-readable summaries
4. Compare results across parameter variations

### Optimize Parameters

```bash
# Grid search optimization
python scripts/optimize_parameters.py \
  --algorithm algorithms/MyStrategy \
  --params "sma_period:10,20,50;rsi_threshold:30,40,50" \
  --metric sharpe_ratio \
  --start 2020-01-01 \
  --end 2024-12-31

# With train/test split for overfitting detection
python scripts/optimize_parameters.py \
  --algorithm algorithms/MyStrategy \
  --params "sma_period:10,20,50;threshold:0.01,0.02,0.05" \
  --metric sharpe_ratio \
  --start 2020-01-01 \
  --end 2024-12-31 \
  --train-test-split 0.6
```

### Natural Language Optimization Examples

When Claude receives requests like:
- "Optimize SMA period from 10 to 100, step 10"
- "Find best RSI threshold between 30 and 70"
- "Test all combinations of period and threshold"

Claude should:
1. Parse parameter ranges from natural language
2. Convert to `--params` format
3. Run `optimize_parameters.py`
4. Interpret results and report top combinations
5. Flag overfitting warnings if present

## Cost Models

### IB Standard Cost Model

Realistic Interactive Brokers commission and fee structure:

```python
# Commission
commission_per_share = 0.005  # $0.005 per share
minimum_commission = 1.00     # $1.00 minimum per order
maximum_commission_rate = 0.01  # 1% of trade value max

# SEC fees (for sells only)
sec_fee_rate = 0.0000278  # $27.80 per $1M

# Slippage (market orders)
slippage_basis_points = 5  # 0.05% typical slippage

# Bid-ask spread simulation
spread_factor = 0.5  # Use midpoint + half spread
```

## Performance Metrics

### Core Metrics
- **Total Return**: Cumulative return over backtest period
- **Annualized Return**: CAGR
- **Sharpe Ratio**: Risk-adjusted return (annualized)
- **Sortino Ratio**: Downside risk-adjusted return
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Recovery Time**: Days to recover from max drawdown

### Trade Metrics
- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Gross profit / gross loss
- **Average Win/Loss**: Mean profit and loss per trade
- **Trade Count**: Total number of trades

### Risk Metrics
- **Volatility**: Annualized standard deviation of returns
- **Beta**: Market sensitivity (vs SPY)
- **Value at Risk (VaR)**: 95% confidence loss threshold

## Parameter Optimization

### Grid Search

Tests all combinations of specified parameter ranges:

```yaml
# config/optimization_config.yaml
parameters:
  sma_period: [10, 20, 50, 100]
  rsi_threshold: [30, 40, 50]
  stop_loss: [0.02, 0.05, 0.10]

optimization:
  metric: sharpe_ratio
  parallel_cores: 8
  train_period: "2020-01-01 to 2022-12-31"
  test_period: "2023-01-01 to 2024-12-31"
```

### Overfitting Detection

- Compare in-sample vs out-of-sample performance
- Flag if out-of-sample Sharpe < 70% of in-sample
- Report top 10 parameter combinations
- Analyze parameter stability across periods

## Walk-Forward Analysis

### Process

1. **Split Data**: Divide into rolling train/test windows
2. **Optimize**: Find best parameters on train window
3. **Validate**: Test on out-of-sample test window
4. **Roll Forward**: Move window and repeat
5. **Aggregate**: Combine all test period results

### Configuration

```yaml
# config/walkforward_config.yaml
train_months: 6
test_months: 2
anchor: false  # true = anchored, false = rolling
step_months: 2  # how far to move window each iteration
```

### Parameter Drift Detection

- Track optimal parameters over time
- Identify regime changes
- Visualize parameter stability
- Alert on significant drift

## Report Generation

### HTML Report

Generated reports include:

- **Summary Stats**: Key performance metrics
- **Equity Curve**: Cumulative returns over time
- **Drawdown Chart**: Underwater plot
- **Monthly Returns**: Heatmap of returns by month
- **Trade Log**: Complete trade-by-trade history (CSV export)
- **Cost Analysis**: Breakdown of commissions and fees

### JSON Export

```json
{
  "backtest_id": "uuid",
  "algorithm": "MyStrategy",
  "period": {"start": "2020-01-01", "end": "2024-12-31"},
  "metrics": {
    "total_return": 0.45,
    "sharpe_ratio": 1.8,
    "max_drawdown": -0.15,
    "win_rate": 0.62
  },
  "trades": [...],
  "equity_curve": [...]
}
```

## Configuration Files

- `config/backtest_config.yaml`: Default backtest settings
- `config/cost_config.yaml`: Commission and fee parameters
- `config/optimization_config.yaml`: Parameter ranges and settings
- `config/walkforward_config.yaml`: Walk-forward analysis settings

## Viewing Results in Dashboard

All backtest and optimization results are viewable in the Streamlit monitoring dashboard:

```bash
# Start dashboard (if not already running)
./scripts/start.sh

# Access at http://localhost:8501
```

### Dashboard Features

**Backtests Tab:**
- List all backtest runs with summary metrics
- View detailed backtest results and equity curves
- Examine trade-by-trade log with P&L breakdown
- Compare multiple backtests side-by-side

**Optimization Tab:**
- List all optimization runs
- View parameter combination results table
- Interactive parameter heatmaps for 2D analysis
- Overfitting analysis with train/test comparison

## Scripts

- `scripts/run_backtest.py`: Execute backtests programmatically
- `scripts/backtest_parser.py`: Parse LEAN output to structured JSON
- `scripts/claude_backtest_helper.py`: Claude-friendly backtest interface
- `scripts/compare_backtests.py`: Compare multiple backtest results
- `scripts/optimize_parameters.py`: Parameter grid search optimization
- `monitoring/app.py`: Streamlit dashboard for result visualization

## Dependencies

- LEAN CLI and engine
- pandas, numpy for data analysis
- matplotlib, plotly for charting
- multiprocessing for parallel optimization
- jinja2 for HTML report templates

## Troubleshooting

### Common Issues

**Backtest Fails:**
- Check algorithm syntax: `python -m py_compile algorithms/MyStrategy/main.py`
- Verify data exists for symbols and date range
- Check LEAN logs: `docker compose logs lean`

**Parsing Fails:**
- LEAN output format may have changed
- Check `scripts/backtest_parser.py` regex patterns
- Manually inspect raw stdout in result JSON

**Dashboard Not Showing Results:**
- Verify results saved to `results/backtests/` or `results/optimizations/`
- Check JSON file format matches expected structure
- Restart dashboard: `docker compose restart monitoring`

### Getting Help

Claude can help with:
- Converting natural language to CLI commands
- Interpreting backtest results and metrics
- Comparing performance across parameter values
- Identifying overfitting or data issues
- Suggesting parameter ranges to test

## Notes

- All backtests use realistic IB cost model by default
- Parallel optimization uses all CPU cores unless specified
- Results automatically saved with UUID for tracking
- Dashboard provides real-time access to all results
- Equity curves and metrics cached for comparison
- Failed backtests logged but don't stop optimization runs
