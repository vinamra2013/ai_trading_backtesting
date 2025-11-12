"""
BollingerBand_ETF_LowFreq Strategy

REVISION of original Bollinger Band strategy to fix critical fee problems.

Original Strategy #2 FAILED:
- 822 trades in 5 years
- $674 in fees on $1K capital (67% of capital destroyed!)
- Win rate: Only 43%

This revision focuses on:
- WIDER Bollinger Bands (2-3 std dev) to filter false signals
- Lower frequency trading (target 50-150 trades/year, NOT 800+)
- Daily resolution only
- Better entry quality with entry_distance_pct parameter
- Strict fee control: <25% of capital
- Risk management: max 1% risk per trade

Strategy Logic:
- Entry: Price touches lower band + entry_distance_pct offset
- Exit 1: Profit target (1.5%-3%)
- Exit 2: Stop loss (1%-2%)
- Exit 3: Mean reversion complete (price > middle band)

Asset Class: ETF (SPY)
Category: Mean Reversion
Expected Trades: 50-150 per year
Expected Sharpe: 0.8+
Max Fee Percentage: <25% of capital
"""

from AlgorithmImports import *


class BollingerBandETFLowFreq(QCAlgorithm):
    """
    Bollinger Band mean reversion strategy with WIDER bands for low-frequency trading.

    This is a fee-conscious revision designed for small accounts ($1K).
    """

    def initialize(self):
        """Initialize strategy with optimizable parameters."""

        # Backtest period
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(1000)

        # Set Interactive Brokers brokerage model for realistic fees
        self.set_brokerage_model(BrokerageName.INTERACTIVE_BROKERS_BROKERAGE)

        # Get optimizable parameters with sensible defaults
        bb_period = int(self.get_parameter("bb_period", "20"))
        bb_std_dev = float(self.get_parameter("bb_std_dev", "2.5"))
        self.entry_distance_pct = float(self.get_parameter("entry_distance_pct", "0.01"))
        self.profit_target_pct = float(self.get_parameter("profit_target_pct", "0.02"))
        self.stop_loss_pct = float(self.get_parameter("stop_loss_pct", "0.015"))

        # Add SPY with daily resolution (key to reducing frequency)
        self.symbol = self.add_equity("SPY", Resolution.DAILY).symbol

        # Create Bollinger Bands indicator with WIDER bands
        # Use SIMPLE moving average (standard for Bollinger Bands)
        self.bb_indicator = self.bb(
            self.symbol,
            bb_period,
            bb_std_dev,
            MovingAverageType.SIMPLE,
            Resolution.DAILY
        )

        # Track entry price for position sizing and exit logic
        self.entry_price = None

        # Debug logging
        self.debug(f"BollingerBand_ETF_LowFreq initialized:")
        self.debug(f"  BB Period: {bb_period}")
        self.debug(f"  BB Std Dev: {bb_std_dev} (WIDER bands for lower frequency)")
        self.debug(f"  Entry Distance: {self.entry_distance_pct * 100}%")
        self.debug(f"  Profit Target: {self.profit_target_pct * 100}%")
        self.debug(f"  Stop Loss: {self.stop_loss_pct * 100}%")
        self.debug(f"  Resolution: DAILY (fee control)")

    def on_data(self, data):
        """Execute trading logic on each data point."""

        # Check data availability
        if not data.bars.contains_key(self.symbol):
            return

        # Wait for indicator to be ready
        if not self.bb_indicator.is_ready:
            return

        # Get current price and Bollinger Bands values
        price = data.bars[self.symbol].close
        upper_band = self.bb_indicator.upper_band.current.value
        middle_band = self.bb_indicator.middle_band.current.value
        lower_band = self.bb_indicator.lower_band.current.value

        # Calculate adjusted lower band entry threshold
        # This allows fine-tuning signal quality vs frequency trade-off
        band_width = middle_band - lower_band
        adjusted_lower_band = lower_band + (self.entry_distance_pct * band_width)

        # Entry Logic: Lower band touch with entry distance offset
        if not self.portfolio.invested:
            # Check if price touches adjusted lower band
            if price <= adjusted_lower_band:
                # Calculate position size based on risk management
                shares = self._calculate_position_size(price)

                if shares > 0:
                    self.market_order(self.symbol, shares)
                    self.entry_price = price

                    self.debug(f"ENTRY: Price {price:.2f} <= Adj Lower Band {adjusted_lower_band:.2f}")
                    self.debug(f"  Lower Band: {lower_band:.2f}, Middle: {middle_band:.2f}, Upper: {upper_band:.2f}")
                    self.debug(f"  Shares: {shares}, Entry Price: {self.entry_price:.2f}")

        # Exit Logic: Multiple exit conditions
        elif self.portfolio.invested and self.entry_price is not None:
            current_return = (price - self.entry_price) / self.entry_price

            # Exit 1: Profit target reached
            if current_return >= self.profit_target_pct:
                self.liquidate(self.symbol)
                self.debug(f"EXIT (Profit Target): Return {current_return * 100:.2f}% >= {self.profit_target_pct * 100}%")
                self.entry_price = None

            # Exit 2: Stop loss hit
            elif current_return <= -self.stop_loss_pct:
                self.liquidate(self.symbol)
                self.debug(f"EXIT (Stop Loss): Return {current_return * 100:.2f}% <= -{self.stop_loss_pct * 100}%")
                self.entry_price = None

            # Exit 3: Mean reversion complete (price crosses middle band)
            elif price > middle_band:
                self.liquidate(self.symbol)
                self.debug(f"EXIT (Mean Reversion): Price {price:.2f} > Middle Band {middle_band:.2f}")
                self.debug(f"  Return: {current_return * 100:.2f}%")
                self.entry_price = None

    def _calculate_position_size(self, entry_price):
        """
        Calculate position size based on risk management.

        Risk Management Rules:
        - Max 1% of portfolio value at risk per trade
        - Risk per share = entry_price × stop_loss_pct
        - Max shares by cash = 95% of available cash
        - Final shares = min(risk-based, cash-based)

        Args:
            entry_price: Planned entry price

        Returns:
            int: Number of shares to purchase (0 if insufficient capital)
        """
        portfolio_value = self.portfolio.total_portfolio_value
        cash = self.portfolio.cash

        # Calculate max risk in dollars (1% of portfolio)
        max_risk_dollars = portfolio_value * 0.01

        # Calculate risk per share based on stop loss
        risk_per_share = entry_price * self.stop_loss_pct

        # Calculate shares based on risk
        shares_by_risk = int(max_risk_dollars / risk_per_share)

        # Calculate shares based on available cash (95% max to leave buffer)
        max_shares_by_cash = int((cash * 0.95) / entry_price)

        # Take minimum to respect both constraints
        final_shares = min(shares_by_risk, max_shares_by_cash)

        return final_shares
