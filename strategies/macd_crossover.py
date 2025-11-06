"""
MACD Signal Line Crossover Strategy
Epic 19: US-19.4 - Timing Indicator Strategy Templates

Implements MACD signal line crossover strategy:
- Entry: MACD line crosses above/below signal line
- Exit: MACD line crosses back below/above signal line
- Works best in trending markets with momentum

Market Conditions:
- Trending markets with clear momentum shifts
- MACD crossovers provide reliable timing signals
- May produce false signals in choppy/sideways markets

Parameters:
- fast_period: Fast EMA period for MACD (default: 12)
- slow_period: Slow EMA period for MACD (default: 26)
- signal_period: Signal line EMA period (default: 9)
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class MACDCrossover(BaseStrategy):
    """
    MACD Signal Line Crossover Strategy for timing entries and exits.

    Uses MACD line crossing signal line to identify momentum shifts.
    Enters long when MACD crosses above signal line.
    Enters short when MACD crosses below signal line.

    Entry: MACD crosses above/below signal line
    Exit: MACD crosses back in opposite direction
    """

    params = (
        ('fast_period', 12),               # Fast EMA period
        ('slow_period', 26),               # Slow EMA period
        ('signal_period', 9),              # Signal line period
        ('position_size', 0.95),           # 95% of portfolio per trade
        ('printlog', True),                # Enable logging
        ('log_trades', True),              # Log trade execution
    )

    def __init__(self):
        """Initialize MACD indicators."""
        super().__init__()

        # MACD indicator
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.fast_period,
            period_me2=self.params.slow_period,
            period_signal=self.params.signal_period
        )

        self.macd_line = self.macd.macd
        self.signal_line = self.macd.signal

        # State tracking
        self.in_position = False
        self.entry_price = None
        self.position_type = None  # 'long' or 'short'

        self.log(f"MACD Crossover initialized: Fast({self.params.fast_period}), "
                f"Slow({self.params.slow_period}), Signal({self.params.signal_period})")

    def _get_crossover_signals(self):
        """
        Get current MACD crossover signals.

        Returns:
            tuple: (long_signal, short_signal)
        """
        if len(self.macd_line) < 2 or len(self.signal_line) < 2:
            return False, False

        current_macd = self.macd_line[0]
        current_signal = self.signal_line[0]
        prev_macd = self.macd_line[-1]
        prev_signal = self.signal_line[-1]

        # Detect crossovers
        macd_cross_up = (prev_macd <= prev_signal) and (current_macd > current_signal)
        macd_cross_down = (prev_macd >= prev_signal) and (current_macd < current_signal)

        return macd_cross_up, macd_cross_down

    def next(self):
        """Execute MACD crossover trading logic."""
        # Check for pending orders
        if self.has_pending_order():
            return

        # Get current signals
        long_signal, short_signal = self._get_crossover_signals()

        current_price = self.data.close[0]
        current_macd = self.macd_line[0] if len(self.macd_line) > 0 else None
        current_signal = self.signal_line[0] if len(self.signal_line) > 0 else None

        # Entry signals
        if not self.is_invested():
            # Long entry: MACD crosses above signal line
            if long_signal and current_macd is not None and current_signal is not None:
                size = self.calculate_position_size(current_price)
                if size > 0:
                    self.log(f"LONG ENTRY: MACD {current_macd:.4f} crossed above Signal {current_signal:.4f} | "
                            f"Price: ${current_price:.2f} | Size: {size}")
                    self.market_order(self.data, size)
                    self.in_position = True
                    self.entry_price = current_price
                    self.position_type = 'long'

            # Short entry: MACD crosses below signal line
            elif short_signal and current_macd is not None and current_signal is not None:
                size = self.calculate_position_size(current_price)
                if size > 0:
                    self.log(f"SHORT ENTRY: MACD {current_macd:.4f} crossed below Signal {current_signal:.4f} | "
                            f"Price: ${current_price:.2f} | Size: {size}")
                    self.market_order(self.data, -size)  # Negative for short
                    self.in_position = True
                    self.entry_price = current_price
                    self.position_type = 'short'

        # Exit signals
        elif self.is_invested():
            exit_signal = None

            # Exit long: MACD crosses below signal line
            if self.position_type == 'long' and short_signal and current_macd is not None and current_signal is not None:
                exit_signal = f"MACD {current_macd:.4f} crossed below Signal {current_signal:.4f}"

            # Exit short: MACD crosses above signal line
            elif self.position_type == 'short' and long_signal and current_macd is not None and current_signal is not None:
                exit_signal = f"MACD {current_macd:.4f} crossed above Signal {current_signal:.4f}"

            if exit_signal and self.entry_price is not None:
                exit_price = current_price
                pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100
                if self.position_type == 'short':
                    pnl_pct = -pnl_pct  # Reverse for short positions

                self.log(f"EXIT SIGNAL: {exit_signal} | "
                        f"Entry: ${self.entry_price:.2f} | Exit: ${exit_price:.2f} | "
                        f"P&L: {pnl_pct:+.2f}%")
                self.close_position(self.data)
                self.in_position = False
                self.entry_price = None
                self.position_type = None

    def notify_order(self, order):
        """Handle order notifications."""
        super().notify_order(order)

        if order.status in [order.Completed]:
            if order.isbuy():
                self.in_position = True
                self.position_type = 'long'
                self.entry_price = order.executed.price
            elif order.issell():
                self.in_position = True
                self.position_type = 'short'
                self.entry_price = order.executed.price

    def stop(self):
        """Strategy cleanup and final reporting."""
        self.log(f"MACD Crossover Strategy ended | "
                f"Fast: {self.params.fast_period} | Slow: {self.params.slow_period} | "
                f"Signal: {self.params.signal_period} | "
                f"Final Value: ${self.broker.getvalue():,.2f}")


if __name__ == "__main__":
    """Test strategy import and basic validation."""
    print("MACD Signal Line Crossover Strategy - Ready for use")
    print("\nParameters:")
    print(f"  Fast Period: {MACDCrossover.params.fast_period}")
    print(f"  Slow Period: {MACDCrossover.params.slow_period}")
    print(f"  Signal Period: {MACDCrossover.params.signal_period}")
    print(f"  Position Size: {MACDCrossover.params.position_size}")
    print("\n✅ Strategy loaded successfully!")
    print("\nUsage:")
    print("  from strategies.macd_crossover import MACDCrossover")
    print("  cerebro.addstrategy(MACDCrossover)")
    print("  # Add data feed")
    print("  cerebro.adddata(data)")