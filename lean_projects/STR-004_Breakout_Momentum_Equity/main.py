"""
Breakout Momentum Equity Strategy

Strategy Logic:
- Entry: Price breaks above N-day resistance (high) by X% with volume spike confirmation
- Exit: Holding period (N days), profit target, or stop loss - whichever comes first
- Risk Management: Maximum 1% portfolio risk per trade
- Position Sizing: Based on stop loss percentage and available capital

This is a breakout momentum strategy designed to:
1. Capture strong price breakouts with volume confirmation
2. Avoid false breakouts through threshold and volume filters
3. Use holding period to ride multi-day momentum
4. Implement strict risk management (1% max risk per trade)
5. Generate 50+ trades over 5-year backtest for statistical significance

Author: QuantConnect LEAN
Version: 1.0 (Initial Implementation)
"""

from AlgorithmImports import *


class BreakoutMomentumEquity(QCAlgorithm):
    """
    Breakout momentum strategy for individual equities.
    Uses N-day high resistance levels, breakout threshold, and volume confirmation.
    """

    def initialize(self):
        """
        Initialize the algorithm with parameters, data, and indicators.
        """
        # Backtest period: 5 years for statistical significance
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(1000)

        # Set brokerage model to Interactive Brokers for accurate fee simulation
        self.set_brokerage_model(BrokerageName.INTERACTIVE_BROKERS_BROKERAGE)

        # CRITICAL: Use get_parameter() for ALL optimizable values
        self.lookback_period = int(self.get_parameter("lookback_period", "30"))
        self.breakout_threshold = float(self.get_parameter("breakout_threshold", "0.02"))
        self.volume_multiplier = float(self.get_parameter("volume_multiplier", "2.0"))
        self.holding_period = int(self.get_parameter("holding_period", "5"))
        self.profit_target_pct = float(self.get_parameter("profit_target_pct", "0.02"))
        self.stop_loss_pct = float(self.get_parameter("stop_loss_pct", "0.015"))

        # Symbol selection (QQQ for testing - can be customized)
        symbol_ticker = self.get_parameter("symbol", "QQQ")
        self.symbol = self.add_equity(symbol_ticker, Resolution.DAILY).symbol

        # Track N-day highs and volumes manually
        self.daily_highs = []
        self.daily_volumes = []

        # Track trade state
        self.entry_price = None
        self.entry_date = None
        self.days_invested = 0

        # Debug logging
        self.debug(f"Strategy initialized with parameters:")
        self.debug(f"  Symbol: {symbol_ticker}")
        self.debug(f"  Lookback Period: {self.lookback_period}")
        self.debug(f"  Breakout Threshold: {self.breakout_threshold * 100}%")
        self.debug(f"  Volume Multiplier: {self.volume_multiplier}x")
        self.debug(f"  Holding Period: {self.holding_period} days")
        self.debug(f"  Profit Target: {self.profit_target_pct * 100}%")
        self.debug(f"  Stop Loss: {self.stop_loss_pct * 100}%")

    def on_data(self, data):
        """
        Called on each data point (daily bar).

        Entry Logic:
        - Calculate N-day high (resistance level)
        - Calculate N-day average volume
        - Entry when: price > (N_day_high × (1 + breakout_threshold))
                      AND volume > (avg_volume × volume_multiplier)

        Exit Logic:
        1. Holding period: Exit after N days
        2. Profit target: Exit when gain >= profit_target_pct
        3. Stop loss: Exit when loss <= -stop_loss_pct
        """
        # CRITICAL: Check data availability first
        if not data.bars.contains_key(self.symbol):
            return

        # Get current bar data
        bar = data.bars[self.symbol]
        current_price = bar.close
        current_high = bar.high
        current_volume = bar.volume

        # Update tracking lists
        self.daily_highs.append(current_high)
        self.daily_volumes.append(current_volume)

        # Keep only last N values (lookback period)
        if len(self.daily_highs) > self.lookback_period:
            self.daily_highs.pop(0)
        if len(self.daily_volumes) > self.lookback_period:
            self.daily_volumes.pop(0)

        # Need at least lookback_period bars before trading
        if len(self.daily_highs) < self.lookback_period:
            return

        # Calculate N-day high (resistance level)
        n_day_high = max(self.daily_highs[:-1])  # Exclude today's high

        # Calculate average volume
        avg_volume = sum(self.daily_volumes) / len(self.daily_volumes)

        # Check if we have an open position
        if self.portfolio[self.symbol].invested:
            # Increment days invested counter
            self.days_invested += 1
            self._check_exit_conditions(current_price)
        else:
            # Reset days invested when not in position
            self.days_invested = 0
            self._check_entry_conditions(current_price, current_volume, n_day_high, avg_volume)

    def _check_entry_conditions(self, current_price, current_volume, n_day_high, avg_volume):
        """
        Check and execute entry logic.

        Entry Signal:
        1. Price > (N_day_high × (1 + breakout_threshold)) - Breakout condition
        2. Volume > (avg_volume × volume_multiplier) - Volume confirmation

        Position Sizing: Risk-based using stop loss percentage
        """
        # Calculate breakout price threshold
        breakout_price = n_day_high * (1.0 + self.breakout_threshold)

        # Calculate volume threshold
        volume_threshold = avg_volume * self.volume_multiplier

        # Check both conditions
        price_breakout = current_price > breakout_price
        volume_confirmation = current_volume > volume_threshold

        if price_breakout and volume_confirmation:
            # Calculate position size based on risk management
            shares = self._calculate_position_size(current_price)

            if shares > 0:
                # Execute market order
                self.market_order(self.symbol, shares)

                # Track entry state
                self.entry_price = current_price
                self.entry_date = self.time
                self.days_invested = 0

                # Debug logging
                self.debug(f"ENTRY: {self.time} | Price: ${current_price:.2f} | Breakout Level: ${breakout_price:.2f} | Volume: {current_volume:.0f} | Avg Volume: {avg_volume:.0f} | Shares: {shares}")

    def _check_exit_conditions(self, current_price):
        """
        Check and execute exit logic.

        Exit Signals (first one to trigger):
        1. Holding Period: Exit after N days
        2. Profit Target: Gain >= profit_target_pct
        3. Stop Loss: Loss <= -stop_loss_pct
        """
        if self.entry_price is None:
            # Safety check: if entry price not tracked, use current holdings value
            self.entry_price = self.portfolio[self.symbol].average_price

        # Calculate current profit/loss percentage
        pnl_pct = (current_price - self.entry_price) / self.entry_price

        exit_reason = None

        # Check holding period (highest priority - always exit after N days)
        if self.days_invested >= self.holding_period:
            exit_reason = f"Holding Period ({self.days_invested} days >= {self.holding_period} days)"

        # Check profit target
        elif pnl_pct >= self.profit_target_pct:
            exit_reason = f"Profit Target ({pnl_pct * 100:.2f}% >= {self.profit_target_pct * 100:.2f}%)"

        # Check stop loss
        elif pnl_pct <= -self.stop_loss_pct:
            exit_reason = f"Stop Loss ({pnl_pct * 100:.2f}% <= {-self.stop_loss_pct * 100:.2f}%)"

        # Execute exit if any condition met
        if exit_reason:
            self.liquidate(self.symbol)

            # Debug logging
            self.debug(f"EXIT: {self.time} | Price: ${current_price:.2f} | Days Held: {self.days_invested} | P&L: {pnl_pct * 100:.2f}% | Reason: {exit_reason}")

            # Reset entry state
            self.entry_price = None
            self.entry_date = None
            self.days_invested = 0

    def _calculate_position_size(self, entry_price):
        """
        Calculate position size based on risk management rules.

        Formula:
        1. Max risk = 1% of portfolio value
        2. Risk per share = entry_price × stop_loss_pct
        3. Max shares by risk = max_risk_dollars / risk_per_share
        4. Max shares by cash = 95% of available cash / entry_price (5% buffer)
        5. Final shares = min(max_shares_by_risk, max_shares_by_cash)

        Returns:
            int: Number of shares to buy (0 if insufficient capital)
        """
        portfolio_value = self.portfolio.total_portfolio_value
        available_cash = self.portfolio.cash

        # Calculate maximum risk in dollars (1% of portfolio)
        max_risk_dollars = portfolio_value * 0.01

        # Calculate risk per share based on stop loss
        risk_per_share = entry_price * self.stop_loss_pct

        # Avoid division by zero
        if risk_per_share == 0:
            return 0

        # Calculate maximum shares based on risk
        max_shares_by_risk = int(max_risk_dollars / risk_per_share)

        # Calculate maximum shares based on available cash (keep 5% buffer)
        max_shares_by_cash = int((available_cash * 0.95) / entry_price)

        # Take the minimum to respect both constraints
        final_shares = min(max_shares_by_risk, max_shares_by_cash)

        # Debug logging for position sizing
        if final_shares > 0:
            self.debug(f"Position Sizing: Portfolio=${portfolio_value:.2f} | Cash=${available_cash:.2f} | Risk Shares={max_shares_by_risk} | Cash Shares={max_shares_by_cash} | Final={final_shares}")

        return final_shares

    def on_order_event(self, order_event):
        """
        Handle order fill events for logging and tracking.
        """
        if order_event.status == OrderStatus.FILLED:
            order = self.transactions.get_order_by_id(order_event.order_id)
            self.debug(f"ORDER FILLED: {order.symbol} | Quantity: {order.quantity} | Fill Price: ${order_event.fill_price:.2f}")
