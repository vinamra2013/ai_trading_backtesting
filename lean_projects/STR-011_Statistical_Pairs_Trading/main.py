"""
Statistical_Pairs_Trading Strategy

Strategy Logic:
- Entry: When spread between QQQ and SPY diverges > threshold std deviations
- Exit: When spread normalizes OR profit target OR stop loss
- Simplified Version: Trades QQQ vs SPY ratio divergence

Pairs trading concept:
- Trade two correlated assets
- When their ratio diverges from mean (statistical anomaly)
- Expect mean reversion (ratio returns to normal)

Expected Performance:
- Trades: 40+ over 5 years
- Sharpe: 0.9+
- Win Rate: 50%+
- Max Drawdown: <15%

Author: QuantConnect LEAN
Category: MEAN REVERSION (Statistical Arbitrage)
"""

from AlgorithmImports import *


class StatisticalPairsTrading(QCAlgorithm):
    """
    Simplified pairs trading strategy using QQQ vs SPY spread divergence.
    Trades mean reversion of price ratio between two correlated ETFs.
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
        self.sma_period = int(self.get_parameter("sma_period", "50"))
        self.std_dev_threshold = float(self.get_parameter("std_dev_threshold", "2.0"))
        self.profit_target_pct = float(self.get_parameter("profit_target_pct", "0.02"))
        self.stop_loss_pct = float(self.get_parameter("stop_loss_pct", "0.015"))

        # Add both ETFs
        self.qqq = self.add_equity("QQQ", Resolution.DAILY).symbol
        self.spy = self.add_equity("SPY", Resolution.DAILY).symbol

        # We'll trade QQQ (tech-heavy) vs SPY (broad market)
        self.symbol = self.qqq

        # Rolling window to track spread history
        self.spread_window = RollingWindow[float](self.sma_period)

        # Track entry details
        self.entry_price = None
        self.entry_spread = None

        # Debug logging
        self.debug(f"Statistical_Pairs_Trading initialized:")
        self.debug(f"  Pair: QQQ vs SPY")
        self.debug(f"  SMA Period: {self.sma_period}")
        self.debug(f"  Std Dev Threshold: {self.std_dev_threshold}")
        self.debug(f"  Profit Target: {self.profit_target_pct * 100}%")
        self.debug(f"  Stop Loss: {self.stop_loss_pct * 100}%")

    def on_data(self, data):
        """Execute trading logic on each data point."""

        # Check data availability for both symbols
        if not data.bars.contains_key(self.qqq) or not data.bars.contains_key(self.spy):
            return

        # Get current prices
        qqq_price = data.bars[self.qqq].close
        spy_price = data.bars[self.spy].close

        # Calculate spread (QQQ/SPY ratio)
        spread = qqq_price / spy_price

        # Add to rolling window
        self.spread_window.add(spread)

        # Wait for window to be ready
        if not self.spread_window.is_ready:
            return

        # Calculate spread statistics
        spread_values = list(self.spread_window)
        spread_mean = sum(spread_values) / len(spread_values)
        spread_variance = sum((x - spread_mean) ** 2 for x in spread_values) / len(spread_values)
        spread_std = spread_variance ** 0.5

        # Calculate z-score (how many std devs from mean)
        z_score = (spread - spread_mean) / spread_std if spread_std > 0 else 0

        # Entry Logic: Spread divergence
        if not self.portfolio.invested:
            # Enter when spread is significantly below mean (QQQ undervalued vs SPY)
            if z_score < -self.std_dev_threshold:
                shares = self._calculate_position_size(qqq_price)

                if shares > 0:
                    self.market_order(self.qqq, shares)
                    self.entry_price = qqq_price
                    self.entry_spread = spread

                    self.debug(f"ENTRY (Spread Divergence): QQQ {qqq_price:.2f}")
                    self.debug(f"  Spread: {spread:.4f}, Mean: {spread_mean:.4f}, Z-Score: {z_score:.2f}")
                    self.debug(f"  Shares: {shares}")

        # Exit Logic: Spread normalization, profit target, or stop loss
        elif self.portfolio.invested and self.entry_price is not None:
            current_return = (qqq_price - self.entry_price) / self.entry_price

            exit_reason = None

            # Exit 1: Spread normalized (z-score back to near zero)
            if abs(z_score) < 0.5:
                exit_reason = f"Spread Normalized (Z: {z_score:.2f})"

            # Exit 2: Profit target
            elif current_return >= self.profit_target_pct:
                exit_reason = f"Profit Target ({current_return * 100:.2f}%)"

            # Exit 3: Stop loss
            elif current_return <= -self.stop_loss_pct:
                exit_reason = f"Stop Loss ({current_return * 100:.2f}%)"

            # Execute exit
            if exit_reason:
                self.liquidate(self.qqq)
                self.debug(f"EXIT: {exit_reason}, Return: {current_return * 100:.2f}%")
                self.debug(f"  Exit Spread: {spread:.4f} (Entry: {self.entry_spread:.4f})")
                self.entry_price = None
                self.entry_spread = None

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
