"""
ATR Breakout Strategy
Epic 19: US-19.3 - Volatility Breakout Strategy Templates

Implements volatility-based breakout strategy using Average True Range (ATR):
- Entry: Price breaks recent high/low by ATR multiple
- Stop Loss: Based on ATR volatility measure
- Works best in volatile markets with clear breakouts

Market Conditions:
- Volatile markets with expanding ranges
- Breakout patterns with increasing volume
- May produce false signals in choppy/sideways markets

Parameters:
- atr_period: ATR calculation period (default: 14)
- breakout_multiplier: ATR multiple for breakout threshold (default: 2.0)
- lookback_period: Period for recent high/low calculation (default: 20)
- stop_loss_multiplier: ATR multiple for stop loss (default: 1.5)
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class ATRBreakout(BaseStrategy):
    """
    ATR Breakout Strategy for volatility-based trading.

    Uses Average True Range to identify breakouts from recent ranges.
    Enters long when price breaks above recent high by ATR multiple.
    Enters short when price breaks below recent low by ATR multiple.

    Entry: Price > Recent High + (ATR × Multiplier) [LONG]
           Price < Recent Low - (ATR × Multiplier) [SHORT]
    Stop Loss: Based on ATR volatility measure
    """

    params = (
        ('atr_period', 14),                    # ATR calculation period
        ('breakout_multiplier', 2.0),          # ATR multiple for breakout
        ('lookback_period', 20),               # Period for recent high/low
        ('stop_loss_multiplier', 1.5),         # ATR multiple for stop loss
        ('position_size', 0.95),               # 95% of portfolio per trade
        ('printlog', True),                    # Enable logging
        ('log_trades', True),                  # Log trade execution
    )

    def __init__(self):
        """Initialize ATR and breakout indicators."""
        super().__init__()

        # ATR indicator for volatility measurement
        self.atr = bt.indicators.ATR(
            self.data,
            period=self.params.atr_period
        )

        # Rolling highest high and lowest low
        self.highest_high = bt.indicators.Highest(
            self.data.high,
            period=self.params.lookback_period
        )

        self.lowest_low = bt.indicators.Lowest(
            self.data.low,
            period=self.params.lookback_period
        )

        # State tracking
        self.in_position = False
        self.entry_price = None
        self.stop_loss_price = None
        self.position_type = None  # 'long' or 'short'

        self.log(f"ATR Breakout initialized: ATR({self.params.atr_period}), "
                f"Breakout Multiplier({self.params.breakout_multiplier}), "
                f"Lookback({self.params.lookback_period}), "
                f"Stop Loss Multiplier({self.params.stop_loss_multiplier})")

    def _calculate_breakout_levels(self):
        """
        Calculate breakout entry levels.

        Returns:
            tuple: (long_entry_level, short_entry_level)
        """
        if len(self.atr) < 1 or len(self.highest_high) < 1 or len(self.lowest_low) < 1:
            return None, None

        current_atr = self.atr[0]
        recent_high = self.highest_high[0]
        recent_low = self.lowest_low[0]

        # Long breakout: Recent high + (ATR × multiplier)
        long_breakout = recent_high + (current_atr * self.params.breakout_multiplier)

        # Short breakout: Recent low - (ATR × multiplier)
        short_breakout = recent_low - (current_atr * self.params.breakout_multiplier)

        return long_breakout, short_breakout

    def _calculate_stop_loss(self, entry_price, position_type):
        """
        Calculate stop loss level based on ATR.

        Args:
            entry_price: Entry price
            position_type: 'long' or 'short'

        Returns:
            Stop loss price
        """
        if len(self.atr) < 1:
            return None

        current_atr = self.atr[0]
        stop_distance = current_atr * self.params.stop_loss_multiplier

        if position_type == 'long':
            return entry_price - stop_distance
        elif position_type == 'short':
            return entry_price + stop_distance

        return None

    def _get_breakout_signals(self):
        """
        Get current breakout signals.

        Returns:
            tuple: (long_signal, short_signal)
        """
        current_price = self.data.close[0]
        long_level, short_level = self._calculate_breakout_levels()

        if long_level is None or short_level is None:
            return False, False

        # Long signal: Price breaks above long breakout level
        long_signal = current_price > long_level

        # Short signal: Price breaks below short breakout level
        short_signal = current_price < short_level

        return long_signal, short_signal

    def next(self):
        """Execute ATR breakout trading logic."""
        # Check for pending orders
        if self.has_pending_order():
            return

        # Get current breakout signals
        long_signal, short_signal = self._get_breakout_signals()

        current_price = self.data.close[0]

        # Check stop loss first (if in position)
        if self.is_invested() and self.stop_loss_price is not None:
            if self.position_type == 'long' and current_price <= self.stop_loss_price:
                self.log(f"STOP LOSS: Long position stopped at ${current_price:.2f} "
                        f"(Stop: ${self.stop_loss_price:.2f})")
                self.close_position(self.data)
                self.in_position = False
                self.entry_price = None
                self.stop_loss_price = None
                self.position_type = None
                return
            elif self.position_type == 'short' and current_price >= self.stop_loss_price:
                self.log(f"STOP LOSS: Short position stopped at ${current_price:.2f} "
                        f"(Stop: ${self.stop_loss_price:.2f})")
                self.close_position(self.data)
                self.in_position = False
                self.entry_price = None
                self.stop_loss_price = None
                self.position_type = None
                return

        # Entry signals
        if not self.is_invested():
            # Long breakout entry
            if long_signal:
                size = self.calculate_position_size(current_price)
                if size > 0:
                    self.log(f"LONG BREAKOUT: Price ${current_price:.2f} breaks resistance | Size: {size}")
                    self.market_order(self.data, size)
                    self.in_position = True
                    self.entry_price = current_price
                    self.position_type = 'long'
                    self.stop_loss_price = self._calculate_stop_loss(current_price, 'long')

            # Short breakout entry
            elif short_signal:
                size = self.calculate_position_size(current_price)
                if size > 0:
                    self.log(f"SHORT BREAKOUT: Price ${current_price:.2f} breaks support | Size: {size}")
                    self.market_order(self.data, -size)  # Negative size for short
                    self.in_position = True
                    self.entry_price = current_price
                    self.position_type = 'short'
                    self.stop_loss_price = self._calculate_stop_loss(current_price, 'short')

    def notify_order(self, order):
        """Handle order notifications."""
        super().notify_order(order)

        if order.status in [order.Completed]:
            if order.isbuy():
                self.in_position = True
                self.position_type = 'long'
                self.entry_price = order.executed.price
                self.stop_loss_price = self._calculate_stop_loss(order.executed.price, 'long')
            elif order.issell():
                self.in_position = True
                self.position_type = 'short'
                self.entry_price = order.executed.price
                self.stop_loss_price = self._calculate_stop_loss(order.executed.price, 'short')

    def stop(self):
        """Strategy cleanup and final reporting."""
        self.log(f"ATR Breakout Strategy ended | "
                f"ATR Period: {self.params.atr_period} | "
                f"Breakout Multiplier: {self.params.breakout_multiplier} | "
                f"Lookback: {self.params.lookback_period} | "
                f"Stop Loss Multiplier: {self.params.stop_loss_multiplier} | "
                f"Final Value: ${self.broker.getvalue():,.2f}")


if __name__ == "__main__":
    """Test strategy import and basic validation."""
    print("ATR Breakout Strategy - Ready for use")
    print("\nParameters:")
    print(f"  ATR Period: {ATRBreakout.params.atr_period}")
    print(f"  Breakout Multiplier: {ATRBreakout.params.breakout_multiplier}")
    print(f"  Lookback Period: {ATRBreakout.params.lookback_period}")
    print(f"  Stop Loss Multiplier: {ATRBreakout.params.stop_loss_multiplier}")
    print(f"  Position Size: {ATRBreakout.params.position_size}")
    print("\n✅ Strategy loaded successfully!")
    print("\nUsage:")
    print("  from strategies.atr_breakout import ATRBreakout")
    print("  cerebro.addstrategy(ATRBreakout)")
    print("  # Add data feed")
    print("  cerebro.adddata(data)")