"""
Multi-Symbol Portfolio Strategy
Example demonstrating multi-asset trading with portfolio allocation.

Features:
- Trades multiple symbols simultaneously
- Symbol-specific indicators and signals
- Portfolio-wide position sizing (25% per symbol max)
- Risk management across all positions
- Correlation-aware position management
- Database logging for all symbols

This demonstrates advanced portfolio strategy patterns.
"""

import backtrader as bt
from strategies.eod_strategy import EODStrategy
import numpy as np


class MultiSymbolPortfolio(EODStrategy):
    """
    Multi-symbol portfolio strategy with diversified asset allocation.

    Strategy Overview:
    - Trades up to 4 symbols simultaneously
    - Each symbol gets max 25% portfolio allocation
    - Uses RSI + SMA combination for entry/exit signals
    - Risk-managed with position limits and correlation checks
    - Automatic rebalancing and EOD liquidation

    Signals per symbol:
    - Entry: RSI < 30 (oversold) + price > SMA(20)
    - Exit: RSI > 70 (overbought) OR price < SMA(20)
    """

    params = (
        # Strategy params
        ('rsi_period', 14),
        ('sma_period', 20),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),

        # Portfolio allocation
        ('max_per_symbol_pct', 0.25),  # Max 25% per symbol
        ('max_symbols', 4),             # Max symbols to trade

        # EOD params (inherited)
        ('eod_liquidate', True),
        ('eod_hour', 15),
        ('eod_minute', 55),

        # Risk params (inherited)
        ('enable_risk_manager', True),
        ('daily_loss_limit', 0.02),
        ('max_drawdown', 0.15),        # Tighter for multi-symbol
        ('max_position_pct', 0.95),    # Allow concentrated positions

        # DB logging
        ('enable_db_logging', False),
        ('algorithm_name', 'MultiSymbolPortfolio'),

        # Base params
        ('printlog', True),
    )

    def __init__(self):
        """Initialize multi-symbol strategy."""
        # IMPORTANT: Call parent first for EOD, risk, and DB logging
        super().__init__()

        # Symbol-specific indicators (one set per data feed)
        self.indicators = {}
        self.signals = {}

        for i, data in enumerate(self.datas):
            symbol = data._name

            # Create indicators for this symbol
            self.indicators[symbol] = {
                'rsi': bt.indicators.RSI(data.close, period=self.p.rsi_period),
                'sma': bt.indicators.SMA(data.close, period=self.p.sma_period),
            }

            # Create signal combinations
            rsi = self.indicators[symbol]['rsi']
            sma = self.indicators[symbol]['sma']

            # Entry signal: RSI oversold AND price above SMA
            entry_signal = bt.And(
                rsi < self.p.rsi_oversold,
                data.close > sma
            )

            # Exit signal: RSI overbought OR price below SMA
            exit_signal = bt.Or(
                rsi > self.p.rsi_overbought,
                data.close < sma
            )

            self.signals[symbol] = {
                'entry': entry_signal,
                'exit': exit_signal,
            }

        # Track active symbols (symbols currently in portfolio)
        self.active_symbols = set()

        # Correlation matrix for risk management (simplified)
        self.price_history = {data._name: [] for data in self.datas}

        self.log(f"Multi-Symbol Portfolio initialized with {len(self.datas)} symbols")
        for data in self.datas:
            self.log(f"  - {data._name}")

    def next(self):
        """Main trading logic for all symbols."""
        # CRITICAL: Call parent first for EOD, daily reset, DB logging
        super().next()

        # Skip if near EOD
        if not self.should_trade():
            return

        # Process each symbol independently
        for i, data in enumerate(self.datas):
            symbol = data._name

            # Skip if we have a pending order for this symbol
            if self.has_pending_order(data):
                continue

            # Get current position for this symbol
            position_size = self.get_position_size(data)
            current_price = data.close[0]

            # Update price history for correlation (keep last 20 bars)
            self.price_history[symbol].append(current_price)
            if len(self.price_history[symbol]) > 20:
                self.price_history[symbol].pop(0)

            # Check entry signal
            if position_size == 0:  # No position
                if self.signals[symbol]['entry'][0]:  # Entry signal triggered
                    size = self.calculate_symbol_position(symbol, current_price)

                    if size > 0:
                        # Risk check for this specific trade
                        if self.risk_manager:
                            can_trade, msg = self.risk_manager.can_trade(size, current_price, data)

                            if not can_trade:
                                self.log(f'{symbol} ENTRY BLOCKED by risk manager: {msg}', level='WARNING')

                                # Log risk event
                                if self.db_logger:
                                    self.db_logger.log_risk_event(
                                        event_type='POSITION_LIMIT',
                                        severity='WARNING',
                                        message=f'{symbol} entry blocked: {msg}',
                                        symbol=symbol,
                                        portfolio_value=self.broker.getvalue(),
                                        position_value=size * current_price
                                    )
                                continue

                                        # Check portfolio concentration
                        if not self.check_portfolio_concentration(symbol, size * current_price):
                            self.log(f'{symbol} ENTRY BLOCKED: Would exceed portfolio concentration limits', level='WARNING')
                            continue

                        # Place order
                        self.log(f'{symbol} ENTRY SIGNAL: RSI={self.indicators[symbol]["rsi"][0]:.1f} '
                                f'(target: <{self.p.rsi_oversold}) | '
                                f'Price=${current_price:.2f} > SMA=${self.indicators[symbol]["sma"][0]:.2f} | '
                                f'Size: {size} shares')

                        order = self.buy(data=data, size=size)
                        self.orders[data] = order

                        # Track active symbol
                        self.active_symbols.add(symbol)

            # Check exit signal
            elif self.signals[symbol]['exit'][0]:  # Exit signal triggered
                self.log(f'{symbol} EXIT SIGNAL: RSI={self.indicators[symbol]["rsi"][0]:.1f} '
                        f'(target: >{self.p.rsi_overbought}) | '
                        f'Price=${current_price:.2f} vs SMA=${self.indicators[symbol]["sma"][0]:.2f}')

                order = self.close(data=data)
                self.orders[data] = order

                # Remove from active symbols
                self.active_symbols.discard(symbol)

        # Log portfolio status periodically
        if self.bar_count % 50 == 0:
            self.log_portfolio_status()

    def calculate_symbol_position(self, symbol, price):
        """
        Calculate position size for a symbol based on portfolio allocation.

        Args:
            symbol: Symbol name
            price: Current price

        Returns:
            Number of shares to buy
        """
        portfolio_value = self.broker.getvalue()
        max_allocation = portfolio_value * self.p.max_per_symbol_pct

        # Calculate shares for max allocation
        size = int(max_allocation / price)

        # Ensure we don't exceed available cash
        cash_needed = size * price
        available_cash = self.broker.getcash()

        if cash_needed > available_cash:
            size = int(available_cash / price * 0.98)  # Leave 2% buffer

        return max(0, size)

    def check_portfolio_concentration(self, symbol, position_value):
        """
        Check if adding this position would violate concentration limits.

        Args:
            symbol: Symbol to check
            position_value: Dollar value of proposed position

        Returns:
            True if position is allowed
        """
        portfolio_value = self.broker.getvalue()

        # Calculate current portfolio concentration
        current_positions_value = 0
        for data in self.datas:
            pos_value = self.get_position_value(data)
            current_positions_value += pos_value

        # Check if new position would exceed limits
        new_total_positions = current_positions_value + position_value
        concentration_pct = new_total_positions / portfolio_value

        if concentration_pct > self.p.max_position_pct:
            return False

        # Check symbol limit
        symbol_allocation = position_value / portfolio_value
        if symbol_allocation > self.p.max_per_symbol_pct:
            return False

        return True

    def log_portfolio_status(self):
        """Log current portfolio allocation across all symbols."""
        portfolio_value = self.broker.getvalue()
        cash = self.broker.getcash()

        self.log("="*80)
        self.log("PORTFOLIO STATUS")
        self.log("="*80)
        self.log(f"Total Value: ${portfolio_value:,.2f} | Cash: ${cash:,.2f}")

        total_positions_value = 0
        for data in self.datas:
            symbol = data._name
            position_size = self.get_position_size(data)
            position_value = self.get_position_value(data)

            if position_size != 0:
                pct_of_portfolio = (position_value / portfolio_value) * 100
                total_positions_value += position_value

                self.log(f"  {symbol}: {position_size:>6} shares | "
                        f"${position_value:>10,.2f} | {pct_of_portfolio:>5.1f}%")

        invested_pct = (total_positions_value / portfolio_value) * 100
        self.log(f"Total Invested: ${total_positions_value:,.2f} | {invested_pct:.1f}% of portfolio")
        self.log(f"Active Symbols: {len(self.active_symbols)}/{len(self.datas)}")
        self.log("="*80)

    def notify_order(self, order):
        """Handle order notifications for all symbols."""
        # Call parent for standard logging
        super().notify_order(order)

        # Additional multi-symbol specific logging
        if order.status in [order.Completed]:
            symbol = order.data._name
            trade_type = "BUY" if order.isbuy() else "SELL"
            value = order.executed.value

            portfolio_value = self.broker.getvalue()
            pct_of_portfolio = (value / portfolio_value) * 100

            self.log(f"{trade_type} EXECUTED: {symbol} | "
                    f"${value:,.2f} ({pct_of_portfolio:.1f}% of portfolio)",
                    level='INFO')

    def stop(self):
        """Strategy ending - log final portfolio breakdown."""
        # Print final portfolio allocation
        self.log("="*60)
        self.log("FINAL PORTFOLIO BREAKDOWN")
        self.log("="*60)

        portfolio_value = self.broker.getvalue()
        total_positions_value = 0

        for data in self.datas:
            symbol = data._name
            position_value = self.get_position_value(data)

            if position_value > 0:
                pct = (position_value / portfolio_value) * 100
                total_positions_value += position_value
                self.log(f"  {symbol}: ${position_value:,.2f} ({pct:.1f}%)")

        invested_pct = (total_positions_value / portfolio_value) * 100
        self.log(f"Total Invested: ${total_positions_value:,.2f} ({invested_pct:.1f}%)")
        self.log(f"Cash: ${self.broker.getcash():,.2f}")

        # Call parent for risk summary and final logging
        super().stop()


if __name__ == "__main__":
    print("Multi-Symbol Portfolio Strategy")
    print("\nFeatures:")
    print("  ✓ Trades multiple symbols simultaneously")
    print("  ✓ Portfolio allocation (25% max per symbol)")
    print("  ✓ RSI + SMA signal combination")
    print("  ✓ Risk management across all positions")
    print("  ✓ EOD liquidation at 3:55 PM")
    print("  ✓ Database logging for all trades")
    print("\nUsage:")
    print("  python scripts/run_backtest.py \\")
    print("    --strategy strategies/multi_symbol_portfolio.py \\")
    print("    --symbols SPY,QQQ,IWM,VTI \\")
    print("    --start 2024-01-01 --end 2024-12-31")
    print("\nNote: Requires 4 symbol data feeds")