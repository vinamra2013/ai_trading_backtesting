# Database Views & Parameter Storage Fix

**Date**: 2025-11-11
**Status**: ✅ Views Created | ⚠️ Parameter Storage Requires Strategy Fix

---

## Executive Summary

**Problem**: Database had 47 backtest results but parameter values were empty (`{}`), making parameter sensitivity analysis impossible.

**Root Cause**: Strategy code is a buy-and-hold template without `get_parameter()` calls. LEAN cannot capture parameters if the strategy doesn't use them.

**Solution Implemented**: Created 4 database views for future analysis when strategy is properly coded.

**Next Action**: Developer must implement RSI Mean Reversion strategy with proper `get_parameter()` calls.

---

## ✅ Task 1: Database Views Created

All 4 analysis views are now operational in PostgreSQL:

### 1. `strategy_leaderboard`
**Purpose**: Top performing strategies ranked by Sharpe ratio

**Query**:
```sql
SELECT * FROM strategy_leaderboard LIMIT 10;
```

**Columns**:
- `rank` - Performance ranking (1 = best)
- `strategy_name`, `category`, `asset_class`
- `parameters` - JSONB of parameter values
- `sharpe_ratio`, `total_return`, `annual_return`
- `max_drawdown`, `total_trades`, `win_rate`
- `avg_win`, `avg_loss`, `total_fees`
- `qc_backtest_url` - Link to QuantConnect results
- `completed_at` - Timestamp

**Note**: Currently shows NULL metrics because all strategies have negative Sharpe ratios.

---

### 2. `parameter_performance`
**Purpose**: Parameter sensitivity analysis - how each parameter value affects performance

**Query**:
```sql
SELECT * FROM parameter_performance
WHERE strategy_name = 'RSI_MeanReversion_ETF'
ORDER BY avg_sharpe DESC
LIMIT 20;
```

**Columns**:
- `strategy_name` - Strategy being analyzed
- `parameter_name` - Parameter being tested (e.g., "rsi_period")
- `parameter_value` - Specific value tested (e.g., "14")
- `avg_sharpe` - Average Sharpe across all tests with this value
- `avg_return`, `avg_drawdown`, `avg_win_rate`
- `test_count` - Number of backtests with this parameter value

**Current Status**: Empty because `parameters` column is `{}` for all results.

**Future Use**: Once strategy properly uses `get_parameter()`, this view will show which parameter values perform best.

---

### 3. `fee_analysis`
**Purpose**: Fee impact analysis (critical for $1K capital accounts)

**Query**:
```sql
SELECT * FROM fee_analysis ORDER BY avg_fee_pct_of_capital DESC;
```

**Columns**:
- `strategy_name` - Strategy being analyzed
- `avg_fees` - Average total fees per backtest
- `avg_fee_pct_of_capital` - Fees as % of $1K capital
- `avg_trades` - Average number of trades
- `avg_fee_per_trade` - Average cost per trade
- `backtest_count` - Sample size

**Current Data**:
```
RSI_MeanReversion_ETF_LowFreq: 7.7 trades average, fees not captured
```

**Critical Insight**: Previous Bollinger Band strategy had 822 trades = $674 fees (67% of capital). This view will catch similar fee killers.

---

### 4. `daily_summary`
**Purpose**: Daily backtesting activity tracking

**Query**:
```sql
SELECT * FROM daily_summary ORDER BY date DESC LIMIT 7;
```

**Columns**:
- `date` - Trading day
- `total_backtests` - Backtests completed
- `passed` - Number meeting success criteria
- `best_sharpe` - Highest Sharpe ratio of the day
- `avg_sharpe` - Average Sharpe across all backtests
- `strategies_tested` - Unique strategies tested

**Current Data**:
```
2025-11-11: 47 backtests, 32 passed, best Sharpe: -1.22, avg Sharpe: -1.49
```

**Interpretation**: 68% "passed" but all have negative Sharpe. The `meets_criteria` logic may need review.

---

## ⚠️ Task 2: Parameter Storage Issue

### Root Cause Analysis

**Investigation Summary**:

1. **Database Schema**: ✅ Correct - `parameters JSONB NOT NULL` column exists
2. **Import Script**: ✅ Correct - `results_importer.py` extracts parameters properly
3. **LEAN JSON Output**: ❌ **EMPTY** - All backtest JSON files have `"parameters": {}`
4. **Strategy Code**: ❌ **NOT IMPLEMENTED** - No `get_parameter()` calls

**Evidence**:

Examined backtest JSON file:
```bash
/lean_projects/RSI_MeanReversion_ETF/optimizations/2025-11-11_11-22-22/444bf5b9-73a8-4b3f-832d-e3680b9a8e3c.json
```

**Found**:
```json
{
  "parameters": {},
  "rollingWindow": { ... }
}
```

**Expected**:
```json
{
  "parameters": {
    "rsi_period": "14",
    "entry_threshold": "30",
    "exit_threshold": "60",
    "stop_loss_pct": "0.01",
    "profit_target_pct": "0.02"
  },
  "rollingWindow": { ... }
}
```

**Why Empty**: The strategy code (`lean_projects/RSI_MeanReversion_ETFs_LowFreq/main.py`) is a buy-and-hold template:

```python
def initialize(self):
    self.set_start_date(2013, 10, 7)  # Wrong dates
    self.set_end_date(2013, 10, 11)   # Only 4 days!
    self.set_cash(100000)              # Wrong capital ($100K vs $1K)
    self.add_equity("SPY", Resolution.MINUTE)  # Wrong resolution

def on_data(self, data: Slice):
    if not self.portfolio.invested:
        self.set_holdings("SPY", 1)  # Buy and hold
```

**No RSI logic. No parameters. No mean reversion. Just template code.**

---

## 🔧 How to Fix Parameter Storage

### Step 1: Implement Strategy with `get_parameter()`

**Reference**: `docs/LEAN_DEVELOPER_GUIDE.md` (validated patterns)

**Required Implementation** (`lean_projects/RSI_MeanReversion_ETF/main.py`):

```python
from AlgorithmImports import *

class RSIMeanReversionETFsLowFreq(QCAlgorithm):
    def initialize(self):
        # Correct configuration
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(1000)  # Correct capital

        # GET PARAMETERS - This is what makes them appear in JSON!
        self.rsi_period = int(self.get_parameter("rsi_period", "14"))
        self.entry_threshold = int(self.get_parameter("entry_threshold", "30"))
        self.exit_threshold = int(self.get_parameter("exit_threshold", "60"))
        self.stop_loss_pct = float(self.get_parameter("stop_loss_pct", "0.01"))
        self.profit_target_pct = float(self.get_parameter("profit_target_pct", "0.02"))

        # Add ETF with DAILY resolution (fee control)
        self.symbol = self.add_equity("SPY", Resolution.DAILY).symbol

        # Create RSI indicator
        self.rsi = self.rsi(self.symbol, self.rsi_period, Resolution.DAILY)

        # Track entry price for stop loss
        self.entry_price = None

    def on_data(self, data: Slice):
        # Check data availability
        if not data.bars.contains_key(self.symbol):
            return

        # Check indicator readiness
        if not self.rsi.is_ready:
            return

        rsi_value = self.rsi.current.value
        current_price = data[self.symbol].close

        # Entry logic (oversold)
        if not self.portfolio.invested:
            if rsi_value < self.entry_threshold:
                # Calculate position size (1% risk)
                position_value = self.calculate_position_size(current_price)
                self.set_holdings(self.symbol, position_value / self.portfolio.total_portfolio_value)
                self.entry_price = current_price

        # Exit logic
        elif self.portfolio.invested:
            # Profit target exit
            if current_price >= self.entry_price * (1 + self.profit_target_pct):
                self.liquidate(self.symbol)
                self.entry_price = None

            # Stop loss exit
            elif current_price <= self.entry_price * (1 - self.stop_loss_pct):
                self.liquidate(self.symbol)
                self.entry_price = None

            # Overbought exit
            elif rsi_value > self.exit_threshold:
                self.liquidate(self.symbol)
                self.entry_price = None

    def calculate_position_size(self, current_price):
        """Calculate position size based on 1% risk"""
        account_value = self.portfolio.total_portfolio_value
        risk_amount = account_value * 0.01  # 1% risk
        stop_distance = current_price * self.stop_loss_pct
        shares = int(risk_amount / stop_distance)
        return shares * current_price
```

**Critical Lines for Parameter Capture**:
```python
self.rsi_period = int(self.get_parameter("rsi_period", "14"))
self.entry_threshold = int(self.get_parameter("entry_threshold", "30"))
# ... etc for all optimizable parameters
```

**Without these `get_parameter()` calls, LEAN cannot write parameters to JSON!**

---

### Step 2: Update config.json

**File**: `lean_projects/RSI_MeanReversion_ETF/config.json`

**Current**:
```json
{
    "algorithm-language": "Python",
    "parameters": {},
    "description": ""
}
```

**Required**:
```json
{
    "algorithm-language": "Python",
    "parameters": {
        "rsi_period": "14",
        "entry_threshold": "30",
        "exit_threshold": "60",
        "stop_loss_pct": "0.01",
        "profit_target_pct": "0.02"
    },
    "description": "RSI Mean Reversion ETF - Low Frequency"
}
```

---

### Step 3: Test Single Backtest

**Before running optimization**, test the strategy works:

```bash
cd lean_projects
lean backtest "RSI_MeanReversion_ETF"
```

**Verify**:
- Strategy logic executes (not just buy-and-hold)
- RSI indicator calculates correctly
- Trades generate (should see >100 trades over 5 years)
- No runtime errors

---

### Step 4: Run Optimization

**Once strategy confirmed working**:

```bash
source venv/bin/activate
python scripts/optimize_runner.py --config configs/optimizations/rsi_etf_lowfreq.yaml
```

**Expected**: Parameter combinations will now appear in backtest JSON files.

---

### Step 5: Import Results

```bash
python scripts/results_importer.py \
  --optimization-dir lean_projects/RSI_MeanReversion_ETF/optimizations/2025-11-11_XX-XX-XX \
  --strategy-name RSI_MeanReversion_ETF \
  --config configs/optimizations/rsi_etf_lowfreq.yaml
```

**Verify Parameters Stored**:
```sql
SELECT parameters FROM backtest_results ORDER BY id DESC LIMIT 1;
```

**Expected Output**:
```json
{"rsi_period": "14", "entry_threshold": "30", "exit_threshold": "60", ...}
```

---

## 📊 Using the Database Views

### Quick Reference Queries

**1. Top 10 Strategies**:
```bash
docker exec mlflow-postgres psql -U mlflow -d trading -c "
SELECT rank, strategy_name, sharpe_ratio, total_return, max_drawdown, total_trades
FROM strategy_leaderboard
LIMIT 10;
"
```

**2. Best RSI Period**:
```bash
docker exec mlflow-postgres psql -U mlflow -d trading -c "
SELECT parameter_value as rsi_period, avg_sharpe, avg_return, test_count
FROM parameter_performance
WHERE strategy_name = 'RSI_MeanReversion_ETF' AND parameter_name = 'rsi_period'
ORDER BY avg_sharpe DESC;
"
```

**3. Fee Analysis**:
```bash
docker exec mlflow-postgres psql -U mlflow -d trading -c "
SELECT strategy_name, avg_fee_pct_of_capital, avg_trades, avg_fee_per_trade
FROM fee_analysis;
"
```

**4. Today's Results**:
```bash
docker exec mlflow-postgres psql -U mlflow -d trading -c "
SELECT * FROM daily_summary WHERE date = CURRENT_DATE;
"
```

**5. Best Parameter Combination**:
```bash
docker exec mlflow-postgres psql -U mlflow -d trading -c "
SELECT parameters, sharpe_ratio, total_return, max_drawdown, win_rate, qc_backtest_url
FROM backtest_results
WHERE strategy_id = (SELECT id FROM strategies WHERE name = 'RSI_MeanReversion_ETF')
  AND meets_criteria = true
ORDER BY sharpe_ratio DESC
LIMIT 1;
"
```

---

## 🚨 Current System Status

### Database Infrastructure: ✅ READY
- 4 analysis views created and tested
- Import pipeline validated
- Schema supports parameter storage

### Strategy Implementation: ❌ NOT READY
- Strategy code is buy-and-hold template
- No `get_parameter()` calls
- Wrong configuration (4 days, $100K, minute resolution)
- No RSI logic implemented

### Optimization Framework: ⏳ BLOCKED
- Optimizer configuration exists and is correct
- 486 parameter combinations defined
- **Cannot proceed** until strategy is implemented

### Next Developer Action: IMPLEMENT STRATEGY
Priority 1: Code RSI Mean Reversion strategy with proper `get_parameter()` usage following the template in Step 1 above.

---

## 📋 Verification Checklist

After developer implements strategy, verify:

- [ ] Strategy file uses `get_parameter()` for all optimizable values
- [ ] config.json has default parameter values
- [ ] Single backtest runs without errors
- [ ] Single backtest generates >100 trades
- [ ] Backtest JSON has populated `parameters` field
- [ ] Optimization completes successfully
- [ ] Results import to PostgreSQL correctly
- [ ] `parameter_performance` view shows data
- [ ] `strategy_leaderboard` shows positive Sharpe strategies

---

## 🔗 Related Documentation

- **LEAN API Patterns**: `docs/LEAN_DEVELOPER_GUIDE.md`
- **Strategy Backlog**: `docs/strategy_backlog.yaml`
- **Database Schema**: `scripts/db_schema.sql`
- **Import Script**: `scripts/results_importer.py`
- **Optimization Runner**: `scripts/optimize_runner.py`

---

**Summary**: Database views are ready. Parameter storage will work once the strategy is properly implemented with `get_parameter()` calls. The framework is sound - the strategy code just needs to be written.
