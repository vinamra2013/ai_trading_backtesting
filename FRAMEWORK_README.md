# QuantConnect Backtesting Framework

**Automated parameter optimization and backtesting system for QuantConnect LEAN**

**Target**: 100+ strategy variations per week with minimal developer time
**Focus**: Euler Search + Walk-Forward Analysis

---

## Quick Start

### 1. Setup Database

```bash
# Create PostgreSQL database
createdb trading

# Run schema
psql -U postgres -d trading -f scripts/db_schema.sql
```

### 2. Create Strategy in LEAN

```python
# lean_projects/MyStrategy/main.py
from AlgorithmImports import *

class MyStrategy(QCAlgorithm):
    def initialize(self):
        # CRITICAL: Use get_parameter() for all optimizable values
        rsi_period = int(self.get_parameter("rsi_period", "14"))
        entry_threshold = int(self.get_parameter("entry_threshold", "30"))

        # Rest of strategy...
```

**See**: `docs/LEAN_DEVELOPER_GUIDE.md` for complete patterns

### 3. Create Optimization Config

```bash
# Copy template
cp configs/optimizations/template.yaml configs/optimizations/my_strategy.yaml

# Edit parameters
nano configs/optimizations/my_strategy.yaml
```

### 4. Run Optimization

```bash
# Activate virtual environment (required)
source venv/bin/activate.fish

# Single optimization
python scripts/optimize_runner.py --config configs/optimizations/my_strategy.yaml

# Estimate fees before running (dry run)
python scripts/optimize_runner.py --config configs/optimizations/my_strategy.yaml --estimate

# Skip results import (useful for testing)
python scripts/optimize_runner.py --config configs/optimizations/my_strategy.yaml --no-import
```

**Note**: The script automatically detects Docker environment. If run on host machine, it delegates to `lean-optimizer` Docker container if available. Batch mode is not yet implemented.

### 5. View Results

```sql
-- Top performers
SELECT * FROM strategy_leaderboard LIMIT 10;

-- Daily summary
SELECT * FROM daily_summary;

-- Parameter analysis
SELECT * FROM parameter_performance
WHERE strategy_name = 'RSI_MeanReversion_ETF'
ORDER BY avg_sharpe DESC;
```

---

## Framework Components

### 1. Database Schema (`scripts/db_schema.sql`)

**Tables**:
- `strategies` - Master list of all strategies
- `optimization_runs` - Each optimization execution
- `backtest_results` - Individual backtest results (one per parameter combination)

**Views**:
- `strategy_leaderboard` - Top performers ranked by Sharpe
- `parameter_performance` - Parameter sensitivity analysis
- `fee_analysis` - Fee impact by strategy
- `daily_summary` - Daily backtesting activity

### 2. LEAN Developer Guide (`docs/LEAN_DEVELOPER_GUIDE.md`)

**Comprehensive reference**:
- ✅ 100+ indicator API signatures
- ✅ Data access patterns
- ✅ Common errors & solutions
- ✅ Position sizing formulas
- ✅ Resolution selection guide

### 3. Config System (`configs/`)

**Structure**:
```
configs/
├── optimizations/
│   ├── template.yaml          # Copy this to create new configs
│   ├── rsi_etf_example.yaml   # Grid Search example
│   └── bollinger_etf_example.yaml  # Euler Search example
└── batches/
    └── mean_reversion_batch.yaml  # Batch run example
```

### 4. Optimization Runner (`scripts/optimize_runner.py`)

**Features**:
- Reads YAML configs
- Generates `lean optimize` commands
- Executes optimizations
- Parses results → PostgreSQL
- Prints short summaries

### 5. Results Importer (`scripts/results_importer.py`)

Parses LEAN optimization JSON output and stores in PostgreSQL.

---

## Workflow Example

### Week 1: Test 72 RSI Variations

**Monday (5 minutes)**:
1. Create config: `configs/optimizations/rsi_etf_week1.yaml`
2. Define parameters:
   - `rsi_period`: 10-20, step 2 (6 values)
   - `entry_threshold`: 25-40, step 5 (4 values)
   - `exit_threshold`: 50-70, step 10 (3 values)
   - **Total**: 6×4×3 = 72 combinations

**Monday Evening**:
```bash
# Estimate fees (prevents surprises)
python scripts/optimize_runner.py --config configs/optimizations/rsi_etf_week1.yaml --estimate

# Run optimization (2-3 hours)
python scripts/optimize_runner.py --config configs/optimizations/rsi_etf_week1.yaml
```

**Tuesday (5 minutes - Director analysis)**:
```sql
-- Short summary
SELECT
    COUNT(*) as total_runs,
    SUM(CASE WHEN meets_criteria THEN 1 ELSE 0 END) as passed,
    MAX(sharpe_ratio) as best_sharpe,
    AVG(total_fees) as avg_fees
FROM backtest_results
WHERE strategy_id = (SELECT id FROM strategies WHERE name = 'RSI_MeanReversion_ETF');

-- Output: "72 runs complete, 3 passed, best Sharpe: 1.8"
```

**Result**: 72 variations tested, minimal developer time, all results stored for analysis.

---

## Config File Format

```yaml
strategy:
  name: "STRATEGY_NAME"
  lean_project_path: "PROJECT_FOLDER"
  category: "mean_reversion"
  asset_class: "etf"

optimization:
  type: "Euler Search"  # Grid Search or Euler Search
  target_metric: "Sharpe Ratio"
  target_direction: "max"

  constraints:
    - "Drawdown < 0.15"
    - "Total Trades > 100"

  parameters:
    parameter_1:
      start: 10
      end: 20
      step: 2  # Generates: 10, 12, 14, 16, 18, 20

    parameter_2:
      start: 0.01
      end: 0.05
      step: 0.01

success_criteria:
  min_trades: 100
  min_sharpe: 1.0
  max_drawdown: 0.15
  max_fee_pct: 0.30
```

---

## Optimization Types

### Grid Search (Exhaustive)

**Pros**:
- Tests all combinations
- Guaranteed to find global optimum
- Best for few parameters (2-4)

**Cons**:
- Slow for many parameters
- 10 parameters × 5 values each = 9.7M combinations

**Use When**: <50 total combinations

### Euler Search (Faster)

**Pros**:
- Converges to optimum faster
- Good for many parameters
- Smart search algorithm

**Cons**:
- May miss global optimum
- Finds local maxima

**Use When**: >50 total combinations

---

## Success Criteria

Framework auto-evaluates each backtest:

```python
# Automatic PASS/FAIL evaluation
def evaluate_backtest(result, criteria):
    if result['total_trades'] < criteria['min_trades']:
        return FAIL, "Insufficient trades"

    if result['total_fees'] / 1000 > criteria['max_fee_pct']:
        return FAIL, "Fees too high"

    if result['sharpe_ratio'] < criteria['min_sharpe']:
        return FAIL, "Sharpe too low"

    # ... other checks

    return PASS
```

**Typical Criteria**:
- Total Trades: ≥100
- Win Rate: ≥50%
- Sharpe Ratio: ≥1.0
- Max Drawdown: ≤15%
- Avg Win: ≥1%
- Fee Impact: ≤30% of capital

---

## Daily Summary Format

**Short format** (as requested):
```
72 runs complete, 3 passed, best Sharpe: 1.8
```

**Query**:
```sql
SELECT * FROM daily_summary WHERE date = CURRENT_DATE;
```

---

## PostgreSQL Queries

### Top 10 Strategies

```sql
SELECT * FROM strategy_leaderboard LIMIT 10;
```

### Parameter Sensitivity

```sql
-- Which RSI period performs best?
SELECT
    parameters->>'rsi_period' as rsi_period,
    AVG(sharpe_ratio) as avg_sharpe,
    COUNT(*) as tests
FROM backtest_results
WHERE strategy_id = (SELECT id FROM strategies WHERE name = 'RSI_MeanReversion_ETF')
GROUP BY parameters->>'rsi_period'
ORDER BY avg_sharpe DESC;
```

### Fee Analysis

```sql
SELECT * FROM fee_analysis
WHERE avg_fee_pct_of_capital > 30  -- Strategies killed by fees
ORDER BY avg_fee_pct_of_capital DESC;
```

### Best Parameter Combination

```sql
SELECT
    parameters,
    sharpe_ratio,
    total_return,
    max_drawdown,
    total_trades,
    win_rate,
    qc_backtest_url
FROM backtest_results
WHERE strategy_id = (SELECT id FROM strategies WHERE name = 'RSI_MeanReversion_ETF')
  AND meets_criteria = true
ORDER BY sharpe_ratio DESC
LIMIT 1;
```

---

## File Structure

```
ai_trading_backtesting/
├── configs/
│   ├── optimizations/
│   │   ├── template.yaml
│   │   ├── rsi_etf_example.yaml
│   │   └── bollinger_etf_example.yaml
│   └── batches/
│       └── mean_reversion_batch.yaml
│
├── docs/
│   ├── LEAN_DEVELOPER_GUIDE.md   # Comprehensive API reference
│   └── FRAMEWORK_README.md       # This file
│
├── scripts/
│   ├── db_schema.sql             # PostgreSQL schema
│   ├── optimize_runner.py        # Main automation script
│   └── results_importer.py       # Parse results → DB
│
├── lean_projects/
│   ├── RSI_MeanReversion_ETF/
│   └── BollingerBand_MeanReversion_ETFs/
│
└── data/
    └── strategy_backlog.yaml     # Director's planning document
```

---

## Best Practices

### 1. Always Use GetParameter()

```python
# ✅ CORRECT - Optimizable
rsi_period = int(self.get_parameter("rsi_period", "14"))

# ❌ WRONG - NOT optimizable
rsi_period = 14
```

### 2. Estimate Fees First

```bash
# ALWAYS run estimate before optimization
python scripts/optimize_runner.py --config my_config.yaml --estimate
```

**Fee Warning**: If estimated fees >30% of capital, adjust:
- Reduce trade frequency (higher RSI thresholds)
- Increase capital
- Longer holding periods

### 3. Start Small

First optimization:
- 2-3 parameters
- 10-20 total combinations
- Verify framework works

Then scale to 100+ variations.

### 4. Use Euler Search for >50 Combinations

- Grid Search: 2-4 parameters, <50 combinations
- Euler Search: 5+ parameters, >50 combinations

### 5. Check LEAN Guide for Syntax

**Before writing code**, check `docs/LEAN_DEVELOPER_GUIDE.md` for:
- Exact indicator signatures
- Data access patterns
- Common errors

**Prevents**: Hours of debugging API errors.

---

## Next Steps

**Immediate (Setup)**:
1. Create database: `createdb trading`
2. Run schema: `psql -d trading -f scripts/db_schema.sql`
3. Read LEAN guide: `docs/LEAN_DEVELOPER_GUIDE.md`

**First Strategy**:
1. Copy template: `cp configs/optimizations/template.yaml configs/optimizations/my_first.yaml`
2. Edit config (5 minutes)
3. Run: `python scripts/optimize_runner.py --config configs/optimizations/my_first.yaml`
4. Query results: `SELECT * FROM strategy_leaderboard;`

**Scale to 100+/week**:
1. Create batch configs
2. Run overnight
3. Analyze results in morning (5 minutes)
4. Iterate

---

## Troubleshooting

### "No module named 'yaml'"
```bash
pip install pyyaml psycopg2-binary
```

### "Database connection failed"
```bash
# Verify PostgreSQL running
pg_isready

# Check database exists
psql -l | grep trading
```

### "lean optimize command not found"
```bash
# Activate venv
source venv/bin/activate.fish

# Verify lean installed
lean --version
```

### "Strategy not found in database"
```sql
-- Add strategy manually
INSERT INTO strategies (name, category, asset_class, lean_project_path)
VALUES ('MyStrategy', 'mean_reversion', 'etf', 'MyStrategy');
```

---

## Support

**Documentation**:
- LEAN Developer Guide: `docs/LEAN_DEVELOPER_GUIDE.md`
- Official LEAN Docs: https://www.quantconnect.com/docs/v2/writing-algorithms/indicators/supported-indicators
- Optimization Docs: https://www.quantconnect.com/docs/v2/lean-cli/optimization/deployment

**Framework Components**:
- Database Schema: `scripts/db_schema.sql`
- Config Templates: `configs/optimizations/template.yaml`
- Example Configs: `configs/optimizations/*_example.yaml`

---

**Built for**: 100+ strategy variations per week
**Optimized for**: Minimal developer time, maximum iteration speed
**Powered by**: QuantConnect LEAN + PostgreSQL + Python automation
