"""
Basic RSI Mean Reversion Strategy - LEAN/QuantConnect Format
Ported from Backtrader to LEAN for QuantConnect cloud platform

Strategy Logic:
- Entry: RSI(14) < 25 (oversold) + Volume > 1.5x average
- Exit: RSI(14) > 50 OR 2% profit OR 1% stop OR 3 days max hold
- Position Sizing: 1% risk per trade, max 3 positions
- Target: 1%+ average profit per trade with 65%+ win rate

Author: Quant Director
Date: 2025-11-10
Platform: QuantConnect LEAN
"""

from AlgorithmImports import *

class RSIMeanReversionBasic(QCAlgorithm):
    """
    Basic RSI Mean Reversion Strategy for QuantConnect

    Entry Conditions (ALL required):
    1. RSI(14) < 25 (deeply oversold)
    2. Volume > 1.5x 20-day average (capitulation confirmation)

    Exit Conditions (ANY triggers exit):
    1. RSI(14) > 50 (return to mean)
    2. Price up 2% from entry (profit target)
    3. Price down 1% from entry (stop loss)
    4. 3 trading days elapsed (time stop)
    """

    def initialize(self):
        """Initialize algorithm parameters and data subscriptions"""

        # Set date range for backtesting
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(1000)

        # Strategy parameters
        self.rsi_period = 14
        self.rsi_entry_threshold = 25
        self.rsi_exit_threshold = 50
        self.volume_period = 20
        self.volume_multiplier = 1.5

        # Exit parameters
        self.profit_target_pct = 0.02  # 2%
        self.stop_loss_pct = 0.01      # 1%
        self.max_hold_days = 3

        # Risk management
        self.risk_per_trade_pct = 0.01  # 1%
        self.max_positions = 3

        # Storage for indicators and position tracking
        self.rsi_indicators = {}
        self.volume_sma = {}
        self.entry_prices = {}
        self.entry_times = {}
        self.entry_bars = {}  # Track number of bars held

        # Add symbols and create indicators
        self.symbols = ["NVDA", "AVGO", "AMZN", "MSFT", "GOOGL", "QCOM", "UNH"]

        for ticker in self.symbols:
            symbol = self.add_equity(ticker, Resolution.Daily).symbol

            # Create and store RSI indicator
            self.rsi_indicators[symbol] = self.rsi(symbol, self.rsi_period, MovingAverageType.Wilders, Resolution.Daily)

            # Create and store Volume SMA indicator
            self.volume_sma[symbol] = self.sma(symbol, self.volume_period, Resolution.Daily, Field.Volume)

        # Set brokerage model
        self.set_brokerage_model(BrokerageName.InteractiveBrokersBrokerage, AccountType.Margin)

        # Log strategy start
        self.debug("=" * 60)
        self.debug("RSI Mean Reversion Strategy Initialized")
        self.debug(f"Symbols: {', '.join(self.symbols)}")
        self.debug(f"Entry: RSI < {self.rsi_entry_threshold}, Volume > {self.volume_multiplier}x avg")
        self.debug(f"Exit: RSI > {self.rsi_exit_threshold} OR +{self.profit_target_pct*100}% OR -{self.stop_loss_pct*100}% OR {self.max_hold_days} days")
        self.debug("=" * 60)

    def on_data(self, data):
        """Main event handler called when new data arrives"""

        # CRITICAL: Check exits FIRST before considering new entries
        self.check_exits_inline(data)

        # Check each symbol for entry opportunities
        for symbol in self.rsi_indicators.keys():

            # Skip if we don't have data
            if symbol not in data or data[symbol] is None:
                continue

            # Skip if already invested
            if self.portfolio[symbol].invested:
                continue

            # Skip if at max positions
            if self.get_open_position_count() >= self.max_positions:
                continue

            # Check entry conditions
            if self.check_entry_conditions(symbol, data):
                self.enter_position(symbol, data)

    def check_entry_conditions(self, symbol, data):
        """Check if entry conditions are met"""

        # Get RSI indicator
        rsi = self.rsi_indicators[symbol]
        if not rsi.is_ready:
            return False

        # Check RSI oversold
        if rsi.current.value >= self.rsi_entry_threshold:
            return False

        # Get volume SMA
        vol_sma = self.volume_sma[symbol]
        if not vol_sma.is_ready:
            return False

        # Check volume confirmation
        current_volume = data[symbol].volume
        if current_volume < (vol_sma.current.value * self.volume_multiplier):
            return False

        return True

    def enter_position(self, symbol, data):
        """Enter a long position"""

        # Get current price
        price = data[symbol].close

        # Calculate position size based on 1% risk
        portfolio_value = self.portfolio.total_portfolio_value
        risk_amount = portfolio_value * self.risk_per_trade_pct

        # Position value = Risk / Stop percentage
        position_value = risk_amount / self.stop_loss_pct

        # Don't exceed available cash
        position_value = min(position_value, self.portfolio.cash * 0.95)

        # Calculate shares
        shares = int(position_value / price)

        if shares < 1:
            return

        # Place market order
        self.market_order(symbol, shares)

        # Track entry
        self.entry_prices[symbol] = price
        self.entry_times[symbol] = self.time
        self.entry_bars[symbol] = 0

        # Log
        rsi_value = self.rsi_indicators[symbol].current.value
        self.debug(f">>> BUY {symbol.value}: {shares} shares @ ${price:.2f}, RSI={rsi_value:.2f}")

    def check_exits_inline(self, data):
        """Check exit conditions for all positions - called every bar in on_data()"""

        for symbol in list(self.entry_prices.keys()):

            # Skip if position is closed
            if not self.portfolio[symbol].invested:
                if symbol in self.entry_prices:
                    del self.entry_prices[symbol]
                if symbol in self.entry_times:
                    del self.entry_times[symbol]
                if symbol in self.entry_bars:
                    del self.entry_bars[symbol]
                continue

            # Skip if no data for this symbol
            if symbol not in data or data[symbol] is None:
                continue

            # Increment bars held counter
            self.entry_bars[symbol] += 1

            # Get position details
            entry_price = self.entry_prices[symbol]
            entry_time = self.entry_times[symbol]
            current_price = data[symbol].close
            bars_held = self.entry_bars[symbol]

            # Calculate P&L percentage
            pnl_pct = (current_price - entry_price) / entry_price

            # Get RSI
            rsi = self.rsi_indicators[symbol]
            rsi_value = rsi.current.value if rsi.is_ready else 0

            # Exit condition 1: RSI return to mean
            if rsi.is_ready and rsi_value > self.rsi_exit_threshold:
                self.liquidate(symbol)
                self.debug(f"<<< EXIT {symbol.value}: RSI>{self.rsi_exit_threshold} (RSI={rsi_value:.2f}), P&L={pnl_pct*100:+.2f}%, Bars={bars_held}")
                self.cleanup_position_tracking(symbol)
                continue

            # Exit condition 2: Profit target
            if pnl_pct >= self.profit_target_pct:
                self.liquidate(symbol)
                self.debug(f"<<< EXIT {symbol.value}: PROFIT TARGET (+{self.profit_target_pct*100}%), P&L={pnl_pct*100:+.2f}%, Bars={bars_held}")
                self.cleanup_position_tracking(symbol)
                continue

            # Exit condition 3: Stop loss
            if pnl_pct <= -self.stop_loss_pct:
                self.liquidate(symbol)
                self.debug(f"<<< EXIT {symbol.value}: STOP LOSS (-{self.stop_loss_pct*100}%), P&L={pnl_pct*100:+.2f}%, Bars={bars_held}")
                self.cleanup_position_tracking(symbol)
                continue

            # Exit condition 4: Time stop (days)
            days_held = (self.time - entry_time).days
            if days_held >= self.max_hold_days:
                self.liquidate(symbol)
                self.debug(f"<<< EXIT {symbol.value}: TIME STOP ({days_held} days), P&L={pnl_pct*100:+.2f}%, Bars={bars_held}")
                self.cleanup_position_tracking(symbol)
                continue

            # Log position status every 5 bars for monitoring
            if bars_held % 5 == 0:
                self.debug(f"--- HOLD {symbol.value}: P&L={pnl_pct*100:+.2f}%, RSI={rsi_value:.2f}, Bars={bars_held}, Days={days_held}")

    def cleanup_position_tracking(self, symbol):
        """Clean up tracking dictionaries after exit"""
        if symbol in self.entry_prices:
            del self.entry_prices[symbol]
        if symbol in self.entry_times:
            del self.entry_times[symbol]
        if symbol in self.entry_bars:
            del self.entry_bars[symbol]

    def get_open_position_count(self):
        """Count number of currently open positions"""
        count = 0
        for kvp in self.portfolio:
            if kvp.value.invested:
                count += 1
        return count

    def on_order_event(self, order_event):
        """Handle order events"""

        if order_event.status != OrderStatus.Filled:
            return

        order = self.transactions.get_order_by_id(order_event.order_id)

        if order.direction == OrderDirection.Buy:
            self.debug(f"*** ORDER FILLED: BUY {order.symbol.value} {order_event.fill_quantity} @ ${order_event.fill_price:.2f}")
        else:
            self.debug(f"*** ORDER FILLED: SELL {order.symbol.value} {order_event.fill_quantity} @ ${order_event.fill_price:.2f}")

    def on_end_of_algorithm(self):
        """Called at the end of the backtest"""
        self.debug("=" * 60)
        self.debug("BACKTEST COMPLETE")
        self.debug(f"Final Portfolio Value: ${self.portfolio.total_portfolio_value:.2f}")
        self.debug(f"Net Profit: ${self.portfolio.total_portfolio_value - 1000:.2f}")
        self.debug(f"Open Positions at End: {self.get_open_position_count()}")
        self.debug("=" * 60)
