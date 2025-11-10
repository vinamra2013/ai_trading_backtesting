# Developer Requirements - High-Frequency Mean Reversion Trading System
**Date**: 2025-11-07
**Requested by**: Quant Director
**Priority**: HIGH - Required for immediate deployment
**Timeline**: 1-2 weeks for MVP

---

## 🎯 EXECUTIVE SUMMARY

We need to build a **high-frequency mean reversion trading system** targeting **1%+ profit per trade** with a **$1000 starting capital**. The system must discover profitable opportunities autonomously, backtest them rigorously, and deploy the best strategies to live trading via Interactive Brokers.

**Key Constraint**: The Director is NOT a developer. All coding, testing, and infrastructure work must be done by the developer. The Director will provide strategic direction, analysis, and operational decisions.

---

## 📊 STRATEGIC DECISIONS (Director's Final Choices)

### **1. Trading Style: High-Frequency Mean Reversion Scalper**
- **Hold Period**: 1-3 days maximum (NOT swing trading)
- **Trade Frequency**: Target 6-9 trades per week across 3 concurrent positions
- **Profit Target**: 1.5-2.5% per trade (quick scalps, not home runs)
- **Stop Loss**: 0.8-1.0% (tight risk management)
- **Win Rate Target**: 65-75% (higher than momentum strategies)

**Rationale**: Mathematical analysis shows this profile achieves 1%+ average profit per trade:
- (0.65 win rate × 2.0% avg win) + (0.35 × -0.8% avg loss) = 1.02% per trade

### **2. Symbol Universe: Volatile Large-Caps + Leveraged ETFs**
**Primary Focus** (discovered via scanner):
- AVGO, NVDA, AMZN, MSFT, GOOGL, QCOM, UNH (ATR 7-13, daily volatility 2-4%)

**Add to Universe**:
- Leveraged ETFs: TQQQ, SQQQ, UPRO, SPXU (3x volatility for easier 1% targets)
- Sector ETFs: XLE, XLF, XLK (diversification, rotation opportunities)

**Total Universe**: 15-20 symbols with daily volatility >2%

### **3. Strategy Priority: Mean Reversion FIRST**
**Primary Strategies to Build**:
1. RSI Mean Reversion (buy oversold, sell at mean)
2. Bollinger Band Reversals
3. Gap Fade (fade large overnight gaps)
4. Volatility Compression (buy after multi-day low volatility)

**Secondary** (if time permits):
- Momentum breakouts for trending regimes
- Sector rotation for ETF plays

**Rationale**: Mean reversion achieves 60-75% win rates vs 40-55% for momentum, which is critical for hitting 1% per trade target.

### **4. Developer Dependency Strategy: Hybrid Approach**
- **Start Immediately**: Use existing tools while building enhancements in parallel
- **Iterative Development**: Build MVP fast, enhance iteratively based on backtest results
- **Don't Block Progress**: If a feature takes >3 days, find workaround and continue

### **5. Success Milestones**
- **30 Days**: 3 validated strategies ready for paper trading
- **60 Days**: Live deployment with $1000 capital, achieving 5-10 trades total
- **90 Days**: Profitable track record, scaling to $2000+ capital

---

## 🛠️ REQUIRED DEVELOPMENT WORK

### **PRIORITY 1: Critical for Strategy Discovery (Week 1)**

#### **REQ-1.1: Mean Reversion Strategy Library**
**Status**: CRITICAL - Blocks all progress
**Effort**: 2-3 days

**Deliverables**:
Create 4 Backtrader strategy files in `strategies/`:

1. **`rsi_mean_reversion.py`**
   - Entry: RSI(14) < 25 (oversold)
   - Exit: RSI(14) > 50 (return to mean) OR 3 days max hold
   - Stop Loss: 1.0% from entry
   - Profit Target: 2.0% from entry
   - Must inherit from `BaseStrategy` for risk management

2. **`bollinger_reversal.py`**
   - Entry: Price touches lower Bollinger Band (2 std dev, 20-period)
   - Exit: Price reaches middle band OR 2 days max hold
   - Stop Loss: 0.8% from entry
   - Profit Target: 1.5% from entry

3. **`gap_fade.py`**
   - Entry: Opening gap >1.5% (up or down) with no fundamental catalyst
   - Exit: Gap fills 50% OR end of day
   - Stop Loss: 1.0% from entry
   - Profit Target: 0.75% gap fill

4. **`volatility_compression.py`**
   - Entry: ATR(14) drops below 0.6 × ATR(20) for 3+ days, then spikes >1.2 × ATR(20)
   - Exit: Volatility returns to mean OR 5 days max
   - Stop Loss: 1.0% from entry
   - Profit Target: 2.5% from entry

**Acceptance Criteria**:
- All strategies must pass syntax validation
- Must work with existing backtest runner (`scripts/run_backtest.py`)
- Must integrate with risk management framework (`BaseStrategy`)
- Must log trades to database for analysis

**Code Template**:
```python
from strategies.base_strategy import BaseStrategy
import backtrader as bt

class RSIMeanReversion(BaseStrategy):
    params = (
        ('rsi_period', 14),
        ('rsi_entry', 25),
        ('rsi_exit', 50),
        ('stop_loss_pct', 1.0),
        ('profit_target_pct', 2.0),
        ('max_hold_days', 3),
    )

    def __init__(self):
        super().__init__()
        self.rsi = bt.indicators.RSI(self.data.close, period=self.p.rsi_period)
        self.entry_price = None
        self.entry_date = None

    def next(self):
        # Entry logic: RSI oversold
        if not self.position:
            if self.rsi[0] < self.p.rsi_entry:
                # Check risk limits before entry
                if self.check_risk_limits():
                    self.entry_price = self.data.close[0]
                    self.entry_date = self.data.datetime.date(0)
                    self.buy()

        # Exit logic
        else:
            # Profit target
            if self.data.close[0] >= self.entry_price * (1 + self.p.profit_target_pct/100):
                self.close()

            # Stop loss
            elif self.data.close[0] <= self.entry_price * (1 - self.p.stop_loss_pct/100):
                self.close()

            # Mean reversion exit
            elif self.rsi[0] > self.p.rsi_exit:
                self.close()

            # Time-based exit
            elif (self.data.datetime.date(0) - self.entry_date).days >= self.p.max_hold_days:
                self.close()
```

---

#### **REQ-1.2: Custom Optimization Metric - Profit Per Trade**
**Status**: HIGH - Needed for parameter optimization
**Effort**: 1 day

**Problem**: Current optimization uses Sharpe ratio, which optimizes for long-term risk-adjusted returns. We need to optimize for **profit per trade** to hit the 1% target.

**Deliverable**:
Modify `scripts/optimize_strategy.py` to add new metric option:

```python
--metric profit_per_trade
```

**Calculation Formula**:
```python
def calculate_profit_per_trade(trades):
    """
    Calculate average profit per trade (including winners and losers)

    Args:
        trades: List of trade results from backtest

    Returns:
        float: Average profit percentage per trade
    """
    if len(trades) == 0:
        return 0.0

    total_profit_pct = sum([trade.pnl_pct for trade in trades])
    avg_profit_per_trade = total_profit_pct / len(trades)

    return avg_profit_per_trade
```

**Additional Metrics to Add**:
```python
--metric win_rate_adjusted_profit
# Formula: win_rate × avg_winner_pct - loss_rate × avg_loser_pct
# This is the EXACT metric we need for 1% per trade target

--metric trade_frequency
# Number of trades per month
# Constraint: Must be >4 trades/month minimum

--metric profit_factor
# Gross profit / Gross loss
# Constraint: Must be >1.5 minimum
```

**Integration**:
- Update Optuna objective function to use new metrics
- Add metric validation (e.g., reject parameter sets with <1% profit per trade)
- Log metric to MLflow for comparison

**Acceptance Criteria**:
- Can run: `python scripts/optimize_strategy.py --metric profit_per_trade`
- Optimization maximizes avg profit per trade, not Sharpe
- Results show: profit_per_trade, win_rate, avg_winner, avg_loser, trade_count

---

#### **REQ-1.3: VIX Data Feed Integration**
**Status**: HIGH - Needed for regime detection
**Effort**: 1-2 days

**Purpose**: Enable strategies to adapt based on market volatility regime (high VIX = mean reversion mode, low VIX = momentum mode)

**Deliverables**:

1. **VIX Data Download Script**:
   - Modify `scripts/download_data.py` to support VIX symbol
   - Download historical VIX data (2020-present)
   - Store in `data/raw/VIX_daily.csv`

2. **VIX Indicator for Backtrader**:
   - Create `indicators/vix_regime.py`:
```python
import backtrader as bt

class VIXRegime(bt.Indicator):
    """
    VIX-based market regime classifier

    Regimes:
    - HIGH_VOL: VIX > 25 (panic, use mean reversion)
    - MEDIUM_VOL: VIX 15-25 (normal, use both strategies)
    - LOW_VOL: VIX < 15 (complacency, use momentum)
    """
    lines = ('regime',)
    params = (
        ('high_threshold', 25),
        ('low_threshold', 15),
    )

    def __init__(self):
        # VIX data must be added as separate data feed
        self.vix = self.data.close

    def next(self):
        if self.vix[0] > self.p.high_threshold:
            self.lines.regime[0] = 2  # HIGH_VOL
        elif self.vix[0] < self.p.low_threshold:
            self.lines.regime[0] = 0  # LOW_VOL
        else:
            self.lines.regime[0] = 1  # MEDIUM_VOL
```

3. **Strategy Integration**:
   - Update mean reversion strategies to only trade when VIX regime = HIGH_VOL or MEDIUM_VOL
   - Add regime filter to entry conditions

**Acceptance Criteria**:
- VIX data downloads successfully via IB or yfinance
- VIX indicator works in backtests
- Strategies can access VIX regime in real-time
- Backtest results show regime-aware trading (fewer trades in wrong regimes)

---

### **PRIORITY 2: Performance Optimization (Week 1-2)**

#### **REQ-2.1: Parallel Backtesting Enhancement**
**Status**: MEDIUM - Improves speed but not blocking
**Effort**: 1 day

**Current State**: Can run parallel backtests via `parallel_backtest.py` but limited to symbol-level parallelization

**Enhancement Needed**:
Enable **strategy-level parallelization** so we can test:
- 4 strategies × 15 symbols = 60 backtests in parallel (vs 60 sequential)

**Deliverable**:
Modify `scripts/parallel_backtest.py` to:
- Accept strategy list: `--strategies strategy1.py,strategy2.py,strategy3.py`
- Create Cartesian product: strategies × symbols
- Distribute via Redis queue
- Consolidate results into unified DataFrame

**Acceptance Criteria**:
- Can run: `python scripts/parallel_backtest.py --strategies rsi_mean_reversion.py,bollinger_reversal.py --symbols NVDA,AVGO,AMZN`
- Completes 60 backtests in <10 minutes (vs 60+ minutes sequential)
- Results include: strategy_name, symbol, sharpe, profit_per_trade, win_rate, trade_count

---

#### **REQ-2.2: Backtest Results Aggregation & Ranking**
**Status**: MEDIUM - Needed for portfolio construction
**Effort**: 0.5 days

**Current State**: Backtest results saved as individual JSON files in `results/backtests/`

**Enhancement Needed**:
Create aggregation script that:
1. Reads all JSON files in `results/backtests/`
2. Extracts key metrics
3. Ranks by profit_per_trade (primary) and Sharpe (secondary)
4. Outputs ranked CSV for portfolio selection

**Deliverable**:
Create `scripts/aggregate_backtest_results.py`:

```python
"""
Aggregate and rank all backtest results

Usage:
    python scripts/aggregate_backtest_results.py \
        --results-dir results/backtests/ \
        --output rankings.csv \
        --sort-by profit_per_trade \
        --top-n 15
"""
```

**Output CSV Format**:
```csv
rank,strategy,symbol,profit_per_trade,win_rate,sharpe,max_drawdown,trade_count,avg_hold_days
1,rsi_mean_reversion,NVDA,1.42%,72%,2.1,-8%,87,2.3
2,bollinger_reversal,AVGO,1.38%,68%,1.9,-12%,63,1.8
...
```

**Acceptance Criteria**:
- Aggregates 100+ backtest results in <30 seconds
- Ranking is accurate (sorted by primary metric)
- CSV is ready for portfolio optimizer input

---

### **PRIORITY 3: Portfolio Assembly (Week 2)**

#### **REQ-3.1: Correlation Analysis for Portfolio Diversification**
**Status**: MEDIUM - Prevents over-concentration
**Effort**: 1 day

**Purpose**: Avoid selecting 3 strategies that are highly correlated (all fail together)

**Deliverable**:
Create `scripts/correlation_analyzer.py`:

**Features**:
1. Load equity curves from top 15 ranked strategies
2. Calculate pairwise correlation matrix
3. Flag highly correlated pairs (ρ > 0.7)
4. Recommend diversified portfolio (select strategies with ρ < 0.5)

**Usage**:
```bash
python scripts/correlation_analyzer.py \
    --rankings rankings.csv \
    --top-n 15 \
    --max-correlation 0.5 \
    --output diversified_portfolio.csv
```

**Output**:
```csv
strategy,symbol,correlation_to_portfolio,allocation
rsi_mean_reversion,NVDA,0.0,33.3%
bollinger_reversal,UNH,0.32,33.3%
gap_fade,XLE,0.18,33.3%
```

**Acceptance Criteria**:
- Correlation matrix calculated correctly
- Portfolio has max pairwise correlation < 0.5
- Handles edge cases (insufficient uncorrelated strategies)

---

#### **REQ-3.2: Portfolio Allocation Optimizer**
**Status**: MEDIUM - Needed for capital allocation
**Effort**: 1 day

**Purpose**: Allocate $1000 across top 3 strategies optimally

**Deliverable**:
Enhance `scripts/portfolio_optimizer.py` with new allocation method:

```python
--method risk_parity_profit_weighted
```

**Allocation Formula**:
```python
# Traditional risk parity: allocate inversely to volatility
# Enhancement: weight by profit_per_trade

def risk_parity_profit_weighted(strategies):
    """
    Allocate capital based on:
    - Inverse volatility (less capital to volatile strategies)
    - Profit per trade (more capital to profitable strategies)

    Formula:
        weight_i = (profit_per_trade_i / volatility_i) / sum(profit/vol for all)
    """
    weights = []
    for strategy in strategies:
        profit = strategy.profit_per_trade
        vol = strategy.volatility  # std dev of returns

        score = profit / vol  # Sharpe-like but using profit per trade
        weights.append(score)

    # Normalize to sum to 1.0
    total = sum(weights)
    normalized_weights = [w/total for w in weights]

    return normalized_weights
```

**Constraints**:
- Max 3 strategies (per risk management rules)
- Min allocation per strategy: $250 (avoid tiny positions)
- Max allocation per strategy: $400 (avoid over-concentration)
- Must respect correlation limits (from REQ-3.1)

**Acceptance Criteria**:
- Generates allocation that sums to $1000
- Respects all constraints
- Includes expected portfolio metrics (expected return, Sharpe, max DD)

---

### **PRIORITY 4: Live Trading Preparation (Week 2)**

#### **REQ-4.1: Risk Management Validator**
**Status**: HIGH - Critical for live deployment
**Effort**: 1 day

**Purpose**: Prevent catastrophic losses by enforcing risk limits BEFORE live deployment

**Deliverable**:
Create `scripts/risk_validator.py`:

**Validation Checks**:
1. **Position Size Validation**:
   - Ensure no position >$400 (40% of capital)
   - Ensure stop loss ≤1% per position
   - Ensure total exposure ≤$1000

2. **Drawdown Monitoring**:
   - Real-time portfolio equity tracking
   - Alert at 1% drawdown
   - Auto-liquidate at 2% drawdown

3. **Correlation Check**:
   - Monitor live position correlations
   - Alert if correlation >0.7 between active positions

4. **Trade Frequency Check**:
   - Ensure not over-trading (max 3 trades/day per strategy)
   - Prevent revenge trading after losses

**Usage**:
```bash
# Run before live deployment
python scripts/risk_validator.py \
    --strategies portfolio_allocation.csv \
    --capital 1000 \
    --max-drawdown 2.0 \
    --output validation_report.txt
```

**Output**:
```
RISK VALIDATION REPORT
======================
✅ Position sizing: PASS (max position $350)
✅ Stop losses: PASS (all ≤1%)
✅ Drawdown limit: PASS (max historical DD 1.8%)
⚠️  Correlation: WARNING (NVDA-GOOGL correlation 0.72)
✅ Trade frequency: PASS (avg 2.1 trades/day)

RECOMMENDATION: APPROVED for paper trading
ACTION REQUIRED: Monitor NVDA-GOOGL correlation in live trading
```

**Acceptance Criteria**:
- All risk checks implemented correctly
- Generates clear pass/fail report
- Blocks deployment if critical risks detected

---

#### **REQ-4.2: Paper Trading Dashboard**
**Status**: MEDIUM - Helpful for validation
**Effort**: 1 day

**Purpose**: Monitor live paper trading performance vs backtest expectations

**Deliverable**:
Add new tab to Streamlit dashboard (`monitoring/app.py`):

**Tab Name**: "📊 Live vs Backtest Comparison"

**Features**:
1. **Performance Comparison Table**:
   - Strategy | Backtest Sharpe | Live Sharpe | Backtest Profit/Trade | Live Profit/Trade | Delta
   - Color coding: Green if live ≥ backtest, Red if live < 0.8 × backtest

2. **Equity Curve Comparison**:
   - Plot backtest equity curve (expected)
   - Overlay live equity curve (actual)
   - Show divergence zones

3. **Risk Metrics Dashboard**:
   - Current portfolio drawdown
   - Distance to 2% emergency stop
   - Current position correlations
   - Trade frequency (actual vs expected)

4. **Alerts Panel**:
   - Live divergence alerts (if live performance < 0.8 × backtest)
   - Risk limit warnings
   - Correlation breaches

**Acceptance Criteria**:
- Dashboard loads in <2 seconds
- Real-time updates (refresh every 30 seconds)
- Clear visual indicators of health (green/yellow/red)
- Export capability for performance reports

---

### **PRIORITY 5: Nice-to-Have Enhancements (Week 3+)**

#### **REQ-5.1: Intraday Data Integration**
**Status**: LOW - Improves precision but not critical
**Effort**: 2 days

**Purpose**: Enable more precise entry/exit timing using 5-minute or 15-minute bars

**Scope**: Currently all strategies use daily data. Intraday data would allow:
- Enter mean reversion trades mid-day (not just at close)
- Tighter stop losses based on intraday support/resistance
- Higher trade frequency (multiple trades per day possible)

**Defer Rationale**: Daily data is sufficient for MVP. Add later if daily strategies work well.

---

#### **REQ-5.2: Earnings Calendar Integration**
**Status**: LOW - Prevents unexpected volatility
**Effort**: 1-2 days

**Purpose**: Avoid entering trades 1-2 days before earnings (unpredictable volatility)

**Implementation**:
- Scrape earnings calendar from Yahoo Finance or IB API
- Add filter to strategies: `if days_to_earnings < 2: skip_entry`

**Defer Rationale**: Can manually avoid earnings for now. Automate later.

---

#### **REQ-5.3: Sentiment Analysis / News Integration**
**Status**: LOW - Experimental
**Effort**: 3-5 days

**Purpose**: Enhance gap fade strategy with sentiment analysis (fade gaps without fundamental catalysts)

**Defer Rationale**: Out of scope for MVP. Consider for version 2.0.

---

## 📋 DEVELOPMENT PRIORITIES SUMMARY

### **MUST HAVE (Week 1)**:
1. ✅ REQ-1.1: Mean Reversion Strategy Library (4 strategies)
2. ✅ REQ-1.2: Custom Optimization Metric (profit_per_trade)
3. ✅ REQ-1.3: VIX Data Feed Integration

### **SHOULD HAVE (Week 1-2)**:
4. ✅ REQ-2.1: Parallel Backtesting Enhancement
5. ✅ REQ-2.2: Backtest Results Aggregation
6. ✅ REQ-3.1: Correlation Analysis
7. ✅ REQ-3.2: Portfolio Allocation Optimizer

### **MUST HAVE BEFORE LIVE (Week 2)**:
8. ✅ REQ-4.1: Risk Management Validator
9. ✅ REQ-4.2: Paper Trading Dashboard

### **NICE TO HAVE (Week 3+)**:
10. ⏳ REQ-5.1: Intraday Data (defer)
11. ⏳ REQ-5.2: Earnings Calendar (defer)
12. ⏳ REQ-5.3: Sentiment Analysis (defer)

---

## 🚀 RECOMMENDED IMPLEMENTATION SEQUENCE

### **Day 1-3: Core Strategies**
- Implement REQ-1.1 (4 mean reversion strategies)
- Test each strategy manually on 1 symbol to verify logic
- Commit to repo with unit tests

### **Day 4-5: Optimization Infrastructure**
- Implement REQ-1.2 (custom metrics)
- Implement REQ-1.3 (VIX data feed)
- Test optimization on 1 strategy to verify metrics work

### **Day 6-7: Parallel Execution**
- Implement REQ-2.1 (parallel backtesting)
- Implement REQ-2.2 (results aggregation)
- Run full backtest suite: 4 strategies × 15 symbols = 60 backtests

### **Day 8-9: Portfolio Construction**
- Implement REQ-3.1 (correlation analysis)
- Implement REQ-3.2 (portfolio optimizer)
- Generate final 3-strategy portfolio allocation

### **Day 10-11: Risk & Deployment**
- Implement REQ-4.1 (risk validator)
- Implement REQ-4.2 (dashboard enhancements)
- Run validation, fix any issues

### **Day 12-14: Paper Trading**
- Deploy to paper trading
- Monitor for 3-5 days
- Compare live vs backtest performance
- Go live if validation passes

---

## 📊 SUCCESS CRITERIA

### **Technical Success**:
- [ ] All 4 mean reversion strategies implemented and tested
- [ ] Optimization finds parameter sets with >1% profit per trade
- [ ] VIX regime filtering works in backtests
- [ ] Parallel backtesting completes 60 tests in <10 minutes
- [ ] Portfolio allocation respects all constraints
- [ ] Risk validator passes all checks

### **Performance Success**:
- [ ] At least 1 strategy achieves >1% avg profit per trade in backtest
- [ ] Portfolio expected Sharpe ratio >1.5
- [ ] Portfolio max drawdown <2% in backtest
- [ ] Trade frequency 6-9 trades/week in backtest

### **Operational Success**:
- [ ] Paper trading runs for 1 week without errors
- [ ] Live performance within 20% of backtest expectations
- [ ] No risk limit breaches
- [ ] Dashboard shows green health indicators

---

## 🔗 DEPENDENCIES & ASSUMPTIONS

### **Existing Infrastructure** (Assumed Working):
- Backtrader engine running in Docker
- IB Gateway connection stable
- PostgreSQL database for trade history
- MLflow for experiment tracking
- Redis queue for parallel execution
- Streamlit dashboard framework

### **Data Availability** (Assumed Available):
- Historical daily data for all symbols (2020-present)
- IB API access for VIX data
- Sufficient data quality (no major gaps)

### **External Dependencies**:
- Interactive Brokers API stable and accessible
- No major brokerage changes during development
- $1000 capital available for deployment

---

## ❓ QUESTIONS FOR DEVELOPER

Before starting, please confirm:

1. **Timeline Feasibility**: Can you deliver REQ-1.1, 1.2, 1.3 within 5 days?
2. **Technical Constraints**: Any limitations with VIX data access via IB API?
3. **Testing Approach**: Will you write unit tests for each strategy?
4. **Communication**: Preferred method for daily progress updates?
5. **Blockers**: Any foreseen technical blockers or risks?

---

## 📞 SUPPORT & COMMUNICATION

**Director Availability**: Available for strategic decisions, not coding support
**Response Time**: Within 4 hours for urgent questions
**Progress Reports**: Daily standup (5 minutes) via text update
**Code Review**: Director will validate strategy logic, not code quality

---

## ✅ ACCEPTANCE & SIGN-OFF

**Director Sign-Off**: Approved - proceed with implementation
**Developer Acknowledgment**: [Pending]
**Start Date**: [To be confirmed by developer]
**Target Completion**: [Start date + 14 days]

---

**END OF REQUIREMENTS DOCUMENT**

*Last Updated: 2025-11-07 by Quant Director*
