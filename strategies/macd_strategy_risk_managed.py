"""
MACD Strategy with Full Risk Management Integration
Example demonstrating MACD-based strategy using complete framework integration.

Epic 13: US-13.2 - Algorithm Migration (Simple Strategy)

Features:
- MACD-based entry/exit signals (signal line crossovers)
- Complete integration with BaseStrategy + RiskManager + DBLogger + EODStrategy
- Risk-controlled position sizing with trend confirmation
- Database logging of all trades and risk events
- Automatic EOD liquidation
- Comprehensive performance tracking

Strategy Logic:
- Entry: MACD line crosses above signal line (bullish momentum)
- Exit: MACD line crosses below signal line OR stop loss hit
- Trend Filter: Only trade in direction of 50-period EMA
- Risk Management: 3% daily loss limit, 15% max drawdown, 20% max position
- EOD: Automatic liquidation at 3:55 PM ET
- Database: Full trade logging and risk event tracking

This demonstrates advanced technical analysis with risk management.
"""

import backtrader as bt
from strategies.eod_strategy import EODStrategy


class MACDStrategyRiskManaged(EODStrategy):
    """
    MACD-based strategy with complete risk management integration.

    This strategy demonstrates advanced technical analysis with the full framework:
    - BaseStrategy: Core trading logic and portfolio helpers
    - RiskManager: Capital protection and position limits
    - DBLogger: Complete audit trail
    - EODStrategy: Automatic overnight risk management

    Entry Signal: MACD line crosses above signal line + trend confirmation
    Exit Signal: MACD line crosses below signal line OR stop loss (8%)
    Trend Filter: Trade only in direction of 50-period EMA
    """

    params = (
        # MACD parameters
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),

        # Trend confirmation
        ('ema_period', 50),

        # Risk management
        ('stop_loss_pct', 0.08),  # 8% stop loss for MACD strategy
        ('enable_risk_manager', True),
        ('daily_loss_limit', 0.03),  # 3% daily loss limit
        ('max_drawdown', 0.15),      # 15% max drawdown
        ('max_position_pct', 0.20),  # 20% max position size

        # EOD parameters
        ('eod_liquidate', True),
        ('eod_hour', 15),
        ('eod_minute', 55),

        # Database logging
        ('enable_db_logging', True),
        ('algorithm_name', 'MACD_Risk_Managed'),

        # Base parameters
        ('printlog', True),
    )

    def __init__(self):
        """Initialize MACD strategy with full framework integration."""
        # CRITICAL: Call parent first for EOD, risk, and DB logging setup
        super().__init__()

        # MACD indicator for momentum signals
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal
        )

        # Extract MACD components for easier access
        self.macd_line = self.macd.macd
        self.signal_line = self.macd.signal
        self.histogram = self.macd.histo

        # Trend confirmation EMA
        self.ema_trend = bt.indicators.EMA(
            self.data.close,
            period=self.p.ema_period
        )

        # Stop loss tracking
        self.stop_loss_price = None
        self.entry_price = None

        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0

        # MACD crossover tracking
        self.prev_macd_above_signal = None

        self.log("="*70)
        self.log("MACD STRATEGY WITH RISK MANAGEMENT INITIALIZED")
        self.log("="*70)
        self.log(f"MACD({self.p.macd_fast}, {self.p.macd_slow}, {self.p.macd_signal}) | EMA({self.p.ema_period})")
        self.log(f"Stop Loss: {self.p.stop_loss_pct*100}% | Trend Filter: EMA({self.p.ema_period})")
        self.log(f"Risk Manager: {'ENABLED' if self.p.enable_risk_manager else 'DISABLED'}")
        self.log(f"EOD Liquidation: {'ENABLED' if self.p.eod_liquidate else 'DISABLED'}")
        self.log(f"DB Logging: {'ENABLED' if self.p.enable_db_logging else 'DISABLED'}")
        self.log("="*70)

    def _get_macd_signal(self):
        """
        Get MACD crossover signals.

        Returns:
            tuple: (bullish_crossover, bearish_crossover)
        """
        if len(self.macd_line) < 2 or len(self.signal_line) < 2:
            return False, False

        current_macd = self.macd_line[0]
        current_signal = self.signal_line[0]
        prev_macd = self.macd_line[-1]
        prev_signal = self.signal_line[-1]

        # Bullish crossover: MACD crosses above signal line
        bullish_crossover = (prev_macd <= prev_signal and current_macd > current_signal)

        # Bearish crossover: MACD crosses below signal line
        bearish_crossover = (prev_macd >= prev_signal and current_macd < current_signal)

        return bullish_crossover, bearish_crossover

    def _trend_filter_active(self, direction):
        """
        Check if trend filter allows trading in the specified direction.

        Args:
            direction: 'long' or 'short'

        Returns:
            True if trend allows the trade direction
        """
        if len(self.ema_trend) < 1:
            return False

        current_price = self.data.close[0]
        ema_value = self.ema_trend[0]

        if direction == 'long':
            return current_price > ema_value  # Price above EMA = bullish trend
        elif direction == 'short':
            return current_price < ema_value  # Price below EMA = bearish trend

        return False

    def next(self):
        """Main trading logic with complete risk management."""
        # CRITICAL: Call parent first for EOD procedures, daily resets, DB logging
        super().next()

        # Skip trading if near EOD (parent handles this)
        if not self.should_trade():
            return

        # Skip if we have pending orders
        if self.order:
            return

        current_price = self.data.close[0]

        # Check for stop loss first (applies whether in position or not)
        if self.position and self.stop_loss_price:
            if current_price <= self.stop_loss_price:
                self.log(f"STOP LOSS TRIGGERED: Price ${current_price:.2f} <= Stop ${self.stop_loss_price:.2f} | "
                        f"P&L: {((current_price - self.entry_price) / self.entry_price * 100):+.2f}%")

                # Log risk event
                if self.db_logger:
                    self.db_logger.log_risk_event(
                        event_type='STOP_LOSS',
                        severity='INFO',
                        message=f'Stop loss triggered at ${current_price:.2f}',
                        symbol=self.data._name,
                        portfolio_value=self.broker.getvalue(),
                        position_value=self.get_position_value()
                    )

                self.close()
                self.stop_loss_price = None
                self.entry_price = None
                return

        # Get MACD signals
        bullish_crossover, bearish_crossover = self._get_macd_signal()

        # ENTRY SIGNAL: Bullish MACD crossover + bullish trend
        if not self.position:
            if bullish_crossover and self._trend_filter_active('long'):
                # Calculate position size using framework helper
                size = self.calculate_position_size(current_price)

                if size > 0:
                    # Risk check using RiskManager
                    if self.risk_manager:
                        can_trade, msg = self.risk_manager.can_trade(size, current_price)

                        if not can_trade:
                            self.log(f"TRADE BLOCKED by Risk Manager: {msg}", level='WARNING')

                            # Log risk event
                            if self.db_logger:
                                self.db_logger.log_risk_event(
                                    event_type='TRADE_BLOCKED',
                                    severity='WARNING',
                                    message=f'Entry blocked: {msg}',
                                    symbol=self.data._name,
                                    portfolio_value=self.broker.getvalue(),
                                    position_value=size * current_price
                                )
                            return

                    # Execute entry
                    macd_value = self.macd_line[0]
                    signal_value = self.signal_line[0]
                    histogram_value = self.histogram[0]

                    self.log(f"ENTRY SIGNAL: MACD Bullish Crossover | "
                            f"MACD: {macd_value:.3f} > Signal: {signal_value:.3f} | "
                            f"Histogram: {histogram_value:.3f} | "
                            f"Price: ${current_price:.2f} > EMA: ${self.ema_trend[0]:.2f} | "
                            f"Size: {size} shares (${size * current_price:,.2f})")

                    self.buy(size=size)
                    self.entry_price = current_price
                    self.stop_loss_price = current_price * (1 - self.p.stop_loss_pct)
                    self.total_trades += 1

        # EXIT SIGNAL: Bearish MACD crossover
        elif bearish_crossover:
            exit_price = current_price
            pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100

            macd_value = self.macd_line[0]
            signal_value = self.signal_line[0]
            histogram_value = self.histogram[0]

            self.log(f"EXIT SIGNAL: MACD Bearish Crossover | "
                    f"MACD: {macd_value:.3f} < Signal: {signal_value:.3f} | "
                    f"Histogram: {histogram_value:.3f} | "
                    f"Entry: ${self.entry_price:.2f} | Exit: ${exit_price:.2f} | "
                    f"P&L: {pnl_pct:+.2f}%")

            if pnl_pct > 0:
                self.winning_trades += 1

            self.close()
            self.stop_loss_price = None
            self.entry_price = None

    def notify_order(self, order):
        """Enhanced order notification with risk management logging."""
        # Call parent for standard logging
        super().notify_order(order)

        if order.status in [order.Completed]:
            if order.isbuy():
                value = order.executed.value
                portfolio_value = self.broker.getvalue()
                pct_of_portfolio = (value / portfolio_value) * 100

                self.log(f"BUY EXECUTED: ${value:,.2f} ({pct_of_portfolio:.1f}% of portfolio) | "
                        f"Stop Loss: ${self.stop_loss_price:.2f}", level='SUCCESS')

            elif order.issell():
                pnl = order.executed.pnl
                pnl_net = order.executed.pnlcomm
                self.log(f"SELL EXECUTED: P&L Gross ${pnl:.2f} | Net ${pnl_net:.2f}", level='SUCCESS')

    def notify_trade(self, trade):
        """Enhanced trade notification with performance tracking."""
        # Call parent for standard logging
        super().notify_trade(trade)

        if trade.isclosed:
            pnl_net = trade.pnlcomm
            duration = trade.barlen

            self.log(f"TRADE CLOSED: Net P&L ${pnl_net:.2f} | Duration: {duration} bars", level='SUCCESS')

            # Log to database (parent handles this, but we can add custom fields)
            if self.db_logger:
                # Additional trade metadata could be logged here
                pass  # Parent already logs comprehensive trade data

    def stop(self):
        """Strategy completion with comprehensive performance summary."""
        self.log("\n" + "="*70)
        self.log("MACD STRATEGY PERFORMANCE SUMMARY")
        self.log("="*70)

        # Basic metrics
        final_value = self.broker.getvalue()
        total_return = ((final_value - self.p.initial_cash) / self.p.initial_cash) * 100

        self.log(f"Final Portfolio Value: ${final_value:,.2f}")
        self.log(f"Total Return: {total_return:+.2f}%")
        self.log(f"Total Trades: {self.total_trades}")
        self.log(f"Winning Trades: {self.winning_trades}")

        if self.total_trades > 0:
            win_rate = (self.winning_trades / self.total_trades) * 100
            self.log(f"Win Rate: {win_rate:.1f}%")

        # MACD-specific metrics
        self.log("\nMACD PARAMETERS:")
        self.log(f"Fast Period: {self.p.macd_fast} | Slow Period: {self.p.macd_slow} | Signal: {self.p.macd_signal}")
        self.log(f"Trend Filter EMA: {self.p.ema_period} | Stop Loss: {self.p.stop_loss_pct*100}%")

        # Risk management summary
        if self.risk_manager:
            self.log("\nRISK MANAGEMENT SUMMARY:")
            self.log(f"Daily Loss Limit: {self.p.daily_loss_limit*100}%")
            self.log(f"Max Drawdown Limit: {self.p.max_drawdown*100}%")
            self.log(f"Max Position Size: {self.p.max_position_pct*100}% of portfolio")

        # Framework usage summary
        self.log("\nFRAMEWORK INTEGRATION:")
        self.log(f"✓ BaseStrategy: Portfolio helpers and order management")
        self.log(f"✓ RiskManager: Capital protection and position limits")
        self.log(f"✓ DBLogger: Complete trade audit trail")
        self.log(f"✓ EODStrategy: Automatic liquidation at {self.p.eod_hour}:{self.p.eod_minute:02d}")

        self.log("="*70)

        # Call parent for final risk summary and DB logging
        super().stop()


if __name__ == "__main__":
    print("MACD Strategy with Full Risk Management Integration")
    print("\nFeatures:")
    print("  ✓ MACD crossover signals (12, 26, 9)")
    print("  ✓ Trend confirmation with EMA(50)")
    print("  ✓ 8% stop loss protection")
    print("  ✓ RiskManager integration (3% daily loss, 15% max drawdown)")
    print("  ✓ DBLogger for complete audit trail")
    print("  ✓ EODStrategy for automatic liquidation")
    print("  ✓ Comprehensive performance tracking")
    print("\nParameters:")
    print(f"  MACD Fast: {MACDStrategyRiskManaged.params.macd_fast}")
    print(f"  MACD Slow: {MACDStrategyRiskManaged.params.macd_slow}")
    print(f"  MACD Signal: {MACDStrategyRiskManaged.params.macd_signal}")
    print(f"  Trend EMA: {MACDStrategyRiskManaged.params.ema_period}")
    print(f"  Stop Loss: {MACDStrategyRiskManaged.params.stop_loss_pct*100}%")
    print("\nUsage:")
    print("  python scripts/run_backtest.py \\")
    print("    --strategy strategies/macd_strategy_risk_managed.py \\")
    print("    --symbols SPY \\")
    print("    --start 2024-01-01 --end 2024-12-31")
    print("\nNote: Demonstrates advanced technical analysis with risk management")