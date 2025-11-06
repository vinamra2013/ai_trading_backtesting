"""
RSI Momentum Strategy
Example demonstrating momentum-based trading using RSI indicator.

Features:
- RSI-based entry and exit signals
- Momentum confirmation with trend filter
- Risk-managed position sizing
- Database logging integration
- Comprehensive signal logging

Signals:
- Entry: RSI crosses above oversold level + upward momentum
- Exit: RSI crosses below overbought level OR momentum reversal
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class RSIMomentumStrategy(BaseStrategy):
    """
    RSI-based momentum strategy with trend confirmation.

    Strategy Overview:
    - Uses RSI for overbought/oversold signals
    - Confirms momentum with price trend
    - Risk-managed entries and exits
    - Database logging for all trades

    Signals:
    - Long Entry: RSI < oversold threshold + rising trend
    - Long Exit: RSI > overbought threshold OR trend reversal
    - Short Entry: RSI > overbought threshold + falling trend
    - Short Exit: RSI < oversold threshold OR trend reversal
    """

    params = (
        # RSI parameters
        ('rsi_period', 14),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),

        # Trend filter parameters
        ('trend_period', 20),  # Period for trend calculation
        ('trend_threshold', 0.001),  # Minimum trend strength (0.1%)

        # Risk management
        ('enable_risk_manager', True),
        ('daily_loss_limit', 0.02),
        ('max_drawdown', 0.20),
        ('max_position_pct', 0.95),

        # Database logging
        ('enable_db_logging', False),
        ('algorithm_name', 'RSIMomentumStrategy'),

        # Base strategy params
        ('printlog', True),
        ('log_trades', True),
        ('log_orders', True),
    )

    def __init__(self):
        """Initialize RSI momentum strategy."""
        super().__init__()

        # RSI indicator
        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=self.p.rsi_period
        )

        # Trend calculation (rate of change)
        self.trend = bt.indicators.ROC(
            self.data.close,
            period=self.p.trend_period
        )

        # Signal tracking
        self.entry_signal = None
        self.exit_signal = None

        # Position tracking
        self.current_position_type = None  # 'long', 'short', or None

        self.log(f"RSI Momentum Strategy initialized: RSI({self.p.rsi_period}), "
                f"Oversold={self.p.rsi_oversold}, Overbought={self.p.rsi_overbought}")

    def next(self):
        """Main trading logic."""
        self.bar_count += 1

        # Skip if we have pending orders
        if self.has_pending_order():
            return

        current_rsi = self.rsi[0]
        current_trend = self.trend[0]
        current_price = self.data.close[0]

        # Determine signals
        long_entry = (current_rsi <= self.p.rsi_oversold and
                     current_trend > self.p.trend_threshold)
        short_entry = (current_rsi >= self.p.rsi_overbought and
                      current_trend < -self.p.trend_threshold)

        long_exit = (current_rsi >= self.p.rsi_overbought or
                    (self.current_position_type == 'long' and
                     current_trend < -self.p.trend_threshold))
        short_exit = (current_rsi <= self.p.rsi_oversold or
                     (self.current_position_type == 'short' and
                      current_trend > self.p.trend_threshold))

        # Execute trades
        if not self.is_invested():
            # Entry logic
            if long_entry:
                self._enter_long_position(current_rsi, current_trend, current_price)
            elif short_entry:
                self._enter_short_position(current_rsi, current_trend, current_price)

        else:
            # Exit logic
            if self.current_position_type == 'long' and long_exit:
                self._exit_long_position(current_rsi, current_trend, current_price)
            elif self.current_position_type == 'short' and short_exit:
                self._exit_short_position(current_rsi, current_trend, current_price)

    def _enter_long_position(self, rsi, trend, price):
        """Enter long position with risk checks."""
        # Calculate position size
        size = self.calculate_position_size(price)

        # Risk check
        if hasattr(self, 'risk_manager') and self.risk_manager:
            can_trade, msg = self.risk_manager.can_trade(size, price, self.data)
            if not can_trade:
                self.log(f'LONG ENTRY BLOCKED by risk manager: {msg}', level='WARNING')
                return

        # Place order
        self.log(f'LONG ENTRY: RSI={rsi:.1f} (≤{self.p.rsi_oversold}), '
                f'Trend={trend:.3f} (>={self.p.trend_threshold}), '
                f'Price=${price:.2f}, Size={size}')

        order = self.buy(size=size)
        self.orders[self.data] = order
        self.current_position_type = 'long'

    def _enter_short_position(self, rsi, trend, price):
        """Enter short position with risk checks."""
        # Calculate position size
        size = self.calculate_position_size(price)

        # Risk check
        if hasattr(self, 'risk_manager') and self.risk_manager:
            can_trade, msg = self.risk_manager.can_trade(size, price, self.data)
            if not can_trade:
                self.log(f'SHORT ENTRY BLOCKED by risk manager: {msg}', level='WARNING')
                return

        # Place order
        self.log(f'SHORT ENTRY: RSI={rsi:.1f} (≥{self.p.rsi_overbought}), '
                f'Trend={trend:.3f} (≤{-self.p.trend_threshold}), '
                f'Price=${price:.2f}, Size={size}')

        order = self.sell(size=size)
        self.orders[self.data] = order
        self.current_position_type = 'short'

    def _exit_long_position(self, rsi, trend, price):
        """Exit long position."""
        self.log(f'LONG EXIT: RSI={rsi:.1f}, Trend={trend:.3f}, Price=${price:.2f}')
        order = self.close()
        self.orders[self.data] = order
        self.current_position_type = None

    def _exit_short_position(self, rsi, trend, price):
        """Exit short position."""
        self.log(f'SHORT EXIT: RSI={rsi:.1f}, Trend={trend:.3f}, Price=${price:.2f}')
        order = self.close()
        self.orders[self.data] = order
        self.current_position_type = None

    def notify_order(self, order):
        """Handle order notifications."""
        super().notify_order(order)

        # Additional strategy-specific logging
        if order.status in [order.Completed]:
            trade_type = "BUY" if order.isbuy() else "SELL"
            self.log(f'{trade_type} ORDER COMPLETED: {order.executed.size} shares @ ${order.executed.price:.2f}',
                    level='INFO')

    def notify_trade(self, trade):
        """Handle trade notifications."""
        super().notify_trade(trade)

        # Track position type for exit logic
        if not trade.isclosed:
            if trade.size > 0:
                self.current_position_type = 'long'
            elif trade.size < 0:
                self.current_position_type = 'short'

    def stop(self):
        """Strategy ending - log final statistics."""
        self.log("="*60)
        self.log("RSI MOMENTUM STRATEGY SUMMARY")
        self.log("="*60)
        self.log(f"Total Trades: {self.trade_count}")
        self.log(f"Final Portfolio Value: ${self.broker.getvalue():,.2f}")
        self.log(f"RSI Period: {self.p.rsi_period}")
        self.log(f"Oversold Level: {self.p.rsi_oversold}")
        self.log(f"Overbought Level: {self.p.rsi_overbought}")
        self.log(f"Trend Period: {self.p.trend_period}")
        self.log(f"Trend Threshold: {self.p.trend_threshold:.1%}")

        # Print risk summary if available
        if hasattr(self, 'risk_manager') and self.risk_manager:
            risk_summary = self.risk_manager.get_risk_summary()
            self.log(f"Risk Events: {risk_summary.get('risk_events_count', 0)}")
            self.log(f"Max Drawdown: {risk_summary.get('current_drawdown', 0):.1%}")

        super().stop()


if __name__ == "__main__":
    print("RSI Momentum Strategy")
    print("\nFeatures:")
    print("  ✓ RSI-based entry/exit signals")
    print("  ✓ Momentum confirmation with trend filter")
    print("  ✓ Risk management integration")
    print("  ✓ Database logging support")
    print("  ✓ Long and short position support")
    print("\nUsage:")
    print("  python scripts/run_backtest.py \\")
    print("    --strategy strategies/rsi_momentum_strategy.py \\")
    print("    --symbols SPY \\")
    print("    --start 2024-01-01 --end 2024-12-31")
    print("\nParameters:")
    print("  --rsi_period: RSI calculation period (default: 14)")
    print("  --rsi_oversold: Oversold threshold (default: 30)")
    print("  --rsi_overbought: Overbought threshold (default: 70)")
    print("  --trend_period: Trend calculation period (default: 20)")