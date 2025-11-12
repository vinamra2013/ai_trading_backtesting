# Database Management Guide

Safe operations for managing the trading backtesting database.

**IMPORTANT: Only two safe operations are available - Views and Strategy Definitions are ALWAYS preserved.**

## Quick Reference

| Task | Python Script | Bash Script |
|------|---------------|------------|
| **Check Status** | `python scripts/reset_database.py --status` | `./scripts/reset_db.sh status` |
| **Clear Optimization Data** | `python scripts/reset_database.py --strategies` | `./scripts/reset_db.sh strategies` |
| **Show Leaderboard** | `python scripts/reset_database.py --display leaderboard` | `./scripts/reset_db.sh leaderboard` |
| **Show Parameter Analysis** | `python scripts/reset_database.py --display parameters` | `./scripts/reset_db.sh parameters` |
| **Show Fee Analysis** | `python scripts/reset_database.py --display fees` | `./scripts/reset_db.sh fees` |
| **Show Daily Summary** | `python scripts/reset_database.py --display daily` | `./scripts/reset_db.sh daily` |

## Safe Operations

### ✅ Operation 1: Check Database Status
```bash
python scripts/reset_database.py --status
```
**Output:**
```
📊 DATABASE STATUS
============================================================
✅ strategies..............................      15 rows
✅ optimization_runs.......................     486 rows
✅ backtest_results........................  12,504 rows
============================================================
📈 Total data rows: 13,005
📍 Database: trading @ localhost:5432
👤 User: mlflow
✅ All views preserved (not shown in row count)
```

**What it does:** Shows current row counts in database and confirms views are intact.

---

### ✅ Operation 2: Clear Optimization Data Only
```bash
# With confirmation
python scripts/reset_database.py --strategies

# Without confirmation
python scripts/reset_database.py --strategies --no-confirm
```

**What it clears:**
- ✗ All backtest results
- ✗ All optimization runs
- ✗ Strategy status reset to 'testing'

**What it keeps:**
- ✓ Strategy definitions (15 strategies)
- ✓ Database schema
- ✓ **All database views** (leaderboard, parameter_performance, fee_analysis, daily_summary)

**Use this when:** You want to run fresh optimizations on the same strategies.

---

### ✅ Operation 3: Display Data from Views

#### 3a. Strategy Leaderboard (Top Performers)
```bash
python scripts/reset_database.py --display leaderboard
```

**Output:** Ranked list of best-performing strategies with metrics:
- Sharpe ratio
- Total return %
- Annual return %
- Max drawdown
- Win rate
- Trading fees

---

#### 3b. Parameter Performance Analysis
```bash
python scripts/reset_database.py --display parameters
```

**Output:** How different parameter values affect performance:
- Strategy name
- Parameter name and value
- Average Sharpe ratio
- Average return
- Average drawdown
- Number of tests

---

#### 3c. Fee Analysis
```bash
python scripts/reset_database.py --display fees
```

**Output:** Fee impact across strategies:
- Average fees per strategy
- Fee % of $1K capital (critical metric!)
- Average trades
- Fee per trade
- Number of backtests

**⚠️ CRITICAL:** Fees > 25% of $1K capital = $250 (unsustainable)

---

#### 3d. Daily Backtesting Summary
```bash
python scripts/reset_database.py --display daily
```

**Output:** Daily backtesting activity:
- Date
- Total backtests run
- Backtests that passed criteria
- Best Sharpe ratio for the day
- Average Sharpe ratio
- Number of strategies tested

---

## Common Workflows

### Workflow 1: Start Fresh Optimization Run
```bash
# 1. Check current state
python scripts/reset_database.py --status

# 2. Clear optimization data (keep strategies)
python scripts/reset_database.py --strategies

# 3. Run fresh optimization
python scripts/optimize_runner.py --config configs/optimizations/STR-001_rsi_etf_lowfreq.yaml
```

### Workflow 2: Review Results Before Starting Fresh
```bash
# 1. View top performing strategies
python scripts/reset_database.py --display leaderboard

# 2. Analyze fee impact
python scripts/reset_database.py --display fees

# 3. Study parameter sensitivity
python scripts/reset_database.py --display parameters

# 4. Then clear and run new optimization
python scripts/reset_database.py --strategies --no-confirm
```

### Workflow 3: Continuous Testing
```bash
# Monitor daily activity
python scripts/reset_database.py --display daily

# Check what's passed so far
python scripts/reset_database.py --display leaderboard

# Analyze parameter effectiveness
python scripts/reset_database.py --display parameters
```

---

## Database Safety

### What You Can Never Lose
- ✅ **Views**: Always preserved (leaderboard, parameter_performance, fee_analysis, daily_summary)
- ✅ **Strategy Definitions**: Always preserved (15 strategies with metadata)
- ✅ **Schema**: Always preserved (tables, indexes, triggers, functions)

### What Can Be Cleared
- ✗ Backtest results (optimization_runs table)
- ✗ Optimization run history (optimization_runs table)

### Confirmation Prompts
All destructive operations require explicit confirmation:
```
⚠️  This will DELETE all optimization runs and backtest results
but KEEP strategy definitions and PRESERVE all views.
Are you sure? Type 'yes' to confirm:
```

Skip with `--no-confirm` flag, but use carefully!

---

## View Descriptions

### `strategy_leaderboard` view
Shows top performing strategies ranked by Sharpe ratio.
- Includes only backtests that passed success criteria
- Displays all key performance metrics
- Useful for: Finding winning strategies

### `parameter_performance` view
Analyzes how different parameter values affect performance.
- Groups results by strategy, parameter name, and parameter value
- Shows average metrics for each parameter combination
- Useful for: Understanding parameter sensitivity, optimizing ranges

### `fee_analysis` view
Shows fee impact across all strategies.
- Calculates average fees per strategy
- Shows fee % of $1K capital (critical for small accounts)
- Calculates fee per trade
- Useful for: Identifying fee-heavy strategies, controlling costs

### `daily_summary` view
Tracks daily backtesting activity.
- Shows daily backtest counts
- Tracks how many passed criteria each day
- Best and average Sharpe ratios by day
- Useful for: Monitoring optimization progress, finding trends

---

## Troubleshooting

### Connection Error
```
❌ Connection failed: connection refused
```

**Solution:**
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Start PostgreSQL if needed
docker-compose up -d mlflow-postgres

# Test connection
psql -h localhost -U mlflow -d trading -c "SELECT 1"
```

### Tabulate Not Installed
```
ModuleNotFoundError: No module named 'tabulate'
```

**Solution:**
```bash
source venv/bin/activate
pip install tabulate
```

### Views Not Found Error
```
❌ View not found or empty
```

**Solution:** Views are automatically created by `db_schema.sql`. If missing:
```bash
# Rebuild from schema (keeps data)
docker exec mlflow-postgres psql -U mlflow -d trading -f scripts/db_schema.sql
```

---

## Python Script Full Options

```bash
python scripts/reset_database.py --help
```

Shows all available commands and options.

---

## Environment Variables

Scripts use these `.env` variables:
- `POSTGRES_DB` (default: `trading`)
- `POSTGRES_USER` (default: `mlflow`)
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST` (default: `localhost`)
- `POSTGRES_PORT` (default: `5432`)

Example `.env`:
```bash
POSTGRES_DB=trading
POSTGRES_USER=mlflow
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

---

## Key Metrics Explained

### Sharpe Ratio
- **Target:** > 1.0
- **Meaning:** Risk-adjusted returns (higher is better)
- **Formula:** (Annual Return - Risk-Free Rate) / Annual Volatility

### Drawdown
- **Target:** < 15%
- **Meaning:** Largest peak-to-trough decline
- **Example:** $1000 → $850 = 15% drawdown

### Win Rate
- **Target:** > 50%
- **Meaning:** % of trades that were profitable
- **Example:** 50 wins out of 100 trades = 50% win rate

### Fees % of Capital
- **Target:** < 25%
- **Meaning:** Trading costs as % of starting capital
- **Critical:** >25% is unsustainable for $1K accounts

---

## Questions?

For more information:
- Schema details: `scripts/db_schema.sql`
- Optimization guide: `docs/OPTIMIZATION_GUIDE.md`
- Project overview: `CLAUDE.md`
