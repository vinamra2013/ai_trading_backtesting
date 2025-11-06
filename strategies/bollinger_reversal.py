"""
Bollinger Band Reversal Strategy
Epic 19: US-19.2 - Mean Reversion Strategy Templates

Implements mean reversion strategy using Bollinger Bands:
- Entry: Price touches lower band + RSI oversold
- Exit: Price reaches middle band or RSI overbought

Market Conditions:
- Ranging/sideways markets
- Works best when price oscillates within bands
- May underperform in strong trending markets

Parameters:
- bb_period: Bollinger Band period (default: 20)
- bb_dev: Standard deviation multiplier (default: 2.0)
- rsi_period: RSI period for confirmation (default: 14)
- rsi_oversold: RSI oversold level (default: 30)
- rsi_overbought: RSI overbought level (default: 70)
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class BollingerReversal(BaseStrategy):
    """
    Bollinger Band Reversal Strategy for mean reversion trading.

    Uses Bollinger Bands to identify price extremes and RSI for confirmation.
    Enters long when price touches lower band and RSI is oversold.
    Exits when price reaches middle band or RSI becomes overbought.

    Entry: Price ≤ Lower Band AND RSI ≤ Oversold Level
    Exit: Price ≥ Middle Band OR RSI ≥ Overbought Level
    """

    params = (
        ('bb_period', 20),                # Bollinger Band period
        ('bb_dev', 2.0),                  # Standard deviation multiplier
        ('rsi_period', 14),               # RSI period for confirmation
        ('rsi_oversold', 30),             # RSI oversold level
        ('rsi_overbought', 70),           # RSI overbought level
        ('position_size', 0.95),          # 95% of portfolio per trade
        ('printlog', True),               # Enable logging
        ('log_trades', True),             # Log trade execution
    )

    def __init__(self):
        """Initialize Bollinger Band and RSI indicators."""
        super().__init__()

        # Bollinger Bands
        self.bbands = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.bb_period,
            devfactor=self.params.bb_dev
        )

        # RSI for confirmation
        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=self.params.rsi_period
        )

        # State tracking
        self.in_position = False
        self.entry_price = None

        self.log(f"Bollinger Reversal initialized: BB({self.params.bb_period}, {self.params.bb_dev}σ), "
                f"RSI({self.params.rsi_period}), "
                f"Oversold: {self.params.rsi_oversold}, Overbought: {self.params.rsi_overbought}")

    def _get_reversal_signals(self):
        """
        Get current reversal signals.

        Returns:
            tuple: (entry_signal, exit_signal)
        """
        if len(self.bbands) < 1 or len(self.rsi) < 1:
            return False, False

        current_price = self.data.close[0]
        lower_band = self.bbands.bot[0]  # Bottom band
        middle_band = self.bbands.mid[0]  # Middle band (SMA)
        current_rsi = self.rsi[0]

        # Entry signal: Price touches lower band AND RSI oversold
        entry_signal = (current_price <= lower_band and
                       current_rsi <= self.params.rsi_oversold)

        # Exit signal: Price reaches middle band OR RSI overbought
        exit_signal = (current_price >= middle_band or
                      current_rsi >= self.params.rsi_overbought)

        return entry_signal, exit_signal

    def next(self):
        """Execute Bollinger Band reversal trading logic."""
        # Check for pending orders
        if self.has_pending_order():
            return

        # Get current signals
        entry_signal, exit_signal = self._get_reversal_signals()

        current_price = self.data.close[0]
        current_rsi = self.rsi[0] if len(self.rsi) > 0 else None
        lower_band = self.bbands.bot[0] if len(self.bbands) > 0 else None
        middle_band = self.bbands.mid[0] if len(self.bbands) > 0 else None

        # Entry signal: Long position on oversold bounce
        if not self.is_invested() and entry_signal:
            if current_price is not None and lower_band is not None and current_rsi is not None:
                # Calculate position size
                size = self.calculate_position_size(current_price)

                if size > 0:
                    self.log(f"ENTRY SIGNAL: Price ${current_price:.2f} ≤ Lower Band ${lower_band:.2f} "
                            f"AND RSI {current_rsi:.2f} ≤ {self.params.rsi_oversold} | Size: {size}")
                    self.market_order(self.data, size)
                    self.in_position = True
                    self.entry_price = current_price

        # Exit signal: Close position on normalization
        elif self.is_invested() and exit_signal:
            exit_reason = None

            if current_price is not None and middle_band is not None and current_price >= middle_band:
                exit_reason = f"Price ${current_price:.2f} ≥ Middle Band ${middle_band:.2f}"
            elif current_rsi is not None and current_rsi >= self.params.rsi_overbought:
                exit_reason = f"RSI {current_rsi:.2f} ≥ {self.params.rsi_overbought}"

            if exit_reason and self.entry_price is not None:
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
        self.log(f"Bollinger Reversal Strategy ended | "
                f"BB Period: {self.params.bb_period} | BB Dev: {self.params.bb_dev} | "
                f"RSI Period: {self.params.rsi_period} | "
                f"Oversold: {self.params.rsi_oversold} | Overbought: {self.params.rsi_overbought} | "
                f"Final Value: ${self.broker.getvalue():,.2f}")


if __name__ == "__main__":
    """Test strategy import and basic validation."""
    print("Bollinger Band Reversal Strategy - Ready for use")
    print("\nParameters:")
    print(f"  BB Period: {BollingerReversal.params.bb_period}")
    print(f"  BB Std Dev: {BollingerReversal.params.bb_dev}")
    print(f"  RSI Period: {BollingerReversal.params.rsi_period}")
    print(f"  RSI Oversold: {BollingerReversal.params.rsi_oversold}")
    print(f"  RSI Overbought: {BollingerReversal.params.rsi_overbought}")
    print(f"  Position Size: {BollingerReversal.params.position_size}")
    print("\n✅ Strategy loaded successfully!")
    print("\nUsage:")
    print("  from strategies.bollinger_reversal import BollingerReversal")
    print("  cerebro.addstrategy(BollingerReversal)")
    print("  # Add data feed")
    print("  cerebro.adddata(data)")