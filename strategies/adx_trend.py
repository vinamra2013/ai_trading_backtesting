"""
ADX Trend Filter Strategy
Epic 19: US-19.4 - Timing Indicator Strategy Templates

Implements ADX trend strength filter strategy:
- Uses ADX to measure trend strength
- Entry: ADX > threshold (trending market)
- Exit: ADX < threshold (sideways market)
- Can be combined with other strategies as a trend filter

Market Conditions:
- All market conditions (trending or ranging)
- ADX > 25 indicates trending markets
- ADX < 20 indicates ranging markets
- ADX 20-25 is neutral

Parameters:
- adx_period: ADX calculation period (default: 14)
- trend_threshold: ADX level for trend confirmation (default: 25)
- exit_threshold: ADX level for exit (default: 20)
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class ADXTrend(BaseStrategy):
    """
    ADX Trend Filter Strategy for identifying trending vs ranging markets.

    Uses Average Directional Index (ADX) to measure trend strength.
    Enters when ADX indicates strong trend, exits when trend weakens.

    Entry: ADX crosses above trend threshold (trending market)
    Exit: ADX crosses below exit threshold (ranging market)

    This strategy can be used as a filter for other strategies.
    """

    params = (
        ('adx_period', 14),               # ADX calculation period
        ('trend_threshold', 25),          # ADX level for trend entry
        ('exit_threshold', 20),            # ADX level for exit
        ('position_size', 0.95),          # 95% of portfolio per trade
        ('printlog', True),               # Enable logging
        ('log_trades', True),             # Log trade execution
    )

    def __init__(self):
        """Initialize ADX indicators."""
        super().__init__()

        # ADX indicator
        self.adx = bt.indicators.ADX(
            self.data,
            period=self.params.adx_period
        )

        # State tracking
        self.in_position = False
        self.entry_price = None
        self.position_type = None  # 'long' or 'short'

        self.log(f"ADX Trend initialized: ADX({self.params.adx_period}), "
                f"Trend Threshold: {self.params.trend_threshold}, "
                f"Exit Threshold: {self.params.exit_threshold}")

    def _get_adx_signals(self):
        """
        Get current ADX trend signals.

        Returns:
            tuple: (entry_signal, exit_signal)
        """
        if len(self.adx) < 2:
            return False, False

        current_adx = self.adx[0]
        prev_adx = self.adx[-1]

        # Entry signal: ADX crosses above trend threshold
        entry_signal = (prev_adx <= self.params.trend_threshold and
                       current_adx > self.params.trend_threshold)

        # Exit signal: ADX crosses below exit threshold
        exit_signal = (prev_adx >= self.params.exit_threshold and
                      current_adx < self.params.exit_threshold)

        return entry_signal, exit_signal

    def _get_trend_direction(self):
        """
        Get trend direction based on DI+ and DI-.

        Returns:
            str: 'up', 'down', or 'neutral'
        """
        if not hasattr(self.adx, 'di_plus') or not hasattr(self.adx, 'di_minus'):
            return 'neutral'

        if len(self.adx.di_plus) < 1 or len(self.adx.di_minus) < 1:
            return 'neutral'

        di_plus = self.adx.di_plus[0]
        di_minus = self.adx.di_minus[0]

        if di_plus > di_minus:
            return 'up'
        elif di_minus > di_plus:
            return 'down'
        else:
            return 'neutral'

    def next(self):
        """Execute ADX trend trading logic."""
        # Check for pending orders
        if self.has_pending_order():
            return

        # Get current signals
        entry_signal, exit_signal = self._get_adx_signals()

        current_price = self.data.close[0]
        current_adx = self.adx[0] if len(self.adx) > 0 else None
        trend_direction = self._get_trend_direction()

        # Entry signals
        if not self.is_invested() and entry_signal and current_adx is not None:
            # Determine position type based on trend direction
            if trend_direction == 'up':
                position_type = 'long'
                signal_desc = f"ADX {current_adx:.2f} > {self.params.trend_threshold} (Uptrend)"
            elif trend_direction == 'down':
                position_type = 'short'
                signal_desc = f"ADX {current_adx:.2f} > {self.params.trend_threshold} (Downtrend)"
            else:
                # Default to long if direction unclear
                position_type = 'long'
                signal_desc = f"ADX {current_adx:.2f} > {self.params.trend_threshold} (Neutral)"

            size = self.calculate_position_size(current_price)
            if size > 0:
                if position_type == 'long':
                    self.log(f"LONG ENTRY: {signal_desc} | Price: ${current_price:.2f} | Size: {size}")
                    self.market_order(self.data, size)
                else:
                    self.log(f"SHORT ENTRY: {signal_desc} | Price: ${current_price:.2f} | Size: {size}")
                    self.market_order(self.data, -size)  # Negative for short

                self.in_position = True
                self.entry_price = current_price
                self.position_type = position_type

        # Exit signals
        elif self.is_invested() and exit_signal and current_adx is not None:
            exit_reason = f"ADX {current_adx:.2f} < {self.params.exit_threshold} (Ranging market)"

            if self.entry_price is not None:
                exit_price = current_price
                pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100
                if self.position_type == 'short':
                    pnl_pct = -pnl_pct  # Reverse for short positions

                self.log(f"EXIT SIGNAL: {exit_reason} | "
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
        self.log(f"ADX Trend Strategy ended | "
                f"ADX Period: {self.params.adx_period} | "
                f"Trend Threshold: {self.params.trend_threshold} | "
                f"Exit Threshold: {self.params.exit_threshold} | "
                f"Final Value: ${self.broker.getvalue():,.2f}")


if __name__ == "__main__":
    """Test strategy import and basic validation."""
    print("ADX Trend Filter Strategy - Ready for use")
    print("\nParameters:")
    print(f"  ADX Period: {ADXTrend.params.adx_period}")
    print(f"  Trend Threshold: {ADXTrend.params.trend_threshold}")
    print(f"  Exit Threshold: {ADXTrend.params.exit_threshold}")
    print(f"  Position Size: {ADXTrend.params.position_size}")
    print("\n✅ Strategy loaded successfully!")
    print("\nUsage:")
    print("  from strategies.adx_trend import ADXTrend")
    print("  cerebro.addstrategy(ADXTrend)")
    print("  # Add data feed")
    print("  cerebro.adddata(data)")