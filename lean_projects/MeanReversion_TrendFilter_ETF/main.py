"""
MeanReversion_TrendFilter_ETF - HYBRID Strategy

Strategy Logic:
- Entry: Buy SPY when RSI < entry_threshold AND price > trend_sma (with-trend mean reversion)
- Exit: Sell when profit target, stop loss, or RSI exit threshold hit
- Risk Management: Maximum 1% portfolio risk per trade
- Position Sizing: Based on stop loss percentage and available capital

KEY HYPOTHESIS TEST:
This strategy tests the hypothesis that "mean reversion works better WITH-TREND than counter-trend"
The require_trend parameter enables A/B testing:
- require_trend=true: Only enter RSI oversold signals when price is above trend SMA
- require_trend=false: Enter all RSI oversold signals (baseline RSI-only strategy)

Expected Results:
- With-trend filtering should improve win rate by avoiding whipsaw trades
- Lower drawdown due to trend context
- Higher Sharpe ratio from improved signal quality
- Fewer total trades (more selective) but better quality

Author: QuantConnect LEAN
Version: 1.0 (Hybrid Mean Reversion + Trend)
"""

from AlgorithmImports import *


class MeanReversionTrendFilterETF(QCAlgorithm):
    """
    Hybrid RSI mean reversion strategy with trend filter.
    Tests hypothesis: mean reversion works better when aligned with longer-term trend.
    """

    def initialize(self):
        """
        Initialize the algorithm with parameters, data, and dual indicators.
        """
        # Backtest period: 5 years for statistical significance
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(1000)

        # Set brokerage model to Interactive Brokers for accurate fee simulation
        self.set_brokerage_model(BrokerageName.INTERACTIVE_BROKERS_BROKERAGE)

        # CRITICAL: Use get_parameter() for ALL optimizable values
        # RSI parameters for mean reversion signals
        self.rsi_period = int(self.get_parameter("rsi_period", "14"))
        self.rsi_entry = int(self.get_parameter("rsi_entry", "30"))

        # Trend filter parameters
        self.trend_sma = int(self.get_parameter("trend_sma", "200"))

        # A/B testing parameter: enable/disable trend filter
        require_trend_str = self.get_parameter("require_trend", "true")
        self.require_trend = require_trend_str.lower() == "true"

        # Exit parameters
        self.profit_target_pct = float(self.get_parameter("profit_target_pct", "0.02"))
        self.stop_loss_pct = float(self.get_parameter("stop_loss_pct", "0.015"))

        # Add SPY with daily resolution for fee control
        self.spy_symbol = self.add_equity("SPY", Resolution.DAILY).symbol

        # DUAL INDICATOR PATTERN
        # Indicator 1: RSI for oversold mean reversion signals
        self.rsi_indicator = self.rsi(
            self.spy_symbol,
            self.rsi_period,
            MovingAverageType.WILDERS,
            Resolution.DAILY
        )

        # Indicator 2: SMA for trend confirmation
        self.trend_sma_indicator = self.sma(
            self.spy_symbol,
            self.trend_sma,
            Resolution.DAILY
        )

        # Track entry price for profit target and stop loss calculations
        self.entry_price = None

        # Debug logging
        self.debug(f"Strategy initialized with parameters:")
        self.debug(f"  RSI Period: {self.rsi_period}")
        self.debug(f"  RSI Entry Threshold: {self.rsi_entry}")
        self.debug(f"  Trend SMA: {self.trend_sma}")
        self.debug(f"  Require Trend Filter: {self.require_trend}")
        self.debug(f"  Stop Loss: {self.stop_loss_pct * 100}%")
        self.debug(f"  Profit Target: {self.profit_target_pct * 100}%")

    def on_data(self, data):
        """
        Called on each data point (daily bar).

        Entry Logic:
        - RSI oversold: RSI < rsi_entry
        - Trend confirmation (if require_trend=true): price > trend_sma
        - Both conditions must pass when trend filter is enabled

        Exit Logic:
        1. Profit target: Exit when gain >= profit_target_pct
        2. Stop loss: Exit when loss <= -stop_loss_pct
        """
        # CRITICAL: Check data availability first
        if not data.bars.contains_key(self.spy_symbol):
            return

        # CRITICAL: Check BOTH indicators for readiness
        if not self.rsi_indicator.is_ready:
            return

        if not self.trend_sma_indicator.is_ready:
            return

        # Get current data
        current_price = data.bars[self.spy_symbol].close
        rsi_value = self.rsi_indicator.current.value
        trend_sma_value = self.trend_sma_indicator.current.value

        # Check if we have an open position
        if self.portfolio[self.spy_symbol].invested:
            self._check_exit_conditions(current_price, rsi_value, trend_sma_value)
        else:
            self._check_entry_conditions(current_price, rsi_value, trend_sma_value)

    def _check_entry_conditions(self, current_price, rsi_value, trend_sma_value):
        """
        Check and execute entry logic with dual indicator approach.

        Entry Signal:
        1. RSI < rsi_entry (oversold mean reversion signal)
        2. Price > trend_sma (with-trend confirmation) - ONLY if require_trend=true

        Position Sizing: Risk-based using stop loss percentage
        """
        # Check RSI oversold condition
        rsi_oversold = rsi_value < self.rsi_entry

        # Check trend condition (if enabled)
        if self.require_trend:
            # With-trend logic: price must be above trend SMA
            # Hypothesis: mean reversion UP works better when longer-term trend is UP
            trend_bullish = current_price > trend_sma_value
            entry_signal = rsi_oversold and trend_bullish
            signal_type = "WITH-TREND" if trend_bullish else "FILTERED-OUT"
        else:
            # Baseline: ignore trend, use RSI only
            entry_signal = rsi_oversold
            signal_type = "RSI-ONLY"

        if entry_signal:
            # Calculate position size based on risk management
            shares = self._calculate_position_size(current_price)

            if shares > 0:
                # Execute market order
                self.market_order(self.spy_symbol, shares)

                # Track entry price for exit logic
                self.entry_price = current_price

                # Debug logging
                trend_context = f"Price: ${current_price:.2f} vs SMA: ${trend_sma_value:.2f}"
                self.debug(f"ENTRY ({signal_type}): {self.time} | {trend_context} | RSI: {rsi_value:.2f} | Shares: {shares}")

    def _check_exit_conditions(self, current_price, rsi_value, trend_sma_value):
        """
        Check and execute exit logic.

        Exit Signals:
        1. Profit Target: Gain >= profit_target_pct
        2. Stop Loss: Loss <= -stop_loss_pct
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

        # Execute exit if any condition met
        if exit_reason:
            self.liquidate(self.spy_symbol)

            # Debug logging
            trend_context = f"Price: ${current_price:.2f} vs SMA: ${trend_sma_value:.2f}"
            self.debug(f"EXIT: {self.time} | {trend_context} | RSI: {rsi_value:.2f} | P&L: {pnl_pct * 100:.2f}% | Reason: {exit_reason}")

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
        if order_event.status == OrderStatus.FILLED:
            order = self.transactions.get_order_by_id(order_event.order_id)
            self.debug(f"ORDER FILLED: {order.symbol} | Quantity: {order.quantity} | Fill Price: ${order_event.fill_price:.2f}")
