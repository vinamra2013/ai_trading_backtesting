"""
MACD Crossover Strategy
Example demonstrating MACD-based trading with signal confirmation.

Features:
- MACD line and signal line crossovers
- Histogram confirmation for signal strength
- Risk-managed position sizing
- Database logging integration
- Comprehensive signal validation

Signals:
- Entry: MACD crosses above signal line + histogram positive
- Exit: MACD crosses below signal line OR histogram negative
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class MACDCrossoverStrategy(BaseStrategy):
    """
    MACD crossover strategy with histogram confirmation.

    Strategy Overview:
    - Uses MACD line crossing signal line for primary signals
    - Histogram provides confirmation of momentum strength
    - Risk-managed entries and exits
    - Database logging for all trades

    Signals:
    - Long Entry: MACD > signal line AND histogram > 0
    - Long Exit: MACD < signal line OR histogram < 0
    - Short Entry: MACD < signal line AND histogram < 0
    - Short Exit: MACD > signal line OR histogram > 0
    """

    params = (
        # MACD parameters
        ('fast_period', 12),
        ('slow_period', 26),
        ('signal_period', 9),

        # Signal confirmation
        ('histogram_threshold', 0.0),  # Minimum histogram value for confirmation

        # Risk management
        ('enable_risk_manager', True),
        ('daily_loss_limit', 0.02),
        ('max_drawdown', 0.20),
        ('max_position_pct', 0.95),

        # Database logging
        ('enable_db_logging', False),
        ('algorithm_name', 'MACDCrossoverStrategy'),

        # Base strategy params
        ('printlog', True),
        ('log_trades', True),
        ('log_orders', True),
    )

    def __init__(self):
        """Initialize MACD crossover strategy."""
        super().__init__()

        # Use built-in MACD indicator with default parameters
        self.macd = bt.indicators.MACD()
        self.macd_line = self.macd.macd
        self.signal_line = self.macd.signal
        self.histogram = self.macd.macd - self.macd.signal  # Calculate histogram

        # Signal tracking
        self.current_position_type = None  # 'long', 'short', or None

        self.log(f"MACD Crossover Strategy initialized: Fast({self.p.fast_period}), "
                f"Slow({self.p.slow_period}), Signal({self.p.signal_period})")

    def next(self):
        """Main trading logic."""
        self.bar_count += 1

        # Skip if we have pending orders
        if self.has_pending_order():
            return

        current_macd = self.macd_line[0]
        current_signal = self.signal_line[0]
        current_histogram = self.histogram[0]
        current_price = self.data.close[0]

        # Determine signals with confirmation
        # Check for crossovers manually
        macd_prev = self.macd_line[-1]
        signal_prev = self.signal_line[-1]
        macd_cross_up = (macd_prev <= signal_prev) and (current_macd > current_signal)
        macd_cross_down = (macd_prev >= signal_prev) and (current_macd < current_signal)

        long_entry = (macd_cross_up and
                      current_histogram > self.p.histogram_threshold)
        short_entry = (macd_cross_down and
                       current_histogram < -self.p.histogram_threshold)

        long_exit = (macd_cross_down or
                     (self.current_position_type == 'long' and
                      current_histogram < -self.p.histogram_threshold))
        short_exit = (macd_cross_up or
                      (self.current_position_type == 'short' and
                       current_histogram > self.p.histogram_threshold))

        # Execute trades
        if not self.is_invested():
            # Entry logic
            if long_entry:
                self._enter_long_position(current_macd, current_signal, current_histogram, current_price)
            elif short_entry:
                self._enter_short_position(current_macd, current_signal, current_histogram, current_price)

        else:
            # Exit logic
            if self.current_position_type == 'long' and long_exit:
                self._exit_long_position(current_macd, current_signal, current_histogram, current_price)
            elif self.current_position_type == 'short' and short_exit:
                self._exit_short_position(current_macd, current_signal, current_histogram, current_price)

    def _enter_long_position(self, macd, signal, histogram, price):
        """Enter long position with risk checks."""
        # Calculate position size
        size = self.calculate_position_size(price)

        # Risk check
        if hasattr(self, 'risk_manager') and self.risk_manager:
            can_trade, msg = self.risk_manager.can_trade(size, price, self.data)
            if not can_trade:
                self.log(f'LONG ENTRY BLOCKED by risk manager: {msg}', level='WARNING')
                return

        # Place order
        self.log(f'LONG ENTRY: MACD={macd:.4f} crossed above Signal={signal:.4f}, '
                f'Histogram={histogram:.4f} (> {self.p.histogram_threshold}), '
                f'Price=${price:.2f}, Size={size}')

        order = self.buy(size=size)
        self.orders[self.data] = order
        self.current_position_type = 'long'

    def _enter_short_position(self, macd, signal, histogram, price):
        """Enter short position with risk checks."""
        # Calculate position size
        size = self.calculate_position_size(price)

        # Risk check
        if hasattr(self, 'risk_manager') and self.risk_manager:
            can_trade, msg = self.risk_manager.can_trade(size, price, self.data)
            if not can_trade:
                self.log(f'SHORT ENTRY BLOCKED by risk manager: {msg}', level='WARNING')
                return

        # Place order
        self.log(f'SHORT ENTRY: MACD={macd:.4f} crossed below Signal={signal:.4f}, '
                f'Histogram={histogram:.4f} (< {-self.p.histogram_threshold}), '
                f'Price=${price:.2f}, Size={size}')

        order = self.sell(size=size)
        self.orders[self.data] = order
        self.current_position_type = 'short'

    def _exit_long_position(self, macd, signal, histogram, price):
        """Exit long position."""
        self.log(f'LONG EXIT: MACD={macd:.4f}, Signal={signal:.4f}, Histogram={histogram:.4f}, Price=${price:.2f}')
        order = self.close()
        self.orders[self.data] = order
        self.current_position_type = None

    def _exit_short_position(self, macd, signal, histogram, price):
        """Exit short position."""
        self.log(f'SHORT EXIT: MACD={macd:.4f}, Signal={signal:.4f}, Histogram={histogram:.4f}, Price=${price:.2f}')
        order = self.close()
        self.orders[self.data] = order
        self.current_position_type = None

    def notify_order(self, order):
        """Handle order notifications."""
        super().notify_order(order)

        # Additional strategy-specific logging
        if order.status in [order.Completed]:
            trade_type = "BUY" if order.isbuy() else "SELL"
            self.log(f'{trade_type} ORDER COMPLETED: {order.executed.size} shares @ ${order.executed.price:.2f}',
                    level='INFO')

    def notify_trade(self, trade):
        """Handle trade notifications."""
        super().notify_trade(trade)

        # Track position type for exit logic
        if not trade.isclosed:
            if trade.size > 0:
                self.current_position_type = 'long'
            elif trade.size < 0:
                self.current_position_type = 'short'

    def stop(self):
        """Strategy ending - log final statistics."""
        self.log("="*60)
        self.log("MACD CROSSOVER STRATEGY SUMMARY")
        self.log("="*60)
        self.log(f"Total Trades: {self.trade_count}")
        self.log(f"Final Portfolio Value: ${self.broker.getvalue():,.2f}")
        self.log(f"MACD Parameters: Fast({self.p.fast_period}), Slow({self.p.slow_period}), Signal({self.p.signal_period})")
        self.log(f"Histogram Threshold: {self.p.histogram_threshold}")

        # Print risk summary if available
        if hasattr(self, 'risk_manager') and self.risk_manager:
            risk_summary = self.risk_manager.get_risk_summary()
            self.log(f"Risk Events: {risk_summary.get('risk_events_count', 0)}")
            self.log(f"Max Drawdown: {risk_summary.get('current_drawdown', 0):.1%}")

        super().stop()


if __name__ == "__main__":
    print("MACD Crossover Strategy")
    print("\nFeatures:")
    print("  ✓ MACD line and signal line crossovers")
    print("  ✓ Histogram confirmation for signal strength")
    print("  ✓ Risk management integration")
    print("  ✓ Database logging support")
    print("  ✓ Long and short position support")
    print("\nUsage:")
    print("  python scripts/run_backtest.py \\")
    print("    --strategy strategies/mac_crossover_strategy.py \\")
    print("    --symbols SPY \\")
    print("    --start 2024-01-01 --end 2024-12-31")
    print("\nParameters:")
    print("  --fast_period: MACD fast EMA period (default: 12)")
    print("  --slow_period: MACD slow EMA period (default: 26)")
    print("  --signal_period: MACD signal line period (default: 9)")
    print("  --histogram_threshold: Minimum histogram value for confirmation (default: 0.0)")