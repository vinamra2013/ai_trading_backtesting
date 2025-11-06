"""
Z-Score Reversal Strategy
Epic 19: US-19.2 - Mean Reversion Strategy Templates

Implements statistical mean reversion using z-score:
- Calculate z-score: (price - mean) / standard_deviation
- Entry: Z-score < -2.0 (oversold)
- Exit: Z-score > 2.0 (overbought) or mean reversion

Market Conditions:
- Ranging/sideways markets with statistical mean reversion
- Works best when price oscillates around mean
- May underperform in strong trending markets

Parameters:
- lookback_period: Period for mean/std calculation (default: 20)
- entry_threshold: Z-score entry threshold (default: -2.0)
- exit_threshold: Z-score exit threshold (default: 2.0)
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class ZScoreReversal(BaseStrategy):
    """
    Z-Score Reversal Strategy for statistical mean reversion trading.

    Uses z-score to identify statistically significant deviations from mean.
    Enters long when price is 2 standard deviations below mean.
    Exits when price returns to 2 standard deviations above mean.

    Entry: Z-score ≤ -2.0 (statistically oversold)
    Exit: Z-score ≥ 2.0 (statistically overbought)
    """

    params = (
        ('lookback_period', 20),        # Period for mean/std calculation
        ('entry_threshold', -2.0),      # Z-score entry threshold
        ('exit_threshold', 2.0),        # Z-score exit threshold
        ('position_size', 0.95),        # 95% of portfolio per trade
        ('printlog', True),             # Enable logging
        ('log_trades', True),           # Log trade execution
    )

    def __init__(self):
        """Initialize z-score calculation and state."""
        super().__init__()

        # Calculate rolling mean and standard deviation
        self.price_mean = bt.indicators.SimpleMovingAverage(
            self.data.close,
            period=self.params.lookback_period
        )

        self.price_std = bt.indicators.StandardDeviation(
            self.data.close,
            period=self.params.lookback_period
        )

        # State tracking
        self.in_position = False
        self.entry_price = None

        self.log(f"Z-Score Reversal initialized: Lookback({self.params.lookback_period}), "
                f"Entry Z ≤ {self.params.entry_threshold}, Exit Z ≥ {self.params.exit_threshold}")

    def _calculate_zscore(self):
        """
        Calculate current z-score.

        Returns:
            Current z-score value or None if insufficient data
        """
        if len(self.price_mean) < 1 or len(self.price_std) < 1:
            return None

        current_price = self.data.close[0]
        mean_price = self.price_mean[0]
        std_price = self.price_std[0]

        if std_price == 0:
            return 0.0

        zscore = (current_price - mean_price) / std_price
        return zscore

    def _get_reversal_signals(self):
        """
        Get current reversal signals based on z-score.

        Returns:
            tuple: (entry_signal, exit_signal)
        """
        zscore = self._calculate_zscore()

        if zscore is None:
            return False, False

        # Entry signal: Z-score drops below entry threshold (oversold)
        entry_signal = zscore <= self.params.entry_threshold

        # Exit signal: Z-score rises above exit threshold (overbought)
        exit_signal = zscore >= self.params.exit_threshold

        return entry_signal, exit_signal

    def next(self):
        """Execute z-score reversal trading logic."""
        # Check for pending orders
        if self.has_pending_order():
            return

        # Get current signals
        entry_signal, exit_signal = self._get_reversal_signals()

        current_price = self.data.close[0]
        current_zscore = self._calculate_zscore()

        # Entry signal: Long position on statistical oversold
        if not self.is_invested() and entry_signal and current_zscore is not None:
            # Calculate position size
            size = self.calculate_position_size(current_price)

            if size > 0:
                self.log(f"ENTRY SIGNAL: Z-Score {current_zscore:.2f} ≤ {self.params.entry_threshold} "
                        f"(Statistically Oversold) | Price: ${current_price:.2f} | Size: {size}")
                self.market_order(self.data, size)
                self.in_position = True
                self.entry_price = current_price

        # Exit signal: Close position on statistical overbought
        elif self.is_invested() and exit_signal and current_zscore is not None:
            exit_reason = f"Z-Score {current_zscore:.2f} ≥ {self.params.exit_threshold} (Statistically Overbought)"

            if self.entry_price is not None:
                exit_price = current_price
                pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100

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
        self.log(f"Z-Score Reversal Strategy ended | "
                f"Lookback: {self.params.lookback_period} | "
                f"Entry Z: ≤{self.params.entry_threshold} | Exit Z: ≥{self.params.exit_threshold} | "
                f"Final Value: ${self.broker.getvalue():,.2f}")


if __name__ == "__main__":
    """Test strategy import and basic validation."""
    print("Z-Score Reversal Strategy - Ready for use")
    print("\nParameters:")
    print(f"  Lookback Period: {ZScoreReversal.params.lookback_period}")
    print(f"  Entry Z-Score Threshold: {ZScoreReversal.params.entry_threshold}")
    print(f"  Exit Z-Score Threshold: {ZScoreReversal.params.exit_threshold}")
    print(f"  Position Size: {ZScoreReversal.params.position_size}")
    print("\n✅ Strategy loaded successfully!")
    print("\nUsage:")
    print("  from strategies.zscore_reversal import ZScoreReversal")
    print("  cerebro.addstrategy(ZScoreReversal)")
    print("  # Add data feed")
    print("  cerebro.adddata(data)")