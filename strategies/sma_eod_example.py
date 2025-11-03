"""
SMA Crossover with EOD Procedures
Example demonstrating full integration of:
- EODStrategy (automatic liquidation at 3:55 PM)
- RiskManager (position limits, loss limits)
- DBLogger (trade tracking)

This is a production-ready example showing best practices.
"""

import backtrader as bt
from strategies.eod_strategy import EODStrategy


class SMAEODExample(EODStrategy):
    """
    SMA crossover strategy with EOD procedures.

    Demonstrates complete integration:
    - Inherits from EODStrategy (not BaseStrategy)
    - Auto-liquidates at 3:55 PM
    - Risk-managed position sizing
    - Database logging (when enabled)
    - Daily resets

    Signals:
    - Buy when fast SMA > slow SMA
    - Sell when fast SMA < slow SMA
    - Force liquidate at 3:55 PM regardless of signals
    """

    params = (
        # Strategy params
        ('fast_period', 10),
        ('slow_period', 30),

        # EOD params (inherited from EODStrategy)
        ('eod_liquidate', True),
        ('eod_hour', 15),
        ('eod_minute', 55),

        # Risk params (inherited from EODStrategy)
        ('enable_risk_manager', True),
        ('daily_loss_limit', 0.02),
        ('max_drawdown', 0.20),
        ('max_position_pct', 0.95),

        # DB logging (set to True for production)
        ('enable_db_logging', False),
        ('algorithm_name', 'SMAEODExample'),

        # Base params
        ('printlog', True),
    )

    def __init__(self):
        """Initialize indicators."""
        # IMPORTANT: Call parent first to get EOD, risk, and DB logging
        super().__init__()

        # Create SMA indicators
        self.sma_fast = bt.indicators.SimpleMovingAverage(
            self.data.close,
            period=self.params.fast_period
        )

        self.sma_slow = bt.indicators.SimpleMovingAverage(
            self.data.close,
            period=self.params.slow_period
        )

        # Crossover signal
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)

        # Track order
        self.order = None

        self.log(f"SMA EOD Example initialized: Fast={self.params.fast_period}, Slow={self.params.slow_period}")

    def next(self):
        """Main trading logic with EOD checks."""
        # CRITICAL: Call parent first to handle EOD, daily reset, DB logging
        super().next()

        # Skip if we have a pending order
        if self.order:
            return

        # Skip if we're near EOD time (parent handles this check)
        if not self.should_trade():
            # Log why we're not trading
            if self.is_eod_time():
                self.log("Skipping trade: EOD time reached", level='DEBUG')
            return

        # Get current position
        position_size = self.get_position_size()

        # Entry Logic: No position + golden cross
        if not self.is_invested():
            if self.crossover[0] > 0:  # Fast SMA crossed above slow SMA
                # Calculate position size
                cash = self.get_cash()
                price = self.data.close[0]
                size = int((cash * self.params.position_size) / price)

                # Risk check (if risk manager enabled)
                if self.risk_manager:
                    can_trade, msg = self.risk_manager.can_trade(size, price, self.data)

                    if not can_trade:
                        self.log(f'BUY SIGNAL BLOCKED by risk manager: {msg}', level='WARNING')

                        # Log risk event to DB if enabled
                        if self.db_logger:
                            self.db_logger.log_risk_event(
                                event_type='POSITION_LIMIT',
                                severity='WARNING',
                                message=f'Trade blocked: {msg}',
                                symbol=self.data._name,
                                portfolio_value=self.broker.getvalue(),
                                position_value=size * price
                            )
                        return

                # Place order
                self.log(f'BUY SIGNAL: Golden Cross | Fast SMA: {self.sma_fast[0]:.2f}, '
                        f'Slow SMA: {self.sma_slow[0]:.2f} | Size: {size} shares @ ${price:.2f}')
                self.order = self.buy(size=size)

        # Exit Logic: Has position + death cross
        elif self.crossover[0] < 0:  # Fast SMA crossed below slow SMA
            self.log(f'SELL SIGNAL: Death Cross | Fast SMA: {self.sma_fast[0]:.2f}, '
                    f'Slow SMA: {self.sma_slow[0]:.2f}')
            self.order = self.close()

    def notify_order(self, order):
        """Handle order notifications."""
        # Call parent to handle logging
        super().notify_order(order)

        # Clear order reference
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None

    def stop(self):
        """Called when strategy ends."""
        # Print risk summary if risk manager enabled
        if self.risk_manager:
            risk_summary = self.risk_manager.get_risk_summary()
            self.log("="*60)
            self.log("RISK SUMMARY")
            self.log("="*60)
            self.log(f"Peak Value: ${risk_summary['peak_value']:,.2f}")
            self.log(f"Final Value: ${risk_summary['portfolio_value']:,.2f}")
            self.log(f"Max Drawdown: {risk_summary['current_drawdown']*100:.2f}%")
            self.log(f"Risk Events: {risk_summary['risk_events_count']}")

        # Call parent to save daily summary
        super().stop()


if __name__ == "__main__":
    print("SMA EOD Example Strategy")
    print("\nDemonstrates:")
    print("  ✓ EOD liquidation at 3:55 PM")
    print("  ✓ Risk management (position limits, loss limits)")
    print("  ✓ Database logging (orders, positions, risk events)")
    print("  ✓ Daily resets and summaries")
    print("\nUsage:")
    print("  python scripts/run_backtest.py \\")
    print("    --strategy strategies/sma_eod_example.py \\")
    print("    --symbols SPY \\")
    print("    --start 2024-01-01 --end 2024-12-31")
