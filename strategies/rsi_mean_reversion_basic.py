"""
Basic RSI Mean Reversion Strategy
Simple implementation for initial validation of mean reversion thesis

Strategy Logic:
- Entry: RSI(14) < 25 (oversold) + Volume > 1.5x average
- Exit: RSI(14) > 50 OR 2% profit OR 1% stop OR 3 days max hold
- Position Sizing: 1% risk per trade, max 3 positions
- Target: 1%+ average profit per trade with 65%+ win rate

Author: Quant Director
Date: 2025-11-07
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy
from datetime import datetime, timedelta


class RSIMeanReversionBasic(BaseStrategy):
    """
    Basic RSI Mean Reversion Strategy

    Entry Conditions (ALL required):
    1. RSI(14) < 25 (deeply oversold)
    2. Volume > 1.5x 20-day average (capitulation confirmation)

    Exit Conditions (ANY triggers exit):
    1. RSI(14) > 50 (return to mean)
    2. Price up 2% from entry (profit target)
    3. Price down 1% from entry (stop loss)
    4. 3 trading days elapsed (time stop)
    """

    params = (
        # Entry parameters
        ('rsi_period', 14),           # RSI calculation period
        ('rsi_entry_threshold', 25),  # Buy when RSI < 25
        ('rsi_exit_threshold', 50),   # Sell when RSI > 50
        ('volume_period', 20),        # Volume average period
        ('volume_multiplier', 1.5),   # Volume must be 1.5x average

        # Exit parameters
        ('profit_target_pct', 2.0),   # 2% profit target
        ('stop_loss_pct', 1.0),       # 1% stop loss
        ('max_hold_days', 3),         # Max 3 day hold

        # Position sizing
        ('risk_per_trade_pct', 1.0),  # 1% risk per trade
        ('max_positions', 3),         # Max 3 concurrent positions

        # Logging
        ('printlog', True),
    )

    def __init__(self):
        """Initialize indicators"""
        super().__init__()

        # RSI indicator
        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=self.p.rsi_period
        )

        # Volume indicator
        self.volume_sma = bt.indicators.SMA(
            self.data.volume,
            period=self.p.volume_period
        )

        # Track entry details
        self.entry_price = None
        self.entry_date = None
        self.trade_count = 0

    def next(self):
        """Main strategy logic called on each bar"""

        # Skip if indicators not ready
        if len(self.data) < self.p.rsi_period:
            return

        # Entry logic
        if not self.position:
            # Check RSI oversold condition
            if self.rsi[0] < self.p.rsi_entry_threshold:
                # Check volume confirmation
                if self.data.volume[0] > (self.volume_sma[0] * self.p.volume_multiplier):
                    # Check risk limits (from BaseStrategy)
                    if self.check_risk_limits():
                        # Calculate position size
                        size = self._calculate_position_size()

                        if size > 0:
                            # Enter long position
                            self.buy(size=size)
                            self.entry_price = self.data.close[0]
                            self.entry_date = self.data.datetime.date(0)
                            self.trade_count += 1

                            if self.p.printlog:
                                self.log(f'BUY SIGNAL: RSI={self.rsi[0]:.2f}, Vol={self.data.volume[0]:.0f} (Avg={self.volume_sma[0]:.0f})')

        # Exit logic
        else:
            current_price = self.data.close[0]
            current_date = self.data.datetime.date(0)

            # Calculate profit/loss percentage
            pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100

            # Exit condition 1: RSI return to mean (> 50)
            if self.rsi[0] > self.p.rsi_exit_threshold:
                self.close()
                if self.p.printlog:
                    self.log(f'EXIT RSI>50: RSI={self.rsi[0]:.2f}, P&L={pnl_pct:+.2f}%')
                return

            # Exit condition 2: Profit target hit (2%)
            if pnl_pct >= self.p.profit_target_pct:
                self.close()
                if self.p.printlog:
                    self.log(f'EXIT PROFIT TARGET: {pnl_pct:+.2f}%')
                return

            # Exit condition 3: Stop loss hit (1%)
            if pnl_pct <= -self.p.stop_loss_pct:
                self.close()
                if self.p.printlog:
                    self.log(f'EXIT STOP LOSS: {pnl_pct:+.2f}%')
                return

            # Exit condition 4: Max hold time (3 days)
            days_held = (current_date - self.entry_date).days
            if days_held >= self.p.max_hold_days:
                self.close()
                if self.p.printlog:
                    self.log(f'EXIT TIME STOP: {days_held} days, P&L={pnl_pct:+.2f}%')
                return

    def _calculate_position_size(self):
        """
        Calculate position size based on 1% risk per trade

        Returns:
            int: Number of shares to buy
        """
        # Get available cash
        cash = self.broker.get_cash()
        portfolio_value = self.broker.get_value()

        # Calculate risk amount (1% of portfolio)
        risk_amount = portfolio_value * (self.p.risk_per_trade_pct / 100)

        # Calculate stop loss distance in dollars
        entry_price = self.data.close[0]
        stop_loss_price = entry_price * (1 - self.p.stop_loss_pct / 100)
        stop_distance = entry_price - stop_loss_price

        # Position size = Risk amount / Stop distance
        if stop_distance > 0:
            position_value = risk_amount / (stop_distance / entry_price)
            shares = int(position_value / entry_price)

            # Don't exceed available cash
            max_shares = int(cash / entry_price)
            shares = min(shares, max_shares)

            # Ensure at least 1 share
            return max(shares, 1)

        return 0

    def notify_order(self, order):
        """Handle order notifications"""
        if order.status in [order.Completed]:
            if order.isbuy():
                if self.p.printlog:
                    self.log(f'BUY EXECUTED: {order.executed.size} shares @ ${order.executed.price:.2f}')
            elif order.issell():
                if self.p.printlog:
                    self.log(f'SELL EXECUTED: {order.executed.size} shares @ ${order.executed.price:.2f}')

    def notify_trade(self, trade):
        """Handle trade notifications"""
        if trade.isclosed:
            pnl_pct = (trade.pnlcomm / abs(trade.value)) * 100 if trade.value != 0 else 0
            if self.p.printlog:
                self.log(f'TRADE CLOSED: P&L ${trade.pnlcomm:.2f} ({pnl_pct:+.2f}%)')

    def stop(self):
        """Called when strategy ends - print summary"""
        if self.p.printlog:
            self.log(f'Strategy Complete: {self.trade_count} total trades', level='INFO')


# Strategy configuration for easy import
BASIC_RSI_PARAMS = {
    'rsi_period': 14,
    'rsi_entry_threshold': 25,
    'rsi_exit_threshold': 50,
    'volume_period': 20,
    'volume_multiplier': 1.5,
    'profit_target_pct': 2.0,
    'stop_loss_pct': 1.0,
    'max_hold_days': 3,
    'risk_per_trade_pct': 1.0,
    'max_positions': 3,
    'printlog': True,
}
