"""
Keltner Channel Breakout Strategy
Epic 19: US-19.3 - Volatility Breakout Strategy Templates

Implements Keltner channel expansion strategy:
- Entry: Price breaks expanding Keltner channel
- Exit: Price returns to channel or volatility contraction
- Uses EMA + ATR for dynamic channel calculation

Market Conditions:
- Volatile markets with expanding ranges
- Strong momentum moves
- May produce false signals in low volatility conditions

Parameters:
- ema_period: EMA period for channel center (default: 20)
- atr_period: ATR period for channel width (default: 10)
- atr_multiplier: ATR multiplier for channel width (default: 2.0)
- expansion_threshold: Minimum channel expansion for valid breakout (default: 1.5)
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class KeltnerBreakout(BaseStrategy):
    """
    Keltner Channel Expansion Breakout Strategy for volatility-based trading.

    Uses Keltner channels (EMA + ATR bands) to identify breakouts during
    periods of expanding volatility. Enters when price breaks expanding channel.

    Entry: Price > Upper Keltner Band AND Channel is expanding
    Exit: Price returns to channel OR volatility contraction
    """

    params = (
        ('ema_period', 20),                    # EMA period for channel center
        ('atr_period', 10),                    # ATR period for channel width
        ('atr_multiplier', 2.0),               # ATR multiplier for bands
        ('expansion_threshold', 1.5),          # Min expansion for valid breakout
        ('position_size', 0.95),               # 95% of portfolio per trade
        ('printlog', True),                    # Enable logging
        ('log_trades', True),                  # Log trade execution
    )

    def __init__(self):
        """Initialize Keltner channel indicators."""
        super().__init__()

        # Keltner Channel components
        self.ema = bt.indicators.ExponentialMovingAverage(
            self.data.close,
            period=self.params.ema_period
        )

        self.atr = bt.indicators.ATR(
            self.data,
            period=self.params.atr_period
        )

        # Upper and lower Keltner bands
        self.upper_band = self.ema + (self.atr * self.params.atr_multiplier)
        self.lower_band = self.ema - (self.atr * self.params.atr_multiplier)

        # Channel width for expansion detection
        self.channel_width = self.upper_band - self.lower_band

        # State tracking
        self.in_position = False
        self.entry_price = None
        self.position_type = None  # 'long' or 'short'

        self.log(f"Keltner Breakout initialized: EMA({self.params.ema_period}), "
                f"ATR({self.params.atr_period}, {self.params.atr_multiplier}x), "
                f"Expansion Threshold({self.params.expansion_threshold})")

    def _get_channel_levels(self):
        """
        Get current Keltner channel levels.

        Returns:
            tuple: (upper_band, ema, lower_band, channel_width)
        """
        if len(self.upper_band) < 1 or len(self.lower_band) < 1 or len(self.ema) < 1:
            return None, None, None, None

        upper = self.upper_band[0]
        ema = self.ema[0]
        lower = self.lower_band[0]
        width = self.channel_width[0] if len(self.channel_width) > 0 else (upper - lower)

        return upper, ema, lower, width

    def _is_channel_expanding(self):
        """
        Check if channel is expanding (increasing volatility).

        Returns:
            True if channel width is increasing
        """
        if len(self.channel_width) < 2:
            return False

        current_width = self.channel_width[0]
        prev_width = self.channel_width[-1]

        return current_width > (prev_width * self.params.expansion_threshold)

    def _get_breakout_signals(self):
        """
        Get current breakout signals with expansion filter.

        Returns:
            tuple: (long_breakout, short_breakout)
        """
        upper, ema, lower, width = self._get_channel_levels()
        if upper is None or lower is None:
            return False, False

        current_price = self.data.close[0]
        expanding = self._is_channel_expanding()

        # Long breakout: Price above upper band AND channel expanding
        long_breakout = current_price > upper and expanding

        # Short breakout: Price below lower band AND channel expanding
        short_breakout = current_price < lower and expanding

        return long_breakout, short_breakout

    def _check_exit_conditions(self):
        """
        Check if position should be exited.

        Returns:
            tuple: (should_exit, exit_reason)
        """
        if not self.in_position or self.position_type is None:
            return False, ""

        upper, ema, lower, width = self._get_channel_levels()
        if upper is None or lower is None:
            return False, ""

        current_price = self.data.close[0]
        expanding = self._is_channel_expanding()

        # Exit conditions
        if self.position_type == 'long':
            # Exit long: Price returns to EMA or volatility contracts
            if current_price <= ema or not expanding:
                reason = "Price returned to EMA" if current_price <= ema else "Volatility contraction"
                return True, reason

        elif self.position_type == 'short':
            # Exit short: Price returns to EMA or volatility contracts
            if current_price >= ema or not expanding:
                reason = "Price returned to EMA" if current_price >= ema else "Volatility contraction"
                return True, reason

        return False, ""

    def next(self):
        """Execute Keltner breakout trading logic."""
        # Check for pending orders
        if self.has_pending_order():
            return

        # Check exit conditions first
        should_exit, exit_reason = self._check_exit_conditions()
        if should_exit:
            exit_price = self.data.close[0]

            if self.entry_price is not None:
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
            return

        # Check for entry signals
        if not self.is_invested():
            long_signal, short_signal = self._get_breakout_signals()

            if long_signal:
                # Long breakout entry
                size = self.calculate_position_size(self.data.close[0])
                if size > 0:
                    upper, ema, lower, width = self._get_channel_levels()
                    self.log(f"LONG BREAKOUT: Price ${self.data.close[0]:.2f} > Upper Band ${upper:.2f} "
                            f"with expanding channel | Size: {size}")
                    self.market_order(self.data, size)
                    self.in_position = True
                    self.entry_price = self.data.close[0]
                    self.position_type = 'long'

            elif short_signal:
                # Short breakout entry
                size = self.calculate_position_size(self.data.close[0])
                if size > 0:
                    upper, ema, lower, width = self._get_channel_levels()
                    self.log(f"SHORT BREAKOUT: Price ${self.data.close[0]:.2f} < Lower Band ${lower:.2f} "
                            f"with expanding channel | Size: {size}")
                    self.market_order(self.data, -size)  # Negative for short
                    self.in_position = True
                    self.entry_price = self.data.close[0]
                    self.position_type = 'short'

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
        self.log(f"Keltner Breakout Strategy ended | "
                f"EMA Period: {self.params.ema_period} | "
                f"ATR Period: {self.params.atr_period} | ATR Multiplier: {self.params.atr_multiplier} | "
                f"Expansion Threshold: {self.params.expansion_threshold} | "
                f"Final Value: ${self.broker.getvalue():,.2f}")


if __name__ == "__main__":
    """Test strategy import and basic validation."""
    print("Keltner Channel Breakout Strategy - Ready for use")
    print("\nParameters:")
    print(f"  EMA Period: {KeltnerBreakout.params.ema_period}")
    print(f"  ATR Period: {KeltnerBreakout.params.atr_period}")
    print(f"  ATR Multiplier: {KeltnerBreakout.params.atr_multiplier}")
    print(f"  Expansion Threshold: {KeltnerBreakout.params.expansion_threshold}")
    print(f"  Position Size: {KeltnerBreakout.params.position_size}")
    print("\n✅ Strategy loaded successfully!")
    print("\nUsage:")
    print("  from strategies.keltner_breakout import KeltnerBreakout")
    print("  cerebro.addstrategy(KeltnerBreakout)")
    print("  # Add data feed")
    print("  cerebro.adddata(data)")