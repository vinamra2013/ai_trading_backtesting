# Epic 5: Live Trading Engine

**Epic Description:** Build production-ready live trading engine using LEAN's native capabilities for order management, position tracking, and end-of-day procedures for paper/live trading.

**Architecture:** LEAN-Native (using QuantConnect LEAN engine for all live trading operations)

**Time Estimate:** 9 hours (reduced from 24h using LEAN-native approach)
**Priority:** P0 (Critical)
**Dependencies:** Epic 1 (Dev Environment), Epic 2 (IB Integration), Epic 3 (Data), Epic 4 (Backtesting)

---

## User Stories

### [X] US-5.1: Live Algorithm Execution
**As a platform, I need to run algorithms live**

**Status:** Complete
**Estimate:** 3 hours (reduced from 6h)
**Priority:** P0

**Acceptance Criteria:**
- [ ] Create LEAN algorithm in algorithms/live_strategy/
- [ ] Implement Initialize() with security setup
- [ ] Configure IB live/paper account via LEAN
- [ ] Create deployment script wrapping `lean live deploy`
- [ ] Implement comprehensive logging in algorithm

**Implementation Notes:**
- Uses `lean live deploy` command with IB credentials
- Algorithm file: `algorithms/live_strategy/main.py`
- Deployment script: `scripts/start_live_trading.sh`
- LEAN handles IB Gateway connection internally

---

### [X] US-5.2: Live Order Management
**As a platform, I need live order management**

**Status:** Complete
**Estimate:** 2 hours (reduced from 8h - LEAN handles this)
**Priority:** P0

**Acceptance Criteria:**
- [ ] Use LEAN's self.MarketOrder() for order placement
- [ ] Use LEAN's self.LimitOrder() for limit orders
- [ ] Implement OnOrderEvent() callback for order tracking
- [ ] Log orders to database via db_logger
- [ ] LEAN handles order queuing, status tracking, retries automatically

**Implementation Notes:**
- LEAN's order system handles all order management internally
- We only need to call order methods and log results
- No custom order queue or retry logic needed
- Order status tracking via OnOrderEvent() callback

---

### [X] US-5.3: Position Tracking
**As a platform, I need position tracking**

**Status:** Complete
**Estimate:** 2 hours (reduced from 6h - LEAN provides Portfolio)
**Priority:** P0

**Acceptance Criteria:**
- [ ] Use LEAN's self.Portfolio for position access
- [ ] Log position changes to database
- [ ] Access unrealized P&L via self.Portfolio.TotalUnrealizedProfit
- [ ] Access realized P&L via self.Portfolio.TotalProfit
- [ ] LEAN handles position reconciliation with IB automatically

**Implementation Notes:**
- LEAN's Portfolio object provides all position tracking
- Cost basis calculated automatically by LEAN
- No manual reconciliation needed - LEAN syncs with IB
- We only log to database for monitoring dashboard

---

### [X] US-5.4: End-of-Day Procedures
**As a platform, I need end-of-day procedures**

**Status:** Complete
**Estimate:** 2 hours (reduced from 4h)
**Priority:** P0

**Acceptance Criteria:**
- [ ] Use self.Schedule.On() to schedule 3:55 PM liquidation
- [ ] Implement LiquidateBeforeClose() method
- [ ] Use self.Liquidate() to close all positions
- [ ] Log daily P&L via OnEndOfDay() callback
- [ ] Generate daily summary in database

**Implementation Notes:**
- LEAN's scheduling system: self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.At(15, 55))
- self.Liquidate() closes all positions instantly
- OnEndOfDay() fires at market close for daily logging
- No separate EOD script needed - built into algorithm

---

## Epic Completion Checklist
- [ ] LEAN algorithm created with trading logic
- [ ] Risk manager library integrated
- [ ] Database logging implemented
- [ ] Deployment scripts created
- [ ] Live trading tested in paper mode via `lean live deploy`
- [ ] Order placement verified through LEAN
- [ ] Position tracking via LEAN Portfolio validated
- [ ] End-of-day procedures tested (scheduled liquidation)
- [ ] Documentation complete
- [ ] Epic demo completed with LEAN
