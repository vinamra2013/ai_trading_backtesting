"""
Donchian_Breakout_ETF Strategy

Strategy Logic:
- Entry: Price breaks above N-day high (Donchian channel upper band)
- Exit: Price breaks below N-day low (Donchian channel lower band)
- Turtle Trading style momentum breakout strategy

Donchian Channel concept:
- Upper band = highest high over N periods
- Lower band = lowest low over N periods
- Breakout above upper = strong bullish momentum
- Breakout below lower = exit signal

Expected Performance:
- Trades: 40+ over 5 years
- Sharpe: 0.8+
- Win Rate: 50%+
- Max Drawdown: <15%

Author: QuantConnect LEAN
Category: MOMENTUM (Trend Following)
"""

from AlgorithmImports import *


class DonchianBreakoutETF(QCAlgorithm):
    """
    Donchian Breakout strategy (Turtle Trading style).
    Enters on breakout above N-day high, exits on breakdown below N-day low.
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
        self.donchian_period = int(self.get_parameter("donchian_period", "30"))
        self.breakout_threshold = float(self.get_parameter("breakout_threshold", "1.00"))
        self.profit_target_pct = float(self.get_parameter("profit_target_pct", "0.05"))
        self.stop_loss_pct = float(self.get_parameter("stop_loss_pct", "0.02"))

        # Add SPY with daily resolution
        self.symbol = self.add_equity("SPY", Resolution.DAILY).symbol

        # Create Donchian Channel using MAX/MIN indicators
        self.donchian_upper = self.max(
            self.symbol,
            self.donchian_period,
            Resolution.DAILY
        )
        self.donchian_lower = self.min(
            self.symbol,
            self.donchian_period,
            Resolution.DAILY
        )

        # Track entry details
        self.entry_price = None

        # Debug logging
        self.debug(f"Donchian_Breakout_ETF initialized:")
        self.debug(f"  Donchian Period: {self.donchian_period} days")
        self.debug(f"  Breakout Threshold: {self.breakout_threshold}")
        self.debug(f"  Profit Target: {self.profit_target_pct * 100}%")
        self.debug(f"  Stop Loss: {self.stop_loss_pct * 100}%")

    def on_data(self, data):
        """Execute trading logic on each data point."""

        # Check data availability
        if not data.bars.contains_key(self.symbol):
            return

        # Wait for Donchian indicators to be ready
        if not self.donchian_upper.is_ready or not self.donchian_lower.is_ready:
            return

        # Get current price and Donchian bands
        price = data.bars[self.symbol].close
        upper_band = self.donchian_upper.current.value
        lower_band = self.donchian_lower.current.value

        # Calculate breakout levels (allows slight threshold adjustment)
        breakout_level = upper_band * self.breakout_threshold

        # Entry Logic: Breakout above Donchian upper band
        if not self.portfolio.invested:
            # Enter when price breaks above upper band
            if price >= breakout_level:
                shares = self._calculate_position_size(price)

                if shares > 0:
                    self.market_order(self.symbol, shares)
                    self.entry_price = price

                    self.debug(f"ENTRY (Donchian Breakout): Price {price:.2f}")
                    self.debug(f"  Upper Band: {upper_band:.2f}, Lower Band: {lower_band:.2f}")
                    self.debug(f"  Breakout Level: {breakout_level:.2f}")
                    self.debug(f"  Shares: {shares}")

        # Exit Logic: Breakdown below lower band, profit target, or stop loss
        elif self.portfolio.invested and self.entry_price is not None:
            current_return = (price - self.entry_price) / self.entry_price

            exit_reason = None

            # Exit 1: Breakdown below Donchian lower band (trend reversal)
            if price <= lower_band:
                exit_reason = f"Donchian Breakdown (Price {price:.2f} <= Lower {lower_band:.2f})"

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
