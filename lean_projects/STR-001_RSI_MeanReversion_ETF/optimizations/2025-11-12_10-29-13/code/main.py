"""
RSI Mean Reversion ETF Strategy - LOW FREQUENCY VERSION

Strategy Logic:
- Entry: Buy SPY when RSI < entry_threshold (oversold condition)
- Exit: Sell when RSI > exit_threshold (overbought), profit target, or stop loss hit
- Risk Management: Maximum 1% portfolio risk per trade
- Position Sizing: Based on stop loss percentage and available capital

This is a low-frequency strategy designed to:
1. Generate 100+ trades over 5-year backtest for statistical significance
2. Control trading costs through daily resolution
3. Implement strict risk management (1% max risk per trade)
4. Use relaxed RSI thresholds (25-35 entry vs original 25) for more signals

Author: QuantConnect LEAN
Version: 2.0 (Rebuild)
"""

from AlgorithmImports import *


class RSIMeanReversionETF(QCAlgorithm):
    """
    RSI-based mean reversion strategy for liquid ETFs (SPY).
    Uses relaxed thresholds to generate consistent trading signals.
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
        # These defaults match the relaxed threshold strategy from lessons learned
        self.rsi_period = int(self.get_parameter("rsi_period", "14"))
        self.entry_threshold = int(self.get_parameter("entry_threshold", "30"))
        self.exit_threshold = int(self.get_parameter("exit_threshold", "70"))
        self.stop_loss_pct = float(self.get_parameter("stop_loss_pct", "0.01"))
        self.profit_target_pct = float(self.get_parameter("profit_target_pct", "0.02"))

        # Add SPY with daily resolution for fee control
        self.spy_symbol = self.add_equity("SPY", Resolution.DAILY).symbol

        # Create RSI indicator with CORRECT LEAN API pattern
        # CRITICAL: Use MovingAverageType.WILDERS for RSI (not Exponential)
        self.rsi_indicator = self.rsi(
            self.spy_symbol,
            self.rsi_period,
            MovingAverageType.WILDERS,
            Resolution.DAILY
        )

        # Track entry price for profit target and stop loss calculations
        self.entry_price = None

        # Debug logging
        self.debug(f"Strategy initialized with parameters:")
        self.debug(f"  RSI Period: {self.rsi_period}")
        self.debug(f"  Entry Threshold: {self.entry_threshold}")
        self.debug(f"  Exit Threshold: {self.exit_threshold}")
        self.debug(f"  Stop Loss: {self.stop_loss_pct * 100}%")
        self.debug(f"  Profit Target: {self.profit_target_pct * 100}%")

    def on_data(self, data):
        """
        Called on each data point (daily bar).

        Entry Logic:
        - Long entry when RSI < entry_threshold AND not invested

        Exit Logic:
        1. Profit target: Exit when gain >= profit_target_pct
        2. Stop loss: Exit when loss <= -stop_loss_pct
        3. RSI overbought: Exit when RSI > exit_threshold
        """
        # CRITICAL: Check data availability first
        if not data.bars.contains_key(self.spy_symbol):
            return

        # CRITICAL: Check indicator readiness before using
        if not self.rsi_indicator.is_ready:
            return

        # Get current data
        current_price = data.bars[self.spy_symbol].close
        rsi_value = self.rsi_indicator.current.value

        # Check if we have an open position
        if self.portfolio[self.spy_symbol].invested:
            self._check_exit_conditions(current_price, rsi_value)
        else:
            self._check_entry_conditions(current_price, rsi_value)

    def _check_entry_conditions(self, current_price, rsi_value):
        """
        Check and execute entry logic.

        Entry Signal: RSI < entry_threshold (oversold condition)
        Position Sizing: Risk-based using stop loss percentage
        """
        if rsi_value < self.entry_threshold:
            # Calculate position size based on risk management
            shares = self._calculate_position_size(current_price)

            if shares > 0:
                # Execute market order
                self.market_order(self.spy_symbol, shares)

                # Track entry price for exit logic
                self.entry_price = current_price

                # Debug logging
                self.debug(f"ENTRY: {self.time} | Price: ${current_price:.2f} | RSI: {rsi_value:.2f} | Shares: {shares}")

    def _check_exit_conditions(self, current_price, rsi_value):
        """
        Check and execute exit logic.

        Exit Signals:
        1. Profit Target: Gain >= profit_target_pct
        2. Stop Loss: Loss <= -stop_loss_pct
        3. RSI Overbought: RSI > exit_threshold
        """
        if self.entry_price is None:
            # Safety check: if entry price not tracked, use current holdings value
            self.entry_price = self.portfolio[self.spy_symbol].average_price

        # Calculate current profit/loss percentage
        pnl_pct = (current_price - self.entry_price) / self.entry_price

        exit_reason = None

        # Check profit target
        if pnl_pct >= self.profit_target_pct:
            exit_reason = f"Profit Target ({pnl_pct * 100:.2f}% >= {self.profit_target_pct * 100:.2f}%)"

        # Check stop loss
        elif pnl_pct <= -self.stop_loss_pct:
            exit_reason = f"Stop Loss ({pnl_pct * 100:.2f}% <= {-self.stop_loss_pct * 100:.2f}%)"

        # Check RSI overbought
        elif rsi_value > self.exit_threshold:
            exit_reason = f"RSI Overbought ({rsi_value:.2f} > {self.exit_threshold})"

        # Execute exit if any condition met
        if exit_reason:
            self.liquidate(self.spy_symbol)

            # Debug logging
            self.debug(f"EXIT: {self.time} | Price: ${current_price:.2f} | RSI: {rsi_value:.2f} | P&L: {pnl_pct * 100:.2f}% | Reason: {exit_reason}")

            # Reset entry price
            self.entry_price = None

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
        if order_event.status == OrderStatus.Filled:
            order = self.transactions.get_order_by_id(order_event.order_id)
            self.debug(f"ORDER FILLED: {order.symbol} | Quantity: {order.quantity} | Fill Price: ${order_event.fill_price:.2f}")
