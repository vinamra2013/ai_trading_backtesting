"""
ATR_Breakout_ETF Strategy

Strategy Logic:
- Entry: Price moves > breakout_multiplier × ATR upward (volatility expansion)
- Exit: After holding_period days OR profit target OR stop loss
- Risk Management: 1% max portfolio risk per trade
- Position Sizing: Based on ATR for volatility-adjusted sizing

ATR (Average True Range) measures volatility:
- High ATR = high volatility
- Breakouts during high volatility often indicate strong moves
- This strategy capitalizes on volatility expansion

Expected Performance:
- Trades: 30+ over 5 years
- Sharpe: 0.8+
- Max Drawdown: <20%

Author: QuantConnect LEAN
Category: VOLATILITY
"""

from AlgorithmImports import *


class ATRBreakoutETF(QCAlgorithm):
    """
    ATR-based breakout strategy trading volatility expansion.
    Uses ATR to identify breakout opportunities and size positions.
    """

    def initialize(self):
        """Initialize strategy with optimizable parameters."""

        # Backtest period
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(1000)

        # Set Interactive Brokers brokerage model
        self.set_brokerage_model(BrokerageName.INTERACTIVE_BROKERS_BROKERAGE)

        # Get optimizable parameters
        self.atr_period = int(self.get_parameter("atr_period", "14"))
        self.breakout_multiplier = float(self.get_parameter("breakout_multiplier", "2.5"))
        self.holding_period = int(self.get_parameter("holding_period", "5"))
        self.profit_target_pct = float(self.get_parameter("profit_target_pct", "0.03"))
        self.stop_loss_pct = float(self.get_parameter("stop_loss_pct", "0.02"))

        # Add SPY with daily resolution
        self.symbol = self.add_equity("SPY", Resolution.DAILY).symbol

        # Create ATR indicator
        self.atr_indicator = self.atr(
            self.symbol,
            self.atr_period,
            MovingAverageType.SIMPLE,
            Resolution.DAILY
        )

        # Track previous close for breakout detection
        self.previous_close = None

        # Track entry details
        self.entry_price = None
        self.entry_date = None
        self.days_held = 0

        # Debug logging
        self.debug(f"ATR_Breakout_ETF initialized:")
        self.debug(f"  ATR Period: {self.atr_period}")
        self.debug(f"  Breakout Multiplier: {self.breakout_multiplier}x ATR")
        self.debug(f"  Holding Period: {self.holding_period} days")
        self.debug(f"  Profit Target: {self.profit_target_pct * 100}%")
        self.debug(f"  Stop Loss: {self.stop_loss_pct * 100}%")

    def on_data(self, data):
        """Execute trading logic on each data point."""

        # Check data availability
        if not data.bars.contains_key(self.symbol):
            return

        # Wait for ATR to be ready
        if not self.atr_indicator.is_ready:
            return

        # Get current price and ATR
        price = data.bars[self.symbol].close
        atr_value = self.atr_indicator.current.value

        # Store previous close for next iteration
        if self.previous_close is None:
            self.previous_close = price
            return

        # Entry Logic: Breakout detection
        if not self.portfolio.invested:
            # Calculate breakout threshold
            breakout_threshold = self.breakout_multiplier * atr_value

            # Check if price moved up by more than threshold
            price_change = price - self.previous_close

            if price_change > breakout_threshold:
                shares = self._calculate_position_size(price, atr_value)

                if shares > 0:
                    self.market_order(self.symbol, shares)
                    self.entry_price = price
                    self.entry_date = self.time
                    self.days_held = 0

                    self.debug(f"ENTRY (Breakout): Price {price:.2f}")
                    self.debug(f"  Price Change: ${price_change:.2f} > Threshold: ${breakout_threshold:.2f}")
                    self.debug(f"  ATR: ${atr_value:.2f}")
                    self.debug(f"  Shares: {shares}")

        # Exit Logic: Time-based, profit target, or stop loss
        elif self.portfolio.invested and self.entry_price is not None:
            self.days_held += 1
            current_return = (price - self.entry_price) / self.entry_price

            exit_reason = None

            # Exit 1: Holding period reached
            if self.days_held >= self.holding_period:
                exit_reason = f"Holding Period ({self.days_held} days)"

            # Exit 2: Profit target
            elif current_return >= self.profit_target_pct:
                exit_reason = f"Profit Target ({current_return * 100:.2f}%)"

            # Exit 3: Stop loss
            elif current_return <= -self.stop_loss_pct:
                exit_reason = f"Stop Loss ({current_return * 100:.2f}%)"

            # Execute exit
            if exit_reason:
                self.liquidate(self.symbol)
                self.debug(f"EXIT: {exit_reason}, Return: {current_return * 100:.2f}%, Days: {self.days_held}")
                self.entry_price = None
                self.entry_date = None
                self.days_held = 0

        # Update previous close for next iteration
        self.previous_close = price

    def _calculate_position_size(self, entry_price, atr_value):
        """
        Calculate position size based on ATR (volatility-adjusted).

        Risk Management:
        - Max 1% portfolio risk per trade
        - Use ATR as risk measure (instead of fixed stop loss)
        - Position size inversely proportional to volatility

        Returns:
            int: Number of shares to purchase
        """
        portfolio_value = self.portfolio.total_portfolio_value
        cash = self.portfolio.cash

        # Max risk: 1% of portfolio
        max_risk_dollars = portfolio_value * 0.01

        # Use ATR as risk measure (volatility-based risk)
        # Risk per share = ATR (represents typical price movement)
        risk_per_share = atr_value * self.breakout_multiplier

        # Shares based on risk
        shares_by_risk = int(max_risk_dollars / risk_per_share)

        # Shares based on available cash (95% max)
        max_shares_by_cash = int((cash * 0.95) / entry_price)

        # Take minimum
        final_shares = min(shares_by_risk, max_shares_by_cash)

        return final_shares
