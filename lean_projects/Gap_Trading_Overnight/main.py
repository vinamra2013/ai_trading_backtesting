"""
Gap_Trading_Overnight Strategy

Strategy Logic:
- Entry: Detect overnight gap > threshold% between previous close and current open
- Exit: During same day OR profit target OR stop loss
- Uses DAILY bars: gap = (open - prev_close) / prev_close

Gap trading concept:
- Overnight gaps indicate news/events
- Trade gap continuation or reversal
- Intraday exit captures immediate reaction

Expected Performance:
- Trades: 50+ over 5 years
- Sharpe: 0.8+
- Win Rate: 50%+
- Max Drawdown: <15%

Author: QuantConnect LEAN
Category: VOLATILITY (Event-Driven)
"""

from AlgorithmImports import *


class GapTradingOvernight(QCAlgorithm):
    """
    Gap trading strategy detecting overnight price gaps.
    Enters on gap and exits same day or via profit/stop targets.
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
        self.gap_threshold = float(self.get_parameter("gap_threshold", "0.015"))
        self.gap_direction = str(self.get_parameter("gap_direction", "up"))
        self.profit_target_pct = float(self.get_parameter("profit_target_pct", "0.02"))
        self.stop_loss_pct = float(self.get_parameter("stop_loss_pct", "0.015"))

        # Add SPY with daily resolution
        self.symbol = self.add_equity("SPY", Resolution.DAILY).symbol

        # Track previous close for gap detection
        self.previous_close = None

        # Track entry details
        self.entry_price = None
        self.entry_date = None

        # Debug logging
        self.debug(f"Gap_Trading_Overnight initialized:")
        self.debug(f"  Gap Threshold: {self.gap_threshold * 100}%")
        self.debug(f"  Gap Direction: {self.gap_direction}")
        self.debug(f"  Profit Target: {self.profit_target_pct * 100}%")
        self.debug(f"  Stop Loss: {self.stop_loss_pct * 100}%")

    def on_data(self, data):
        """Execute trading logic on each data point."""

        # Check data availability
        if not data.bars.contains_key(self.symbol):
            return

        # Get current bar
        bar = data.bars[self.symbol]
        current_open = bar.open
        current_close = bar.close

        # Store previous close for next iteration
        if self.previous_close is None:
            self.previous_close = current_close
            return

        # Calculate overnight gap
        gap = (current_open - self.previous_close) / self.previous_close

        # Entry Logic: Gap detection
        if not self.portfolio.invested:
            gap_up = gap > self.gap_threshold
            gap_down = gap < -self.gap_threshold

            # Check if gap meets direction criteria
            should_enter = False
            if self.gap_direction == "up" and gap_up:
                should_enter = True
            elif self.gap_direction == "down" and gap_down:
                should_enter = True
            elif self.gap_direction == "both" and (gap_up or gap_down):
                should_enter = True

            if should_enter:
                shares = self._calculate_position_size(current_open)

                if shares > 0:
                    # Enter at open (gap detected)
                    self.market_order(self.symbol, shares)
                    self.entry_price = current_open
                    self.entry_date = self.time

                    self.debug(f"ENTRY (Gap {self.gap_direction}): Open {current_open:.2f}")
                    self.debug(f"  Gap: {gap * 100:.2f}% (Prev Close: {self.previous_close:.2f})")
                    self.debug(f"  Shares: {shares}")

        # Exit Logic: Same-day exit, profit target, or stop loss
        elif self.portfolio.invested and self.entry_price is not None:
            # Use current close for exit calculation (intraday movement)
            current_return = (current_close - self.entry_price) / self.entry_price

            exit_reason = None

            # Exit 1: End of day (close position before market close)
            # Note: With daily bars, we exit at close of entry day
            if self.time.date() == self.entry_date.date():
                exit_reason = f"End of Day"

            # Exit 2: Profit target
            elif current_return >= self.profit_target_pct:
                exit_reason = f"Profit Target ({current_return * 100:.2f}%)"

            # Exit 3: Stop loss
            elif current_return <= -self.stop_loss_pct:
                exit_reason = f"Stop Loss ({current_return * 100:.2f}%)"

            # Execute exit
            if exit_reason:
                self.liquidate(self.symbol)
                self.debug(f"EXIT: {exit_reason}, Return: {current_return * 100:.2f}%")
                self.entry_price = None
                self.entry_date = None

        # Update previous close for next iteration
        self.previous_close = current_close

    def _calculate_position_size(self, entry_price):
        """
        Calculate position size based on risk management.

        Risk Management:
        - Max 1% portfolio risk per trade
        - Fixed stop loss for risk calculation
        - 95% max cash usage

        Returns:
            int: Number of shares to purchase
        """
        portfolio_value = self.portfolio.total_portfolio_value
        cash = self.portfolio.cash

        # Max risk: 1% of portfolio
        max_risk_dollars = portfolio_value * 0.01

        # Risk per share based on stop loss
        risk_per_share = entry_price * self.stop_loss_pct

        # Shares based on risk
        shares_by_risk = int(max_risk_dollars / risk_per_share)

        # Shares based on available cash (95% max)
        max_shares_by_cash = int((cash * 0.95) / entry_price)

        # Take minimum
        final_shares = min(shares_by_risk, max_shares_by_cash)

        return final_shares
