# Epic 21: Strategy Ranking & Portfolio Optimizer

**Epic Description:** Build a systematic strategy ranking system and portfolio optimizer that evaluates backtest results using multi-criteria scoring, removes correlated strategies, and constructs optimal portfolios with position limits and capital constraints.

**Time Estimate:** 20 hours
**Priority:** P2 (Medium - Important for portfolio construction)
**Dependencies:** Parallel backtesting results (Epic 20), Performance metrics framework

---

## User Stories

### [ ] US-21.1: Multi-Criteria Ranking System
**As a quant researcher, I need a systematic way to rank strategies based on multiple performance metrics**

**Status:** ⏳ Pending
**Estimate:** 6 hours
**Priority:** P2

**Acceptance Criteria:**
- [ ] Scoring weights: Sharpe Ratio (40%), Consistency (20%), Drawdown control (20%), Trade frequency (10%), Capital efficiency (10%)
- [ ] Rolling 30-day returns standard deviation for consistency scoring
- [ ] Max drawdown percentage for drawdown control scoring
- [ ] Trade count per month for frequency scoring
- [ ] Return per dollar deployed for capital efficiency scoring
- [ ] Normalized scoring system (0-100 scale) for each metric

**Notes:**
- Implement as pandas-based calculation engine
- Include configurable weights via YAML config

---

### [ ] US-21.2: Correlation Analysis Engine
**As a quant researcher, I need to identify and filter out correlated strategies**

**Status:** ⏳ Pending
**Estimate:** 4 hours
**Priority:** P2

**Acceptance Criteria:**
- [ ] Returns correlation matrix calculation across all strategies
- [ ] Correlation threshold filtering (>0.7 correlation triggers removal)
- [ ] Greedy selection algorithm to maximize diversity
- [ ] Correlation heatmap visualization
- [ ] Configurable correlation threshold

**Notes:**
- Use daily returns for correlation calculation
- Implement both Pearson and Spearman correlation options

---

### [ ] US-21.3: Strategy Leaderboard Generation
**As a quant researcher, I need a ranked leaderboard of top uncorrelated strategies**

**Status:** ⏳ Pending
**Estimate:** 3 hours
**Priority:** P2

**Acceptance Criteria:**
- [ ] Top 15 uncorrelated strategies selection
- [ ] Leaderboard DataFrame with: Rank, Strategy, Symbol, Score, Sharpe, MaxDrawdown, WinRate, CorrelationCount
- [ ] CSV/JSON export functionality
- [ ] Filtering options (by symbol, strategy type, minimum score)
- [ ] Historical leaderboard tracking

**Notes:**
- Include metadata about why strategies were selected/rejected
- Support leaderboard persistence for trend analysis

---

### [ ] US-21.4: Portfolio Allocation Engine
**As a quant researcher, I need multiple portfolio construction methods**

**Status:** ⏳ Pending
**Estimate:** 5 hours
**Priority:** P2

**Acceptance Criteria:**
- [ ] Equal weight allocation method
- [ ] Volatility-adjusted allocation (inverse volatility weighting)
- [ ] Risk parity allocation method
- [ ] Capital constraint: $1000 total portfolio value
- [ ] Position limits: Maximum 3 concurrent positions
- [ ] Allocation validation and rebalancing logic

**Notes:**
- Implement as modular allocation classes
- Include transaction cost estimation in allocations

---

### [ ] US-21.5: Portfolio Analytics & Reporting
**As a quant researcher, I need detailed portfolio performance metrics and reports**

**Status:** ⏳ Pending
**Estimate:** 2 hours
**Priority:** P2

**Acceptance Criteria:**
- [ ] Expected portfolio metrics: Sharpe, Sortino, MaxDrawdown, WinRate, ProfitFactor
- [ ] Risk decomposition by strategy
- [ ] Portfolio allocation summary with weights and capital allocation
- [ ] Performance attribution analysis
- [ ] Export to CSV/JSON and visualization charts

**Notes:**
- Integrate with existing metrics framework
- Include comparison to individual strategy performance