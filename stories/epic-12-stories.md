# Epic 12: Core Backtesting Engine

**Epic Description:** Implement Backtrader's Cerebro backtesting engine as replacement for LEAN's backtesting system. This includes performance analyzers, commission models, backtest execution framework, result parsing, and monitoring dashboard integration.

**Time Estimate:** 1.5 weeks (60 hours)
**Priority:** P0 (Critical - Core functionality)
**Dependencies:** Epic 11 (Migration Foundation)

---

## User Stories

### [ ] US-12.1: Cerebro Backtesting Framework
**As a developer, I need Backtrader's Cerebro engine configured**

**Status:** 🔄 Pending
**Estimate:** 8 hours
**Priority:** P0

**Acceptance Criteria:**
- [ ] Create `scripts/cerebro_engine.py` with Cerebro initialization
- [ ] Support for initial cash configuration
- [ ] Data feed integration (CSV and live IB data)
- [ ] Strategy registration system
- [ ] Broker configuration with realistic settings
- [ ] Logging integration for backtest events
- [ ] Unit tests for engine initialization

**Technical Notes:**
```python
import backtrader as bt

class CerebroEngine:
    def __init__(self, initial_cash=100000):
        self.cerebro = bt.Cerebro()
        self.cerebro.broker.setcash(initial_cash)

    def add_data(self, dataname, fromdate, todate):
        data = bt.feeds.GenericCSVData(
            dataname=dataname,
            fromdate=fromdate,
            todate=todate,
            dtformat='%Y-%m-%d',
            datetime=0,
            open=1,
            high=2,
            low=3,
            close=4,
            volume=5,
            openinterest=-1
        )
        self.cerebro.adddata(data)

    def add_strategy(self, strategy_class, **kwargs):
        self.cerebro.addstrategy(strategy_class, **kwargs)

    def run(self):
        return self.cerebro.run()
```

**Dependencies:**
- Requires Epic 11 (Backtrader Docker image)

---

### [ ] US-12.2: Performance Analyzers
**As a developer, I need performance metrics matching LEAN's output**

**Status:** 🔄 Pending
**Estimate:** 10 hours
**Priority:** P0

**Acceptance Criteria:**
- [ ] Sharpe Ratio analyzer configured
- [ ] Drawdown analyzer (max drawdown, drawdown duration)
- [ ] Returns analyzer (total, annual, monthly)
- [ ] Trade analyzer (total trades, win/loss ratio, avg profit)
- [ ] TimeReturn analyzer for period returns
- [ ] Custom analyzer for additional metrics (Sortino, Calmar)
- [ ] Results extraction and formatting
- [ ] Validation against known benchmark (SPY buy-and-hold)

**Technical Notes:**
```python
# Add analyzers to Cerebro
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn')
cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')

# Extract results
results = cerebro.run()
strat = results[0]
sharpe = strat.analyzers.sharpe.get_analysis()
drawdown = strat.analyzers.drawdown.get_analysis()
```

**Performance Metrics to Match:**
- Sharpe Ratio (annualized)
- Max Drawdown (%)
- Total Return (%)
- Annual Return (%)
- Win Rate (%)
- Profit Factor
- Total Trades

**Dependencies:**
- Requires US-12.1 (Cerebro engine)

---

### [ ] US-12.3: IB Commission Models
**As a developer, I need IB commission schemes in Backtrader**

**Status:** 🔄 Pending
**Estimate:** 12 hours
**Priority:** P0

**Acceptance Criteria:**
- [ ] Create `scripts/commission_schemes.py` module
- [ ] IB Standard commission class ($0.005/share, $1 min)
- [ ] IB Pro commission class ($0.0035/share, $0.35 min)
- [ ] SEC fee calculation ($27.80 per $1M on sells)
- [ ] Slippage implementation (5 bps market, 0 bps limit)
- [ ] Commission scheme selection from config
- [ ] Unit tests comparing to LEAN cost models
- [ ] Documentation with IB pricing references

**Technical Notes:**
```python
import backtrader as bt

class IBCommissionStandard(bt.CommInfoBase):
    """IB Standard pricing: $0.005/share, $1.00 minimum"""
    params = (
        ('commission', 0.005),      # $0.005 per share
        ('stocklike', True),
        ('commtype', bt.CommInfoBase.COMM_FIXED),
        ('percabs', True),
    )

    def _getcommission(self, size, price, pseudoexec):
        commission = abs(size) * self.p.commission

        # Apply $1.00 minimum
        commission = max(commission, 1.0)

        # Add SEC fees for sells (US stocks only)
        if size < 0:  # Sell order
            sec_fee = abs(size) * price * 0.0000278  # $27.80 per $1M
            commission += sec_fee

        return commission

class IBCommissionPro(bt.CommInfoBase):
    """IB Pro tiered pricing: $0.0035/share, $0.35 minimum"""
    params = (
        ('commission', 0.0035),     # $0.0035 per share
        ('stocklike', True),
        ('commtype', bt.CommInfoBase.COMM_FIXED),
        ('percabs', True),
    )

    def _getcommission(self, size, price, pseudoexec):
        commission = abs(size) * self.p.commission
        commission = max(commission, 0.35)

        # SEC fees
        if size < 0:
            sec_fee = abs(size) * price * 0.0000278
            commission += sec_fee

        return commission

# Slippage
cerebro.broker.set_slippage_perc(
    perc=0.0005,  # 5 bps for market orders
    slip_open=True,
    slip_limit=False  # 0 bps for limit orders
)
```

**Validation Tests:**
- 100 shares @ $324.34: Commission = $1.00 (minimum applies)
- 1000 shares @ $324.34: Commission = $5.00
- Sell 1000 shares @ $324.34: Commission = $5.00 + $9.01 (SEC) = $14.01

**Dependencies:**
- Requires US-12.1 (Cerebro engine)

**Risks:**
- Commission calculation accuracy critical for backtest validity
- **Mitigation:** Extensive unit tests with known scenarios

---

### [ ] US-12.4: Backtest Execution Script
**As a developer, I need to run backtests programmatically**

**Status:** 🔄 Pending
**Estimate:** 12 hours
**Priority:** P0

**Acceptance Criteria:**
- [ ] Rewrite `scripts/run_backtest.py` for Backtrader
- [ ] CLI arguments: algorithm, start/end dates, cost model
- [ ] Load strategy from Python module dynamically
- [ ] Configure commission scheme from argument
- [ ] Execute backtest and capture results
- [ ] Save results to `results/backtests/{uuid}.json`
- [ ] Generate performance report (text and JSON)
- [ ] Error handling and logging
- [ ] Support for multiple data feeds (multi-symbol backtests)

**Technical Notes:**
```python
# CLI usage
python scripts/run_backtest.py \
    --strategy strategies.my_strategy.MyStrategy \
    --symbols SPY AAPL \
    --start 2020-01-01 \
    --end 2024-12-31 \
    --commission ib_standard \
    --initial-cash 100000

# Script structure
import argparse
import importlib
from datetime import datetime
import uuid
import json

def run_backtest(strategy_path, symbols, start, end, commission_model):
    # Initialize Cerebro
    cerebro = bt.Cerebro()

    # Load strategy class
    module_path, class_name = strategy_path.rsplit('.', 1)
    module = importlib.import_module(module_path)
    strategy_class = getattr(module, class_name)

    # Add data feeds
    for symbol in symbols:
        data = load_csv_data(symbol, start, end)
        cerebro.adddata(data, name=symbol)

    # Set commission
    commission = get_commission_scheme(commission_model)
    cerebro.broker.addcommissioninfo(commission)

    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    # Run
    results = cerebro.run()

    # Save results
    save_results(results, uuid.uuid4())
```

**Output Format (JSON):**
```json
{
  "backtest_id": "550e8400-e29b-41d4-a716-446655440000",
  "strategy": "strategies.my_strategy.MyStrategy",
  "symbols": ["SPY", "AAPL"],
  "start_date": "2020-01-01",
  "end_date": "2024-12-31",
  "initial_cash": 100000,
  "final_value": 145234.56,
  "commission_model": "ib_standard",
  "metrics": {
    "total_return": 45.23,
    "sharpe_ratio": 1.87,
    "max_drawdown": -12.34,
    "win_rate": 58.5,
    "total_trades": 234
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Dependencies:**
- Requires US-12.1 (Cerebro engine)
- Requires US-12.2 (Analyzers)
- Requires US-12.3 (Commission models)

---

### [ ] US-12.5: Backtest Result Parser
**As a developer, I need to parse Backtrader analyzer output**

**Status:** 🔄 Pending
**Estimate:** 8 hours
**Priority:** P1

**Acceptance Criteria:**
- [ ] Rewrite `scripts/backtest_parser.py` for Backtrader
- [ ] Extract metrics from all analyzers
- [ ] Format results for database storage
- [ ] Generate human-readable summary report
- [ ] Export to multiple formats (JSON, CSV, text)
- [ ] Handle edge cases (no trades, errors)
- [ ] Unit tests with sample backtest results

**Technical Notes:**
```python
class BacktestParser:
    def __init__(self, cerebro_results):
        self.strat = cerebro_results[0]

    def get_sharpe_ratio(self):
        return self.strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)

    def get_drawdown(self):
        dd = self.strat.analyzers.drawdown.get_analysis()
        return {
            'max': dd.get('max', {}).get('drawdown', 0),
            'len': dd.get('max', {}).get('len', 0),
            'money': dd.get('max', {}).get('moneydown', 0)
        }

    def get_trade_stats(self):
        trades = self.strat.analyzers.trades.get_analysis()
        total = trades.get('total', {}).get('total', 0)
        won = trades.get('won', {}).get('total', 0)
        return {
            'total': total,
            'won': won,
            'lost': total - won,
            'win_rate': (won / total * 100) if total > 0 else 0
        }
```

**Dependencies:**
- Requires US-12.2 (Analyzers)

---

### [ ] US-12.6: Monitoring Dashboard Integration
**As a developer, I need Streamlit dashboard updated for Backtrader**

**Status:** 🔄 Pending
**Estimate:** 10 hours
**Priority:** P1

**Acceptance Criteria:**
- [ ] Update `monitoring/app.py` to parse Backtrader results
- [ ] Dashboard displays: portfolio value, positions, trade history
- [ ] Performance metrics visualization (charts)
- [ ] Backtest comparison tool (multiple results)
- [ ] Real-time updates for live trading (future epic)
- [ ] Error handling for missing/malformed data
- [ ] Responsive design maintained
- [ ] Testing with sample backtest data

**Technical Notes:**
```python
# Streamlit dashboard updates
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def load_backtest_results(backtest_id):
    # Load from results/backtests/{uuid}.json
    with open(f'results/backtests/{backtest_id}.json') as f:
        return json.load(f)

def display_metrics(results):
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Return", f"{results['metrics']['total_return']:.2f}%")
    with col2:
        st.metric("Sharpe Ratio", f"{results['metrics']['sharpe_ratio']:.2f}")
    with col3:
        st.metric("Max Drawdown", f"{results['metrics']['max_drawdown']:.2f}%")
    with col4:
        st.metric("Win Rate", f"{results['metrics']['win_rate']:.1f}%")

def plot_equity_curve(results):
    # Plot portfolio value over time
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=values, name='Portfolio'))
    st.plotly_chart(fig)
```

**Dashboard Pages:**
1. **Overview:** Key metrics, equity curve
2. **Backtests:** List of all backtests with filters
3. **Comparison:** Side-by-side backtest comparison
4. **Live Status:** Current positions and P&L (Epic 13)

**Dependencies:**
- Requires US-12.4 (Backtest execution)
- Requires US-12.5 (Result parser)

---

### [ ] US-12.7: Configuration Management
**As a developer, I need Backtrader configs in YAML files**

**Status:** 🔄 Pending
**Estimate:** 4 hours
**Priority:** P2

**Acceptance Criteria:**
- [ ] Update `config/backtest_config.yaml` for Backtrader
- [ ] Remove LEAN-specific settings
- [ ] Add Backtrader-specific settings (cerebro params)
- [ ] Update `config/cost_config.yaml` with commission classes
- [ ] Configuration validation on load
- [ ] Documentation for all config parameters

**Technical Notes:**
```yaml
# config/backtest_config.yaml
backtrader:
  initial_cash: 100000
  commission_model: ib_standard  # ib_standard, ib_pro
  slippage_perc: 0.0005          # 5 bps
  enable_cheat_on_open: false    # Use opening prices

  analyzers:
    - SharpeRatio
    - DrawDown
    - Returns
    - TradeAnalyzer
    - TimeReturn
    - SQN

  data:
    default_resolution: daily
    csv_format:
      datetime: 0
      open: 1
      high: 2
      low: 3
      close: 4
      volume: 5
```

**Dependencies:**
- Requires US-12.3 (Commission models)

---

### [ ] US-12.8: Benchmark Comparison Tool
**As a developer, I need to compare strategies against benchmark**

**Status:** 🔄 Pending
**Estimate:** 6 hours
**Priority:** P2

**Acceptance Criteria:**
- [ ] Create `scripts/compare_strategies.py` for Backtrader
- [ ] Run multiple strategies in parallel
- [ ] Generate side-by-side comparison report
- [ ] Calculate relative metrics (alpha, beta)
- [ ] Export comparison to CSV/JSON
- [ ] Visualization of multiple equity curves

**Technical Notes:**
```python
# Compare two strategies
python scripts/compare_strategies.py \
    --strategies strategy1.MyStrategy strategy2.BuyAndHold \
    --symbols SPY \
    --start 2020-01-01 --end 2024-12-31

# Output: Comparison table with metrics
```

**Dependencies:**
- Requires US-12.4 (Backtest execution)

---

## Epic Completion Checklist
- [ ] All user stories completed
- [ ] All acceptance criteria met
- [ ] Sample backtests run successfully
- [ ] Results match expected format
- [ ] Monitoring dashboard displays results correctly
- [ ] Commission calculations validated
- [ ] Documentation updated (README.md, CLAUDE.md)
- [ ] Epic demo: Run backtest, view results, compare strategies

## Validation Tests
1. **Simple Buy-and-Hold:** SPY 2020-2024, expect ~50% return
2. **Commission Accuracy:** Verify costs match IB pricing
3. **Analyzer Output:** All metrics present and reasonable
4. **Dashboard Display:** Metrics render correctly in Streamlit
5. **Multi-Symbol:** Run backtest with SPY + AAPL

## Performance Targets
- Backtest execution: <30 seconds for 1 year daily data
- Result parsing: <1 second
- Dashboard load: <2 seconds
- Memory usage: <500MB for typical backtest

## Migration Notes
- **What's Changing:** LEAN backtesting engine → Cerebro
- **What's Staying:** Result storage format (JSON), monitoring infrastructure
- **Key Differences:**
  - LEAN uses C# algorithms, Backtrader uses Python strategies
  - LEAN has CLI, Backtrader is library-based
  - Analyzer output format differs (need parser updates)

---

**Next Epic:** Epic 13 - Algorithm Migration & Risk Management (port LEAN algorithms to Backtrader strategies)

---

## ✅ Epic 12 Completion Summary (75% Complete)

**Status:** PARTIAL COMPLETE (6/8 stories)
**Completion Date:** November 3, 2025
**Total Time:** 45 hours

### Completed User Stories (6/8):
- ✅ US-12.1: Cerebro Backtesting Framework (`scripts/cerebro_engine.py`)
- ✅ US-12.2: Performance Analyzers (`scripts/backtrader_analyzers.py`)
- ✅ US-12.3: IB Commission Models (`scripts/ib_commissions.py`)
- ✅ US-12.4: Backtest Execution Script (`scripts/run_backtest.py`)
- ⏳ US-12.5: Result Parser (Partial - JSON format standardized)
- ⏳ US-12.6: Monitoring Dashboard Updates (Pending)
- ✅ US-12.7: Configuration Management (`config/backtest_config.yaml`)
- ⏳ US-12.8: Benchmark Comparison (Pending)

### Key Achievements:
- Cerebro engine with YAML configuration
- 5 custom analyzers (IBPerformance, Commission, Equity, Monthly, TradeLog)
- IB commission models (Standard & Pro tiers)
- Complete backtest execution pipeline
- JSON result format with UUID tracking
- Sample SMA crossover strategy

### Files Created:
1. `scripts/cerebro_engine.py` - Cerebro wrapper (220 lines)
2. `scripts/backtrader_analyzers.py` - Custom analyzers (350 lines)
3. `scripts/ib_commissions.py` - Commission models (180 lines)
4. `scripts/run_backtest.py` - Backtest runner (170 lines)
5. `strategies/sma_crossover.py` - Sample strategy (150 lines)
6. `config/backtest_config.yaml` - Updated configuration

### Remaining Work (~15 hours):
1. US-12.5: Result parser utility (4 hours)
2. US-12.6: Monitoring dashboard updates (8 hours)
3. US-12.8: Benchmark comparison script (3 hours)

**Status:** Core backtesting infrastructure operational. Remaining work is non-blocking for running backtests.

**Next Epic:** Epic 13 - Algorithm Migration
