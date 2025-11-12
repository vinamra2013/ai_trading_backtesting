"""
SMA Crossover ETF Strategy
Strategy ID: STR-003
Category: Momentum
Asset Class: ETF (SPY)

Classic golden cross/death cross strategy with volume confirmation.
Trend-following approach using dual SMA indicators.
"""

from AlgorithmImports import *


class SMACrossoverETF(QCAlgorithm):
    """
    SMA Crossover Strategy Implementation

    Entry: Golden Cross (fast SMA > slow SMA) + Volume confirmation
    Exit: Death Cross (fast SMA < slow SMA) OR profit target OR stop loss
    """

    def initialize(self):
        """Initialize strategy with parameters and indicators."""

        # Backtest period
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(1000)

        # Set Interactive Brokers brokerage model
        self.set_brokerage_model(BrokerageName.INTERACTIVE_BROKERS_BROKERAGE)

        # Get optimizable parameters
        self.fast_period = int(self.get_parameter("fast_sma", "30"))
        self.slow_period = int(self.get_parameter("slow_sma", "150"))
        self.volume_threshold = float(self.get_parameter("volume_threshold", "1.5"))
        self.profit_target_pct = float(self.get_parameter("profit_target_pct", "0.02"))
        self.stop_loss_pct = float(self.get_parameter("stop_loss_pct", "0.015"))

        # Risk management: 1% max risk per trade
        self.max_risk_per_trade = 0.01

        # Add SPY ETF with daily resolution
        self.symbol = self.add_equity("SPY", Resolution.DAILY).symbol

        # Create SMA indicators
        self.fast_sma = self.sma(self.symbol, self.fast_period, Resolution.DAILY)
        self.slow_sma = self.sma(self.symbol, self.slow_period, Resolution.DAILY)

        # Volume tracking
        self.volume_sum = 0
        self.bar_count = 0

        # Entry tracking
        self.entry_price = 0
        self.entry_time = None

        # Previous SMA values for crossover detection
        self.previous_fast = 0
        self.previous_slow = 0

        self.debug(f"Strategy initialized: Fast SMA={self.fast_period}, Slow SMA={self.slow_period}")
        self.debug(f"Volume threshold={self.volume_threshold}x, Profit target={self.profit_target_pct*100:.1f}%, Stop loss={self.stop_loss_pct*100:.1f}%")

    def on_data(self, data):
        """Process incoming data and execute trading logic."""

        # Check data availability
        if not data.bars.contains_key(self.symbol):
            return

        # Wait for indicators to be ready
        if not self.fast_sma.is_ready or not self.slow_sma.is_ready:
            return

        # Get current bar data
        bar = data.bars[self.symbol]
        current_price = bar.close
        current_volume = bar.volume

        # Update volume tracking
        self.volume_sum += current_volume
        self.bar_count += 1

        # Calculate average volume
        avg_volume = self.volume_sum / self.bar_count if self.bar_count > 0 else current_volume

        # Get SMA values
        fast_value = self.fast_sma.current.value
        slow_value = self.slow_sma.current.value

        # Check if we're invested
        invested = self.portfolio[self.symbol].invested

        # Exit logic (check first)
        if invested:
            self._check_exit_conditions(current_price, fast_value, slow_value)

        # Entry logic (only if not invested)
        if not invested:
            self._check_entry_conditions(
                current_price,
                current_volume,
                avg_volume,
                fast_value,
                slow_value
            )

        # Store current values for next iteration
        self.previous_fast = fast_value
        self.previous_slow = slow_value

    def _check_entry_conditions(self, price, volume, avg_volume, fast_sma, slow_sma):
        """
        Check for golden cross entry signal with volume confirmation.

        Entry conditions:
        1. Golden Cross: Fast SMA > Slow SMA (bullish crossover)
        2. Volume Confirmation: Current volume > average volume × threshold
        """

        # Golden cross condition: fast SMA above slow SMA
        golden_cross = fast_sma > slow_sma

        # Volume confirmation: current volume exceeds threshold
        volume_confirmed = volume > (avg_volume * self.volume_threshold)

        # Check if we just crossed over (optional enhancement for precision)
        # crossover_happened = self.previous_fast <= self.previous_slow and fast_sma > slow_sma

        # Entry signal
        if golden_cross and volume_confirmed:
            # Calculate position size based on risk management
            # Risk = stop_loss_pct × position_value
            # Max risk per trade = max_risk_per_trade × portfolio_value
            stop_distance = self.stop_loss_pct
            max_position_value = (self.max_risk_per_trade * self.portfolio.total_portfolio_value) / stop_distance

            # Convert to percentage of portfolio (max 100%)
            position_pct = min(max_position_value / self.portfolio.total_portfolio_value, 1.0)

            # Enter position
            self.set_holdings(self.symbol, position_pct)

            # Track entry
            self.entry_price = price
            self.entry_time = self.time

            self.debug(f"ENTRY: Golden Cross detected at ${price:.2f}")
            self.debug(f"  Fast SMA: {fast_sma:.2f}, Slow SMA: {slow_sma:.2f}")
            self.debug(f"  Volume: {volume:,.0f} vs Avg: {avg_volume:,.0f} ({volume/avg_volume:.2f}x)")
            self.debug(f"  Position size: {position_pct*100:.1f}%")

    def _check_exit_conditions(self, price, fast_sma, slow_sma):
        """
        Check exit conditions: profit target, stop loss, or death cross.

        Exit conditions:
        1. Profit target reached
        2. Stop loss triggered
        3. Death Cross: Fast SMA < Slow SMA (bearish crossover)
        """

        if self.entry_price == 0:
            return

        # Calculate P&L percentage
        pnl_pct = (price - self.entry_price) / self.entry_price

        # Exit reason
        exit_reason = None

        # 1. Profit target
        if pnl_pct >= self.profit_target_pct:
            exit_reason = f"Profit target reached: {pnl_pct*100:.2f}%"

        # 2. Stop loss
        elif pnl_pct <= -self.stop_loss_pct:
            exit_reason = f"Stop loss triggered: {pnl_pct*100:.2f}%"

        # 3. Death cross
        elif fast_sma < slow_sma:
            exit_reason = f"Death Cross detected (Fast: {fast_sma:.2f} < Slow: {slow_sma:.2f})"

        # Execute exit
        if exit_reason:
            self.liquidate(self.symbol)

            self.debug(f"EXIT: {exit_reason}")
            self.debug(f"  Entry: ${self.entry_price:.2f} @ {self.entry_time}")
            self.debug(f"  Exit: ${price:.2f} @ {self.time}")
            self.debug(f"  P&L: {pnl_pct*100:.2f}%")

            # Reset entry tracking
            self.entry_price = 0
            self.entry_time = None
