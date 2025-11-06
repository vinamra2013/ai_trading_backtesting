"""
Bollinger Bands Mean Reversion Strategy
Example demonstrating mean reversion trading using Bollinger Bands.

Features:
- Bollinger Bands for mean reversion signals
- Entry at lower band, exit at middle band (or upper for short)
- Risk-managed position sizing
- Database logging integration
- Comprehensive signal validation

Signals:
- Long Entry: Price touches lower Bollinger Band
- Long Exit: Price reaches middle band (mean)
- Short Entry: Price touches upper Bollinger Band
- Short Exit: Price reaches middle band (mean)
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy


class BollingerMeanReversionStrategy(BaseStrategy):
    """
    Bollinger Bands mean reversion strategy.

    Strategy Overview:
    - Uses Bollinger Bands to identify overbought/oversold conditions
    - Buys when price touches lower band (oversold)
    - Sells when price reaches middle band (mean reversion)
    - Short sells when price touches upper band (overbought)
    - Covers when price reaches middle band
    - Risk-managed with position limits

    Signals:
    - Long: Price ≤ lower band → expect reversion up to middle
    - Short: Price ≥ upper band → expect reversion down to middle
    - Exit: Price reaches middle band
    """

    params = (
        # Bollinger Bands parameters
        ('bb_period', 20),
        ('bb_dev', 2.0),

        # Mean reversion parameters
        ('reversion_target', 'middle'),  # 'middle' or 'opposite_band'

        # Risk management
        ('enable_risk_manager', True),
        ('daily_loss_limit', 0.02),
        ('max_drawdown', 0.20),
        ('max_position_pct', 0.95),

        # Database logging
        ('enable_db_logging', False),
        ('algorithm_name', 'BollingerMeanReversionStrategy'),

        # Base strategy params
        ('printlog', True),
        ('log_trades', True),
        ('log_orders', True),
    )

    def __init__(self):
        """Initialize Bollinger Bands mean reversion strategy."""
        super().__init__()

        # Bollinger Bands
        self.bbands = bt.indicators.BollingerBands(
            self.data.close,
            period=self.p.bb_period,
            devfactor=self.p.bb_dev
        )

        # Bollinger Band components
        self.bb_top = self.bbands.lines.top
        self.bb_mid = self.bbands.lines.mid
        self.bb_bot = self.bbands.lines.bot

        # Position tracking
        self.current_position_type = None  # 'long', 'short', or None

        self.log(f"Bollinger Mean Reversion initialized: Period({self.p.bb_period}), "
                f"Dev({self.p.bb_dev}), Target({self.p.reversion_target})")

    def next(self):
        """Main trading logic."""
        self.bar_count += 1

        # Skip if we have pending orders
        if self.has_pending_order():
            return

        current_price = self.data.close[0]
        current_top = self.bb_top[0]
        current_mid = self.bb_mid[0]
        current_bot = self.bb_bot[0]

        # Determine signals
        long_entry = current_price <= current_bot  # Price touches lower band
        short_entry = current_price >= current_top  # Price touches upper band

        # Exit conditions based on reversion target
        if self.p.reversion_target == 'middle':
            long_exit = current_price >= current_mid  # Reached middle band
            short_exit = current_price <= current_mid  # Reached middle band
        else:  # 'opposite_band'
            long_exit = current_price >= current_top  # Reached opposite band
            short_exit = current_price <= current_bot  # Reached opposite band

        # Execute trades
        if not self.is_invested():
            # Entry logic
            if long_entry:
                self._enter_long_position(current_price, current_bot, current_mid, current_top)
            elif short_entry:
                self._enter_short_position(current_price, current_bot, current_mid, current_top)

        else:
            # Exit logic
            if self.current_position_type == 'long' and long_exit:
                self._exit_long_position(current_price, current_bot, current_mid, current_top)
            elif self.current_position_type == 'short' and short_exit:
                self._exit_short_position(current_price, current_bot, current_mid, current_top)

    def _enter_long_position(self, price, bot, mid, top):
        """Enter long position when price touches lower band."""
        # Calculate position size
        size = self.calculate_position_size(price)

        # Risk check
        if hasattr(self, 'risk_manager') and self.risk_manager:
            can_trade, msg = self.risk_manager.can_trade(size, price, self.data)
            if not can_trade:
                self.log(f'LONG ENTRY BLOCKED by risk manager: {msg}', level='WARNING')
                return

        # Place order
        self.log(f'LONG ENTRY: Price=${price:.2f} touched lower band (${bot:.2f}), '
                f'target middle=${mid:.2f}, Size={size}')

        order = self.buy(size=size)
        self.orders[self.data] = order
        self.current_position_type = 'long'

    def _enter_short_position(self, price, bot, mid, top):
        """Enter short position when price touches upper band."""
        # Calculate position size
        size = self.calculate_position_size(price)

        # Risk check
        if hasattr(self, 'risk_manager') and self.risk_manager:
            can_trade, msg = self.risk_manager.can_trade(size, price, self.data)
            if not can_trade:
                self.log(f'SHORT ENTRY BLOCKED by risk manager: {msg}', level='WARNING')
                return

        # Place order
        self.log(f'SHORT ENTRY: Price=${price:.2f} touched upper band (${top:.2f}), '
                f'target middle=${mid:.2f}, Size={size}')

        order = self.sell(size=size)
        self.orders[self.data] = order
        self.current_position_type = 'short'

    def _exit_long_position(self, price, bot, mid, top):
        """Exit long position when price reaches target."""
        self.log(f'LONG EXIT: Price=${price:.2f} reached target (${mid:.2f})')
        order = self.close()
        self.orders[self.data] = order
        self.current_position_type = None

    def _exit_short_position(self, price, bot, mid, top):
        """Exit short position when price reaches target."""
        self.log(f'SHORT EXIT: Price=${price:.2f} reached target (${mid:.2f})')
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
        self.log("BOLLINGER MEAN REVERSION STRATEGY SUMMARY")
        self.log("="*60)
        self.log(f"Total Trades: {self.trade_count}")
        self.log(f"Final Portfolio Value: ${self.broker.getvalue():,.2f}")
        self.log(f"Bollinger Bands: Period({self.p.bb_period}), Dev({self.p.bb_dev})")
        self.log(f"Reversion Target: {self.p.reversion_target}")

        # Print risk summary if available
        if hasattr(self, 'risk_manager') and self.risk_manager:
            risk_summary = self.risk_manager.get_risk_summary()
            self.log(f"Risk Events: {risk_summary.get('risk_events_count', 0)}")
            self.log(f"Max Drawdown: {risk_summary.get('current_drawdown', 0):.1%}")

        super().stop()


if __name__ == "__main__":
    print("Bollinger Bands Mean Reversion Strategy")
    print("\nFeatures:")
    print("  ✓ Bollinger Bands for overbought/oversold signals")
    print("  ✓ Mean reversion entry/exit logic")
    print("  ✓ Risk management integration")
    print("  ✓ Database logging support")
    print("  ✓ Long and short position support")
    print("\nUsage:")
    print("  python scripts/run_backtest.py \\")
    print("    --strategy strategies/bollinger_mean_reversion_strategy.py \\")
    print("    --symbols SPY \\")
    print("    --start 2024-01-01 --end 2024-12-31")
    print("\nParameters:")
    print("  --bb_period: Bollinger Bands period (default: 20)")
    print("  --bb_dev: Bollinger Bands standard deviation (default: 2.0)")
    print("  --reversion_target: Exit target - 'middle' or 'opposite_band' (default: 'middle')")