"""
Simple Test Strategy for Optimization Testing
Epic 17: Test strategy that generates trades for optimization validation
"""

import backtrader as bt
import random


class TestStrategy(bt.Strategy):
    """
    Simple test strategy that generates random trades for optimization testing.
    """

    params = (
        ('buy_threshold', 0.5),  # Random threshold for buying
        ('sell_threshold', 0.5),  # Random threshold for selling
        ('position_size', 100),
        ('printlog', True),
    )

    def __init__(self):
        """Initialize strategy"""
        self.dataclose = self.datas[0].close
        self.order = None

    def next(self):
        """Execute strategy logic"""
        if self.order:
            return

        # Generate random signals to ensure some trades happen
        if not self.position:
            # Buy if random > buy_threshold
            if random.random() > self.params.buy_threshold:
                self.log(f'BUY SIGNAL | Price: ${self.dataclose[0]:.2f}')
                self.order = self.buy(size=self.params.position_size)
        else:
            # Sell if random > sell_threshold
            if random.random() > self.params.sell_threshold:
                self.log(f'SELL SIGNAL | Price: ${self.dataclose[0]:.2f}')
                self.order = self.sell(size=self.params.position_size)

    def notify_order(self, order):
        """Notification of order status"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED | Price: ${order.executed.price:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED | Price: ${order.executed.price:.2f}')

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        """Notification of closed trade"""
        if not trade.isclosed:
            return

        self.log(f'TRADE CLOSED | P&L: ${trade.pnl:.2f}')

    def log(self, txt, dt=None):
        """Logging function"""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} | {txt}')

    def stop(self):
        """Called when backtest ends"""
        self.log(f'Test Strategy Ended | Final Value: ${self.broker.getvalue():.2f}')