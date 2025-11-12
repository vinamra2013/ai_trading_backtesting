"""
RSI_MACD_Combo_ETF Strategy

Strategy Logic:
- Entry: RSI < threshold (oversold) AND MACD > signal line (bullish momentum)
- Exit: RSI > exit_threshold OR MACD < signal line (momentum reversal)
- Risk Management: 1% max portfolio risk per trade
- Position Sizing: Based on stop loss percentage

This hybrid strategy combines:
1. RSI for oversold/overbought conditions (mean reversion signal)
2. MACD for momentum confirmation (trend following signal)
3. Both must align for entry (reduces false signals)

Expected Performance:
- Trades: 50+ over 5 years
- Sharpe: 1.2+
- Win Rate: 50%+
- Max Drawdown: <15%

Author: QuantConnect LEAN
Category: HYBRID (Mean Reversion + Momentum)
"""

from AlgorithmImports import *


class RSIMACDComboETF(QCAlgorithm):
    """
    Hybrid RSI + MACD strategy combining mean reversion and momentum signals.
    Uses RSI for entry timing and MACD for momentum confirmation.
    """

    def initialize(self):
        """Initialize strategy with optimizable parameters."""

        # Backtest period
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(1000)

        # Set Interactive Brokers brokerage model
        self.set_brokerage_model(BrokerageName.INTERACTIVE_BROKERS_BROKERAGE)

        # Get optimizable parameters - RSI
        self.rsi_period = int(self.get_parameter("rsi_period", "14"))
        self.rsi_threshold = int(self.get_parameter("rsi_threshold", "30"))
        self.rsi_exit_threshold = int(self.get_parameter("rsi_exit_threshold", "60"))

        # Get optimizable parameters - MACD
        self.macd_fast = int(self.get_parameter("macd_fast", "12"))
        self.macd_slow = int(self.get_parameter("macd_slow", "26"))
        self.macd_signal = int(self.get_parameter("macd_signal", "9"))

        # Risk management parameters
        self.stop_loss_pct = float(self.get_parameter("stop_loss_pct", "0.015"))
        self.profit_target_pct = float(self.get_parameter("profit_target_pct", "0.025"))

        # Add SPY with daily resolution
        self.symbol = self.add_equity("SPY", Resolution.DAILY).symbol

        # Create RSI indicator (use WILDERS for standard RSI)
        self.rsi_indicator = self.rsi(
            self.symbol,
            self.rsi_period,
            MovingAverageType.WILDERS,
            Resolution.DAILY
        )

        # Create MACD indicator
        self.macd_indicator = self.macd(
            self.symbol,
            self.macd_fast,
            self.macd_slow,
            self.macd_signal,
            MovingAverageType.EXPONENTIAL,
            Resolution.DAILY
        )

        # Track entry price for exit logic
        self.entry_price = None

        # Debug logging
        self.debug(f"RSI_MACD_Combo_ETF initialized:")
        self.debug(f"  RSI Period: {self.rsi_period}, Entry: {self.rsi_threshold}, Exit: {self.rsi_exit_threshold}")
        self.debug(f"  MACD: {self.macd_fast}/{self.macd_slow}/{self.macd_signal}")
        self.debug(f"  Stop Loss: {self.stop_loss_pct * 100}%, Profit Target: {self.profit_target_pct * 100}%")

    def on_data(self, data):
        """Execute trading logic on each data point."""

        # Check data availability
        if not data.bars.contains_key(self.symbol):
            return

        # Wait for indicators to be ready
        if not self.rsi_indicator.is_ready or not self.macd_indicator.is_ready:
            return

        # Get current price and indicator values
        price = data.bars[self.symbol].close
        rsi_value = self.rsi_indicator.current.value
        macd_value = self.macd_indicator.current.value
        macd_signal_value = self.macd_indicator.signal.current.value

        # Entry Logic: RSI oversold AND MACD bullish
        if not self.portfolio.invested:
            # Both conditions must be true for entry
            rsi_oversold = rsi_value < self.rsi_threshold
            macd_bullish = macd_value > macd_signal_value

            if rsi_oversold and macd_bullish:
                shares = self._calculate_position_size(price)

                if shares > 0:
                    self.market_order(self.symbol, shares)
                    self.entry_price = price

                    self.debug(f"ENTRY: Price {price:.2f}")
                    self.debug(f"  RSI: {rsi_value:.2f} < {self.rsi_threshold} (oversold)")
                    self.debug(f"  MACD: {macd_value:.4f} > Signal {macd_signal_value:.4f} (bullish)")
                    self.debug(f"  Shares: {shares}")

        # Exit Logic: Multiple conditions
        elif self.portfolio.invested and self.entry_price is not None:
            current_return = (price - self.entry_price) / self.entry_price

            exit_reason = None

            # Exit 1: Profit target
            if current_return >= self.profit_target_pct:
                exit_reason = f"Profit Target ({current_return * 100:.2f}%)"

            # Exit 2: Stop loss
            elif current_return <= -self.stop_loss_pct:
                exit_reason = f"Stop Loss ({current_return * 100:.2f}%)"

            # Exit 3: RSI overbought
            elif rsi_value > self.rsi_exit_threshold:
                exit_reason = f"RSI Overbought ({rsi_value:.2f} > {self.rsi_exit_threshold})"

            # Exit 4: MACD bearish crossover
            elif macd_value < macd_signal_value:
                exit_reason = f"MACD Bearish (MACD {macd_value:.4f} < Signal {macd_signal_value:.4f})"

            # Execute exit if any condition met
            if exit_reason:
                self.liquidate(self.symbol)
                self.debug(f"EXIT: {exit_reason}, Return: {current_return * 100:.2f}%")
                self.entry_price = None

    def _calculate_position_size(self, entry_price):
        """
        Calculate position size based on risk management.

        Risk Management:
        - Max 1% portfolio risk per trade
        - Position sized based on stop loss
        - 95% max cash usage (5% buffer)

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
