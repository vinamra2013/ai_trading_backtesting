"""
SMA Crossover Strategy with Risk Management
Epic 13: Example Strategy Using BaseStrategy + RiskManager

Enhanced SMA crossover strategy demonstrating:
- Inheritance from BaseStrategy
- Integration with RiskManager
- Portfolio-based position sizing
- Risk-controlled trading

Signals:
- Buy when fast SMA crosses above slow SMA (golden cross)
- Sell when fast SMA crosses below slow SMA (death cross)

Risk Controls:
- Position size based on portfolio percentage
- Daily loss limits
- Maximum drawdown protection
- Concentration limits
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy
from strategies.risk_manager import RiskManager


class SMACrossoverRiskManaged(BaseStrategy):
    """
    Risk-managed SMA crossover strategy.

    Demonstrates proper integration of:
    - BaseStrategy template
    - RiskManager framework
    - LEAN-style portfolio management
    """

    params = (
        ('fast_period', 10),            # Fast SMA period
        ('slow_period', 30),             # Slow SMA period
        ('position_size', 0.95),         # 95% of portfolio per trade
        ('printlog', True),              # Enable logging
        ('log_trades', True),            # Log trade execution
        # Risk management params
        ('daily_loss_limit', 0.02),      # 2% daily loss limit
        ('max_drawdown', 0.20),          # 20% max drawdown
        ('max_position_pct', 0.95),      # 95% max position size
        ('max_leverage', 1.0),           # 1x leverage (no margin)
    )

    def __init__(self):
        """Initialize strategy with indicators and risk manager."""
        # Call parent initialization
        super().__init__()

        # Initialize Risk Manager
        risk_config = {
            'daily_loss_limit': self.params.daily_loss_limit,
            'max_drawdown': self.params.max_drawdown,
            'max_position_pct': self.params.max_position_pct,
            'max_leverage': self.params.max_leverage,
            'max_positions': 1,  # Single position strategy
        }
        self.risk_manager = RiskManager(self, config=risk_config)

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

        self.log(f"Strategy initialized: Fast SMA({self.params.fast_period}), "
                f"Slow SMA({self.params.slow_period})")

    def next(self):
        """Main trading logic - called on each bar."""
        # Call parent to handle bar counting and logging
        super().next()

        # Skip if we have a pending order
        if self.order:
            return

        # Get current position
        position_size = self.get_position_size()

        # Entry Logic: No position + golden cross
        if not self.is_invested():
            if self.crossover[0] > 0:  # Fast SMA crossed above slow SMA
                # Calculate position size based on available cash
                cash = self.get_cash()
                price = self.data.close[0]
                size = int((cash * self.params.position_size) / price)

                # Risk check before entering
                can_trade, msg = self.risk_manager.can_trade(size, price, self.data)

                if can_trade:
                    self.log(f'BUY SIGNAL: Golden Cross | SMA Fast: {self.sma_fast[0]:.2f}, '
                            f'SMA Slow: {self.sma_slow[0]:.2f} | Size: {size} shares')
                    self.order = self.buy(size=size)
                else:
                    self.log(f'BUY SIGNAL BLOCKED: {msg}', level='WARNING')

        # Exit Logic: Has position + death cross
        elif self.crossover[0] < 0:  # Fast SMA crossed below slow SMA
            self.log(f'SELL SIGNAL: Death Cross | SMA Fast: {self.sma_fast[0]:.2f}, '
                    f'SMA Slow: {self.sma_slow[0]:.2f}')
            self.order = self.close()

    def notify_order(self, order):
        """Handle order notifications."""
        # Call parent handler
        super().notify_order(order)

        # Clear order reference when done
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None

    def stop(self):
        """Called when strategy ends."""
        super().stop()

        # Print risk summary
        risk_summary = self.risk_manager.get_risk_summary()
        self.log("="*60)
        self.log("RISK MANAGEMENT SUMMARY")
        self.log("="*60)
        self.log(f"Initial Value: ${risk_summary['initial_value']:,.2f}")
        self.log(f"Peak Value: ${risk_summary['peak_value']:,.2f}")
        self.log(f"Final Value: ${risk_summary['portfolio_value']:,.2f}")
        self.log(f"Max Drawdown: {risk_summary['current_drawdown']*100:.2f}%")
        self.log(f"Risk Events: {risk_summary['risk_events_count']}")

        # Log any risk violations
        risk_events = self.risk_manager.get_risk_events()
        if risk_events:
            self.log("\nRisk Events:")
            for event in risk_events[-10:]:  # Last 10 events
                self.log(f"  [{event['severity']}] {event['type']}: {event['description']}")


if __name__ == "__main__":
    print("SMA Crossover Strategy with Risk Management")
    print("\nFeatures:")
    print("  - Inherits from BaseStrategy")
    print("  - Integrated RiskManager")
    print("  - Portfolio-based position sizing")
    print("  - Daily loss and drawdown protection")
    print("\nUsage:")
    print("  python scripts/run_backtest.py \\")
    print("    --strategy strategies/sma_crossover_risk_managed.py \\")
    print("    --symbols SPY \\")
    print("    --start 2024-01-01 --end 2024-12-31")
