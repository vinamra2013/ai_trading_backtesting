"""
RSI Strategy with Full Risk Management Integration
Example demonstrating RSI-based strategy using complete framework integration.

Epic 13: US-13.2 - Algorithm Migration (Simple Strategy)

Features:
- RSI-based entry/exit signals (oversold/overbought)
- Complete integration with BaseStrategy + RiskManager + DBLogger + EODStrategy
- Risk-controlled position sizing
- Database logging of all trades and risk events
- Automatic EOD liquidation
- Comprehensive logging and monitoring

Strategy Logic:
- Entry: RSI < 30 (oversold) + price > SMA(20) for trend confirmation
- Exit: RSI > 70 (overbought) OR stop loss hit
- Risk Management: 2% daily loss limit, 20% max drawdown, 25% max position
- EOD: Automatic liquidation at 3:55 PM ET
- Database: Full trade logging and risk event tracking

This demonstrates best practices for production-ready strategies.
"""

import backtrader as bt
from strategies.eod_strategy import EODStrategy


class RSIStrategyRiskManaged(EODStrategy):
    """
    RSI-based strategy with complete risk management integration.

    This strategy demonstrates the full framework integration:
    - BaseStrategy: Core trading logic and portfolio helpers
    - RiskManager: Capital protection and position limits
    - DBLogger: Complete audit trail
    - EODStrategy: Automatic overnight risk management

    Entry Signal: RSI < 30 (oversold) + price > SMA(20)
    Exit Signal: RSI > 70 (overbought) OR stop loss (5%)
    """

    params = (
        # RSI parameters
        ('rsi_period', 14),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),

        # Trend confirmation
        ('sma_period', 20),

        # Risk management
        ('stop_loss_pct', 0.05),  # 5% stop loss
        ('enable_risk_manager', True),
        ('daily_loss_limit', 0.02),  # 2% daily loss limit
        ('max_drawdown', 0.20),      # 20% max drawdown
        ('max_position_pct', 0.25),  # 25% max position size

        # EOD parameters
        ('eod_liquidate', True),
        ('eod_hour', 15),
        ('eod_minute', 55),

        # Database logging
        ('enable_db_logging', True),
        ('algorithm_name', 'RSI_Risk_Managed'),

        # Base parameters
        ('printlog', True),
    )

    def __init__(self):
        """Initialize RSI strategy with full framework integration."""
        # CRITICAL: Call parent first for EOD, risk, and DB logging setup
        super().__init__()

        # RSI indicator for momentum signals
        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=self.p.rsi_period
        )

        # SMA for trend confirmation
        self.sma = bt.indicators.SMA(
            self.data.close,
            period=self.p.sma_period
        )

        # Stop loss tracking
        self.stop_loss_price = None
        self.entry_price = None

        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0

        self.log("="*70)
        self.log("RSI STRATEGY WITH RISK MANAGEMENT INITIALIZED")
        self.log("="*70)
        self.log(f"RSI Period: {self.p.rsi_period} | Oversold: {self.p.rsi_oversold} | Overbought: {self.p.rsi_overbought}")
        self.log(f"SMA Period: {self.p.sma_period} | Stop Loss: {self.p.stop_loss_pct*100}%")
        self.log(f"Risk Manager: {'ENABLED' if self.p.enable_risk_manager else 'DISABLED'}")
        self.log(f"EOD Liquidation: {'ENABLED' if self.p.eod_liquidate else 'DISABLED'}")
        self.log(f"DB Logging: {'ENABLED' if self.p.enable_db_logging else 'DISABLED'}")
        self.log("="*70)

    def next(self):
        """Main trading logic with complete risk management."""
        # CRITICAL: Call parent first for EOD procedures, daily resets, DB logging
        super().next()

        # Skip trading if near EOD (parent handles this)
        if not self.should_trade():
            return

        # Skip if we have pending orders
        if self.order:
            return

        current_price = self.data.close[0]
        current_rsi = self.rsi[0] if len(self.rsi) > 0 else None
        current_sma = self.sma[0] if len(self.sma) > 0 else None

        # Skip if indicators not ready
        if current_rsi is None or current_sma is None:
            return

        # Check for stop loss first (applies whether in position or not)
        if self.position and self.stop_loss_price:
            if current_price <= self.stop_loss_price:
                self.log(f"STOP LOSS TRIGGERED: Price ${current_price:.2f} <= Stop ${self.stop_loss_price:.2f} | "
                        f"P&L: {((current_price - self.entry_price) / self.entry_price * 100):+.2f}%")

                # Log risk event
                if self.db_logger:
                    self.db_logger.log_risk_event(
                        event_type='STOP_LOSS',
                        severity='INFO',
                        message=f'Stop loss triggered at ${current_price:.2f}',
                        symbol=self.data._name,
                        portfolio_value=self.broker.getvalue(),
                        position_value=self.get_position_value()
                    )

                self.close()
                self.stop_loss_price = None
                self.entry_price = None
                return

        # ENTRY SIGNAL: RSI oversold + trend confirmation (price > SMA)
        if not self.position:
            if (current_rsi < self.p.rsi_oversold and
                current_price > current_sma):

                # Calculate position size using framework helper
                size = self.calculate_position_size(current_price)

                if size > 0:
                    # Risk check using RiskManager
                    if self.risk_manager:
                        can_trade, msg = self.risk_manager.can_trade(size, current_price)

                        if not can_trade:
                            self.log(f"TRADE BLOCKED by Risk Manager: {msg}", level='WARNING')

                            # Log risk event
                            if self.db_logger:
                                self.db_logger.log_risk_event(
                                    event_type='TRADE_BLOCKED',
                                    severity='WARNING',
                                    message=f'Entry blocked: {msg}',
                                    symbol=self.data._name,
                                    portfolio_value=self.broker.getvalue(),
                                    position_value=size * current_price
                                )
                            return

                    # Execute entry
                    self.log(f"ENTRY SIGNAL: RSI {current_rsi:.1f} < {self.p.rsi_oversold} + "
                            f"Price ${current_price:.2f} > SMA ${current_sma:.2f} | "
                            f"Size: {size} shares (${size * current_price:,.2f})")

                    self.buy(size=size)
                    self.entry_price = current_price
                    self.stop_loss_price = current_price * (1 - self.p.stop_loss_pct)
                    self.total_trades += 1

        # EXIT SIGNAL: RSI overbought
        elif current_rsi > self.p.rsi_overbought:
            exit_price = current_price
            pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100

            self.log(f"EXIT SIGNAL: RSI {current_rsi:.1f} > {self.p.rsi_overbought} | "
                    f"Entry: ${self.entry_price:.2f} | Exit: ${exit_price:.2f} | "
                    f"P&L: {pnl_pct:+.2f}%")

            if pnl_pct > 0:
                self.winning_trades += 1

            self.close()
            self.stop_loss_price = None
            self.entry_price = None

    def notify_order(self, order):
        """Enhanced order notification with risk management logging."""
        # Call parent for standard logging
        super().notify_order(order)

        if order.status in [order.Completed]:
            if order.isbuy():
                value = order.executed.value
                portfolio_value = self.broker.getvalue()
                pct_of_portfolio = (value / portfolio_value) * 100

                self.log(f"BUY EXECUTED: ${value:,.2f} ({pct_of_portfolio:.1f}% of portfolio) | "
                        f"Stop Loss: ${self.stop_loss_price:.2f}", level='SUCCESS')

            elif order.issell():
                pnl = order.executed.pnl
                pnl_net = order.executed.pnlcomm
                self.log(f"SELL EXECUTED: P&L Gross ${pnl:.2f} | Net ${pnl_net:.2f}", level='SUCCESS')

    def notify_trade(self, trade):
        """Enhanced trade notification with performance tracking."""
        # Call parent for standard logging
        super().notify_trade(trade)

        if trade.isclosed:
            pnl_net = trade.pnlcomm
            duration = trade.barlen

            self.log(f"TRADE CLOSED: Net P&L ${pnl_net:.2f} | Duration: {duration} bars", level='SUCCESS')

            # Log to database (parent handles this, but we can add custom fields)
            if self.db_logger:
                # Additional trade metadata
                pass  # Parent already logs comprehensive trade data

    def stop(self):
        """Strategy completion with comprehensive performance summary."""
        self.log("\n" + "="*70)
        self.log("RSI STRATEGY PERFORMANCE SUMMARY")
        self.log("="*70)

        # Basic metrics
        final_value = self.broker.getvalue()
        total_return = ((final_value - self.p.initial_cash) / self.p.initial_cash) * 100

        self.log(f"Final Portfolio Value: ${final_value:,.2f}")
        self.log(f"Total Return: {total_return:+.2f}%")
        self.log(f"Total Trades: {self.total_trades}")
        self.log(f"Winning Trades: {self.winning_trades}")

        if self.total_trades > 0:
            win_rate = (self.winning_trades / self.total_trades) * 100
            self.log(f"Win Rate: {win_rate:.1f}%")

        # Risk management summary
        if self.risk_manager:
            self.log("\nRISK MANAGEMENT SUMMARY:")
            self.log(f"Daily Loss Limit: {self.p.daily_loss_limit*100}%")
            self.log(f"Max Drawdown Limit: {self.p.max_drawdown*100}%")
            self.log(f"Max Position Size: {self.p.max_position_pct*100}% of portfolio")

        # Framework usage summary
        self.log("\nFRAMEWORK INTEGRATION:")
        self.log(f"✓ BaseStrategy: Portfolio helpers and order management")
        self.log(f"✓ RiskManager: Capital protection and position limits")
        self.log(f"✓ DBLogger: Complete trade audit trail")
        self.log(f"✓ EODStrategy: Automatic liquidation at {self.p.eod_hour}:{self.p.eod_minute:02d}")

        self.log("="*70)

        # Call parent for final risk summary and DB logging
        super().stop()


if __name__ == "__main__":
    print("RSI Strategy with Full Risk Management Integration")
    print("\nFeatures:")
    print("  ✓ RSI-based entry/exit signals (30/70)")
    print("  ✓ Trend confirmation with SMA(20)")
    print("  ✓ 5% stop loss protection")
    print("  ✓ RiskManager integration (2% daily loss, 20% max drawdown)")
    print("  ✓ DBLogger for complete audit trail")
    print("  ✓ EODStrategy for automatic liquidation")
    print("  ✓ Comprehensive performance tracking")
    print("\nParameters:")
    print(f"  RSI Period: {RSIStrategyRiskManaged.params.rsi_period}")
    print(f"  RSI Oversold: {RSIStrategyRiskManaged.params.rsi_oversold}")
    print(f"  RSI Overbought: {RSIStrategyRiskManaged.params.rsi_overbought}")
    print(f"  SMA Period: {RSIStrategyRiskManaged.params.sma_period}")
    print(f"  Stop Loss: {RSIStrategyRiskManaged.params.stop_loss_pct*100}%")
    print("\nUsage:")
    print("  python scripts/run_backtest.py \\")
    print("    --strategy strategies/rsi_strategy_risk_managed.py \\")
    print("    --symbols SPY \\")
    print("    --start 2024-01-01 --end 2024-12-31")
    print("\nNote: Demonstrates complete framework integration")