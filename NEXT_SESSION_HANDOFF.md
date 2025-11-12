# Next Session Handoff - Framework Completion

**Context**: Session 2025-01-10 ran out of context at 75% (150k/200k tokens)
**Status**: Framework foundation complete, automation scripts pending

---

## What Was Completed This Session

### ✅ 1. Backtesting Results
- **Strategy #1** (RSI Equities): REJECTED - 8 trades, Sharpe -1.042, too restrictive
- **Strategy #2** (Bollinger ETFs): REJECTED - 822 trades, -$142 loss, fees ($674) destroyed profitability

### ✅ 2. Framework Built
- **Database**: `scripts/db_schema.sql` - Complete PostgreSQL schema with tables, views, triggers
- **Developer Guide**: `docs/LEAN_DEVELOPER_GUIDE.md` - 400+ lines, all indicators, exact API signatures
- **Configs**: `configs/optimizations/*.yaml` - Templates and examples
- **Documentation**: `FRAMEWORK_README.md` - Complete usage guide
- **Strategy Backlog**: `data/strategy_backlog.yaml` - 15 strategies with parameters and priorities

### ⏳ 3. Pending Work (Next Session)

**TWO automation scripts needed**:

#### A. `scripts/optimize_runner.py`
**Purpose**: Main automation - reads config, runs optimization, stores results

**Required functionality**:
```python
# Usage
python scripts/optimize_runner.py --config configs/optimizations/rsi_etf.yaml
python scripts/optimize_runner.py --batch configs/batches/mean_reversion_batch.yaml
python scripts/optimize_runner.py --config my_config.yaml --estimate  # Fee estimation
```

**Must do**:
1. Parse YAML config file
2. Validate parameters and constraints
3. Generate `lean optimize` command from config
4. Execute command via subprocess
5. Monitor progress (optional)
6. Call results_importer.py when complete
7. Print short summary: "72 runs complete, 3 passed, best Sharpe: 1.8"

**Key modules needed**:
- `yaml` - Parse configs
- `subprocess` - Run lean optimize
- `psycopg2` - PostgreSQL connection
- `argparse` - CLI arguments

**Complexity**: ~250 lines

---

#### B. `scripts/results_importer.py`
**Purpose**: Parse LEAN optimization JSON → PostgreSQL

**Required functionality**:
```python
# Usage (called by optimize_runner.py or standalone)
python scripts/results_importer.py --optimization-dir .optimization/MyStrategy/
```

**Must do**:
1. Find LEAN optimization results (JSON files in `.optimization/` folder)
2. Parse optimization metadata (strategy name, parameters tested, etc.)
3. Extract all backtest metrics:
   - Sharpe ratio, returns, drawdown
   - Total trades, win rate, avg win/loss
   - Fees, turnover, capacity
4. Evaluate vs success criteria from config
5. Generate rejection reasons if failed
6. Insert into PostgreSQL:
   - `optimization_runs` table (one row)
   - `backtest_results` table (one row per parameter combination)
7. Update strategy status via trigger

**Key modules needed**:
- `json` - Parse LEAN results
- `psycopg2` - PostgreSQL insert
- `pathlib` - File system navigation

**Complexity**: ~200 lines

---

## Next Session TODO List

### Priority 1: Build Automation Scripts

1. **Read this handoff** to understand context
2. **Read** `FRAMEWORK_README.md` for framework overview
3. **Create** `scripts/optimize_runner.py`:
   - Start with basic version (parse config → run lean optimize)
   - Add fee estimation logic
   - Add batch support
4. **Create** `scripts/results_importer.py`:
   - Parse LEAN JSON (find format first)
   - Map metrics to database schema
   - Evaluate success criteria
5. **Test** end-to-end:
   - Use existing `configs/optimizations/rsi_etf_example.yaml`
   - Run small test (3-5 combinations)
   - Verify database populated correctly
6. **Document** in README if needed

### Priority 2: First Real Optimization Run

1. **Create revised strategy** (STR-001 from backlog):
   - Copy RSIMeanReversion → RSI_MeanReversion_ETF
   - Update to use `get_parameter()` for all values
   - Relaxed thresholds (25→30-35)
2. **Create config** with parameter ranges
3. **Run optimization** (50-100 combinations)
4. **Analyze results** via PostgreSQL queries
5. **Update strategy backlog** with findings

---

## Key Files for Next Session

### Must Read:
- `FRAMEWORK_README.md` - Framework overview
- `data/strategy_backlog.yaml` - Strategies to build
- `docs/LEAN_DEVELOPER_GUIDE.md` - API reference

### Must Create:
- `scripts/optimize_runner.py` - Main automation
- `scripts/results_importer.py` - Results parser

### Already Done (Reference):
- `scripts/db_schema.sql` - Database schema
- `configs/optimizations/template.yaml` - Config template
- `configs/optimizations/rsi_etf_example.yaml` - Example config

---

## Important Context from This Session

### Key Learnings:
1. **Fees kill small accounts**: 822 trades on $1K = $674 fees (67% of capital!)
2. **Daily resolution best** for $1K capital
3. **RSI < 25 too restrictive**: Generated only 8 trades in 5 years
4. **Need 100-200 trades** for statistical significance, not 10 or 1000
5. **ETFs work well** for mean reversion (reliable liquidity)

### LEAN API Patterns (Validated):
```python
# ✅ CORRECT patterns
rsi_indicator = self.rsi(symbol, period, MovingAverageType.WILDERS, Resolution.DAILY)
bb = self.bb(symbol, period, std_dev, MovingAverageType.SIMPLE, Resolution.DAILY)
if data.bars.contains_key(symbol):
    price = data.bars[symbol].close
```

### Fee Warning:
- If optimization estimates >30% fees, **stop and revise**
- Reduce trade frequency OR increase capital
- Small accounts need lower frequency strategies

---

## Database Quick Reference

### Connect:
```python
import psycopg2
conn = psycopg2.connect(dbname="trading", user="postgres")
```

### Insert Optimization Run:
```sql
INSERT INTO optimization_runs (strategy_id, config_file, optimization_type, target_metric, total_combinations, status)
VALUES (1, 'rsi_etf_example.yaml', 'Grid Search', 'Sharpe Ratio', 72, 'running')
RETURNING id;
```

### Insert Backtest Result:
```sql
INSERT INTO backtest_results (optimization_run_id, strategy_id, parameters, sharpe_ratio, total_return, ...)
VALUES (1, 1, '{"rsi_period": "14", "entry_threshold": "30"}', 1.42, 0.15, ...)
```

### Query Results:
```sql
SELECT * FROM strategy_leaderboard LIMIT 10;
SELECT * FROM daily_summary;
```

---

## LEAN Optimize Command Format

**What framework must generate**:
```bash
lean optimize "ProjectName" \
  --strategy "Grid Search" \
  --target "Sharpe Ratio" \
  --target-direction "max" \
  --parameter param1 start end step \
  --parameter param2 start end step \
  --constraint "Drawdown < 0.15"
```

**Example from config**:
```yaml
optimization:
  type: "Grid Search"
  target_metric: "Sharpe Ratio"
  target_direction: "max"
  constraints:
    - "Drawdown < 0.15"
  parameters:
    rsi_period: {start: 10, end: 20, step: 2}
    entry_threshold: {start: 25, end: 35, step: 5}
```

**Becomes**:
```bash
lean optimize "RSI_MeanReversion_ETF" \
  --strategy "Grid Search" \
  --target "Sharpe Ratio" \
  --target-direction "max" \
  --parameter rsi_period 10 20 2 \
  --parameter entry_threshold 25 35 5 \
  --constraint "Drawdown < 0.15"
```

---

## Expected LEAN Output Location

**After running `lean optimize`**:
- Results saved to: `lean_projects/.optimization/ProjectName/`
- JSON files with all backtest metrics
- Need to parse these files → PostgreSQL

**TODO for next session**: Find exact JSON format by running small test

---

## Success Criteria (From Config)

Framework must auto-evaluate each backtest:

```python
def evaluate(result, criteria):
    reasons = []

    if result['total_trades'] < criteria['min_trades']:
        reasons.append(f"Insufficient trades: {result['total_trades']} < {criteria['min_trades']}")

    if result['total_fees'] / 1000 > criteria['max_fee_pct']:
        reasons.append(f"Fees too high: {result['total_fees']/1000:.1%} > {criteria['max_fee_pct']:.1%}")

    # ... other checks

    return len(reasons) == 0, reasons
```

---

## Questions to Resolve Next Session

1. **Exact LEAN JSON format**: Run small optimization, inspect output
2. **PostgreSQL connection details**: What credentials to use?
3. **Error handling**: What if lean optimize fails?
4. **Progress monitoring**: Poll for completion or blocking wait?

---

## User Preferences (From This Session)

- **Daily summary format**: "72 runs complete, 3 passed, best Sharpe: 1.8" (short!)
- **Optimization type**: Euler Search + Walk-Forward Analysis preferred
- **Analysis**: Director (me) does analysis via PostgreSQL queries, not scripts
- **Database**: PostgreSQL (already setup ready)
- **Target**: 100+ strategy variations per week
- **Developer skill**: Expert level Python

---

## Files Created This Session

```
scripts/
└── db_schema.sql                    # PostgreSQL schema

docs/
├── LEAN_DEVELOPER_GUIDE.md          # API reference
└── FRAMEWORK_README.md              # This was created (but might be NEXT_SESSION_HANDOFF.md)

configs/
├── optimizations/
│   ├── template.yaml
│   ├── rsi_etf_example.yaml
│   └── bollinger_etf_example.yaml
└── batches/
    └── mean_reversion_batch.yaml

data/
└── strategy_backlog.yaml            # 15 strategies with parameters

FRAMEWORK_README.md                  # Usage guide
NEXT_SESSION_HANDOFF.md             # This file
```

---

## Immediate Next Steps

1. **Read** this handoff completely
2. **Review** FRAMEWORK_README.md
3. **Build** optimize_runner.py (~1 hour)
4. **Build** results_importer.py (~1 hour)
5. **Test** with small optimization (10 combinations)
6. **Run** first real optimization (50-100 combinations)
7. **Query** results via PostgreSQL
8. **Iterate** on strategies based on results

**Estimated time**: 2-3 hours to complete framework + run first optimization

---

## Contact Points

- **Framework docs**: `FRAMEWORK_README.md`
- **Strategy list**: `data/strategy_backlog.yaml`
- **API reference**: `docs/LEAN_DEVELOPER_GUIDE.md`
- **Session notes**: `data/notes/session_20250110.md`
- **Leaderboard**: `lean_projects/results/leaderboard/strategy_leaderboard.md`

**Good luck! The foundation is solid, just need those 2 automation scripts!**
