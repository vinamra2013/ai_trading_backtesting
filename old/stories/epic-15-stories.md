# Epic 15: Testing & Validation

**Epic Description:** Comprehensive testing and validation of the Backtrader migration including parallel paper trading comparison with LEAN, integration testing, performance benchmarking, and results verification. This epic ensures migration accuracy and production readiness.

**Time Estimate:** 1 week (40 hours)
**Priority:** P0 (Critical - Migration validation)
**Dependencies:** Epic 11-14 (All previous epics)

---

## User Stories

### [ ] US-15.1: Unit Test Suite for Backtrader Components
**As a developer, I need comprehensive unit tests**

**Status:** 🔄 Pending
**Estimate:** 10 hours
**Priority:** P0

**Acceptance Criteria:**
- [ ] Unit tests for CerebroEngine (initialization, data loading)
- [ ] Unit tests for commission schemes (IB Standard, IB Pro)
- [ ] Unit tests for analyzers (Sharpe, DrawDown, Returns)
- [ ] Unit tests for RiskManager (all limit checks)
- [ ] Unit tests for DatabaseLogger (all logging methods)
- [ ] Unit tests for data pipeline (download, validation)
- [ ] Code coverage >80% for critical components
- [ ] Tests run in CI pipeline

**Technical Notes:**
```python
# tests/unit/test_commission.py
import unittest
import backtrader as bt
from scripts.commission_schemes import IBCommissionStandard, IBCommissionPro

class TestIBCommission(unittest.TestCase):

    def test_standard_minimum_commission(self):
        """Test $1.00 minimum on small orders"""
        comm = IBCommissionStandard()

        # 100 shares @ $10 = $1000 value
        # Commission: 100 * $0.005 = $0.50, but minimum is $1.00
        commission = comm._getcommission(100, 10.0, None)

        self.assertEqual(commission, 1.00)

    def test_standard_regular_commission(self):
        """Test regular commission calculation"""
        comm = IBCommissionStandard()

        # 1000 shares @ $10 = $10000 value
        # Commission: 1000 * $0.005 = $5.00
        commission = comm._getcommission(1000, 10.0, None)

        self.assertEqual(commission, 5.00)

    def test_standard_sec_fees_on_sell(self):
        """Test SEC fee calculation on sell orders"""
        comm = IBCommissionStandard()

        # Sell 1000 shares @ $324.34
        # Commission: $5.00
        # SEC fee: 1000 * 324.34 * 0.0000278 = $9.01
        # Total: $14.01
        commission = comm._getcommission(-1000, 324.34, None)

        self.assertAlmostEqual(commission, 14.01, places=2)

    def test_pro_minimum_commission(self):
        """Test $0.35 minimum for Pro pricing"""
        comm = IBCommissionPro()

        commission = comm._getcommission(50, 10.0, None)

        self.assertEqual(commission, 0.35)

# tests/unit/test_risk_manager.py
class TestRiskManager(unittest.TestCase):

    def setUp(self):
        """Create mock strategy for testing"""
        self.strategy = MockStrategy()
        self.risk_manager = RiskManager(self.strategy)

    def test_position_size_limit(self):
        """Test position size limit enforcement"""
        # Try to buy position worth 30% of portfolio (exceeds 25% limit)
        portfolio_value = 100000
        size = 300
        price = 100  # $30,000 position

        self.strategy.broker.set_value(portfolio_value)

        can_trade, msg = self.risk_manager.check_position_size(size, price)

        self.assertFalse(can_trade)
        self.assertIn("exceeds", msg.lower())

    def test_daily_loss_limit(self):
        """Test daily loss limit"""
        self.strategy.broker.set_value(98000)  # 2% loss
        self.risk_manager.daily_start_value = 100000

        can_trade, msg = self.risk_manager.check_daily_loss()

        self.assertFalse(can_trade)
        self.assertIn("daily loss", msg.lower())
```

**Test Categories:**
- Commission calculations (edge cases, SEC fees)
- Risk manager (all limit types, edge cases)
- Data pipeline (CSV parsing, IB connection)
- Strategy base class (initialization, order flow)
- Database logging (CRUD operations)

**Dependencies:**
- All Epics 11-14 components

---

### [ ] US-15.2: Integration Tests
**As a developer, I need end-to-end integration tests**

**Status:** 🔄 Pending
**Estimate:** 8 hours
**Priority:** P0

**Acceptance Criteria:**
- [ ] Test full backtest workflow (data → cerebro → results)
- [ ] Test optimization workflow (grid search + results)
- [ ] Test live trading simulation (paper trading connection)
- [ ] Test database persistence (write → read → verify)
- [ ] Test monitoring dashboard (data display)
- [ ] Test emergency stop procedure
- [ ] All tests pass in Docker environment

**Technical Notes:**
```python
# tests/integration/test_backtest_workflow.py
import unittest
from datetime import datetime
from scripts.cerebro_engine import CerebroEngine
from strategies.simple_sma import SimpleSMAStrategy

class TestBacktestWorkflow(unittest.TestCase):

    def test_full_backtest_execution(self):
        """Test complete backtest from data to results"""

        # 1. Load data
        data_path = 'tests/fixtures/SPY_2020_2021.csv'
        data = bt.feeds.GenericCSVData(
            dataname=data_path,
            fromdate=datetime(2020, 1, 1),
            todate=datetime(2021, 12, 31)
        )

        # 2. Setup Cerebro
        engine = CerebroEngine(initial_cash=100000)
        engine.cerebro.adddata(data)
        engine.cerebro.addstrategy(SimpleSMAStrategy)

        # 3. Add commission
        from scripts.commission_schemes import IBCommissionStandard
        engine.cerebro.broker.addcommissioninfo(IBCommissionStandard())

        # 4. Add analyzers
        engine.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        engine.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

        # 5. Run
        results = engine.cerebro.run()

        # 6. Verify results
        self.assertIsNotNone(results)
        self.assertEqual(len(results), 1)

        strat = results[0]
        sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)

        # 7. Validate metrics are reasonable
        self.assertIsNotNone(sharpe)
        self.assertGreater(sharpe, -3)  # Not absurdly bad
        self.assertLess(sharpe, 10)     # Not absurdly good

# tests/integration/test_live_trading_simulation.py
class TestLiveTradingSimulation(unittest.TestCase):

    @unittest.skipIf(not IB_GATEWAY_AVAILABLE, "IB Gateway not running")
    def test_paper_trading_connection(self):
        """Test connection to IB paper trading"""

        from ib_insync import IB

        ib = IB()
        connected = ib.connect('ib-gateway', 4001, clientId=999)

        self.assertTrue(connected)

        # Request market data
        from ib_insync import Stock
        contract = Stock('SPY', 'SMART', 'USD')
        ticker = ib.reqMktData(contract)

        # Wait for data
        ib.sleep(2)

        self.assertIsNotNone(ticker.last)
        self.assertGreater(ticker.last, 0)

        ib.disconnect()
```

**Test Scenarios:**
1. **Complete Backtest:** Data load → execution → results
2. **Optimization:** Parameter search → best params → validation
3. **Live Trading:** Connect → subscribe data → verify updates
4. **Database:** Log trades → query → verify data
5. **Emergency Stop:** Detect positions → liquidate → verify closed

**Dependencies:**
- Requires all Epic 11-14 functionality
- Requires test fixtures (sample data)

---

### [ ] US-15.3: LEAN vs Backtrader Comparison
**As a developer, I need to verify migration accuracy**

**Status:** 🔄 Pending
**Estimate:** 12 hours
**Priority:** P0

**Acceptance Criteria:**
- [ ] Run identical strategy in both LEAN and Backtrader
- [ ] Same data, same period, same parameters
- [ ] Compare total return (within ±5%)
- [ ] Compare Sharpe ratio (within ±0.3)
- [ ] Compare max drawdown (within ±3%)
- [ ] Compare number of trades (within ±10%)
- [ ] Document all differences found
- [ ] Root cause analysis for any major deviations

**Technical Notes:**
```python
# tests/validation/test_lean_backtrader_comparison.py
import unittest
import json

class TestLEANBacktraderComparison(unittest.TestCase):

    def test_simple_sma_strategy_comparison(self):
        """
        Compare SimpleSMAStrategy results between LEAN and Backtrader

        Test Strategy:
        - Symbol: SPY
        - Period: 2020-01-01 to 2024-12-31
        - Logic: Buy when price > SMA(20), sell when price < SMA(20)
        - Initial cash: $100,000
        - Commission: IB Standard ($0.005/share, $1 min)
        """

        # 1. Run LEAN backtest (or load existing results)
        lean_results = self._run_lean_backtest()

        # 2. Run Backtrader backtest
        backtrader_results = self._run_backtrader_backtest()

        # 3. Compare metrics
        self._compare_results(lean_results, backtrader_results)

    def _run_lean_backtest(self):
        """Run LEAN backtest or load cached results"""
        # If LEAN still available, run it
        # Otherwise, load pre-migration results
        with open('tests/fixtures/lean_baseline.json') as f:
            return json.load(f)

    def _run_backtrader_backtest(self):
        """Run Backtrader backtest"""
        cerebro = bt.Cerebro()
        # ... setup and run
        # Return results in same format as LEAN

    def _compare_results(self, lean, backtrader):
        """Compare metrics with tolerance"""

        # Total Return
        lean_return = lean['total_return']
        bt_return = backtrader['total_return']
        diff_pct = abs(lean_return - bt_return) / lean_return * 100

        self.assertLess(diff_pct, 5.0,
            f"Return diff {diff_pct:.2f}% exceeds 5% tolerance")

        # Sharpe Ratio
        lean_sharpe = lean['sharpe_ratio']
        bt_sharpe = backtrader['sharpe_ratio']
        sharpe_diff = abs(lean_sharpe - bt_sharpe)

        self.assertLess(sharpe_diff, 0.3,
            f"Sharpe diff {sharpe_diff:.2f} exceeds 0.3 tolerance")

        # Max Drawdown
        lean_dd = lean['max_drawdown']
        bt_dd = backtrader['max_drawdown']
        dd_diff = abs(lean_dd - bt_dd)

        self.assertLess(dd_diff, 3.0,
            f"Drawdown diff {dd_diff:.2f}% exceeds 3% tolerance")

        # Trade Count
        lean_trades = lean['total_trades']
        bt_trades = backtrader['total_trades']
        trade_diff_pct = abs(lean_trades - bt_trades) / lean_trades * 100

        self.assertLess(trade_diff_pct, 10.0,
            f"Trade count diff {trade_diff_pct:.2f}% exceeds 10% tolerance")
```

**Comparison Report Template:**
```
LEAN vs Backtrader Comparison Report
=====================================
Strategy: SimpleSMAStrategy
Period: 2020-01-01 to 2024-12-31
Symbol: SPY

Metric              LEAN        Backtrader   Diff (%)   Status
----------------------------------------------------------------
Total Return       45.23%       44.87%       -0.80%     ✅ PASS
Sharpe Ratio        1.87         1.82        -2.67%     ✅ PASS
Max Drawdown      -12.34%      -12.89%       +4.46%     ✅ PASS
Total Trades        234          229         -2.14%     ✅ PASS
Win Rate           58.5%        57.6%        -1.54%     ✅ PASS

Overall: ✅ PASS - All metrics within tolerance
```

**Acceptance Tolerances:**
- Total Return: ±5% (absolute difference)
- Sharpe Ratio: ±0.3 (absolute difference)
- Max Drawdown: ±3% (absolute difference)
- Trade Count: ±10% (relative difference)

**Dependencies:**
- LEAN baseline results (pre-migration)
- Epic 12 (Backtest engine)
- Epic 13 (Migrated strategies)

**Risks:**
- Minor differences expected due to:
  - Floating point precision
  - Bar timestamp handling
  - Commission rounding
  - Slippage models
- **Mitigation:** Document all known sources of variance

---

### [ ] US-15.4: Parallel Paper Trading Validation
**As a developer, I need real-world validation**

**Status:** 🔄 Pending
**Estimate:** 16 hours (includes 1 week monitoring time)
**Priority:** P0

**Acceptance Criteria:**
- [ ] Deploy same strategy to both LEAN and Backtrader paper trading
- [ ] Run for 1 week minimum
- [ ] Log all orders and fills
- [ ] Compare execution prices
- [ ] Compare order timing
- [ ] Compare portfolio values daily
- [ ] Document any discrepancies
- [ ] Generate comparison report

**Technical Notes:**
```python
# scripts/parallel_paper_trading.py
import logging
from datetime import datetime

class ParallelPaperTradingValidator:
    """Run LEAN and Backtrader in parallel for validation"""

    def __init__(self, strategy_class):
        self.strategy_class = strategy_class
        self.lean_orders = []
        self.backtrader_orders = []

        # Setup logging
        logging.basicConfig(
            filename=f'logs/parallel_validation_{datetime.now():%Y%m%d}.log',
            level=logging.INFO
        )

    def start_lean(self):
        """Start LEAN paper trading"""
        # Keep LEAN running temporarily for validation
        # lean live deploy ...

    def start_backtrader(self):
        """Start Backtrader paper trading"""
        from scripts.live_trading import LiveTradingRunner

        runner = LiveTradingRunner(
            self.strategy_class,
            symbols=['SPY'],
            ib_config={'host': 'ib-gateway', 'port': 4001, 'client_id': 2}
        )
        runner.run()

    def compare_orders(self):
        """Compare orders from both systems"""
        # Query databases
        lean_orders = self._get_lean_orders()
        bt_orders = self._get_backtrader_orders()

        # Match by timestamp (within 5 seconds)
        matches = self._match_orders(lean_orders, bt_orders)

        for match in matches:
            lean_order = match['lean']
            bt_order = match['backtrader']

            # Compare
            symbol_match = lean_order['symbol'] == bt_order['symbol']
            side_match = lean_order['side'] == bt_order['side']
            size_match = abs(lean_order['size'] - bt_order['size']) / lean_order['size'] < 0.05

            price_diff = abs(lean_order['price'] - bt_order['price'])
            price_diff_pct = price_diff / lean_order['price'] * 100

            if not (symbol_match and side_match and size_match):
                logging.warning(f"Order mismatch: {lean_order} vs {bt_order}")

            if price_diff_pct > 0.1:  # >0.1% price difference
                logging.warning(f"Price diff {price_diff_pct:.2f}%")

    def daily_portfolio_comparison(self):
        """Compare portfolio values"""
        lean_value = self._get_lean_portfolio_value()
        bt_value = self._get_backtrader_portfolio_value()

        diff_pct = abs(lean_value - bt_value) / lean_value * 100

        logging.info(f"Portfolio comparison: LEAN ${lean_value:.2f}, "
                    f"Backtrader ${bt_value:.2f}, Diff {diff_pct:.3f}%")

        if diff_pct > 1.0:
            logging.error(f"Portfolio divergence exceeds 1%!")
```

**Validation Checks:**
- Order generation timing (should be within 5 seconds)
- Order parameters (symbol, side, size should match)
- Fill prices (should be within bid-ask spread)
- Portfolio value (should diverge <1% daily)
- P&L tracking (cumulative P&L should match within $100)

**Duration:** 1 week minimum, 2 weeks recommended

**Dependencies:**
- LEAN system still operational (temporary)
- Epic 14 (Live trading deployment)

---

### [ ] US-15.5: Performance Benchmarking
**As a developer, I need performance metrics**

**Status:** 🔄 Pending
**Estimate:** 6 hours
**Priority:** P1

**Acceptance Criteria:**
- [ ] Benchmark backtest execution speed (LEAN vs Backtrader)
- [ ] Benchmark memory usage during backtests
- [ ] Benchmark optimization performance (grid search)
- [ ] Benchmark live trading latency (order to fill)
- [ ] Document performance characteristics
- [ ] Identify bottlenecks if any
- [ ] Optimization recommendations

**Technical Notes:**
```python
# tests/performance/benchmark_backtest.py
import time
import psutil
import backtrader as bt

class BacktestBenchmark:

    def benchmark_execution_speed(self, data_size):
        """Measure backtest execution time"""

        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        # Run backtest
        cerebro = bt.Cerebro()
        # ... setup
        results = cerebro.run()

        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024

        return {
            'execution_time': end_time - start_time,
            'memory_delta': end_memory - start_memory,
            'bars_per_second': data_size / (end_time - start_time)
        }

    def benchmark_suite(self):
        """Run comprehensive benchmark suite"""

        results = {}

        # Test 1: Daily data, 1 year
        results['daily_1yr'] = self.benchmark_execution_speed(252)

        # Test 2: Daily data, 5 years
        results['daily_5yr'] = self.benchmark_execution_speed(1260)

        # Test 3: Minute data, 1 month
        results['minute_1mo'] = self.benchmark_execution_speed(6.5 * 60 * 20)

        return results
```

**Performance Targets:**
| Test Case | Target Speed | Target Memory |
|-----------|--------------|---------------|
| Daily, 1 year | <2 seconds | <100 MB |
| Daily, 5 years | <10 seconds | <200 MB |
| Minute, 1 month | <30 seconds | <300 MB |
| Optimization (100 trials) | <10 minutes | <500 MB |

**Dependencies:**
- Epic 12 (Backtest engine)

---

### [ ] US-15.6: Test Data Fixtures
**As a developer, I need standardized test data**

**Status:** 🔄 Pending
**Estimate:** 4 hours
**Priority:** P1

**Acceptance Criteria:**
- [ ] Create test data fixtures (SPY 2020-2024)
- [ ] Include edge cases: gaps, splits, dividends
- [ ] Create synthetic data for specific scenarios
- [ ] Document fixture characteristics
- [ ] Version control fixtures in tests/fixtures/

**Technical Notes:**
```python
# tests/fixtures/generate_fixtures.py

def create_spy_fixture():
    """Create SPY test data 2020-2024"""
    # Download real data or load from backup
    # Save to tests/fixtures/SPY_2020_2024.csv

def create_edge_case_fixtures():
    """Create synthetic data for edge cases"""

    # Fixture 1: Gap down event
    create_gap_down_data('gap_down.csv')

    # Fixture 2: Low volatility period
    create_low_vol_data('low_vol.csv')

    # Fixture 3: High volatility period
    create_high_vol_data('high_vol.csv')

    # Fixture 4: Trending market
    create_trending_data('trending.csv')

    # Fixture 5: Range-bound market
    create_ranging_data('ranging.csv')
```

**Fixtures to Create:**
- `SPY_2020_2024.csv` - Real market data
- `gap_down.csv` - -10% overnight gap
- `low_vol.csv` - Volatility <10%
- `high_vol.csv` - Volatility >30%
- `trending.csv` - Consistent uptrend
- `ranging.csv` - Sideways market

**Dependencies:**
- Data download capability (Epic 11)

---

### [ ] US-15.7: Regression Test Suite
**As a developer, I need to prevent regressions**

**Status:** 🔄 Pending
**Estimate:** 4 hours
**Priority:** P2

**Acceptance Criteria:**
- [ ] Create regression test suite
- [ ] Baseline results from migrated system
- [ ] Run on every code change
- [ ] Alert on metric degradation >10%
- [ ] Integration with CI/CD pipeline
- [ ] Automated reporting

**Technical Notes:**
```python
# tests/regression/test_regression.py

class RegressionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Load baseline results"""
        with open('tests/regression/baseline.json') as f:
            cls.baseline = json.load(f)

    def test_simple_sma_regression(self):
        """Ensure SimpleSMA performance hasn't degraded"""

        # Run current version
        current_results = self._run_simple_sma()

        # Compare to baseline
        baseline_sharpe = self.baseline['simple_sma']['sharpe']
        current_sharpe = current_results['sharpe']

        degradation = (baseline_sharpe - current_sharpe) / baseline_sharpe * 100

        self.assertLess(degradation, 10.0,
            f"Sharpe degraded by {degradation:.2f}%")
```

**Dependencies:**
- Baseline results (established after migration)
- CI/CD pipeline setup

---

## Epic Completion Checklist
- [ ] All user stories completed
- [ ] Unit test coverage >80%
- [ ] Integration tests passing
- [ ] LEAN comparison within tolerances
- [ ] Parallel paper trading completed (1 week)
- [ ] Performance benchmarks meet targets
- [ ] Test fixtures created and documented
- [ ] Regression test suite operational
- [ ] Epic demo: Run full test suite, show passing tests, display comparison report

## Validation Criteria
1. **Unit Tests:** >80% coverage, all pass
2. **Integration Tests:** All critical workflows pass
3. **LEAN Comparison:** All metrics within tolerance
4. **Paper Trading:** <1% portfolio divergence over 1 week
5. **Performance:** Meet all speed/memory targets
6. **Regression:** Baseline established, monitoring active

## Risk Assessment
- **High Risk:** LEAN comparison fails tolerance → Investigation required
- **Medium Risk:** Performance slower than expected → Optimization needed
- **Low Risk:** Minor test failures → Fix and rerun

## Success Metrics
- All automated tests pass
- Manual validation confirms accuracy
- Performance acceptable for production use
- Migration approved for production deployment

---

**Next Epic:** Epic 16 - Documentation, Cleanup & Deprecation (update all docs, remove LEAN, final cutover)
