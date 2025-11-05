# Epic 18: Symbol Discovery Engine

**Epic Description:** Build an autonomous symbol discovery system that identifies tradable opportunities using IB API scanner functionality without requiring human-provided tickers.

**Time Estimate:** 16 hours
**Priority:** P1 (High - Critical for autonomous operation)
**Dependencies:** IB Gateway integration (Epic 16), ib_insync library

---

## User Stories

### [ ] US-18.1: IB Scanner API Integration
**As a quant researcher, I need to connect to IB API scanner functionality**

**Status:** ⏳ Pending
**Estimate:** 4 hours
**Priority:** P1

**Acceptance Criteria:**
- [ ] ib_insync scanner API connection established
- [ ] Authentication and session management implemented
- [ ] Error handling for connection failures and rate limits
- [ ] Scanner subscription parameters configured

**Notes:**
- Use existing ib_connection.py as foundation
- Implement retry logic for scanner queries

---

### [ ] US-18.2: Market Data Scanner Types
**As a quant researcher, I need multiple scanner types for opportunity discovery**

**Status:** ⏳ Pending
**Estimate:** 3 hours
**Priority:** P1

**Acceptance Criteria:**
- [ ] Top % gainers/losers (daily) scanner implemented
- [ ] High volume stocks (>$1M avg daily volume) scanner implemented
- [ ] Most active contracts (stocks, ETFs, forex, futures) scanner implemented
- [ ] Volatility leaders (ATR-based filtering) scanner implemented
- [ ] Configurable scanner parameters via YAML config

**Notes:**
- Leverage IB scanner presets where available
- Custom scanner logic for ATR-based filtering

---

### [ ] US-18.3: Filtering and Validation Logic
**As a quant researcher, I need intelligent filtering of discovered symbols**

**Status:** ⏳ Pending
**Estimate:** 4 hours
**Priority:** P1

**Acceptance Criteria:**
- [ ] Minimum liquidity filter: $1M avg daily volume
- [ ] Minimum volatility filter: ATR > 0.5%
- [ ] Price range filter: $5-$500 (avoid penny stocks and extreme prices)
- [ ] Exchange filter: NYSE, NASDAQ, ARCA (ETFs)
- [ ] Real-time validation of filter criteria
- [ ] Configurable filter parameters

**Notes:**
- Implement ATR calculation using historical data
- Cache filter results for performance

---

### [ ] US-18.4: Data Output and Storage
**As a quant researcher, I need structured output of discovered symbols**

**Status:** ⏳ Pending
**Estimate:** 3 hours
**Priority:** P1

**Acceptance Criteria:**
- [ ] CSV output format with required columns: Symbol, Exchange, Sector, AvgVolume, ATR, Price, %Change
- [ ] JSON output format for API integration
- [ ] Database storage in SQLite for historical tracking
- [ ] Output validation and error handling
- [ ] Configurable output destinations

**Notes:**
- Use existing database schema or extend as needed
- Include timestamp metadata for data freshness

---

### [ ] US-18.5: Command Line Interface
**As a quant researcher, I need a CLI tool to run symbol discovery**

**Status:** ⏳ Pending
**Estimate:** 2 hours
**Priority:** P1

**Acceptance Criteria:**
- [ ] Python script: scripts/symbol_discovery.py
- [ ] Command line arguments for scanner type and filters
- [ ] Output format selection (CSV/JSON)
- [ ] Logging integration with existing system
- [ ] Help documentation and usage examples

**Notes:**
- Follow existing script patterns (run_backtest.py, download_data.py)
- Include in AGENTS.md build/test commands