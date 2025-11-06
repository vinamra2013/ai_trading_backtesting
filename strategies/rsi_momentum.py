"""
RSI Momentum Strategy
Epic 19: US-19.1 - Momentum Strategy Templates

Implements RSI-based momentum strategy with trend confirmation:
- RSI > 50 indicates bullish momentum
- Trend filter: Price > 200-day MA for uptrend confirmation

Entry Signal:
- RSI crosses above 50 from below
- Trend filter active (price > 200-day MA)

Exit Signal:
- RSI crosses below 50 from above
- Trend filter fails (price < 200-day MA)

Market Conditions:
- Trending markets with momentum
- Works best when RSI confirms trend direction
- May produce false signals in choppy/sideways markets

Parameters:
- rsi_period: RSI calculation period (default: 14)
- trend_period: Trend filter MA period (default: 200)
- rsi_entry_threshold: RSI level for entry (default: 50)
- rsi_exit_threshold: RSI level for exit (default: 50)
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class RSIMomentum(BaseStrategy):
    """
    RSI Momentum Strategy with trend confirmation.

    Uses RSI to identify momentum shifts and trend filter to avoid
    false signals in choppy markets.

    Entry: RSI crosses above 50 + trend filter (price > MA)
    Exit: RSI crosses below 50 or trend filter fails
    """

    params = (
        ('rsi_period', 14),               # RSI calculation period
        ('trend_period', 200),            # Trend filter MA period
        ('rsi_entry_threshold', 50),      # RSI level for entry
        ('rsi_exit_threshold', 50),       # RSI level for exit
        ('position_size', 0.95),          # 95% of portfolio per trade
        ('printlog', True),               # Enable logging
        ('log_trades', True),             # Log trade execution
    )

    def __init__(self):
        """Initialize RSI momentum indicators and state."""
        super().__init__()

        # RSI indicator
        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=self.params.rsi_period
        )

        # Trend filter: 200-day moving average
        self.trend_ma = bt.indicators.SimpleMovingAverage(
            self.data.close,
            period=self.params.trend_period
        )

        # Track previous RSI values for crossover detection
        self.prev_rsi = None

        # State tracking
        self.in_position = False
        self.entry_price = None

        self.log(f"RSI Momentum initialized: RSI({self.params.rsi_period}), "
                f"Trend MA({self.params.trend_period}), "
                f"Entry RSI > {self.params.rsi_entry_threshold}, "
                f"Exit RSI < {self.params.rsi_exit_threshold}")

    def _trend_filter_active(self):
        """
        Check if trend filter is active (price > MA).

        Returns:
            True if price is above trend MA, False otherwise
        """
        if len(self.trend_ma) < 1:
            return False

        current_price = self.data.close[0]
        trend_ma_value = self.trend_ma[0]

        return current_price > trend_ma_value

    def _get_rsi_signal(self):
        """
        Get current RSI signal by detecting crosses manually.

        Returns:
            tuple: (entry_signal, exit_signal)
        """
        if len(self.rsi) < 2:
            return False, False

        current_rsi = self.rsi[0]
        prev_rsi = self.rsi[-1]

        # Entry signal: RSI crosses above entry threshold
        entry_signal = (prev_rsi <= self.params.rsi_entry_threshold and
                       current_rsi > self.params.rsi_entry_threshold)

        # Exit signal: RSI crosses below exit threshold
        exit_signal = (prev_rsi >= self.params.rsi_exit_threshold and
                      current_rsi < self.params.rsi_exit_threshold)

        return entry_signal, exit_signal

    def next(self):
        """Execute RSI momentum trading logic."""
        # Check for pending orders
        if self.has_pending_order():
            return

        # Get current signals
        rsi_entry, rsi_exit = self._get_rsi_signal()
        trend_active = self._trend_filter_active()

        current_price = self.data.close[0]
        current_rsi = self.rsi[0] if len(self.rsi) > 0 else None

        # Entry signal: RSI crosses above threshold + trend filter
        if not self.is_invested():
            if rsi_entry and trend_active and current_rsi is not None:
                # Calculate position size
                size = self.calculate_position_size(current_price)

                if size > 0:
                    self.log(f"ENTRY SIGNAL: RSI crossed above {self.params.rsi_entry_threshold} "
                            f"(RSI: {current_rsi:.2f}) + Trend filter active | "
                            f"Price: ${current_price:.2f} | Size: {size}")
                    self.market_order(self.data, size)
                    self.in_position = True
                    self.entry_price = current_price

        # Exit signals
        elif self.is_invested():
            exit_reason = None

            # RSI exit signal
            if rsi_exit and current_rsi is not None:
                exit_reason = f"RSI crossed below {self.params.rsi_exit_threshold} (RSI: {current_rsi:.2f})"

            # Trend filter failure
            elif not trend_active:
                exit_reason = "Trend filter failed (price < MA)"

            if exit_reason:
                exit_price = current_price
                pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100 if self.entry_price else 0

                self.log(f"EXIT SIGNAL: {exit_reason} | "
                        f"Entry: ${self.entry_price:.2f} | Exit: ${exit_price:.2f} | "
                        f"P&L: {pnl_pct:+.2f}%")
                self.close_position(self.data)
                self.in_position = False
                self.entry_price = None

    def notify_order(self, order):
        """Handle order notifications."""
        super().notify_order(order)

        if order.status in [order.Completed]:
            if order.isbuy():
                self.in_position = True
                self.entry_price = order.executed.price
            elif order.issell():
                self.in_position = False
                self.entry_price = None

    def stop(self):
        """Strategy cleanup and final reporting."""
        self.log(f"RSI Momentum Strategy ended | "
                f"RSI Period: {self.params.rsi_period} | "
                f"Trend MA: {self.params.trend_period} | "
                f"Entry RSI: >{self.params.rsi_entry_threshold} | "
                f"Exit RSI: <{self.params.rsi_exit_threshold} | "
                f"Final Value: ${self.broker.getvalue():,.2f}")


if __name__ == "__main__":
    """Test strategy import and basic validation."""
    print("RSI Momentum Strategy - Ready for use")
    print("\nParameters:")
    print(f"  RSI Period: {RSIMomentum.params.rsi_period}")
    print(f"  Trend MA Period: {RSIMomentum.params.trend_period}")
    print(f"  RSI Entry Threshold: {RSIMomentum.params.rsi_entry_threshold}")
    print(f"  RSI Exit Threshold: {RSIMomentum.params.rsi_exit_threshold}")
    print(f"  Position Size: {RSIMomentum.params.position_size}")
    print("\n✅ Strategy loaded successfully!")
    print("\nUsage:")
    print("  from strategies.rsi_momentum import RSIMomentum")
    print("  cerebro.addstrategy(RSIMomentum)")
    print("  # Add data feed")
    print("  cerebro.adddata(data)")