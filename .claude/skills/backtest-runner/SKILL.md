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
# Using LEAN CLI
lean backtest algorithms/MyStrategy \
  --start 20200101 \
  --end 20241231

# Or programmatically
python scripts/run_backtest.py \
  --algorithm algorithms/MyStrategy \
  --start 2020-01-01 \
  --end 2024-12-31 \
  --cost-model ib_standard
```

### Analyze Results

```bash
python scripts/analyze_backtest.py \
  --result results/backtests/latest.json \
  --output results/analysis/report.html
```

### Optimize Parameters

```bash
python scripts/optimize_strategy.py \
  --algorithm algorithms/MyStrategy \
  --params "sma_period:10,20,50;threshold:0.01,0.02,0.05" \
  --metric sharpe_ratio \
  --parallel 8
```

### Walk-Forward Analysis

```bash
python scripts/walk_forward.py \
  --algorithm algorithms/MyStrategy \
  --train-months 6 \
  --test-months 2 \
  --params "sma_period:10,20,50"
```

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

## Scripts

- `scripts/run_backtest.py`: Execute backtests programmatically
- `scripts/analyze_backtest.py`: Calculate performance metrics
- `scripts/generate_report.py`: Create HTML/JSON reports
- `scripts/optimize_strategy.py`: Parameter grid search
- `scripts/walk_forward.py`: Walk-forward validation
- `scripts/cost_model.py`: IB commission and slippage calculator

## Dependencies

- LEAN CLI and engine
- pandas, numpy for data analysis
- matplotlib, plotly for charting
- multiprocessing for parallel optimization
- jinja2 for HTML report templates

## Notes

- All backtests use realistic IB cost model by default
- Parallel optimization uses all CPU cores unless specified
- Walk-forward analysis prevents look-ahead bias
- Reports saved to `results/` directory
- Equity curves and metrics cached for comparison
