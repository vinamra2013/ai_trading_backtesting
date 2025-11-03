"""
Simple Moving Average Crossover Strategy
Epic 12: Sample Strategy for Testing

Classic SMA crossover strategy:
- Buy when fast SMA crosses above slow SMA (golden cross)
- Sell when fast SMA crosses below slow SMA (death cross)

Parameters:
- fast_period: Fast SMA period (default: 10)
- slow_period: Slow SMA period (default: 30)
- position_size: Number of shares per trade (default: 100)
"""

import backtrader as bt


class SMACrossover(bt.Strategy):
    """
    Simple Moving Average Crossover Strategy

    Entry Signal:
    - Buy when fast SMA crosses above slow SMA

    Exit Signal:
    - Sell when fast SMA crosses below slow SMA

    Position Sizing:
    - Fixed number of shares per trade
    """

    params = (
        ('fast_period', 10),
        ('slow_period', 30),
        ('position_size', 100),
        ('printlog', True),
    )

    def __init__(self):
        """Initialize strategy indicators"""
        # Keep reference to close price
        self.dataclose = self.datas[0].close

        # Create SMA indicators
        self.sma_fast = bt.indicators.SimpleMovingAverage(
            self.datas[0],
            period=self.params.fast_period
        )

        self.sma_slow = bt.indicators.SimpleMovingAverage(
            self.datas[0],
            period=self.params.slow_period
        )

        # Create crossover indicator
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)

        # Track order status
        self.order = None
        self.buy_price = None
        self.buy_comm = None

    def notify_order(self, order):
        """Notification of order status"""
        if order.status in [order.Submitted, order.Accepted]:
            # Order submitted/accepted - no action required
            return

        # Check if order completed
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
                self.log(
                    f'BUY EXECUTED | Price: ${order.executed.price:.2f} | '
                    f'Cost: ${order.executed.value:.2f} | '
                    f'Comm: ${order.executed.comm:.2f}'
                )
            elif order.issell():
                self.log(
                    f'SELL EXECUTED | Price: ${order.executed.price:.2f} | '
                    f'Cost: ${order.executed.value:.2f} | '
                    f'Comm: ${order.executed.comm:.2f}'
                )

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order Canceled/Margin/Rejected')

        # Reset order
        self.order = None

    def notify_trade(self, trade):
        """Notification of closed trade"""
        if not trade.isclosed:
            return

        self.log(
            f'TRADE CLOSED | Gross P&L: ${trade.pnl:.2f} | '
            f'Net P&L: ${trade.pnlcomm:.2f}'
        )

    def next(self):
        """Execute strategy logic on each bar"""
        # Check if an order is pending
        if self.order:
            return

        # Check if we are in the market
        if not self.position:
            # Not in market - look for buy signal
            if self.crossover > 0:  # Golden cross
                self.log(f'BUY SIGNAL | Price: ${self.dataclose[0]:.2f}')
                self.order = self.buy(size=self.params.position_size)

        else:
            # In market - look for sell signal
            if self.crossover < 0:  # Death cross
                self.log(f'SELL SIGNAL | Price: ${self.dataclose[0]:.2f}')
                self.order = self.sell(size=self.params.position_size)

    def log(self, txt, dt=None):
        """Logging function"""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} | {txt}')

    def stop(self):
        """Called when backtest ends"""
        self.log(
            f'Strategy Ended | Fast SMA: {self.params.fast_period} | '
            f'Slow SMA: {self.params.slow_period} | '
            f'Final Value: ${self.broker.getvalue():.2f}',
            dt=self.datas[0].datetime.date(0)
        )


class SMACrossoverOptimized(SMACrossover):
    """
    Optimized version of SMA Crossover with additional features:
    - Stop loss
    - Take profit
    - Position sizing based on portfolio value
    """

    params = (
        ('fast_period', 10),
        ('slow_period', 30),
        ('position_pct', 0.10),  # 10% of portfolio per trade
        ('stop_loss_pct', 0.05),  # 5% stop loss
        ('take_profit_pct', 0.15),  # 15% take profit
        ('printlog', True),
    )

    def next(self):
        """Execute strategy logic with risk management"""
        # Check if an order is pending
        if self.order:
            return

        # Check if we are in the market
        if not self.position:
            # Not in market - look for buy signal
            if self.crossover > 0:  # Golden cross
                # Calculate position size based on portfolio value
                cash = self.broker.get_cash()
                price = self.dataclose[0]
                size = int((cash * self.params.position_pct) / price)

                if size > 0:
                    self.log(f'BUY SIGNAL | Price: ${price:.2f} | Size: {size}')
                    self.order = self.buy(size=size)

        else:
            # In market - check exit conditions
            current_price = self.dataclose[0]
            entry_price = self.buy_price

            # Calculate P&L percentage
            pnl_pct = ((current_price - entry_price) / entry_price) * 100

            # Stop loss
            if pnl_pct <= -self.params.stop_loss_pct * 100:
                self.log(f'STOP LOSS | P&L: {pnl_pct:.2f}% | Price: ${current_price:.2f}')
                self.order = self.sell(size=self.position.size)

            # Take profit
            elif pnl_pct >= self.params.take_profit_pct * 100:
                self.log(f'TAKE PROFIT | P&L: {pnl_pct:.2f}% | Price: ${current_price:.2f}')
                self.order = self.sell(size=self.position.size)

            # Death cross exit
            elif self.crossover < 0:
                self.log(f'SELL SIGNAL | P&L: {pnl_pct:.2f}% | Price: ${current_price:.2f}')
                self.order = self.sell(size=self.position.size)


if __name__ == '__main__':
    """Test strategy import"""
    print("SMA Crossover Strategy")
    print(f"  Default Parameters:")
    print(f"    Fast Period: {SMACrossover.params.fast_period}")
    print(f"    Slow Period: {SMACrossover.params.slow_period}")
    print(f"    Position Size: {SMACrossover.params.position_size}")
    print("\n✅ Strategy loaded successfully!")
