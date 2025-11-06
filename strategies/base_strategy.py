#!/usr/bin/env python3
"""
Base Strategy Template for Backtrader
Epic 13: US-13.1 - Base Strategy Template

Provides foundation for migrating LEAN algorithms to Backtrader.
All custom strategies should inherit from BaseStrategy.

LEAN → Backtrader Mapping:
- Initialize() → __init__()
- OnData() → next()
- self.Portfolio → self.broker / self.position
- self.MarketOrder() → self.buy() / self.sell()
- self.Securities["SPY"] → self.datas[0] or self.getdatabyname("SPY")
- self.Time → self.datetime.datetime(0)
- self.Schedule.On() → Implement in prenext() / next()
"""

import backtrader as bt
import logging
from datetime import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BaseStrategy(bt.Strategy):
    """
    Base strategy template for Backtrader strategies.

    Provides common functionality and LEAN-compatible patterns:
    - Order management and tracking
    - Portfolio access methods
    - Position sizing helpers
    - Logging integration
    - Notification handlers
    """

    params = (
        ('initial_cash', 100000),      # Initial portfolio value
        ('position_size', 0.95),        # Default position size (95% of portfolio)
        ('printlog', True),             # Enable logging
        ('log_trades', True),           # Log trade execution
        ('log_orders', True),           # Log order events
    )

    def __init__(self):
        """
        Initialize strategy.

        Override this method in subclasses to:
        - Define indicators
        - Initialize state variables
        - Set up data references

        Equivalent to LEAN's Initialize()
        """
        # Track pending orders (one per data feed)
        self.orders = {}  # data -> order mapping

        # Track order history for analysis
        self.order_history = []

        # Initialize counters
        self.bar_count = 0
        self.trade_count = 0

        logger.info(f"{self.__class__.__name__} initialized")

    def log(self, txt, dt=None, level='INFO'):
        """
        Logging function with timestamp.

        Args:
            txt: Message to log
            dt: Optional datetime (uses current bar time if None)
            level: Log level (INFO, WARNING, ERROR)
        """
        if not self.params.printlog:
            return

        # Check if data is available
        if len(self.datas) > 0 and len(self.datas[0]) > 0:
            dt = dt or self.datas[0].datetime.date(0)
            timestamp = dt.isoformat()
        else:
            # Fallback to current datetime if no data available yet
            from datetime import datetime
            timestamp = datetime.now().isoformat()

        if level == 'INFO':
            logger.info(f'{timestamp} | {txt}')
        elif level == 'WARNING':
            logger.warning(f'{timestamp} | {txt}')
        elif level == 'ERROR':
            logger.error(f'{timestamp} | {txt}')
        else:
            logger.info(f'{timestamp} | {txt}')

    # ===================================================================
    # Order Notification Methods (Equivalent to LEAN's OnOrderEvent)
    # ===================================================================

    def notify_order(self, order):
        """
        Notification of order status changes.

        Called when orders are submitted, accepted, completed, canceled, etc.
        Override this to add custom order handling logic.

        Args:
            order: Backtrader Order object
        """
        # Get the data this order belongs to
        data = order.data

        # Pending states
        if order.status in [order.Submitted, order.Accepted]:
            if self.params.log_orders:
                self.log(f'Order {order.ref} {"SUBMITTED" if order.status == order.Submitted else "ACCEPTED"}: '
                        f'{order.tradeid} {data._name} '
                        f'{"BUY" if order.isbuy() else "SELL"} {order.created.size}')
            return

        # Completed orders
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED: {data._name} | '
                        f'Price: ${order.executed.price:.2f} | '
                        f'Size: {order.executed.size} | '
                        f'Cost: ${order.executed.value:.2f} | '
                        f'Comm: ${order.executed.comm:.2f}',
                        level='INFO' if self.params.log_trades else 'DEBUG')

            elif order.issell():
                self.log(f'SELL EXECUTED: {data._name} | '
                        f'Price: ${order.executed.price:.2f} | '
                        f'Size: {order.executed.size} | '
                        f'Value: ${order.executed.value:.2f} | '
                        f'Comm: ${order.executed.comm:.2f}',
                        level='INFO' if self.params.log_trades else 'DEBUG')

            # Record order execution
            self.order_history.append({
                'datetime': self.datas[0].datetime.datetime(0),
                'type': 'BUY' if order.isbuy() else 'SELL',
                'symbol': data._name,
                'size': order.executed.size,
                'price': order.executed.price,
                'value': order.executed.value,
                'commission': order.executed.comm,
            })

        # Failed orders
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order {order.ref} FAILED: '
                    f'{"CANCELED" if order.status == order.Canceled else "MARGIN" if order.status == order.Margin else "REJECTED"}',
                    level='WARNING')

        # Clear the order reference
        if data in self.orders and self.orders[data] == order:
            self.orders[data] = None

    def notify_trade(self, trade):
        """
        Notification of closed trades.

        Called when a trade is closed (position goes to 0).
        Override this to add custom trade analysis.

        Args:
            trade: Backtrader Trade object
        """
        if not trade.isclosed:
            return

        self.trade_count += 1
        pnl_pct = (trade.pnlcomm / abs(trade.value)) * 100 if trade.value != 0 else 0

        self.log(f'TRADE CLOSED: {trade.data._name} | '
                f'Gross P&L: ${trade.pnl:.2f} | '
                f'Net P&L: ${trade.pnlcomm:.2f} ({pnl_pct:+.2f}%) | '
                f'Bars: {trade.barlen}',
                level='INFO' if self.params.log_trades else 'DEBUG')

    # ===================================================================
    # Main Strategy Logic (Equivalent to LEAN's OnData)
    # ===================================================================

    def prenext(self):
        """
        Called before minimum period is met.

        Use this for warmup logic or to handle partial indicator availability.
        """
        self.bar_count += 1

    def next(self):
        """
        Main strategy logic - called for each bar.

        Override this method in subclasses to implement trading logic.
        This is equivalent to LEAN's OnData() method.

        Example:
            def next(self):
                # Check if we have pending orders
                if self.order:
                    return

                # Entry logic
                if not self.position:
                    if self.data.close[0] > self.sma[0]:
                        self.order = self.buy()

                # Exit logic
                else:
                    if self.data.close[0] < self.sma[0]:
                        self.order = self.close()
        """
        self.bar_count += 1

        # Log portfolio status periodically (every 20 bars)
        if self.bar_count % 20 == 0:
            self.log(f'Portfolio Value: ${self.broker.getvalue():,.2f} | '
                    f'Cash: ${self.broker.getcash():,.2f} | '
                    f'Bars: {self.bar_count}',
                    level='DEBUG')

    # ===================================================================
    # Portfolio Access Methods (LEAN-compatible)
    # ===================================================================

    def get_portfolio_value(self):
        """
        Get current total portfolio value (cash + positions).

        Equivalent to LEAN's self.Portfolio.TotalPortfolioValue
        """
        return self.broker.getvalue()

    def get_cash(self):
        """
        Get available cash.

        Equivalent to LEAN's self.Portfolio.Cash
        """
        return self.broker.getcash()

    def get_position_size(self, data=None):
        """
        Get current position size for a data feed.

        Args:
            data: Data feed (uses self.data if None)

        Returns:
            Position size (positive for long, negative for short, 0 for flat)

        Equivalent to LEAN's self.Portfolio[symbol].Quantity
        """
        data = data or self.data
        position = self.getposition(data)
        return position.size if position else 0

    def get_position_value(self, data=None):
        """
        Get current position value.

        Args:
            data: Data feed (uses self.data if None)

        Returns:
            Position value in dollars
        """
        data = data or self.data
        position = self.getposition(data)
        if position and position.size != 0:
            return position.size * data.close[0]
        return 0.0

    def is_invested(self, data=None):
        """
        Check if we have an open position.

        Args:
            data: Data feed (uses self.data if None)

        Returns:
            True if position size != 0

        Equivalent to LEAN's self.Portfolio[symbol].Invested
        """
        return self.get_position_size(data) != 0

    # ===================================================================
    # Position Sizing Helpers
    # ===================================================================

    def calculate_position_size(self, price, pct_portfolio=None):
        """
        Calculate position size based on portfolio percentage.

        Args:
            price: Entry price per share
            pct_portfolio: Percentage of portfolio to allocate (uses self.params.position_size if None)

        Returns:
            Number of shares to buy/sell
        """
        pct = pct_portfolio or self.params.position_size
        cash_to_invest = self.broker.getcash() * pct
        size = int(cash_to_invest / price)
        return size

    def calculate_shares_from_value(self, target_value, price):
        """
        Calculate shares needed to reach target dollar value.

        Args:
            target_value: Target position value in dollars
            price: Price per share

        Returns:
            Number of shares
        """
        return int(target_value / price)

    # ===================================================================
    # Order Management Helpers
    # ===================================================================

    def has_pending_order(self, data=None):
        """
        Check if there's a pending order for a data feed.

        Args:
            data: Data feed (uses self.data if None)

        Returns:
            True if there's a pending order
        """
        data = data or self.data
        return data in self.orders and self.orders[data] is not None

    def cancel_pending_orders(self, data=None):
        """
        Cancel all pending orders for a data feed.

        Args:
            data: Data feed (cancels all if None)
        """
        if data:
            if data in self.orders and self.orders[data]:
                self.cancel(self.orders[data])
                self.orders[data] = None
        else:
            for data_feed, order in list(self.orders.items()):
                if order:
                    self.cancel(order)
                    self.orders[data_feed] = None

    # ===================================================================
    # Trading Methods (LEAN-compatible wrappers)
    # ===================================================================

    def market_order(self, data, size):
        """
        Place market order (LEAN-compatible method).

        Args:
            data: Data feed
            size: Number of shares (positive for buy, negative for sell)

        Returns:
            Order object
        """
        if size > 0:
            order = self.buy(data=data, size=size)
        elif size < 0:
            order = self.sell(data=data, size=abs(size))
        else:
            return None

        self.orders[data] = order
        return order

    def close_position(self, data=None):
        """
        Close current position for a data feed.

        Args:
            data: Data feed (uses self.data if None)

        Returns:
            Order object (or None if no position)

        Equivalent to LEAN's self.Liquidate(symbol)
        """
        data = data or self.data
        position_size = self.get_position_size(data)

        if position_size == 0:
            return None

        order = self.close(data=data)
        self.orders[data] = order
        return order

    # ===================================================================
    # Lifecycle Methods
    # ===================================================================

    def start(self):
        """Called when strategy starts (before any data)."""
        self.log(f"Strategy starting with ${self.broker.getvalue():,.2f}")

    def stop(self):
        """Called when strategy ends."""
        self.log(f"Strategy stopping. Final value: ${self.broker.getvalue():,.2f}")
        self.log(f"Total trades: {self.trade_count}")
        self.log(f"Total bars processed: {self.bar_count}")


if __name__ == "__main__":
    print("BaseStrategy Template - Ready for use")
    print("\nUsage:")
    print("  from strategies.base_strategy import BaseStrategy")
    print("  class MyStrategy(BaseStrategy):")
    print("      def __init__(self):")
    print("          super().__init__()")
    print("          # Initialize indicators")
    print("      def next(self):")
    print("          # Trading logic")
