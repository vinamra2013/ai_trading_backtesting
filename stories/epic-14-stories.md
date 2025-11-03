# Epic 14: Advanced Features & Optimization

**Epic Description:** Implement advanced trading platform features including parameter optimization, walk-forward analysis, live trading deployment, and updated Claude Skills for Backtrader. These features enable strategy development, validation, and production deployment.

**Time Estimate:** 1 week (40 hours)
**Priority:** P1 (High - Production readiness)
**Dependencies:** Epic 11 (Foundation), Epic 12 (Backtesting), Epic 13 (Algorithms)

---

## User Stories

### [ ] US-14.1: Parameter Optimization Framework
**As a developer, I need to optimize strategy parameters**

**Status:** 🔄 Pending
**Estimate:** 12 hours
**Priority:** P1

**Acceptance Criteria:**
- [ ] Rewrite `scripts/optimize_parameters.py` for Backtrader
- [ ] Grid search optimization using Cerebro.optstrategy()
- [ ] Optuna integration for Bayesian optimization
- [ ] Parameter ranges configuration
- [ ] Parallel optimization support
- [ ] Results ranking and visualization
- [ ] Export best parameters to config file
- [ ] Documentation with usage examples

**Technical Notes:**
```python
import backtrader as bt
import optuna

class ParameterOptimizer:
    """Parameter optimization for Backtrader strategies"""

    def __init__(self, strategy_class, data_feeds, param_ranges):
        self.strategy_class = strategy_class
        self.data_feeds = data_feeds
        self.param_ranges = param_ranges

    def grid_search(self):
        """Grid search optimization using Cerebro"""
        cerebro = bt.Cerebro()

        # Add data
        for data in self.data_feeds:
            cerebro.adddata(data)

        # Add optimization parameters
        cerebro.optstrategy(
            self.strategy_class,
            sma_period=range(10, 51, 5),      # [10, 15, 20, ..., 50]
            threshold=np.arange(0.01, 0.1, 0.01)
        )

        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

        # Run optimization
        results = cerebro.run()

        # Process results
        return self._rank_results(results)

    def bayesian_search(self, n_trials=100):
        """Bayesian optimization using Optuna"""

        def objective(trial):
            # Suggest parameters
            sma_period = trial.suggest_int('sma_period', 10, 50)
            threshold = trial.suggest_float('threshold', 0.01, 0.1)

            # Run backtest
            cerebro = bt.Cerebro()
            for data in self.data_feeds:
                cerebro.adddata(data)

            cerebro.addstrategy(
                self.strategy_class,
                sma_period=sma_period,
                threshold=threshold
            )

            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')

            results = cerebro.run()
            sharpe = results[0].analyzers.sharpe.get_analysis().get('sharperatio', 0)

            return sharpe if sharpe else -999

        # Run Optuna study
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials)

        return study.best_params, study.best_value

    def _rank_results(self, results):
        """Rank optimization results by Sharpe ratio"""
        ranked = []

        for result in results:
            strat = result[0]
            sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
            drawdown = strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0)
            returns = strat.analyzers.returns.get_analysis().get('rtot', 0)

            # Get parameters
            params = {}
            for key in strat.params._getkeys():
                if not key.startswith('_'):
                    params[key] = getattr(strat.params, key)

            ranked.append({
                'params': params,
                'sharpe': sharpe,
                'drawdown': drawdown,
                'returns': returns,
                'score': sharpe  # Primary ranking metric
            })

        # Sort by score descending
        ranked.sort(key=lambda x: x['score'], reverse=True)
        return ranked

# CLI usage
python scripts/optimize_parameters.py \
    --strategy strategies.my_strategy.MyStrategy \
    --symbols SPY \
    --start 2020-01-01 --end 2024-12-31 \
    --method bayesian \
    --trials 100 \
    --output results/optimization/
```

**Output Format:**
```json
{
  "optimization_id": "opt_550e8400",
  "strategy": "strategies.my_strategy.MyStrategy",
  "method": "bayesian",
  "trials": 100,
  "best_params": {
    "sma_period": 23,
    "threshold": 0.037
  },
  "best_metrics": {
    "sharpe": 1.87,
    "returns": 45.2,
    "drawdown": -12.3
  },
  "top_10_results": [...]
}
```

**Dependencies:**
- Requires Epic 12 (Cerebro engine)
- Requires Epic 13 (Strategies)

**Risks:**
- Overfitting to historical data
- **Mitigation:** Use walk-forward validation (US-14.2)

---

### [ ] US-14.2: Walk-Forward Analysis
**As a developer, I need walk-forward validation**

**Status:** 🔄 Pending
**Estimate:** 10 hours
**Priority:** P1

**Acceptance Criteria:**
- [ ] Update `scripts/walkforward.py` for Backtrader
- [ ] Configurable in-sample/out-sample split (e.g., 12/6 months)
- [ ] Rolling window walk-forward
- [ ] Anchored walk-forward
- [ ] Parameter stability analysis
- [ ] Degradation metrics calculation
- [ ] Visualization of IS vs OOS performance
- [ ] Export results with statistics

**Technical Notes:**
```python
from datetime import datetime, timedelta
import pandas as pd

class WalkForwardAnalyzer:
    """Walk-forward analysis for Backtrader strategies"""

    def __init__(self, strategy_class, data_feeds, param_ranges):
        self.strategy_class = strategy_class
        self.data_feeds = data_feeds
        self.param_ranges = param_ranges

    def rolling_walkforward(self, is_months=12, oos_months=6):
        """
        Rolling window walk-forward analysis

        Process:
        1. Optimize on in-sample period (12 months)
        2. Test on out-sample period (6 months)
        3. Roll window forward by oos_months
        4. Repeat until end of data
        """
        results = []
        current_start = self.data_feeds[0].fromdate

        while current_start < self.data_feeds[0].todate:
            # Define IS period
            is_end = current_start + timedelta(days=30*is_months)

            # Define OOS period
            oos_start = is_end + timedelta(days=1)
            oos_end = oos_start + timedelta(days=30*oos_months)

            if oos_end > self.data_feeds[0].todate:
                break

            print(f"IS: {current_start} to {is_end}")
            print(f"OOS: {oos_start} to {oos_end}")

            # Optimization on IS data
            is_data = self._filter_data(current_start, is_end)
            optimizer = ParameterOptimizer(
                self.strategy_class,
                is_data,
                self.param_ranges
            )
            best_params = optimizer.bayesian_search(n_trials=50)[0]

            # Test on OOS data
            oos_data = self._filter_data(oos_start, oos_end)
            oos_performance = self._backtest_with_params(oos_data, best_params)

            results.append({
                'is_start': current_start,
                'is_end': is_end,
                'oos_start': oos_start,
                'oos_end': oos_end,
                'best_params': best_params,
                'is_sharpe': optimizer.best_value,
                'oos_sharpe': oos_performance['sharpe'],
                'degradation': optimizer.best_value - oos_performance['sharpe']
            })

            # Roll window
            current_start = oos_start

        return self._analyze_results(results)

    def _analyze_results(self, results):
        """Analyze walk-forward results"""
        df = pd.DataFrame(results)

        analysis = {
            'avg_is_sharpe': df['is_sharpe'].mean(),
            'avg_oos_sharpe': df['oos_sharpe'].mean(),
            'avg_degradation': df['degradation'].mean(),
            'degradation_pct': (df['degradation'].mean() / df['is_sharpe'].mean()) * 100,
            'consistency': (df['oos_sharpe'] > 0).sum() / len(df),
            'parameter_stability': self._calculate_param_stability(df)
        }

        return results, analysis

    def _calculate_param_stability(self, df):
        """Calculate how stable parameters are across windows"""
        # Check variance of optimal parameters
        param_names = list(df.iloc[0]['best_params'].keys())
        stability = {}

        for param in param_names:
            values = [r['best_params'][param] for r in df.to_dict('records')]
            stability[param] = {
                'mean': np.mean(values),
                'std': np.std(values),
                'cv': np.std(values) / np.mean(values) if np.mean(values) != 0 else 0
            }

        return stability

# CLI usage
python scripts/walkforward.py \
    --strategy strategies.my_strategy.MyStrategy \
    --symbols SPY \
    --start 2020-01-01 --end 2024-12-31 \
    --is-months 12 \
    --oos-months 6 \
    --output results/walkforward/
```

**Metrics:**
- Average IS Sharpe vs OOS Sharpe
- Degradation % (IS - OOS) / IS
- Consistency (% of OOS periods profitable)
- Parameter stability (coefficient of variation)

**Dependencies:**
- Requires US-14.1 (Parameter optimization)

---

### [ ] US-14.3: Live Trading Deployment Scripts
**As a developer, I need to deploy strategies to live trading**

**Status:** 🔄 Pending
**Estimate:** 10 hours
**Priority:** P1

**Acceptance Criteria:**
- [ ] Rewrite `scripts/start_live_trading.sh` for Backtrader
- [ ] Rewrite `scripts/stop_live_trading.sh` for graceful shutdown
- [ ] Update `scripts/emergency_stop.sh` for position liquidation
- [ ] Process management (daemonize, PID file, auto-restart)
- [ ] Live data feed integration via IBStore
- [ ] Error handling and reconnection logic
- [ ] Logging to file and database
- [ ] Status monitoring endpoint

**Technical Notes:**
```python
# scripts/live_trading.py
import backtrader as bt
import logging
from datetime import datetime
import signal
import sys

class LiveTradingRunner:
    """Run Backtrader strategy in live trading mode"""

    def __init__(self, strategy_class, symbols, ib_config):
        self.strategy_class = strategy_class
        self.symbols = symbols
        self.ib_config = ib_config
        self.cerebro = None

        # Setup logging
        logging.basicConfig(
            filename='logs/live_trading.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def setup_cerebro(self):
        """Initialize Cerebro for live trading"""
        self.cerebro = bt.Cerebro()

        # Connect to IB
        ibstore = bt.stores.IBStore(
            host=self.ib_config['host'],
            port=self.ib_config['port'],
            clientId=self.ib_config['client_id']
        )

        # Set broker
        self.cerebro.broker = ibstore.getbroker()

        # Add live data feeds
        for symbol in self.symbols:
            data = ibstore.getdata(
                dataname=f'{symbol}-STK-SMART-USD',
                timeframe=bt.TimeFrame.Minutes,
                compression=1,
                rtbar=True  # Use 5-second real-time bars
            )
            self.cerebro.adddata(data, name=symbol)

        # Add strategy
        self.cerebro.addstrategy(self.strategy_class)

        logging.info(f"Cerebro configured for live trading: {self.symbols}")

    def run(self):
        """Start live trading"""
        try:
            logging.info("Starting live trading...")
            self.setup_cerebro()

            # Register signal handlers
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

            # Run (blocking call)
            self.cerebro.run()

            logging.info("Live trading ended normally")

        except Exception as e:
            logging.error(f"Live trading error: {e}", exc_info=True)
            raise

    def _signal_handler(self, sig, frame):
        """Handle shutdown signals"""
        logging.info(f"Received signal {sig}, shutting down...")
        self.stop()
        sys.exit(0)

    def stop(self):
        """Stop live trading gracefully"""
        if self.cerebro:
            # Close all positions
            logging.info("Closing all positions...")
            # Cerebro handles this automatically on stop

# scripts/start_live_trading.sh
#!/bin/bash
set -e

echo "Starting Backtrader live trading..."

# Load environment
source venv/bin/activate
source .env

# Validate IB credentials
if [ -z "$IB_USER_NAME" ] || [ -z "$IB_PASSWORD" ]; then
    echo "Error: IB credentials not found in .env"
    exit 1
fi

# Check algorithm exists
STRATEGY="strategies.live_strategy.LiveStrategy"
if [ ! -f "strategies/live_strategy.py" ]; then
    echo "Error: Strategy file not found"
    exit 1
fi

# Start live trading in background
nohup python scripts/live_trading.py \
    --strategy $STRATEGY \
    --symbols SPY \
    --ib-host ib-gateway \
    --ib-port 4001 \
    > logs/live_trading.out 2>&1 &

# Save PID
echo $! > logs/live_trading.pid

echo "Live trading started (PID: $!)"
echo "View logs: tail -f logs/live_trading.log"
```

**Emergency Stop:**
```python
# scripts/emergency_stop.py
import backtrader as bt
import logging

def emergency_liquidate():
    """Emergency liquidation of all positions"""
    logging.critical("EMERGENCY STOP TRIGGERED")

    # Connect to IB
    ibstore = bt.stores.IBStore(host='ib-gateway', port=4001, clientId=999)
    broker = ibstore.getbroker()

    # Get current positions
    positions = broker.getposition()

    # Close all positions
    for symbol, position in positions.items():
        if position.size != 0:
            logging.critical(f"Liquidating {symbol}: {position.size} shares")
            # Submit market order to close
            # (Implementation depends on Backtrader API)

    logging.critical("Emergency liquidation complete")

if __name__ == '__main__':
    emergency_liquidate()
```

**Dependencies:**
- Requires Epic 11 (IB integration)
- Requires Epic 13 (Strategies)

**Risks:**
- IB connection failures during live trading
- **Mitigation:** Auto-reconnect, alerting, circuit breakers

---

### [ ] US-14.4: Update Claude Skills for Backtrader
**As a developer, I need Claude Skills updated**

**Status:** 🔄 Pending
**Estimate:** 6 hours
**Priority:** P2

**Acceptance Criteria:**
- [ ] Update `data-manager` skill for Backtrader data pipeline
- [ ] Update `backtest-runner` skill for Cerebro execution
- [ ] Remove LEAN-specific logic
- [ ] Add Backtrader-specific workflows
- [ ] Update skill documentation
- [ ] Test skills with natural language requests

**Technical Notes:**
```markdown
# skills/data-manager.md (updated)

Download and validate market data for Backtrader using IB.

## Capabilities
- Download historical data via ib_insync
- Save in Backtrader-compatible CSV format
- Validate data quality (gaps, outliers)
- Update existing datasets incrementally

## Trigger Phrases
- "download SPY data"
- "update historical data"
- "get AAPL data for 2023"

## Workflow
1. Parse symbols and date range
2. Connect to IB Gateway
3. Download bars via reqHistoricalData()
4. Convert to DataFrame
5. Save as CSV in data/csv/
6. Validate and report

---

# skills/backtest-runner.md (updated)

Run backtests using Backtrader Cerebro engine with IB cost models.

## Capabilities
- Execute backtests with Cerebro
- Apply IB commission schemes
- Generate performance reports
- Compare multiple strategies

## Trigger Phrases
- "run backtest for MyStrategy"
- "backtest SPY with SMA strategy"
- "compare strategy A vs B"

## Workflow
1. Parse strategy and parameters
2. Load data feeds
3. Configure Cerebro with analyzers
4. Apply commission model
5. Execute backtest
6. Parse and save results
7. Display summary
```

**Dependencies:**
- Requires Epic 12 (Backtest engine)
- Requires Epic 13 (Strategies)

---

### [ ] US-14.5: Strategy Comparison Tool
**As a developer, I need to compare multiple strategies**

**Status:** 🔄 Pending
**Estimate:** 6 hours
**Priority:** P2

**Acceptance Criteria:**
- [ ] Update `scripts/compare_strategies.py` for Backtrader
- [ ] Run multiple strategies in parallel
- [ ] Side-by-side metric comparison
- [ ] Statistical significance testing (t-test on returns)
- [ ] Visualization (equity curves overlay)
- [ ] Export comparison report (HTML, PDF)

**Technical Notes:**
```python
class StrategyComparator:
    """Compare multiple Backtrader strategies"""

    def __init__(self, strategies, data_feeds):
        self.strategies = strategies  # List of strategy classes
        self.data_feeds = data_feeds
        self.results = []

    def run_comparison(self):
        """Run all strategies and collect results"""
        for strategy_class in self.strategies:
            cerebro = bt.Cerebro()

            # Add data
            for data in self.data_feeds:
                cerebro.adddata(data)

            # Add strategy
            cerebro.addstrategy(strategy_class)

            # Add analyzers
            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

            # Run
            result = cerebro.run()[0]

            self.results.append({
                'strategy': strategy_class.__name__,
                'sharpe': result.analyzers.sharpe.get_analysis().get('sharperatio', 0),
                'returns': result.analyzers.returns.get_analysis().get('rtot', 0),
                'drawdown': result.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0),
                'trades': result.analyzers.trades.get_analysis().get('total', {}).get('total', 0)
            })

    def generate_report(self):
        """Generate comparison report"""
        df = pd.DataFrame(self.results)

        # Rank by Sharpe ratio
        df = df.sort_values('sharpe', ascending=False)

        # Calculate statistical significance
        # (Compare returns distributions)

        return df

# CLI usage
python scripts/compare_strategies.py \
    --strategies strategies.sma.SMAStrategy strategies.rsi.RSIStrategy \
    --symbols SPY \
    --start 2020-01-01 --end 2024-12-31 \
    --output results/comparison.html
```

**Dependencies:**
- Requires Epic 12 (Backtest engine)

---

### [ ] US-14.6: Performance Monitoring & Alerts
**As a developer, I need live trading alerts**

**Status:** 🔄 Pending
**Estimate:** 6 hours
**Priority:** P2

**Acceptance Criteria:**
- [ ] Create `scripts/monitoring.py` for live status checks
- [ ] Email/SMS alerts for critical events
- [ ] Risk violation alerts
- [ ] Connection loss alerts
- [ ] Daily P&L summary emails
- [ ] Configurable alert thresholds

**Technical Notes:**
```python
import smtplib
from email.mime.text import MIMEText

class AlertManager:
    """Send alerts for live trading events"""

    def __init__(self, email_config):
        self.email_config = email_config

    def send_email(self, subject, body):
        """Send email alert"""
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.email_config['from']
        msg['To'] = self.email_config['to']

        with smtplib.SMTP(self.email_config['smtp_host']) as server:
            server.send_message(msg)

    def alert_risk_violation(self, event_type, description):
        """Alert on risk management event"""
        subject = f"RISK ALERT: {event_type}"
        body = f"Risk violation detected:\n\n{description}"
        self.send_email(subject, body)

    def alert_connection_loss(self):
        """Alert on IB connection loss"""
        subject = "CONNECTION ALERT: IB Gateway Disconnected"
        body = "IB Gateway connection lost. Manual intervention required."
        self.send_email(subject, body)

    def daily_summary(self, portfolio_value, pnl, trades):
        """Send daily P&L summary"""
        subject = f"Daily Trading Summary - P&L: ${pnl:.2f}"
        body = f"""
        Portfolio Value: ${portfolio_value:.2f}
        Daily P&L: ${pnl:.2f}
        Trades Today: {trades}
        """
        self.send_email(subject, body)
```

**Alert Triggers:**
- Risk limit violations
- Daily loss exceeds threshold
- Position size errors
- IB connection loss
- Strategy exceptions

**Dependencies:**
- Requires US-14.3 (Live trading)

---

## Epic Completion Checklist
- [ ] All user stories completed
- [ ] All acceptance criteria met
- [ ] Parameter optimization working (grid + Bayesian)
- [ ] Walk-forward analysis validated
- [ ] Live trading deployment tested (paper trading)
- [ ] Claude Skills updated and functional
- [ ] Alert system operational
- [ ] Documentation updated
- [ ] Epic demo: Optimize parameters, run walk-forward, deploy to paper trading

## Validation Tests
1. **Optimization:** Run grid search, verify best parameters found
2. **Walk-Forward:** Run 12/6 month WF, analyze degradation
3. **Live Deployment:** Start paper trading, verify orders execute
4. **Emergency Stop:** Test liquidation script
5. **Alerts:** Trigger test alert, verify email received

## Performance Targets
- Parameter optimization: <10 minutes for 100 Bayesian trials
- Walk-forward: <1 hour for 3-year dataset
- Live trading latency: <100ms order execution
- Alert delivery: <30 seconds

---

**Next Epic:** Epic 15 - Testing & Validation (comprehensive testing, LEAN vs Backtrader comparison, integration tests)
