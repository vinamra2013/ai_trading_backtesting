"""
Stochastic Oscillator Strategy
Epic 19: US-19.4 - Timing Indicator Strategy Templates

Implements stochastic oscillator strategy:
- Entry: %K crosses above/below %D at oversold/overbought levels
- Exit: %K crosses back in opposite direction
- Works best in ranging markets with clear oscillator signals

Market Conditions:
- Ranging/sideways markets with oscillator cycles
- Works well when stochastic provides clear overbought/oversold signals
- May produce false signals in strong trends

Parameters:
- k_period: %K period (default: 14)
- d_period: %D period (default: 3)
- oversold_level: Oversold threshold (default: 20)
- overbought_level: Overbought threshold (default: 80)
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class StochasticOscillator(BaseStrategy):
    """
    Stochastic Oscillator Strategy for timing entries and exits.

    Uses stochastic oscillator to identify overbought and oversold conditions.
    Enters long when %K crosses above %D from oversold levels.
    Enters short when %K crosses below %D from overbought levels.

    Entry: %K crosses %D from oversold/overbought levels
    Exit: %K crosses back in opposite direction
    """

    params = (
        ('k_period', 14),               # %K period
        ('d_period', 3),                # %D period (smoothing)
        ('oversold_level', 20),         # Oversold threshold
        ('overbought_level', 80),       # Overbought threshold
        ('position_size', 0.95),        # 95% of portfolio per trade
        ('printlog', True),             # Enable logging
        ('log_trades', True),           # Log trade execution
    )

    def __init__(self):
        """Initialize Stochastic indicators."""
        super().__init__()

        # Stochastic oscillator
        self.stoch = bt.indicators.Stochastic(
            self.data,
            period=self.params.k_period,
            period_d=self.params.d_period
        )

        self.percent_k = self.stoch.percK
        self.percent_d = self.stoch.percD

        # State tracking
        self.in_position = False
        self.entry_price = None
        self.position_type = None  # 'long' or 'short'

        self.log(f"Stochastic Oscillator initialized: %K({self.params.k_period}), "
                f"%D({self.params.d_period}), "
                f"Oversold: {self.params.oversold_level}, Overbought: {self.params.overbought_level}")

    def _get_stochastic_signals(self):
        """
        Get current stochastic oscillator signals.

        Returns:
            tuple: (long_signal, short_signal)
        """
        if len(self.percent_k) < 2 or len(self.percent_d) < 2:
            return False, False

        current_k = self.percent_k[0]
        current_d = self.percent_d[0]
        prev_k = self.percent_k[-1]
        prev_d = self.percent_d[-1]

        # Detect crossovers
        k_cross_up = (prev_k <= prev_d) and (current_k > current_d)
        k_cross_down = (prev_k >= prev_d) and (current_k < current_d)

        # Long signal: %K crosses above %D from oversold levels
        long_signal = k_cross_up and (current_k <= self.params.oversold_level or prev_k <= self.params.oversold_level)

        # Short signal: %K crosses below %D from overbought levels
        short_signal = k_cross_down and (current_k >= self.params.overbought_level or prev_k >= self.params.overbought_level)

        return long_signal, short_signal

    def next(self):
        """Execute Stochastic oscillator trading logic."""
        # Check for pending orders
        if self.has_pending_order():
            return

        # Get current signals
        long_signal, short_signal = self._get_stochastic_signals()

        current_price = self.data.close[0]
        current_k = self.percent_k[0] if len(self.percent_k) > 0 else None
        current_d = self.percent_d[0] if len(self.percent_d) > 0 else None

        # Entry signals
        if not self.is_invested():
            # Long entry: %K crosses above %D from oversold
            if long_signal and current_k is not None and current_d is not None:
                size = self.calculate_position_size(current_price)
                if size > 0:
                    self.log(f"LONG ENTRY: %K {current_k:.2f} crossed above %D {current_d:.2f} "
                            f"from oversold levels | Price: ${current_price:.2f} | Size: {size}")
                    self.market_order(self.data, size)
                    self.in_position = True
                    self.entry_price = current_price
                    self.position_type = 'long'

            # Short entry: %K crosses below %D from overbought
            elif short_signal and current_k is not None and current_d is not None:
                size = self.calculate_position_size(current_price)
                if size > 0:
                    self.log(f"SHORT ENTRY: %K {current_k:.2f} crossed below %D {current_d:.2f} "
                            f"from overbought levels | Price: ${current_price:.2f} | Size: {size}")
                    self.market_order(self.data, -size)  # Negative for short
                    self.in_position = True
                    self.entry_price = current_price
                    self.position_type = 'short'

        # Exit signals
        elif self.is_invested():
            exit_signal = None

            # Exit long: %K crosses below %D
            if self.position_type == 'long' and short_signal and current_k is not None and current_d is not None:
                exit_signal = f"%K {current_k:.2f} crossed below %D {current_d:.2f}"

            # Exit short: %K crosses above %D
            elif self.position_type == 'short' and long_signal and current_k is not None and current_d is not None:
                exit_signal = f"%K {current_k:.2f} crossed above %D {current_d:.2f}"

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
        self.log(f"Stochastic Oscillator Strategy ended | "
                f"%K: {self.params.k_period} | %D: {self.params.d_period} | "
                f"Oversold: {self.params.oversold_level} | Overbought: {self.params.overbought_level} | "
                f"Final Value: ${self.broker.getvalue():,.2f}")


if __name__ == "__main__":
    """Test strategy import and basic validation."""
    print("Stochastic Oscillator Strategy - Ready for use")
    print("\nParameters:")
    print(f"  %K Period: {StochasticOscillator.params.k_period}")
    print(f"  %D Period: {StochasticOscillator.params.d_period}")
    print(f"  Oversold Level: {StochasticOscillator.params.oversold_level}")
    print(f"  Overbought Level: {StochasticOscillator.params.overbought_level}")
    print(f"  Position Size: {StochasticOscillator.params.position_size}")
    print("\n✅ Strategy loaded successfully!")
    print("\nUsage:")
    print("  from strategies.stochastic_oscillator import StochasticOscillator")
    print("  cerebro.addstrategy(StochasticOscillator)")
    print("  # Add data feed")
    print("  cerebro.adddata(data)")