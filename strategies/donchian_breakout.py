"""
Donchian Breakout Strategy
Epic 19: US-19.3 - Volatility Breakout Strategy Templates

Implements Donchian channel breakout strategy:
- Entry: Price breaks upper/lower channel boundary
- Exit: Price reaches opposite channel boundary or time-based
- Works best in trending markets with clear channel breakouts

Market Conditions:
- Strong trending markets
- Clear channel formations
- May produce false signals in choppy/sideways markets

Parameters:
- channel_period: Donchian channel period (default: 20)
- breakout_confirm: Bars to wait for breakout confirmation (default: 1)
- exit_type: 'opposite' for opposite boundary, 'time' for time-based (default: 'opposite')
- max_hold_period: Maximum bars to hold position if time-based exit (default: 20)
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class DonchianBreakout(BaseStrategy):
    """
    Donchian Channel Breakout Strategy for trend-following trading.

    Uses Donchian channels to identify breakouts from trading ranges.
    Enters long when price breaks above upper channel.
    Enters short when price breaks below lower channel.

    Entry: Price > Upper Channel [LONG] or Price < Lower Channel [SHORT]
    Exit: Price reaches opposite channel boundary or time-based exit
    """

    params = (
        ('channel_period', 20),           # Donchian channel period
        ('breakout_confirm', 1),          # Bars to confirm breakout
        ('exit_type', 'opposite'),        # 'opposite' or 'time'
        ('max_hold_period', 20),          # Max bars to hold if time-based
        ('position_size', 0.95),          # 95% of portfolio per trade
        ('printlog', True),               # Enable logging
        ('log_trades', True),             # Log trade execution
    )

    def __init__(self):
        """Initialize Donchian channel indicators."""
        super().__init__()

        # Donchian channel: Highest high and lowest low over period
        self.donchian_high = bt.indicators.Highest(
            self.data.high,
            period=self.params.channel_period
        )

        self.donchian_low = bt.indicators.Lowest(
            self.data.low,
            period=self.params.channel_period
        )

        # Middle channel (optional for reference)
        self.donchian_mid = (self.donchian_high + self.donchian_low) / 2

        # State tracking
        self.in_position = False
        self.entry_price = None
        self.position_type = None  # 'long' or 'short'
        self.entry_bar = None
        self.breakout_detected = False
        self.confirmation_count = 0

        self.log(f"Donchian Breakout initialized: Channel({self.params.channel_period}), "
                f"Confirmation({self.params.breakout_confirm}), "
                f"Exit({self.params.exit_type})")

    def _get_channel_levels(self):
        """
        Get current Donchian channel levels.

        Returns:
            tuple: (upper_channel, lower_channel, middle_channel)
        """
        if len(self.donchian_high) < 1 or len(self.donchian_low) < 1:
            return None, None, None

        upper = self.donchian_high[0]
        lower = self.donchian_low[0]
        middle = self.donchian_mid[0] if len(self.donchian_mid) > 0 else (upper + lower) / 2

        return upper, lower, middle

    def _check_breakout_signals(self):
        """
        Check for breakout signals with confirmation.

        Returns:
            tuple: (long_breakout, short_breakout)
        """
        upper, lower, middle = self._get_channel_levels()
        if upper is None or lower is None:
            return False, False

        current_high = self.data.high[0]
        current_low = self.data.low[0]

        # Check for breakouts
        long_breakout = current_high > upper
        short_breakout = current_low < lower

        # Apply confirmation logic
        if self.params.breakout_confirm > 1:
            if long_breakout and not self.breakout_detected:
                self.confirmation_count += 1
                if self.confirmation_count >= self.params.breakout_confirm:
                    self.breakout_detected = True
                    self.confirmation_count = 0
                    return True, False
                else:
                    return False, False
            elif short_breakout and not self.breakout_detected:
                self.confirmation_count += 1
                if self.confirmation_count >= self.params.breakout_confirm:
                    self.breakout_detected = True
                    self.confirmation_count = 0
                    return False, True
                else:
                    return False, False
            else:
                # Reset if breakout condition no longer met
                if not long_breakout and not short_breakout:
                    self.confirmation_count = 0
                return False, False
        else:
            # No confirmation needed
            return long_breakout, short_breakout

    def _check_exit_conditions(self):
        """
        Check if position should be exited.

        Returns:
            True if position should be closed
        """
        if not self.in_position or self.position_type is None:
            return False

        upper, lower, middle = self._get_channel_levels()
        if upper is None or lower is None:
            return False

        current_price = self.data.close[0]

        # Opposite boundary exit
        if self.params.exit_type == 'opposite':
            if self.position_type == 'long' and current_price <= lower:
                return True
            elif self.position_type == 'short' and current_price >= upper:
                return True

        # Time-based exit
        elif self.params.exit_type == 'time':
            if self.entry_bar is not None:
                bars_held = len(self) - self.entry_bar
                if bars_held >= self.params.max_hold_period:
                    return True

        return False

    def next(self):
        """Execute Donchian breakout trading logic."""
        # Check for pending orders
        if self.has_pending_order():
            return

        # Check exit conditions first
        if self._check_exit_conditions():
            exit_reason = "Opposite boundary exit" if self.params.exit_type == 'opposite' else "Time-based exit"
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
            self.entry_bar = None
            self.breakout_detected = False
            return

        # Check for entry signals
        if not self.is_invested():
            long_signal, short_signal = self._check_breakout_signals()

            if long_signal:
                # Long breakout entry
                size = self.calculate_position_size(self.data.close[0])
                if size > 0:
                    upper, lower, middle = self._get_channel_levels()
                    self.log(f"LONG BREAKOUT: Price ${self.data.close[0]:.2f} > Upper Channel ${upper:.2f} | Size: {size}")
                    self.market_order(self.data, size)
                    self.in_position = True
                    self.entry_price = self.data.close[0]
                    self.position_type = 'long'
                    self.entry_bar = len(self)

            elif short_signal:
                # Short breakout entry
                size = self.calculate_position_size(self.data.close[0])
                if size > 0:
                    upper, lower, middle = self._get_channel_levels()
                    self.log(f"SHORT BREAKOUT: Price ${self.data.close[0]:.2f} < Lower Channel ${lower:.2f} | Size: {size}")
                    self.market_order(self.data, -size)  # Negative for short
                    self.in_position = True
                    self.entry_price = self.data.close[0]
                    self.position_type = 'short'
                    self.entry_bar = len(self)

    def notify_order(self, order):
        """Handle order notifications."""
        super().notify_order(order)

        if order.status in [order.Completed]:
            if order.isbuy():
                self.in_position = True
                self.position_type = 'long'
                self.entry_price = order.executed.price
                self.entry_bar = len(self)
            elif order.issell():
                self.in_position = True
                self.position_type = 'short'
                self.entry_price = order.executed.price
                self.entry_bar = len(self)

    def stop(self):
        """Strategy cleanup and final reporting."""
        self.log(f"Donchian Breakout Strategy ended | "
                f"Channel Period: {self.params.channel_period} | "
                f"Breakout Confirm: {self.params.breakout_confirm} | "
                f"Exit Type: {self.params.exit_type} | "
                f"Final Value: ${self.broker.getvalue():,.2f}")


if __name__ == "__main__":
    """Test strategy import and basic validation."""
    print("Donchian Breakout Strategy - Ready for use")
    print("\nParameters:")
    print(f"  Channel Period: {DonchianBreakout.params.channel_period}")
    print(f"  Breakout Confirmation: {DonchianBreakout.params.breakout_confirm}")
    print(f"  Exit Type: {DonchianBreakout.params.exit_type}")
    print(f"  Max Hold Period: {DonchianBreakout.params.max_hold_period}")
    print(f"  Position Size: {DonchianBreakout.params.position_size}")
    print("\n✅ Strategy loaded successfully!")
    print("\nUsage:")
    print("  from strategies.donchian_breakout import DonchianBreakout")
    print("  cerebro.addstrategy(DonchianBreakout)")
    print("  # Add data feed")
    print("  cerebro.adddata(data)")