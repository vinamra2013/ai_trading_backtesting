# Epic 22: Live Performance Monitor

**Epic Description:** Build a live performance monitoring system that tracks strategy performance in real-time against backtest expectations, generates alerts for underperformance, and provides strategy health scoring for portfolio rotation decisions.

**Time Estimate:** 16 hours
**Priority:** P3 (Low - Nice to have for live trading)
**Dependencies:** Live trading integration (Epic 16), Dashboard (Epic 7), MLflow experiment tracking

---

## User Stories

### [ ] US-22.1: Live Performance Data Collection
**As a trader, I need real-time performance data collection from live trading**

**Status:** ⏳ Pending
**Estimate:** 4 hours
**Priority:** P3

**Acceptance Criteria:**
- [ ] P&L tracking: Daily cumulative returns from IB account
- [ ] Trade logging: Individual trade records with entry/exit prices and timestamps
- [ ] Position monitoring: Current positions and unrealized P&L
- [ ] Commission tracking: Real trading costs vs backtest assumptions
- [ ] Data persistence: SQLite storage with historical performance data

**Notes:**
- Integrate with existing IB connection (scripts/ib_connection.py)
- Include both realized and unrealized P&L tracking

---

### [ ] US-22.2: Backtest vs Live Comparison Engine
**As a trader, I need daily comparison between live performance and backtest expectations**

**Status:** ⏳ Pending
**Estimate:** 4 hours
**Priority:** P3

**Acceptance Criteria:**
- [ ] Expected metrics retrieval from MLflow experiments
- [ ] Daily performance comparison: Live vs backtest Sharpe, returns, drawdown
- [ ] Rolling window analysis: 30-day, 90-day performance windows
- [ ] Statistical significance testing of performance differences
- [ ] Performance degradation calculation (% difference from expectations)

**Notes:**
- Compare on same time periods and market conditions
- Include confidence intervals for backtest expectations

---

### [ ] US-22.3: Alerting System
**As a trader, I need automated alerts for strategy underperformance**

**Status:** ⏳ Pending
**Estimate:** 4 hours
**Priority:** P3

**Acceptance Criteria:**
- [ ] Underperformance alert: Strategy returns >20% below backtest expectations
- [ ] Drawdown alert: Current drawdown exceeds 75% of historical maximum
- [ ] Win rate alert: Live win rate >15% below backtest win rate
- [ ] Alert channels: Email, dashboard notifications, log files
- [ ] Configurable alert thresholds and time windows

**Notes:**
- Implement hysteresis to prevent alert spam
- Include alert history and resolution tracking

---

### [ ] US-22.4: Strategy Health Scoring
**As a trader, I need a quantitative health score for each strategy**

**Status:** ⏳ Pending
**Estimate:** 2 hours
**Priority:** P3

**Acceptance Criteria:**
- [ ] Multi-factor health score: Performance vs expectations (40%), Drawdown control (30%), Win rate consistency (20%), Trade frequency (10%)
- [ ] Score range: 0-100 (100 = perfect health)
- [ ] Rolling score calculation: Updated daily with 30-day lookback
- [ ] Health score persistence and historical tracking

**Notes:**
- Weight factors based on importance to overall strategy success
- Include score trend analysis (improving/declining)

---

### [ ] US-22.5: Dashboard Integration
**As a trader, I need strategy health monitoring in the dashboard**

**Status:** ⏳ Pending
**Estimate:** 2 hours
**Priority:** P3

**Acceptance Criteria:**
- [ ] New dashboard tab: "Strategy Health Monitor"
- [ ] Real-time health scores for all active strategies
- [ ] Performance comparison charts: Live vs backtest
- [ ] Alert status display with timestamps
- [ ] Strategy rotation recommendations based on health scores

**Notes:**
- Integrate with existing Streamlit dashboard
- Include drill-down capability for detailed strategy analysis