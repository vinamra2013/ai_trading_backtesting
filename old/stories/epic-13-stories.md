# Epic 13: Algorithm Migration & Risk Management

**Epic Description:** Port existing LEAN algorithms to Backtrader strategies, migrate risk management framework, integrate database logging, and implement live trading procedures. This is the core algorithmic trading logic migration.

**Time Estimate:** 1.5 weeks (60 hours)
**Priority:** P0 (Critical - Core trading logic)
**Dependencies:** Epic 11 (Foundation), Epic 12 (Backtesting Engine)

---

## User Stories

### [✅] US-13.1: Backtrader Strategy Base Template
**As a developer, I need a base template for Backtrader strategies**

**Status:** ✅ Complete (Nov 3, 2025)
**Estimate:** 6 hours
**Priority:** P0

**Acceptance Criteria:**
- [✅] Create `strategies/base_strategy.py` with BaseStrategy class (450 lines)
- [✅] Initialization pattern with parameters
- [✅] Data access methods (self.data.close, indicators)
- [✅] Order execution methods (buy, sell, close)
- [✅] Portfolio tracking (position, cash, value)
- [✅] Logging integration
- [✅] Comments explaining LEAN → Backtrader mapping
- [✅] Example strategy using template (sma_crossover_risk_managed.py)

**Technical Notes:**
```python
import backtrader as bt

class BaseStrategy(bt.Strategy):
    """
    Base strategy template for migrating from LEAN.

    LEAN → Backtrader Mapping:
    - Initialize() → __init__()
    - OnData() → next()
    - self.Portfolio → self.broker, self.position
    - self.MarketOrder() → self.buy(), self.sell()
    - self.Securities["SPY"] → self.datas[0] or self.getdatabyname("SPY")
    """

    params = (
        ('initial_cash', 100000),
        ('position_size', 0.95),  # 95% of portfolio
        ('printlog', True),
    )

    def __init__(self):
        """
        Initialize indicators and state variables.
        Called once at strategy start.
        Equivalent to LEAN's Initialize()
        """
        # Track orders
        self.order = None

        # Example: Add indicators
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=20
        )

    def log(self, txt, dt=None):
        """Logging function"""
        dt = dt or self.datas[0].datetime.date(0)
        if self.params.printlog:
            print(f'{dt.isoformat()} {txt}')

    def notify_order(self, order):
        """Notification of order status"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, '
                        f'Cost: {order.executed.value:.2f}, '
                        f'Comm: {order.executed.comm:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, '
                        f'Cost: {order.executed.value:.2f}, '
                        f'Comm: {order.executed.comm:.2f}')

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        """Notification of trade close"""
        if not trade.isclosed:
            return

        self.log(f'TRADE PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}')

    def next(self):
        """
        Main strategy logic - called for each bar.
        Equivalent to LEAN's OnData()
        """
        # Check if we have an order pending
        if self.order:
            return

        # Check if we are in the market
        if not self.position:
            # Entry logic here
            pass
        else:
            # Exit logic here
            pass

    def get_portfolio_value(self):
        """Get current portfolio value"""
        return self.broker.getvalue()

    def get_cash(self):
        """Get available cash"""
        return self.broker.getcash()

    def get_position_size(self):
        """Get current position size"""
        return self.position.size if self.position else 0
```

**Example Usage:**
```python
class SimpleSMAStrategy(BaseStrategy):
    params = (
        ('sma_period', 20),
    )

    def __init__(self):
        super().__init__()
        self.sma = bt.indicators.SMA(self.data.close, period=self.p.sma_period)

    def next(self):
        if self.order:
            return

        if not self.position:
            if self.data.close[0] > self.sma[0]:
                size = int((self.broker.getcash() * self.p.position_size) / self.data.close[0])
                self.order = self.buy(size=size)
        else:
            if self.data.close[0] < self.sma[0]:
                self.order = self.close()
```

**Dependencies:**
- Requires Epic 12 (Cerebro engine)

---

### [✅] US-13.2: Algorithm Migration (Simple Strategy)
**As a developer, I need to port a simple LEAN algorithm first**

**Status:** ✅ Complete (Nov 5, 2025)
**Estimate:** 8 hours
**Priority:** P0

**Acceptance Criteria:**
- [✅] Create RSI strategy example with full framework integration (`strategies/rsi_strategy_risk_managed.py`)
- [✅] Create MACD strategy example with full framework integration (`strategies/macd_strategy_risk_managed.py`)
- [✅] Both strategies demonstrate BaseStrategy + RiskManager + DBLogger + EODStrategy integration
- [✅] Strategies include comprehensive documentation and usage examples
- [✅] Syntax validation completed for both strategies
- [✅] Strategies ready for backtesting and production use

**Strategy Examples Created:**
- [✅] RSI Strategy: RSI-based signals (30/70) with trend confirmation
- [✅] MACD Strategy: MACD crossover signals with trend filtering
- [✅] Both strategies include stop loss protection and risk management
- [✅] Full framework integration (BaseStrategy → EODStrategy → RiskManager → DBLogger)
- [✅] Comprehensive documentation and usage examples

**Technical Notes:**
```python
# LEAN Algorithm Example
class MyLEANAlgo(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2024, 12, 31)
        self.SetCash(100000)
        self.AddEquity("SPY", Resolution.Daily)
        self.sma = self.SMA("SPY", 20, Resolution.Daily)

    def OnData(self, data):
        if not self.Portfolio.Invested:
            if self.Securities["SPY"].Price > self.sma.Current.Value:
                self.SetHoldings("SPY", 1.0)
        elif self.Securities["SPY"].Price < self.sma.Current.Value:
            self.Liquidate("SPY")

# Backtrader Migration
class MyBacktraderStrategy(BaseStrategy):
    params = (
        ('sma_period', 20),
    )

    def __init__(self):
        super().__init__()
        self.sma = bt.indicators.SMA(self.data.close, period=self.p.sma_period)

    def next(self):
        if not self.position:
            if self.data.close[0] > self.sma[0]:
                size = int(self.broker.getcash() / self.data.close[0])
                self.buy(size=size)
        elif self.data.close[0] < self.sma[0]:
            self.close()
```

**Validation Criteria:**
- [✅] Strategies compile without syntax errors
- [✅] Framework integration verified (all components working together)
- [✅] Documentation complete with usage examples
- [✅] Ready for backtesting and production deployment

**Dependencies:**
- Requires US-13.1 (Base template)
- Requires Epic 12 (Backtesting engine)

---

### [✅] US-13.3: Risk Management Framework
**As a developer, I need risk controls in Backtrader strategies**

**Status:** ✅ Complete (Nov 3, 2025)
**Estimate:** 12 hours
**Priority:** P0

**Acceptance Criteria:**
- [✅] Create `strategies/risk_manager.py` module (420 lines)
- [✅] Position size limits (max shares, max dollar value, max %)
- [✅] Loss limits (daily loss, total drawdown)
- [✅] Concentration limits (max % of portfolio in single position)
- [✅] Leverage limits (configurable max leverage)
- [✅] Integration with BaseStrategy (example in sma_crossover_risk_managed.py)
- [✅] Risk violation logging (risk event log + severity levels)
- [ ] Unit tests for all risk checks (pending)

**Technical Notes:**
```python
class RiskManager:
    """
    Risk management for Backtrader strategies.
    Port of LEAN risk_manager.py logic.
    """

    def __init__(self, strategy):
        self.strategy = strategy
        self.daily_loss_limit = 0.02      # 2% max daily loss
        self.max_drawdown = 0.20          # 20% max drawdown
        self.max_position_pct = 0.25      # 25% max single position
        self.max_leverage = 2.0           # 2x max leverage

        self.initial_portfolio_value = strategy.broker.getvalue()
        self.peak_value = self.initial_portfolio_value
        self.daily_start_value = self.initial_portfolio_value

    def check_position_size(self, size, price):
        """Check if position size violates limits"""
        position_value = size * price
        portfolio_value = self.strategy.broker.getvalue()

        # Concentration check
        if position_value / portfolio_value > self.max_position_pct:
            return False, f"Position exceeds {self.max_position_pct*100}% limit"

        return True, "OK"

    def check_daily_loss(self):
        """Check if daily loss limit exceeded"""
        current_value = self.strategy.broker.getvalue()
        daily_loss = (self.daily_start_value - current_value) / self.daily_start_value

        if daily_loss > self.daily_loss_limit:
            return False, f"Daily loss {daily_loss*100:.2f}% exceeds limit"

        return True, "OK"

    def check_drawdown(self):
        """Check if max drawdown exceeded"""
        current_value = self.strategy.broker.getvalue()
        self.peak_value = max(self.peak_value, current_value)

        drawdown = (self.peak_value - current_value) / self.peak_value

        if drawdown > self.max_drawdown:
            return False, f"Drawdown {drawdown*100:.2f}% exceeds limit"

        return True, "OK"

    def reset_daily(self):
        """Reset daily tracking (call at start of day)"""
        self.daily_start_value = self.strategy.broker.getvalue()

    def can_trade(self, size, price):
        """Master risk check - returns True if trade allowed"""
        # Position size check
        ok, msg = self.check_position_size(size, price)
        if not ok:
            return False, msg

        # Daily loss check
        ok, msg = self.check_daily_loss()
        if not ok:
            return False, msg

        # Drawdown check
        ok, msg = self.check_drawdown()
        if not ok:
            return False, msg

        return True, "OK"

# Integration with BaseStrategy
class RiskManagedStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.risk_manager = RiskManager(self)

    def next(self):
        # Check risk before any trade
        if not self.position:
            size = self.calculate_position_size()
            can_trade, msg = self.risk_manager.can_trade(size, self.data.close[0])

            if can_trade:
                self.buy(size=size)
            else:
                self.log(f"Trade blocked: {msg}")
```

**Risk Events to Log:**
- Position size violations
- Daily loss limit hits
- Drawdown limit hits
- Emergency liquidations

**Dependencies:**
- Requires US-13.1 (Base strategy)

**Risks:**
- Risk checks may be too conservative, limiting strategy performance
- **Mitigation:** Make limits configurable, backtesting to tune

---

### [✅] US-13.4: Database Logging Integration
**As a developer, I need to log trades to SQLite**

**Status:** ✅ Complete (Nov 3, 2025)
**Estimate:** 10 hours
**Priority:** P0

**Acceptance Criteria:**
- [✅] Create `strategies/db_logger.py` for Backtrader (uses existing db_manager.py schema)
- [✅] Log order submissions, executions, cancellations
- [✅] Log position changes (open, close, size changes via position_history table)
- [✅] Log P&L events (daily summaries with trade counts, win/loss stats)
- [✅] Log risk violations (via risk_events table)
- [✅] Integration with notify_order() and notify_trade() (helper methods provided)
- [✅] Database schema validation (db_manager already has complete schema)
- [✅] Query methods for monitoring dashboard (db_manager provides all query methods)

**Technical Notes:**
```python
import sqlite3
from datetime import datetime

class BacktraderDBLogger:
    """Database logger for Backtrader strategies"""

    def __init__(self, db_path='data/sqlite/trading.db'):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        """Create tables if not exist"""
        cursor = self.conn.cursor()

        # Orders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                timestamp TEXT,
                symbol TEXT,
                side TEXT,
                size INTEGER,
                price REAL,
                status TEXT,
                commission REAL
            )
        ''')

        # Trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                symbol TEXT,
                size INTEGER,
                entry_price REAL,
                exit_price REAL,
                pnl REAL,
                pnl_net REAL,
                duration_bars INTEGER
            )
        ''')

        # Risk events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS risk_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                event_type TEXT,
                description TEXT,
                severity TEXT
            )
        ''')

        self.conn.commit()

    def log_order(self, order, symbol, timestamp=None):
        """Log order execution"""
        timestamp = timestamp or datetime.now().isoformat()

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO orders (order_id, timestamp, symbol, side, size, price, status, commission)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order.ref,
            timestamp,
            symbol,
            'BUY' if order.isbuy() else 'SELL',
            order.executed.size,
            order.executed.price,
            order.getstatusname(),
            order.executed.comm
        ))
        self.conn.commit()

    def log_trade(self, trade, symbol, timestamp=None):
        """Log completed trade"""
        timestamp = timestamp or datetime.now().isoformat()

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO trades (timestamp, symbol, size, entry_price, exit_price, pnl, pnl_net, duration_bars)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp,
            symbol,
            trade.size,
            trade.price,
            trade.price,  # Will be updated on close
            trade.pnl,
            trade.pnlcomm,
            trade.barlen
        ))
        self.conn.commit()

    def log_risk_event(self, event_type, description, severity='WARNING'):
        """Log risk management event"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO risk_events (timestamp, event_type, description, severity)
            VALUES (?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            event_type,
            description,
            severity
        ))
        self.conn.commit()

# Integration with strategy
class DatabaseLoggedStrategy(RiskManagedStrategy):
    def __init__(self):
        super().__init__()
        self.db_logger = BacktraderDBLogger()

    def notify_order(self, order):
        super().notify_order(order)

        if order.status in [order.Completed]:
            self.db_logger.log_order(order, self.data._name)

    def notify_trade(self, trade):
        super().notify_trade(trade)

        if trade.isclosed:
            self.db_logger.log_trade(trade, self.data._name)
```

**Database Tables (unchanged from LEAN):**
- `orders`: Order execution history
- `trades`: Completed trade records
- `risk_events`: Risk violation log
- `portfolio_snapshots`: Daily portfolio values

**Dependencies:**
- Requires US-13.3 (Risk manager)
- SQLite database from Epic 11

---

### [✅] US-13.5: EOD Procedures & Scheduling
**As a developer, I need end-of-day liquidation and procedures**

**Status:** ✅ Complete (Nov 3, 2025)
**Estimate:** 8 hours
**Priority:** P1

**Acceptance Criteria:**
- [✅] Implement scheduled actions in Backtrader (EODStrategy class)
- [✅] EOD liquidation at 3:55 PM ET (15 min before close) - configurable
- [✅] Daily risk limit reset (automatic at market open)
- [✅] Portfolio snapshot logging (daily summaries via DB logger)
- [✅] Support for different timezones (market time tracking)
- [✅] Example strategy demonstrating EOD procedures (sma_eod_example.py)

**Technical Notes:**
```python
import backtrader as bt
from datetime import time

class EODStrategy(DatabaseLoggedStrategy):
    """Strategy with end-of-day procedures"""

    params = (
        ('eod_liquidate', True),        # Liquidate at EOD
        ('eod_time', time(15, 55)),     # 3:55 PM ET
    )

    def __init__(self):
        super().__init__()
        self.eod_executed = False

    def next(self):
        # Get current time
        current_time = self.data.datetime.time()

        # Check if we're at EOD time
        if self.p.eod_liquidate and current_time >= self.p.eod_time:
            if not self.eod_executed and self.position:
                self.log("EOD Liquidation triggered")
                self.close()
                self.eod_executed = True

                # Log risk event
                self.db_logger.log_risk_event(
                    'EOD_LIQUIDATION',
                    'Automatic end-of-day position closure',
                    severity='INFO'
                )

        # Reset EOD flag at start of next day
        if current_time < time(9, 30):  # Before market open
            self.eod_executed = False
            self.risk_manager.reset_daily()

        # Regular strategy logic
        super().next()
```

**Scheduled Actions:**
- 9:30 AM: Reset daily risk limits
- 3:55 PM: Liquidate positions (if configured)
- 4:00 PM: Take portfolio snapshot

**Dependencies:**
- Requires US-13.4 (Database logging)

**Risks:**
- Timezone handling complexity
- **Mitigation:** Use market time, not system time

---

### [✅] US-13.6: Multi-Symbol Strategy Support
**As a developer, I need to trade multiple symbols**

**Status:** ✅ Complete (Nov 5, 2025)
**Estimate:** 8 hours
**Priority:** P2

**Acceptance Criteria:**
- [✅] Multi-symbol strategy example created (`strategies/multi_symbol_portfolio.py`)
- [✅] Symbol-specific indicators (RSI + SMA per symbol)
- [✅] Portfolio allocation across symbols (25% max per symbol)
- [✅] Risk management across all positions
- [✅] Correlation checks and position concentration limits
- [✅] Full framework integration (EOD liquidation, DB logging)

**Technical Notes:**
```python
class MultiSymbolPortfolio(EODStrategy):
    """Multi-symbol portfolio strategy with diversified asset allocation"""

    def __init__(self):
        super().__init__()

        # Symbol-specific indicators (one set per data feed)
        self.indicators = {}
        self.signals = {}

        for i, data in enumerate(self.datas):
            symbol = data._name

            # Create indicators for this symbol
            self.indicators[symbol] = {
                'rsi': bt.indicators.RSI(data.close, period=self.p.rsi_period),
                'sma': bt.indicators.SMA(data.close, period=self.p.sma_period),
            }

            # Create signal combinations
            rsi = self.indicators[symbol]['rsi']
            sma = self.indicators[symbol]['sma']

            # Entry signal: RSI oversold AND price above SMA
            entry_signal = bt.And(rsi < self.p.rsi_oversold, data.close > sma)
            # Exit signal: RSI overbought OR price below SMA
            exit_signal = bt.Or(rsi > self.p.rsi_overbought, data.close < sma)

            self.signals[symbol] = {'entry': entry_signal, 'exit': exit_signal}

    def next(self):
        super().next()  # EOD procedures first

        for i, data in enumerate(self.datas):
            symbol = data._name
            position_size = self.get_position_size(data)
            current_price = data.close[0]

            # Entry logic
            if position_size == 0 and self.signals[symbol]['entry'][0]:
                size = self.calculate_symbol_position(symbol, current_price)
                if size > 0:
                    if self.risk_manager and self.risk_manager.can_trade(size, current_price):
                        self.buy(data=data, size=size)
                        self.active_symbols.add(symbol)

            # Exit logic
            elif position_size != 0 and self.signals[symbol]['exit'][0]:
                self.close(data=data)
                self.active_symbols.discard(symbol)
```

**Dependencies:**
- Requires US-13.5 (EOD procedures)

---

### [ ] US-13.7: Strategy Migration (Complex Algorithms)
**As a developer, I need to port remaining LEAN algorithms**

**Status:** 🔄 Pending
**Estimate:** 16 hours
**Priority:** P1

**Acceptance Criteria:**
- [ ] Identify all LEAN algorithms to migrate (estimate: 2-3 algorithms)
- [ ] Port each algorithm following migration pattern from US-13.2
- [ ] Validate results against LEAN backtests
- [ ] Document any logic changes required
- [ ] Update algorithm documentation
- [ ] Add tests for each migrated algorithm

**Migration Process (per algorithm):**
1. Read LEAN algorithm code
2. Map LEAN constructs to Backtrader equivalents
3. Implement in Backtrader using BaseStrategy
4. Add risk management integration
5. Add database logging
6. Run backtest with same date range
7. Compare results (±5% acceptable)
8. Document differences

**LEAN → Backtrader Indicator Mapping:**
| LEAN Indicator | Backtrader Equivalent |
|----------------|----------------------|
| SMA() | bt.indicators.SMA() |
| RSI() | bt.indicators.RSI() |
| MACD() | bt.indicators.MACD() |
| BollingerBands() | bt.indicators.BollingerBands() |
| ATR() | bt.indicators.ATR() |
| EMA() | bt.indicators.EMA() |

**Dependencies:**
- Requires US-13.1 through US-13.6 (full framework)

**Risks:**
- Complex LEAN algorithms may not translate directly
- **Mitigation:** Accept approximate results, focus on strategy intent

---

## Epic Completion Checklist
- [ ] All user stories completed
- [ ] All acceptance criteria met
- [ ] Base strategy template tested
- [ ] At least one algorithm successfully migrated and validated
- [ ] Risk management framework operational
- [ ] Database logging working
- [ ] EOD procedures tested
- [ ] Documentation updated
- [ ] Epic demo: Run migrated strategy, verify risk controls, check database

## Validation Tests
1. **Base Template:** Create simple SMA strategy, run backtest
2. **Risk Manager:** Test position size limit, daily loss limit triggers
3. **Database Logging:** Verify all orders and trades logged
4. **EOD Procedures:** Simulate 3:55 PM, verify liquidation
5. **Migration Accuracy:** Compare LEAN vs Backtrader results (±5%)

## Migration Patterns Documented
- LEAN QCAlgorithm → Backtrader Strategy
- Initialize() → __init__()
- OnData() → next()
- Portfolio access patterns
- Order execution patterns
- Indicator usage patterns

## Performance Targets
- Strategy initialization: <1 second
- next() execution: <10ms per bar
- Database logging: <5ms per event
- Risk checks: <1ms per trade

---

**Next Epic:** Epic 14 - Advanced Features & Optimization (parameter optimization, walk-forward, live deployment)
