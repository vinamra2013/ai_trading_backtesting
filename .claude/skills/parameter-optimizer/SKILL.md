---
name: parameter-optimizer
description: Find optimal algorithm parameters using grid search with parallel execution, overfitting detection, and comprehensive result analysis.
---

# Parameter Optimizer Skill

Systematic parameter optimization for LEAN algorithms using grid search, parallel execution, and statistical validation.

## Capabilities

1. **Grid Search Optimization**: Test all combinations of parameter ranges
2. **Parallel Execution**: Utilize all CPU cores for faster optimization
3. **Overfitting Detection**: Train/test split validation to detect parameter overfitting
4. **Result Ranking**: Automatic sorting by optimization metric
5. **Progress Tracking**: Real-time progress with ETA estimates
6. **Dashboard Integration**: Results saved in format compatible with monitoring dashboard

## Usage

### Basic Optimization

```bash
# Optimize a single parameter
python scripts/optimize_parameters.py \
  --algorithm algorithms/MyStrategy \
  --params "sma_period:10,20,50" \
  --metric sharpe_ratio \
  --start 2020-01-01 --end 2024-12-31

# View results in dashboard at http://localhost:8501 (Optimization tab)
```

### Multiple Parameters

```bash
# Optimize multiple parameters simultaneously
python scripts/optimize_parameters.py \
  --algorithm algorithms/MyStrategy \
  --params "sma_period:10,20,50;rsi_threshold:30,40,50;stop_loss:0.02,0.05,0.10" \
  --metric sharpe_ratio \
  --start 2020-01-01 --end 2024-12-31
```

### With Overfitting Detection

```bash
# Use train/test split to detect overfitting
python scripts/optimize_parameters.py \
  --algorithm algorithms/MyStrategy \
  --params "sma_period:10,20,50;threshold:0.01,0.02,0.05" \
  --metric sharpe_ratio \
  --start 2020-01-01 --end 2024-12-31 \
  --train-test-split 0.6  # 60% train, 40% test
```

## Natural Language Examples

When Claude receives requests like:

**Single Parameter:**
- "Optimize SMA period from 10 to 100, step 10"
- "Find best SMA period between 10 and 50"
- "Test SMA periods of 10, 20, 50, and 100"

Claude should:
1. Convert range to parameter list: `"sma_period:10,20,30,40,50,60,70,80,90,100"`
2. Run optimization with appropriate metric
3. Report top 3-5 combinations with metrics
4. Warn about overfitting if test performance is significantly worse

**Multiple Parameters:**
- "Optimize SMA period and RSI threshold"
- "Find best combination of period 10-50 and threshold 30-70"
- "Test all combinations of SMA 10,20,50 and RSI 30,40,50"

Claude should:
1. Parse both parameter ranges
2. Calculate total combinations (e.g., 3 x 3 = 9)
3. Run grid search
4. Analyze parameter interaction via heatmaps
5. Report best combination

**With Validation:**
- "Optimize parameters but check for overfitting"
- "Find best parameters with train/test split"
- "Validate parameters on out-of-sample data"

Claude should:
1. Use `--train-test-split 0.6` (60/40 split)
2. Report both in-sample and out-of-sample performance
3. Calculate test/train performance ratio
4. Flag if ratio < 0.7 (significant degradation)
5. Recommend more robust parameters if overfitting detected

## Parameter Format

Parameters are specified as semicolon-separated pairs:

```
"param1:val1,val2,val3;param2:val1,val2;param3:val1,val2,val3"
```

**Examples:**
- Single: `"sma_period:10,20,50"`
- Multiple: `"sma_period:10,20,50;rsi_threshold:30,40,50"`
- Mixed types: `"period:10,20,50;threshold:0.01,0.02,0.05;use_stops:true,false"`

**Value Types:**
- Integers: `10,20,50`
- Floats: `0.01,0.02,0.05`
- Strings: `"fast,medium,slow"` (if supported by algorithm)

## Optimization Metrics

Available metrics for optimization:

| Metric | Description | Best Value |
|--------|-------------|------------|
| `sharpe_ratio` | Risk-adjusted return (default) | Higher |
| `sortino_ratio` | Downside risk-adjusted return | Higher |
| `total_return` | Cumulative return | Higher |
| `profit_factor` | Gross profit / gross loss | Higher |
| `max_drawdown` | Maximum peak-to-trough decline | Lower (closer to 0) |

**Recommendation**: Use `sharpe_ratio` for most cases as it balances return and risk.

## Overfitting Detection

### Train/Test Split

Use `--train-test-split` to validate parameters on out-of-sample data:

```bash
--train-test-split 0.6  # 60% train, 40% test
```

**Process:**
1. Optimize on training period (first 60% of data)
2. Test best parameters on test period (last 40% of data)
3. Calculate test/train performance ratio
4. Flag overfitting if test < 70% of train performance

### Overfitting Threshold

Adjust sensitivity with `--overfitting-threshold`:

```bash
--overfitting-threshold 0.8  # Flag if test < 80% of train (stricter)
--overfitting-threshold 0.6  # Flag if test < 60% of train (looser)
```

**Default**: 0.7 (test must be ≥70% of train performance)

### Interpreting Results

**Overfitting Indicators:**
- Test/train ratio < 0.7: **HIGH overfitting** - parameters too specific to training data
- Test/train ratio 0.7-0.8: **MODERATE overfitting** - some concern, validate further
- Test/train ratio 0.8-1.0: **GOOD** - parameters generalize well
- Test/train ratio > 1.0: **EXCELLENT** - parameters improve on test data (rare)

**Recommendations:**
- If overfitting detected: Use simpler parameters, fewer constraints
- If no overfitting: Parameters are robust, safe to use
- If test > train: Excellent generalization, but verify not due to luck

## Output Format

### JSON Structure

Results saved to `results/optimizations/{uuid}.json`:

```json
{
  "optimization_id": "uuid",
  "algorithm": "algorithms/MyStrategy",
  "metric": "sharpe_ratio",
  "param_ranges": {
    "sma_period": [10, 20, 50],
    "rsi_threshold": [30, 40, 50]
  },
  "total_combinations": 9,
  "train_period": {"start": "2020-01-01", "end": "2022-12-31"},
  "test_period": {"start": "2023-01-01", "end": "2024-12-31"},
  "execution_time_seconds": 450,
  "parallel_workers": 8,
  "results": [
    {
      "parameters": {"sma_period": 20, "rsi_threshold": 40},
      "train_sharpe_ratio": 1.82,
      "test_sharpe_ratio": 1.65,
      "overfitting_ratio": 0.91,
      "overfitting_detected": false
    },
    ...
  ],
  "top_10": [...],  // Top 10 parameter combinations
  "timestamp": "2024-11-02T..."
}
```

### Console Output

```
=== Starting Parameter Optimization ===
Total combinations: 9
Parallel workers: 8

Running backtests in parallel...
Progress: 33.3% (3/9) - ETA: 2.5m
Progress: 66.7% (6/9) - ETA: 1.2m
Progress: 100.0% (9/9) - ETA: 0.0m

✓ Optimization completed in 3.8 minutes
Results saved to: results/optimizations/abc-123.json

================================================================================
TOP 3 PARAMETER COMBINATIONS:
================================================================================

1. Parameters: {'sma_period': 20, 'rsi_threshold': 40}
   Train sharpe_ratio: 1.82
   Test sharpe_ratio: 1.65
   Overfitting ratio: 0.91

2. Parameters: {'sma_period': 50, 'rsi_threshold': 30}
   Train sharpe_ratio: 1.75
   Test sharpe_ratio: 1.58
   Overfitting ratio: 0.90

3. Parameters: {'sma_period': 20, 'rsi_threshold': 30}
   Train sharpe_ratio: 1.68
   Test sharpe_ratio: 1.52
   Overfitting ratio: 0.90
```

## Dashboard Integration

### Viewing Results

1. Start monitoring dashboard: `./scripts/start.sh`
2. Navigate to http://localhost:8501
3. Click "Optimization" tab
4. Select optimization run from list
5. View results table, parameter heatmaps, and analysis

### Features Available in Dashboard

- **Results Table**: Sortable table of all parameter combinations
- **Parameter Heatmaps**: Visual analysis of parameter interactions
- **Metric Comparison**: Compare train vs test performance
- **Overfitting Analysis**: Visual indicators for overfitting detection
- **Export**: Download results as CSV for further analysis

## Performance Considerations

### Computational Cost

Grid search tests **all combinations**:
- 3 parameters × 3 values each = **27 backtests**
- 3 parameters × 5 values each = **125 backtests**
- 4 parameters × 5 values each = **625 backtests**

**Time Estimate**: ~30 seconds per backtest × combinations / CPU cores

**Example**: 125 backtests on 8-core machine = ~8 minutes

### Optimization Strategies

**Coarse to Fine:**
1. Start with wide ranges and few values: `10,50,100`
2. Identify promising region
3. Refine with narrower range: `40,50,60,70,80`

**Parameter Reduction:**
- Test most impactful parameters first
- Fix less sensitive parameters at reasonable defaults
- Add more parameters once primary ones optimized

**Parallel Workers:**
```bash
--workers 4   # Use 4 CPU cores (conservative)
--workers 8   # Use 8 CPU cores (typical)
# Omit flag to use all available cores (default)
```

## LEAN Parameter Passing

### How Parameters Work

LEAN algorithms can receive parameters via:

1. **Command-line flags** (used by this optimizer):
   ```bash
   lean backtest algorithms/MyStrategy \
     --parameter sma_period 20 \
     --parameter rsi_threshold 40
   ```

2. **Algorithm code** (must be set up to receive parameters):
   ```python
   class MyStrategy(QCAlgorithm):
       def Initialize(self):
           # Read parameters passed via CLI
           self.sma_period = self.GetParameter("sma_period", 20)
           self.rsi_threshold = self.GetParameter("rsi_threshold", 40)
   ```

### Setting Up Algorithm for Optimization

To make your algorithm optimizable, add parameter reading in `Initialize()`:

```python
def Initialize(self):
    # Read parameters with defaults
    self.sma_period = int(self.GetParameter("sma_period", 20))
    self.rsi_threshold = int(self.GetParameter("rsi_threshold", 40))
    self.stop_loss = float(self.GetParameter("stop_loss", 0.02))

    # Use parameters in strategy
    self.sma = self.SMA("SPY", self.sma_period)
    self.rsi = self.RSI("SPY", 14, MovingAverageType.Simple)
```

## Troubleshooting

### Common Issues

**Issue**: No results returned
- **Cause**: Algorithm doesn't read parameters via `GetParameter()`
- **Fix**: Add parameter reading code to algorithm's `Initialize()` method

**Issue**: All backtests fail
- **Cause**: Invalid parameter values or algorithm errors
- **Fix**: Test algorithm manually with sample parameters first

**Issue**: Optimization takes too long
- **Cause**: Too many parameter combinations
- **Fix**: Reduce parameter ranges or use coarse-to-fine approach

**Issue**: Overfitting detected for all parameters
- **Cause**: Strategy too complex or data too limited
- **Fix**: Simplify strategy, use more data, or adjust overfitting threshold

### Debugging

Run single backtest to verify parameters work:

```bash
lean backtest algorithms/MyStrategy \
  --parameter sma_period 20 \
  --parameter rsi_threshold 40
```

Check optimization logs:
```bash
# Logs show each backtest's stdout
cat results/optimizations/{optimization-id}.json | jq '.results[0].train_stdout'
```

## Best Practices

### Parameter Selection

1. **Start Simple**: Begin with 1-2 most impactful parameters
2. **Reasonable Ranges**: Use domain knowledge to set sensible ranges
3. **Avoid Overfitting**: More parameters = higher overfitting risk
4. **Economic Rationale**: Parameters should have business logic behind them

### Validation

1. **Always Use Train/Test Split**: Minimum 60/40 split recommended
2. **Walk-Forward Analysis**: For more robust validation (use walkforward script)
3. **Multiple Periods**: Test on different market conditions
4. **Out-of-Sample**: Reserve 20% of data never used in optimization

### Interpretation

1. **Top 10 Combinations**: Review top 10, not just #1 (avoids overfitting)
2. **Parameter Stability**: Similar parameter values in top 10 = more robust
3. **Metric Consistency**: Check multiple metrics, not just optimization target
4. **Economic Reality**: Does parameter make sense? (e.g., SMA period = 2 is suspicious)

## Related Tools

- **`scripts/run_backtest.py`**: Run single backtest with specific parameters
- **`scripts/compare_backtests.py`**: Compare multiple backtest results
- **`scripts/claude_backtest_helper.py`**: Claude-friendly backtest interface
- **Monitoring Dashboard**: Visualize optimization results at http://localhost:8501

## Configuration

Default optimization settings in `config/optimization_config.yaml`:

```yaml
optimization:
  metric: sharpe_ratio
  train_test_split: 0.6
  parallel_cores: 8
  overfitting:
    enabled: true
    min_test_performance_ratio: 0.7
    warn_if_below: 0.8
  top_n_results: 10
```

## Notes

- Optimization results are cached and never overwritten
- Each optimization run gets unique UUID
- Failed backtests are logged but don't stop optimization
- Progress tracking shows ETA based on completed backtests
- Results are immediately available in dashboard
- Supports mixed parameter types (int, float, string)
- All backtests use same cost model for fair comparison
- Train/test split is chronological (not random) to respect time-series nature

## Examples for Claude

### Example 1: Basic Optimization

**User**: "Optimize the SMA period from 10 to 100"

**Claude Response**:
```bash
# Convert range to discrete values (step 10)
python scripts/optimize_parameters.py \
  --algorithm algorithms/MyStrategy \
  --params "sma_period:10,20,30,40,50,60,70,80,90,100" \
  --metric sharpe_ratio \
  --start 2020-01-01 --end 2024-12-31
```

Expected: 10 backtests, ~5 minutes on 8-core machine

### Example 2: Multiple Parameters with Overfitting Check

**User**: "Find best SMA period and RSI threshold, check for overfitting"

**Claude Response**:
```bash
python scripts/optimize_parameters.py \
  --algorithm algorithms/MyStrategy \
  --params "sma_period:10,20,50;rsi_threshold:30,40,50,60,70" \
  --metric sharpe_ratio \
  --start 2020-01-01 --end 2024-12-31 \
  --train-test-split 0.6
```

Expected: 15 backtests (3 × 5), train on 2020-2022, test on 2023-2024

### Example 3: Interpreting Results

**User**: "What do the optimization results mean?"

**Claude Analysis**:
- Top combination: SMA=20, RSI=40 → Sharpe 1.82 (train), 1.65 (test)
- Overfitting ratio: 0.91 (test is 91% of train) → **GOOD**
- Conclusion: Parameters generalize well, safe to use
- Next step: Validate on most recent data or paper trading

**User**: "Overfitting detected warning?"

**Claude Analysis**:
- Top combination: SMA=10, RSI=30 → Sharpe 2.5 (train), 1.5 (test)
- Overfitting ratio: 0.60 (test is 60% of train) → **HIGH OVERFITTING**
- Conclusion: Parameters too specific to training period
- Recommendation: Simplify strategy, use longer SMA periods, or get more data
