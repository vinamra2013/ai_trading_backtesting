# Epic 6: Risk Management System

**Epic Description:** Implement automated risk management library integrated with LEAN algorithm for position size limits, loss limits, concurrent position limits, emergency stop capability, and risk metrics tracking.

**Architecture:** Risk Manager Library (imported and used by LEAN algorithm)

**Time Estimate:** 11 hours (reduced from 25h using library approach)
**Priority:** P0 (Critical)
**Dependencies:** Epic 5 (Live Trading Engine with LEAN)

---

## User Stories

### [X] US-6.1: Position Size Limits
**As a platform, I need position size limits**

**Status:** Complete
**Estimate:** 2 hours (reduced from 4h)
**Priority:** P0

**Acceptance Criteria:**
- [ ] RiskManager class with can_open_position() method
- [ ] Check position size before self.MarketOrder() in algorithm
- [ ] Max position size: configurable (default 10% of portfolio)
- [ ] Reject orders exceeding limit (don't place order)
- [ ] Log rejection reason to database
- [ ] Alert trader of rejection via AlertManager

**Implementation Notes:**
- RiskManager library in algorithms/live_strategy/risk_manager.py
- Called in OnData() before order placement
- Uses self.Portfolio.TotalPortfolioValue for calculations
- Configuration loaded from config/risk_config.yaml

---

### [X] US-6.2: Loss Limits
**As a platform, I need loss limits**

**Status:** Complete
**Estimate:** 3 hours (reduced from 6h)
**Priority:** P0

**Acceptance Criteria:**
- [ ] RiskManager.check_loss_limit() method
- [ ] Track starting equity at market open (OnData first call)
- [ ] Calculate daily P&L using self.Portfolio.TotalPortfolioValue
- [ ] Check loss limit on every OnData() call
- [ ] Auto-liquidate using self.Liquidate() when limit breached
- [ ] Halt trading flag to prevent new orders
- [ ] Alert trader immediately via AlertManager
- [ ] Manual override mechanism via trading_state database table

**Implementation Notes:**
- Daily loss limit: configurable (default 2%)
- Real-time tracking via OnData() (called every data tick)
- self.Liquidate() handles liquidation immediately
- trading_enabled flag prevents new orders after breach

---

### [X] US-6.3: Concurrent Position Limits
**As a platform, I need concurrent position limits**

**Status:** Complete
**Estimate:** 2 hours (reduced from 3h)
**Priority:** P0

**Acceptance Criteria:**
- [ ] RiskManager.check_concentration() method
- [ ] Count positions using len([x for x in self.Portfolio.Values if x.Invested])
- [ ] Max concurrent positions: configurable (default 5)
- [ ] Reject new entries if at limit
- [ ] Allow exits even when at limit
- [ ] Track portfolio concentration percentage

**Implementation Notes:**
- LEAN Portfolio provides easy position counting
- Check in OnData() before new entries
- Exit logic bypasses concentration check

---

### [X] US-6.4: Emergency Stop Capability
**As a platform, I need emergency stop capability**

**Status:** Complete
**Estimate:** 1 hour (reduced from 4h)
**Priority:** P0

**Acceptance Criteria:**
- [ ] Shell script: scripts/emergency_stop.sh
- [ ] Query database for all open positions
- [ ] Execute `lean live liquidate <symbol>` for each position
- [ ] Execute `lean live stop <project>` to halt algorithm
- [ ] Log emergency event to emergency_stops table
- [ ] Send critical alert via AlertManager
- [ ] Single command execution: ./scripts/emergency_stop.sh

**Implementation Notes:**
- Uses LEAN CLI commands for liquidation
- No complex Python script needed
- Reads positions from database
- Simple bash script ~50 lines

---

### [X] US-6.5: Risk Metrics Tracking
**As a platform, I need risk metrics tracking**

**Status:** Complete
**Estimate:** 3 hours (reduced from 8h - simplified for P2)
**Priority:** P2 (Medium)

**Acceptance Criteria:**
- [ ] RiskManager.calculate_metrics() method
- [ ] Portfolio heat (total exposure %)
- [ ] Basic VaR calculation (95% confidence)
- [ ] Position correlation tracking
- [ ] Leverage ratio from Portfolio
- [ ] Update metrics in OnData() or scheduled event
- [ ] Log to risk_metrics table

**Implementation Notes:**
- Simplified implementation for P2 priority
- Advanced VaR can be added later
- Uses LEAN Portfolio data for calculations
- Can schedule updates every 5 minutes if needed

---

## Epic Completion Checklist
- [ ] All user stories completed
- [ ] RiskManager library created and tested
- [ ] Position limits tested in LEAN algorithm
- [ ] Loss limits verified with paper trading
- [ ] Emergency stop script tested
- [ ] Risk metrics calculated and logged
- [ ] Integration with LEAN algorithm validated
- [ ] Documentation complete
- [ ] Epic demo completed
