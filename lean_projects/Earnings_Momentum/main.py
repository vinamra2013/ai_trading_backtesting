"""
Earnings_Momentum Strategy

Strategy Logic:
- Entry: Price momentum after earnings dates (proxy for earnings surprise)
- Exit: After holding_period days OR profit target OR stop loss
- Simplified Version: Uses price momentum as proxy (no earnings API required)

Note: This is a simplified implementation that trades on momentum
spikes as a proxy for earnings surprises. A full implementation would
use earnings data APIs to detect actual earnings beats.

Expected Performance:
- Trades: 30+ over 5 years
- Sharpe: 1.0+
- Win Rate: 50%+
- Max Drawdown: <15%

Author: QuantConnect LEAN
Category: EVENT-BASED (Simplified)
"""

from AlgorithmImports import *


class EarningsMomentum(QCAlgorithm):
    """
    Simplified earnings momentum strategy using price momentum as proxy.
    Trades strong upward price movements that may indicate earnings surprises.
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
        self.lookback_period = int(self.get_parameter("lookback_period", "5"))
        self.momentum_threshold = float(self.get_parameter("momentum_threshold", "0.03"))
        self.holding_period = int(self.get_parameter("holding_period", "3"))
        self.profit_target_pct = float(self.get_parameter("profit_target_pct", "0.05"))
        self.stop_loss_pct = float(self.get_parameter("stop_loss_pct", "0.02"))

        # Add QQQ (tech-heavy ETF where earnings surprises are more common)
        self.symbol = self.add_equity("QQQ", Resolution.DAILY).symbol

        # Create momentum indicator (ROC - Rate of Change)
        self.momentum_indicator = self.roc(
            self.symbol,
            self.lookback_period,
            Resolution.DAILY
        )

        # Track entry details
        self.entry_price = None
        self.entry_date = None
        self.days_held = 0

        # Debug logging
        self.debug(f"Earnings_Momentum initialized:")
        self.debug(f"  Lookback Period: {self.lookback_period} days")
        self.debug(f"  Momentum Threshold: {self.momentum_threshold * 100}% (proxy for earnings surprise)")
        self.debug(f"  Holding Period: {self.holding_period} days")
        self.debug(f"  Profit Target: {self.profit_target_pct * 100}%")
        self.debug(f"  Stop Loss: {self.stop_loss_pct * 100}%")

    def on_data(self, data):
        """Execute trading logic on each data point."""

        # Check data availability
        if not data.bars.contains_key(self.symbol):
            return

        # Wait for momentum indicator to be ready
        if not self.momentum_indicator.is_ready:
            return

        # Get current price and momentum
        price = data.bars[self.symbol].close
        momentum = self.momentum_indicator.current.value / 100.0  # Convert to decimal

        # Entry Logic: Strong momentum spike (proxy for earnings surprise)
        if not self.portfolio.invested:
            # Check if momentum exceeds threshold
            if momentum > self.momentum_threshold:
                shares = self._calculate_position_size(price)

                if shares > 0:
                    self.market_order(self.symbol, shares)
                    self.entry_price = price
                    self.entry_date = self.time
                    self.days_held = 0

                    self.debug(f"ENTRY (Momentum Spike): Price {price:.2f}")
                    self.debug(f"  Momentum: {momentum * 100:.2f}% > Threshold: {self.momentum_threshold * 100:.2f}%")
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
