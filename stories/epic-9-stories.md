# Epic 9: AI Integration Layer

**Epic Description:** Build programmatic APIs and Claude Skills for AI agents to interact with the trading platform for backtesting, optimization, deployment, and monitoring.

**Architecture Note:** APIs work with LEAN engine - algorithms are LEAN Python files, backtests use `lean backtest` command, live deployment uses `lean live deploy` command.

**Time Estimate:** 50 hours
**Priority:** P0 (Critical for AI-driven workflow)
**Dependencies:** Epic 4 (Backtesting), Epic 5 (Live Trading), Epic 6 (Risk Management)

---

## User Stories

### [ ] US-9.1: Programmatic Backtest Execution
**As an AI agent, I need programmatic backtest execution**

**Status:** Not Started
**Estimate:** 6 hours
**Priority:** P0

**Acceptance Criteria:**
- [ ] Python API: `run_backtest(strategy_code, start_date, end_date, symbols, parameters)`
- [ ] Returns structured results (JSON)
- [ ] Async execution support
- [ ] Progress callbacks
- [ ] Error handling with meaningful messages

**Implementation Notes:**
- Uses `lean backtest` command under the hood to execute LEAN algorithm
- Wrapper function parses LEAN CLI output and returns structured results
- Supports passing LEAN algorithm path and configuration parameters

---

### [ ] US-9.2: Read Backtest Results Programmatically
**As an AI agent, I need to read backtest results programmatically**

**Status:** Not Started
**Estimate:** 4 hours
**Priority:** P0

**Acceptance Criteria:**
- [ ] API: `get_backtest_results(backtest_id)`
- [ ] Returns: metrics dict (Sharpe, win rate, trades, drawdown, etc.)
- [ ] API: `get_trades(backtest_id)` returns trade list
- [ ] API: `get_equity_curve(backtest_id)` returns time series
- [ ] All data in machine-readable format (JSON/dict)

**Implementation Notes:**
- Reads from `results/backtests/{backtest_id}.json` (saved by LEAN backtest)
- Parses LEAN algorithm output for performance metrics
- Queries database for detailed trade/position history if available

---

### [ ] US-9.3: Parameter Optimization API
**As an AI agent, I need parameter optimization API**

**Status:** Not Started
**Estimate:** 8 hours
**Priority:** P0

**Acceptance Criteria:**
- [ ] API: `optimize_parameters(strategy_code, param_ranges, optimization_metric)`
- [ ] Runs grid search or Bayesian optimization
- [ ] Returns ranked results with top N parameter sets
- [ ] Progress tracking
- [ ] Can specify constraints (max drawdown, min win rate)

**Implementation Notes:**
- Generates LEAN parameter configurations from param_ranges
- Calls `lean optimize` command or runs backtests across parameter combinations
- Parses results and ranks by optimization_metric
- Uses LEAN's native optimization or implements wrapper for custom algorithms

---

### [ ] US-9.4: Strategy Deployment API
**As an AI agent, I need strategy deployment API**

**Status:** Not Started
**Estimate:** 6 hours
**Priority:** P0

**Acceptance Criteria:**
- [ ] API: `deploy_strategy(strategy_code, mode='paper'|'live', parameters)`
- [ ] Validates strategy before deployment
- [ ] Hot-swap capability (replace running strategy)
- [ ] Rollback to previous strategy
- [ ] Returns deployment status

**Implementation Notes:**
- Deploys LEAN algorithms via `lean live deploy` command
- Validates LEAN algorithm syntax and dependencies before deployment
- Supports hot-swap by stopping current algorithm and starting replacement
- Maintains backup of previous algorithm for rollback capability

---

### [ ] US-9.5: Live Performance Monitoring API
**As an AI agent, I need live performance monitoring API**

**Status:** Not Started
**Estimate:** 6 hours
**Priority:** P1 (High)

**Acceptance Criteria:**
- [ ] API: `get_current_positions()` returns active positions
- [ ] API: `get_today_trades()` returns today's executions
- [ ] API: `get_performance_metrics()` returns live P&L, win rate, etc.
- [ ] API: `get_system_health()` returns connection status, errors
- [ ] WebSocket stream for real-time updates (optional)

**Implementation Notes:**
- Reads from database tables populated by LEAN algorithm (positions, trades, orders)
- LEAN algorithm populates db_logger tables in real-time during live trading
- Provides query interfaces for current state and historical data from database

---

### [ ] US-9.6: Data Access API
**As an AI agent, I need data access API**

**Status:** Not Started
**Estimate:** 4 hours
**Priority:** P1 (High)

**Acceptance Criteria:**
- [ ] API: `get_historical_data(symbols, start_date, end_date, resolution)`
- [ ] API: `download_data(symbols, date_range)` triggers download
- [ ] API: `get_data_quality_report(symbols)` checks for gaps/issues
- [ ] Caching handled transparently

**Implementation Notes:**
- Wrapper around LEAN's data management (download, query, cache)
- Supports querying LEAN-formatted data from `data/` directory
- Download functionality uses LEAN CLI data download features

---

### [ ] US-9.7: Strategy Comparison API
**As an AI agent, I need strategy comparison API**

**Status:** Not Started
**Estimate:** 4 hours
**Priority:** P1 (High)

**Acceptance Criteria:**
- [ ] API: `compare_strategies([backtest_id1, backtest_id2, ...])`
- [ ] Returns side-by-side metrics comparison
- [ ] Generates comparison charts
- [ ] Highlights winner by specified metric
- [ ] Export to report format

**Implementation Notes:**
- Compares backtest results from LEAN backtest JSON files
- Extracts performance metrics from LEAN algorithm output
- Generates comparison matrix and ranking by selected metrics

---

### [ ] US-9.8: Claude Skills for Common Tasks
**As a developer, I need Claude Skills for common tasks**

**Status:** Partially Complete
**Estimate:** 12 hours (reduced - 2 skills already exist)
**Priority:** P1 (High)

**Acceptance Criteria:**
- [X] Skill: "data-manager" (download, cache, validate data) - EXISTS
- [X] Skill: "backtest-runner" (run backtest, get results) - EXISTS
- [ ] Skill: "parameter-optimizer" (optimize and rank)
- [ ] Skill: "strategy-deployer" (deploy to paper/live)
- [ ] Skill: "performance-monitor" (get current status)
- [ ] Each skill has clear interface and examples
- [ ] Skills documented in /skills directory

**Implementation Notes:**
- data-manager and backtest-runner skills already implemented and integrated
- Remaining skills build on existing API layer from US-9.1 through US-9.6
- Each skill provides natural language interface to underlying Python APIs

---

## Epic Completion Checklist
- [ ] All user stories completed
- [ ] All acceptance criteria met
- [ ] APIs tested programmatically
- [ ] Claude Skills implemented
- [ ] Documentation complete
- [ ] Example usage provided
- [ ] Epic demo completed
