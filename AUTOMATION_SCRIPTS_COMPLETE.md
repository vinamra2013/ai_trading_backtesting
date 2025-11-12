# Automation Scripts Implementation - Complete ✅

**Date**: 2025-01-10
**Status**: Framework automation complete, ready for testing
**Session**: Continuation from NEXT_SESSION_HANDOFF.md

---

## ✅ Completed Work

### 1. `scripts/optimize_runner.py` (325 lines)

**Purpose**: Main automation orchestrator - reads config, runs LEAN optimization, stores results

**Features Implemented**:
- ✅ YAML config parsing with validation
- ✅ `lean optimize` command generation from config
- ✅ Subprocess execution with error handling
- ✅ PostgreSQL integration (strategy and optimization_run record creation)
- ✅ Automatic results import after optimization completes
- ✅ Short summary output: "72 runs complete, 3 passed, best Sharpe: 1.8"
- ✅ Fee estimation mode (`--estimate` flag)
- ✅ Dry run support (`--no-import` flag)
- ✅ Combination calculation for progress tracking

**CLI Interface**:
```bash
# Single optimization
python scripts/optimize_runner.py --config configs/optimizations/rsi_etf.yaml

# Fee estimation (dry run)
python scripts/optimize_runner.py --config configs/optimizations/rsi_etf.yaml --estimate

# Without database import
python scripts/optimize_runner.py --config configs/optimizations/rsi_etf.yaml --no-import
```

**Dependencies**: `yaml`, `subprocess`, `psycopg2`, `argparse`, `dotenv`

---

### 2. `scripts/results_importer.py` (417 lines)

**Purpose**: Parse LEAN optimization JSON output and import to PostgreSQL

**Features Implemented**:
- ✅ Automatic JSON file discovery in `.optimization/` directory
- ✅ Flexible JSON parsing (handles multiple LEAN output formats)
- ✅ Complete metrics extraction:
  - Performance: Sharpe, Sortino, Calmar, returns
  - Risk: Drawdown, volatility, variance
  - Trading: Total trades, win rate, avg win/loss, profit-loss ratio
  - Portfolio: Fees, profit, turnover, capacity
  - Greeks: Alpha, Beta
- ✅ Success criteria evaluation (automatic PASS/FAIL)
- ✅ Rejection reason generation for failed results
- ✅ PostgreSQL insertion (backtest_results table)
- ✅ Optimization run status updates
- ✅ Dry run mode for testing

**CLI Interface**:
```bash
# Standalone usage
python scripts/results_importer.py --optimization-dir lean_projects/.optimization/RSI_MeanReversion_ETF/

# With config for success criteria
python scripts/results_importer.py --optimization-dir lean_projects/.optimization/RSI_MeanReversion_ETF/ --config configs/optimizations/rsi_etf.yaml

# Dry run (parse only, no database insert)
python scripts/results_importer.py --optimization-dir lean_projects/.optimization/RSI_MeanReversion_ETF/ --dry-run
```

**Dependencies**: `json`, `psycopg2`, `pathlib`, `dotenv`, `yaml`

---

### 3. Environment Configuration

**Updated `.env` file**:
```bash
# PostgreSQL Configuration (for Trading Framework)
POSTGRES_DB=trading
POSTGRES_USER=postgres
POSTGRES_PASSWORD=
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

**Note**: User needs to set `POSTGRES_PASSWORD` if PostgreSQL requires authentication.

---

### 4. Script Permissions

Both scripts are executable:
```bash
-rwxrwxr-x optimize_runner.py
-rwxrwxr-x results_importer.py
```

---

## 📋 Dependencies Status

All required Python packages are installed in venv:
- ✅ `PyYAML 6.0.3` - YAML parsing
- ✅ `psycopg2-binary 2.9.11` - PostgreSQL connector
- ✅ `python-dotenv 1.2.1` - Environment variable loading

---

## ⏳ Next Steps (Priority Order)

### Step 1: PostgreSQL Setup (REQUIRED)

**If PostgreSQL not installed**:
```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**Create trading database**:
```bash
# Create database
sudo -u postgres createdb trading

# Run schema (from project root)
sudo -u postgres psql -d trading -f scripts/db_schema.sql

# Verify tables created
sudo -u postgres psql -d trading -c "\dt"
```

**Expected output**:
```
                List of relations
 Schema |        Name         | Type  |  Owner
--------+---------------------+-------+----------
 public | backtest_results    | table | postgres
 public | optimization_runs   | table | postgres
 public | strategies          | table | postgres
```

**Set PostgreSQL password** (if needed):
```bash
# Set password for postgres user
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'your_password';"

# Update .env file
# POSTGRES_PASSWORD=your_password
```

---

### Step 2: Verify Framework Integration (5 minutes)

Test the scripts work together:

```bash
# 1. Verify config exists
ls configs/optimizations/rsi_etf_example.yaml

# 2. Run fee estimation (dry run)
venv/bin/python scripts/optimize_runner.py \
  --config configs/optimizations/rsi_etf_example.yaml \
  --estimate

# Expected output:
# ============================================================
# FEE ESTIMATION (Dry Run)
# ============================================================
# Strategy: RSI_MeanReversion_ETF
# Total Parameter Combinations: 54
# Expected combinations to test: 54
# Estimated time (@ 30 sec/backtest): 27.0 minutes
```

---

### Step 3: Create First Optimizable Strategy (30-60 minutes)

**CRITICAL**: The existing strategies (RSIMeanReversion, BollingerBand_MeanReversion_ETFs) do NOT use `get_parameter()` and cannot be optimized.

**You must create a NEW strategy** following the backlog:

```bash
# Create new LEAN project
cd lean_projects
lean project-create "RSI_MeanReversion_ETF" --language python
```

**Template for optimizable strategy** (from LEAN_DEVELOPER_GUIDE.md):

```python
from AlgorithmImports import *

class RSIMeanReversionETF(QCAlgorithm):
    def initialize(self):
        # CRITICAL: Use get_parameter() for ALL optimizable values
        rsi_period = int(self.get_parameter("rsi_period", "14"))
        entry_threshold = int(self.get_parameter("entry_threshold", "30"))
        exit_threshold = int(self.get_parameter("exit_threshold", "60"))
        stop_loss_pct = float(self.get_parameter("stop_loss_pct", "0.01"))
        profit_target_pct = float(self.get_parameter("profit_target_pct", "0.02"))

        self.set_start_date(2020, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(1000)

        # ETF universe
        etf_tickers = ["SPY", "QQQ", "IWM", "XLF", "XLE", "XLK", "XLV", "XLI"]
        self.symbols = [self.add_equity(ticker, Resolution.DAILY).symbol for ticker in etf_tickers]

        # RSI indicators
        self.rsi_indicators = {}
        for symbol in self.symbols:
            self.rsi_indicators[symbol] = self.rsi(symbol, rsi_period, MovingAverageType.WILDERS, Resolution.DAILY)

        # Store parameters for use in on_data
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
        self.stop_loss_pct = stop_loss_pct
        self.profit_target_pct = profit_target_pct

    def on_data(self, data: Slice):
        # Trading logic implementation
        for symbol in self.symbols:
            if not data.bars.contains_key(symbol):
                continue

            if not self.rsi_indicators[symbol].is_ready:
                continue

            rsi = self.rsi_indicators[symbol].current.value
            price = data.bars[symbol].close

            # Entry logic: RSI oversold
            if not self.portfolio[symbol].invested:
                if rsi < self.entry_threshold:
                    # Risk-based position sizing
                    max_risk = self.portfolio.total_portfolio_value * 0.01
                    stop_price = price * (1 - self.stop_loss_pct)
                    risk_per_share = price - stop_price
                    shares = int(max_risk / risk_per_share)
                    max_shares_by_cash = int(self.portfolio.cash / price)
                    shares = min(shares, max_shares_by_cash)

                    if shares > 0:
                        self.market_order(symbol, shares)

            # Exit logic: RSI overbought or profit target/stop loss hit
            elif self.portfolio[symbol].invested:
                position = self.portfolio[symbol]
                entry_price = position.average_price
                current_return = (price - entry_price) / entry_price

                # Exit conditions
                should_exit = False

                if rsi > self.exit_threshold:
                    should_exit = True  # RSI overbought

                if current_return >= self.profit_target_pct:
                    should_exit = True  # Profit target hit

                if current_return <= -self.stop_loss_pct:
                    should_exit = True  # Stop loss hit

                if should_exit:
                    self.liquidate(symbol)
```

**Save to**: `lean_projects/RSI_MeanReversion_ETF/main.py`

---

### Step 4: Run First Small Test (10 combinations, ~5 minutes)

**Create test config** (small parameter ranges for quick test):

```yaml
# configs/optimizations/rsi_etf_test.yaml
strategy:
  name: "RSI_MeanReversion_ETF"
  lean_project_path: "RSI_MeanReversion_ETF"
  description: "Test optimization with small parameter ranges"
  category: "mean_reversion"
  asset_class: "etf"

optimization:
  type: "Grid Search"
  target_metric: "Sharpe Ratio"
  target_direction: "max"

  constraints:
    - "Drawdown < 0.20"

  parameters:
    rsi_period:
      start: 12
      end: 16
      step: 2  # Values: 12, 14, 16 (3 values)

    entry_threshold:
      start: 25
      end: 35
      step: 5  # Values: 25, 30, 35 (3 values)

# Total combinations: 3 × 3 = 9 backtests

success_criteria:
  min_trades: 50
  min_win_rate: 0.45
  min_sharpe: 0.8
  max_drawdown: 0.20
  min_avg_win: 0.01
  max_fee_pct: 0.35
```

**Run test**:
```bash
venv/bin/python scripts/optimize_runner.py --config configs/optimizations/rsi_etf_test.yaml
```

**Expected workflow**:
1. Validates config ✅
2. Ensures strategy in database ✅
3. Creates optimization_run record ✅
4. Generates `lean optimize` command ✅
5. Executes optimization (9 backtests) ⏳ (~4-5 minutes)
6. Calls results_importer.py ✅
7. Imports results to PostgreSQL ✅
8. Prints summary ✅

**Expected summary**:
```
============================================================
SUMMARY
============================================================
9 runs complete, 2 passed, best Sharpe: 1.23
============================================================
```

---

### Step 5: Verify Database Results (2 minutes)

```bash
# Connect to PostgreSQL
sudo -u postgres psql -d trading

# View leaderboard
SELECT * FROM strategy_leaderboard LIMIT 5;

# View all results
SELECT
    parameters->>'rsi_period' as rsi,
    parameters->>'entry_threshold' as entry,
    sharpe_ratio,
    total_trades,
    win_rate,
    meets_criteria
FROM backtest_results
ORDER BY sharpe_ratio DESC;

# Daily summary
SELECT * FROM daily_summary;
```

---

### Step 6: Run Full Optimization (54 combinations, ~30 minutes)

Once small test succeeds, run full optimization:

```bash
venv/bin/python scripts/optimize_runner.py --config configs/optimizations/rsi_etf_example.yaml
```

**Expected**: 54 backtests, ~27-30 minutes runtime

---

## 🔧 Troubleshooting

### Issue: "No module named 'yaml'"
**Fix**:
```bash
venv/bin/pip install pyyaml psycopg2-binary python-dotenv
```

### Issue: "Database connection failed"
**Check**:
```bash
# Verify PostgreSQL running
sudo systemctl status postgresql

# Test connection
sudo -u postgres psql -d trading -c "SELECT 1;"

# Check credentials in .env
cat .env | grep POSTGRES
```

### Issue: "Strategy not found in database"
**Fix**:
```bash
# Manually insert strategy
sudo -u postgres psql -d trading -c "
INSERT INTO strategies (name, category, asset_class, lean_project_path)
VALUES ('RSI_MeanReversion_ETF', 'mean_reversion', 'etf', 'RSI_MeanReversion_ETF')
ON CONFLICT (name) DO NOTHING;
"
```

### Issue: "Optimization directory not found"
**Cause**: LEAN optimize command failed or didn't create output
**Debug**:
```bash
# Check if .optimization folder exists
ls -la lean_projects/.optimization/

# Run lean optimize manually to see errors
cd lean_projects
lean optimize "RSI_MeanReversion_ETF" --strategy "Grid Search" --target "Sharpe Ratio" --target-direction "max" --parameter rsi_period 12 16 2 --parameter entry_threshold 25 35 5
```

### Issue: "JSON parsing errors"
**Cause**: LEAN JSON format differs from expected
**Debug**:
```bash
# Inspect actual JSON structure
cat lean_projects/.optimization/RSI_MeanReversion_ETF/*.json | head -50

# Run results_importer in dry-run mode
venv/bin/python scripts/results_importer.py \
  --optimization-dir lean_projects/.optimization/RSI_MeanReversion_ETF/ \
  --dry-run
```

---

## 📊 Framework Capabilities

### What's Now Possible

**Before** (manual testing):
- 1 strategy variation per 5-10 minutes
- Manual tracking in markdown files
- No systematic parameter exploration
- High token usage from Claude interaction

**After** (automation framework):
- 100+ variations per week
- Automatic PostgreSQL storage
- Systematic optimization (Grid Search, Euler Search)
- Short summaries: "72 runs complete, 3 passed, best Sharpe: 1.8"
- 90%+ token savings (no Claude interaction during optimization)
- Director analysis via SQL queries

### Workflow Efficiency

**Developer** (5 minutes/week):
1. Copy strategy backlog → Create LEAN project
2. Copy template.yaml → Edit parameters
3. Run: `python scripts/optimize_runner.py --config my_config.yaml`

**Director** (5 minutes/week):
1. Query PostgreSQL for results
2. Analyze parameter performance
3. Update strategy priorities
4. Request next strategy variations

**Total time**: 10 minutes/week for 100+ variations

---

## 🎯 Success Metrics

Framework is ready for production when:
- ✅ PostgreSQL database created with schema
- ✅ First optimizable strategy created
- ✅ Small test (9-10 combinations) completes successfully
- ✅ Results appear in database
- ✅ Summary prints correctly
- ✅ Full optimization (50+ combinations) completes

---

## 📝 Key Learnings from Previous Session

**Critical patterns validated**:
1. **Fees kill small accounts**: 822 trades on $1K = $674 fees (67% of capital!)
2. **Daily resolution best** for $1K capital
3. **RSI < 25 too restrictive**: Generated only 8 trades in 5 years
4. **Need 100-200 trades** for statistical significance, not 10 or 1000
5. **ETFs work well** for mean reversion (reliable liquidity)

**LEAN API conventions** (see LEAN_DEVELOPER_GUIDE.md):
- Lowercase methods: `self.rsi()`, `self.bb()`
- Uppercase enums: `Resolution.DAILY`, `MovingAverageType.WILDERS`
- Always check data: `if data.bars.contains_key(symbol):`
- Avoid naming conflicts: `self.rsi_indicator` not `self.rsi`

---

## 📚 Documentation References

- **Framework overview**: `FRAMEWORK_README.md`
- **API patterns**: `docs/LEAN_DEVELOPER_GUIDE.md`
- **Strategy list**: `data/strategy_backlog.yaml`
- **Database schema**: `scripts/db_schema.sql`
- **Config examples**: `configs/optimizations/*.yaml`
- **Session notes**: `data/notes/session_20250110.md`

---

## ✅ Completion Checklist

- [x] `scripts/optimize_runner.py` created (325 lines)
- [x] `scripts/results_importer.py` created (417 lines)
- [x] PostgreSQL config added to `.env`
- [x] Scripts made executable
- [x] All Python dependencies installed
- [ ] **PostgreSQL database created** ← USER ACTION REQUIRED
- [ ] **First optimizable strategy created** ← USER ACTION REQUIRED
- [ ] **Small test run (9 combinations)** ← NEXT STEP
- [ ] **Full optimization run (54 combinations)** ← NEXT STEP

---

**Framework Status**: 🟢 **READY FOR TESTING**

**Next Session Priority**: Complete checklist items above (Steps 1-6)

**Estimated Time to First Results**: 1-2 hours (if PostgreSQL already running, 30 minutes)
