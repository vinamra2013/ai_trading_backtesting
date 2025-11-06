"""
RSI Reversal Strategy
Epic 19: US-19.2 - Mean Reversion Strategy Templates

Implements pure RSI-based mean reversion strategy:
- Entry: RSI < 30 (oversold)
- Exit: RSI > 70 (overbought)

Market Conditions:
- Ranging/sideways markets
- Works best when RSI oscillates between oversold/overbought levels
- May produce whipsaws in strong trends

Parameters:
- rsi_period: RSI calculation period (default: 14)
- rsi_oversold: Oversold threshold (default: 30)
- rsi_overbought: Overbought threshold (default: 70)
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class RSIReversal(BaseStrategy):
    """
    RSI Reversal Strategy for mean reversion trading.

    Uses RSI to identify overbought and oversold conditions.
    Enters long when RSI drops below oversold level.
    Exits when RSI rises above overbought level.

    Entry: RSI ≤ Oversold Level
    Exit: RSI ≥ Overbought Level
    """

    params = (
        ('rsi_period', 14),               # RSI calculation period
        ('rsi_oversold', 30),             # Oversold threshold
        ('rsi_overbought', 70),           # Overbought threshold
        ('position_size', 0.95),          # 95% of portfolio per trade
        ('printlog', True),               # Enable logging
        ('log_trades', True),             # Log trade execution
    )

    def __init__(self):
        """Initialize RSI indicator and state."""
        super().__init__()

        # RSI indicator
        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=self.params.rsi_period
        )

        # State tracking
        self.in_position = False
        self.entry_price = None

        self.log(f"RSI Reversal initialized: RSI({self.params.rsi_period}), "
                f"Oversold: {self.params.rsi_oversold}, Overbought: {self.params.rsi_overbought}")

    def _get_rsi_signals(self):
        """
        Get current RSI reversal signals.

        Returns:
            tuple: (entry_signal, exit_signal)
        """
        if len(self.rsi) < 1:
            return False, False

        current_rsi = self.rsi[0]

        # Entry signal: RSI drops to oversold level
        entry_signal = current_rsi <= self.params.rsi_oversold

        # Exit signal: RSI rises to overbought level
        exit_signal = current_rsi >= self.params.rsi_overbought

        return entry_signal, exit_signal

    def next(self):
        """Execute RSI reversal trading logic."""
        # Check for pending orders
        if self.has_pending_order():
            return

        # Get current signals
        entry_signal, exit_signal = self._get_rsi_signals()

        current_price = self.data.close[0]
        current_rsi = self.rsi[0] if len(self.rsi) > 0 else None

        # Entry signal: Long position on oversold
        if not self.is_invested() and entry_signal and current_rsi is not None:
            # Calculate position size
            size = self.calculate_position_size(current_price)

            if size > 0:
                self.log(f"ENTRY SIGNAL: RSI {current_rsi:.2f} ≤ {self.params.rsi_oversold} "
                        f"(Oversold) | Price: ${current_price:.2f} | Size: {size}")
                self.market_order(self.data, size)
                self.in_position = True
                self.entry_price = current_price

        # Exit signal: Close position on overbought
        elif self.is_invested() and exit_signal and current_rsi is not None:
            exit_reason = f"RSI {current_rsi:.2f} ≥ {self.params.rsi_overbought} (Overbought)"

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
        self.log(f"RSI Reversal Strategy ended | "
                f"RSI Period: {self.params.rsi_period} | "
                f"Oversold: {self.params.rsi_oversold} | Overbought: {self.params.rsi_overbought} | "
                f"Final Value: ${self.broker.getvalue():,.2f}")


if __name__ == "__main__":
    """Test strategy import and basic validation."""
    print("RSI Reversal Strategy - Ready for use")
    print("\nParameters:")
    print(f"  RSI Period: {RSIReversal.params.rsi_period}")
    print(f"  RSI Oversold: {RSIReversal.params.rsi_oversold}")
    print(f"  RSI Overbought: {RSIReversal.params.rsi_overbought}")
    print(f"  Position Size: {RSIReversal.params.position_size}")
    print("\n✅ Strategy loaded successfully!")
    print("\nUsage:")
    print("  from strategies.rsi_reversal import RSIReversal")
    print("  cerebro.addstrategy(RSIReversal)")
    print("  # Add data feed")
    print("  cerebro.adddata(data)")