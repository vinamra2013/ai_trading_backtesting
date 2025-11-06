"""
Dual Momentum Strategy
Epic 19: US-19.1 - Momentum Strategy Templates

Implements dual momentum strategy combining relative and absolute momentum:
- Relative momentum: Asset performance vs benchmark (SPY)
- Absolute momentum: Asset performance vs its own history (200-day MA)

Entry Signal:
- Both relative and absolute momentum positive

Exit Signal:
- Either momentum turns negative

Market Conditions:
- Trending markets (bull/bear markets)
- Works best in strong directional moves
- May underperform in sideways/choppy markets

Parameters:
- relative_period: Lookback period for relative momentum (default: 252, ~1 year)
- absolute_period: Lookback period for absolute momentum (default: 200, ~1 year)
- benchmark_symbol: Benchmark for relative comparison (default: SPY)
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class DualMomentum(BaseStrategy):
    """
    Dual Momentum Strategy combining relative and absolute momentum filters.

    Relative Momentum:
    - Compares asset performance vs benchmark over specified period
    - Positive when asset outperforms benchmark

    Absolute Momentum:
    - Compares current price vs moving average over specified period
    - Positive when price > moving average (uptrend)

    Entry: Both relative and absolute momentum positive
    Exit: Either momentum becomes negative
    """

    params = (
        ('relative_period', 252),        # ~1 year for relative momentum
        ('absolute_period', 200),        # 200-day MA for absolute momentum
        ('benchmark_symbol', 'SPY'),     # Benchmark for relative comparison
        ('position_size', 0.95),         # 95% of portfolio per trade
        ('printlog', True),              # Enable logging
        ('log_trades', True),            # Log trade execution
    )

    def __init__(self):
        """Initialize dual momentum indicators and state."""
        super().__init__()

        # Get data feeds - assume primary data is asset, benchmark is second data
        self.asset_data = self.datas[0]
        self.benchmark_data = None

        # Find benchmark data feed
        for data in self.datas:
            if hasattr(data, '_name') and data._name == self.params.benchmark_symbol:
                self.benchmark_data = data
                break

        if self.benchmark_data is None:
            self.log(f"WARNING: Benchmark symbol '{self.params.benchmark_symbol}' not found in data feeds",
                    level='WARNING')
            # Fallback: use asset's own performance for relative momentum
            self.benchmark_data = self.asset_data

        # Absolute momentum: Price vs moving average
        self.absolute_ma = bt.indicators.SimpleMovingAverage(
            self.asset_data.close,
            period=self.params.absolute_period
        )

        # Relative momentum: Asset return vs benchmark return
        # Calculate percentage change over the period
        self.asset_returns = bt.indicators.PctChange(
            self.asset_data.close,
            period=self.params.relative_period
        )

        self.benchmark_returns = bt.indicators.PctChange(
            self.benchmark_data.close,
            period=self.params.relative_period
        )

        # State tracking
        self.in_position = False
        self.entry_price = None

        self.log(f"Dual Momentum initialized: Relative({self.params.relative_period}d) vs {self.params.benchmark_symbol}, "
                f"Absolute({self.params.absolute_period}d MA)")

    def _calculate_relative_momentum(self):
        """
        Calculate relative momentum: Asset return vs benchmark return.

        Returns:
            True if asset outperforms benchmark, False otherwise
        """
        if len(self.asset_returns) < 1 or len(self.benchmark_returns) < 1:
            return False

        asset_return = self.asset_returns[0]
        benchmark_return = self.benchmark_returns[0]

        return asset_return > benchmark_return

    def _calculate_absolute_momentum(self):
        """
        Calculate absolute momentum: Current price vs moving average.

        Returns:
            True if price > MA (uptrend), False otherwise
        """
        if len(self.absolute_ma) < 1:
            return False

        current_price = self.asset_data.close[0]
        ma_value = self.absolute_ma[0]

        return current_price > ma_value

    def _get_momentum_signals(self):
        """
        Get current momentum signals.

        Returns:
            tuple: (relative_momentum, absolute_momentum)
        """
        relative_mom = self._calculate_relative_momentum()
        absolute_mom = self._calculate_absolute_momentum()

        return relative_mom, absolute_mom

    def next(self):
        """Execute dual momentum trading logic."""
        # Check for pending orders
        if self.has_pending_order():
            return

        # Get current momentum signals
        relative_mom, absolute_mom = self._get_momentum_signals()

        current_price = self.asset_data.close[0]

        # Entry signal: Both momentums positive
        if not self.is_invested():
            if relative_mom and absolute_mom:
                # Calculate position size
                size = self.calculate_position_size(current_price)

                if size > 0:
                    self.log(f"ENTRY SIGNAL: Relative(+), Absolute(+) | "
                            f"Price: ${current_price:.2f} | Size: {size}")
                    self.market_order(self.asset_data, size)
                    self.in_position = True
                    self.entry_price = current_price

        # Exit signal: Either momentum turns negative
        elif self.is_invested():
            exit_reason = None

            if not relative_mom:
                exit_reason = "Relative momentum negative"
            elif not absolute_mom:
                exit_reason = "Absolute momentum negative"

            if exit_reason:
                exit_price = current_price
                pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100

                self.log(f"EXIT SIGNAL: {exit_reason} | "
                        f"Entry: ${self.entry_price:.2f} | Exit: ${exit_price:.2f} | "
                        f"P&L: {pnl_pct:+.2f}%")
                self.close_position(self.asset_data)
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
        self.log(f"Dual Momentum Strategy ended | "
                f"Relative Period: {self.params.relative_period}d | "
                f"Absolute Period: {self.params.absolute_period}d | "
                f"Benchmark: {self.params.benchmark_symbol} | "
                f"Final Value: ${self.broker.getvalue():,.2f}")


if __name__ == "__main__":
    """Test strategy import and basic validation."""
    print("Dual Momentum Strategy - Ready for use")
    print("\nParameters:")
    print(f"  Relative Period: {DualMomentum.params.relative_period}")
    print(f"  Absolute Period: {DualMomentum.params.absolute_period}")
    print(f"  Benchmark Symbol: {DualMomentum.params.benchmark_symbol}")
    print(f"  Position Size: {DualMomentum.params.position_size}")
    print("\n✅ Strategy loaded successfully!")
    print("\nUsage:")
    print("  from strategies.dual_momentum import DualMomentum")
    print("  cerebro.addstrategy(DualMomentum)")
    print("  # Add both asset and SPY data feeds")
    print("  cerebro.adddata(asset_data)")
    print("  cerebro.adddata(spy_data, name='SPY')")