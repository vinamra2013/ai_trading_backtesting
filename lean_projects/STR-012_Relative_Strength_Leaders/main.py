"""
Relative_Strength_Leaders Strategy

Strategy Logic:
- Entry: Stock returns > SPY returns over lookback period (relative strength)
- Exit: After holding_period OR profit target OR stop loss
- Simplified Version: Tests QQQ relative strength vs SPY

Relative strength concept:
- Compare asset performance vs benchmark
- Buy assets outperforming benchmark
- Expect continued outperformance (momentum persistence)

Expected Performance:
- Trades: 40+ over 5 years
- Sharpe: 0.8+
- Win Rate: 50%+
- Max Drawdown: <15%

Author: QuantConnect LEAN
Category: MOMENTUM
"""

from AlgorithmImports import *


class RelativeStrengthLeaders(QCAlgorithm):
    """
    Relative strength momentum strategy.
    Buys QQQ when it outperforms SPY over lookback period.
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
        self.lookback_period = int(self.get_parameter("lookback_period", "30"))
        self.holding_period = int(self.get_parameter("holding_period", "5"))
        self.profit_target_pct = float(self.get_parameter("profit_target_pct", "0.03"))
        self.stop_loss_pct = float(self.get_parameter("stop_loss_pct", "0.02"))

        # Add both ETFs
        self.qqq = self.add_equity("QQQ", Resolution.DAILY).symbol
        self.spy = self.add_equity("SPY", Resolution.DAILY).symbol

        # We'll trade QQQ based on its relative strength vs SPY
        self.symbol = self.qqq

        # Create momentum indicators for both
        self.qqq_momentum = self.roc(
            self.qqq,
            self.lookback_period,
            Resolution.DAILY
        )
        self.spy_momentum = self.roc(
            self.spy,
            self.lookback_period,
            Resolution.DAILY
        )

        # Track entry details
        self.entry_price = None
        self.entry_date = None
        self.days_held = 0

        # Debug logging
        self.debug(f"Relative_Strength_Leaders initialized:")
        self.debug(f"  Asset: QQQ, Benchmark: SPY")
        self.debug(f"  Lookback Period: {self.lookback_period} days")
        self.debug(f"  Holding Period: {self.holding_period} days")
        self.debug(f"  Profit Target: {self.profit_target_pct * 100}%")
        self.debug(f"  Stop Loss: {self.stop_loss_pct * 100}%")

    def on_data(self, data):
        """Execute trading logic on each data point."""

        # Check data availability for both symbols
        if not data.bars.contains_key(self.qqq) or not data.bars.contains_key(self.spy):
            return

        # Wait for both momentum indicators to be ready
        if not self.qqq_momentum.is_ready or not self.spy_momentum.is_ready:
            return

        # Get current prices
        qqq_price = data.bars[self.qqq].close

        # Get momentum values (already in percentage)
        qqq_mom = self.qqq_momentum.current.value / 100.0  # Convert to decimal
        spy_mom = self.spy_momentum.current.value / 100.0

        # Calculate relative strength (QQQ momentum - SPY momentum)
        relative_strength = qqq_mom - spy_mom

        # Entry Logic: QQQ outperforming SPY
        if not self.portfolio.invested:
            # Enter when QQQ momentum > SPY momentum (outperformance)
            if relative_strength > 0:
                shares = self._calculate_position_size(qqq_price)

                if shares > 0:
                    self.market_order(self.qqq, shares)
                    self.entry_price = qqq_price
                    self.entry_date = self.time
                    self.days_held = 0

                    self.debug(f"ENTRY (Relative Strength): QQQ {qqq_price:.2f}")
                    self.debug(f"  QQQ Mom: {qqq_mom * 100:.2f}%, SPY Mom: {spy_mom * 100:.2f}%")
                    self.debug(f"  Relative Strength: {relative_strength * 100:.2f}%")
                    self.debug(f"  Shares: {shares}")

        # Exit Logic: Time-based, profit target, or stop loss
        elif self.portfolio.invested and self.entry_price is not None:
            self.days_held += 1
            current_return = (qqq_price - self.entry_price) / self.entry_price

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

            # Exit 4: Relative strength turned negative (underperformance)
            elif relative_strength < 0:
                exit_reason = f"Underperformance (RS: {relative_strength * 100:.2f}%)"

            # Execute exit
            if exit_reason:
                self.liquidate(self.qqq)
                self.debug(f"EXIT: {exit_reason}, Return: {current_return * 100:.2f}%, Days: {self.days_held}")
                self.entry_price = None
                self.entry_date = None
                self.days_held = 0

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
