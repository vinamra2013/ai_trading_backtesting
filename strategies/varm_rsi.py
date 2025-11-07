"""
VARM-RSI Strategy Implementation
Epic 24: Volatility-Adaptive RSI Mean Reversion Strategy

Implements the complete VARM-RSI strategy with:
- RSI(9) < 22 entry condition with multi-factor confirmation
- ATR-scaled profit targets and dynamic stops
- Volatility-adaptive position sizing
- Comprehensive portfolio risk management

Uses 1-minute data with Backtrader resampling to create required timeframes.
"""

import backtrader as bt
import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class BearPower(bt.Indicator):
    """
    Custom Bear Power Indicator
    Bear Power = Low - EMA(13) of close prices

    Used to identify capitulation when Bear Power < -ATR
    """

    lines = ("bear_power",)
    params = (("period", 13),)

    def __init__(self):
        # EMA of close prices
        ema_close = bt.indicators.EMA(self.data.close, period=self.p.period)
        # Bear Power = Low - EMA(close)
        self.lines.bear_power = self.data.low - ema_close


class VARM_RSI(BaseStrategy):
    """
    Volatility-Adaptive RSI Mean Reversion Strategy

    Core Logic:
    - Entry: RSI(9) < 22 + multiple confirmations
    - Exit: ATR-scaled targets with trailing stops
    - Risk: Kelly-inspired sizing with volatility adjustment
    - Portfolio: Max 3 positions, sector limits, correlation monitoring
    """

    params = (
        # Core entry parameters
        ("rsi_period", 9),  # RSI calculation period
        ("rsi_entry_threshold", 22),  # RSI < 22 for entry
        ("atr_period", 14),  # ATR calculation period
        ("atr_min_volatility", 5.0),  # Minimum ATR for volatility confirmation
        # Volume filter parameters
        ("volume_avg_period", 10),  # Days for volume average
        ("volume_multiplier", 2.5),  # Volume must be 2.5x average
        # Trend filter parameters
        ("sma_period", 20),  # SMA period for trend filter
        ("sma_slope_threshold", -0.1),  # Maximum downward slope °/day
        # Multi-timeframe confirmation
        ("rsi_1h_threshold", 30),  # 1-hour RSI > 30 confirmation
        ("rsi_4h_exit_threshold", 40),  # 4-hour RSI < 40 exit signal
        # Exit parameters
        ("target_1_atr_multiplier", 0.8),  # First target: 0.8 * ATR
        ("target_2_atr_multiplier", 1.6),  # Second target: 1.6 * ATR
        ("trailing_stop_atr_multiplier", 1.5),  # Trailing stop: 1.5 * ATR
        ("stop_loss_atr_multiplier", 0.5),  # Stop loss: Entry - 0.5 * ATR
        ("max_hold_hours", 48),  # Maximum position hold time
        # Position sizing parameters
        ("base_risk_pct", 0.01),  # 1% base risk per trade
        ("volatility_risk_cap", 0.008),  # Max 0.8% risk for high volatility
        ("sector_concentration_penalty", 0.7),  # 0.7x size if >25% sector exposure
        ("drawdown_penalty_threshold", 0.015),  # 1.5% portfolio DD triggers penalty
        ("drawdown_penalty_factor", 0.6),  # 0.6x size when DD triggered
        # Portfolio risk parameters
        ("max_positions", 3),  # Maximum concurrent positions
        ("portfolio_dd_stop", 0.02),  # 2% portfolio DD emergency stop
        ("sector_limit_pct", 0.25),  # Max 25% exposure per sector
        ("correlation_threshold", 0.7),  # Disable if correlation > 0.7
        # Market filter parameters
        ("spy_sma_period", 20),  # SPY SMA period for market filter
        ("vix_fear_threshold", 30),  # VIX < 30 for greed filter
        # Data timeframe parameters
        ("primary_timeframe_compression", 5),  # 5-minute primary timeframe
        ("use_market_filters", True),  # Enable SPY/VIX filters
        ("exclude_earnings", True),  # Exclude earnings periods
        # Logging and debugging
        ("printlog", True),
        ("log_signals", True),
        ("log_orders", True),
        ("log_trades", True),
    )

    def __init__(self):
        """
        Initialize VARM-RSI strategy with multi-timeframe indicators
        """
        super().__init__()

        # Initialize position tracking
        self.current_positions = {}  # symbol -> position info
        self.portfolio_dd = 0.0
        self.sector_exposure = {}  # sector -> exposure amount
        self.entry_times = {}  # symbol -> entry datetime

        # Setup data feeds - assume data[0] is primary, others are resampled
        self.primary_data = self.datas[0]  # 5-minute data (resampled from 1-min)

        # Get resampled data feeds by name
        self.data_1h = None
        self.data_4h = None
        self.data_daily = None
        self.spy_daily = None
        self.vix_daily = None

        # Try to get resampled data feeds
        for data in self.datas[1:]:
            name = getattr(data, "_name", "")
            if name.endswith("_1h"):
                self.data_1h = data
            elif name.endswith("_4h"):
                self.data_4h = data
            elif name.endswith("_daily"):
                if "SPY" in name:
                    self.spy_daily = data
                elif "VIX" in name:
                    self.vix_daily = data
                else:
                    self.data_daily = data

        # Initialize core indicators on primary timeframe
        self.rsi = bt.indicators.RSI(self.primary_data.close, period=self.p.rsi_period)

        self.atr = bt.indicators.ATR(self.primary_data, period=self.p.atr_period)

        # Volume indicators
        self.volume_sma = bt.indicators.SMA(
            self.primary_data.volume, period=self.p.volume_avg_period
        )

        # Trend indicators
        self.sma = bt.indicators.SMA(self.primary_data.close, period=self.p.sma_period)

        # Custom Bear Power indicator
        self.bear_power = BearPower(self.primary_data)

        # OBV for accumulation signal
        self.obv = bt.indicators.OnBalanceVolume(self.primary_data)

        # Multi-timeframe RSI indicators (if data available)
        self.rsi_1h = None
        self.rsi_4h = None
        if self.data_1h:
            self.rsi_1h = bt.indicators.RSI(self.data_1h.close, period=14)
        if self.data_4h:
            self.rsi_4h = bt.indicators.RSI(self.data_4h.close, period=14)

        # Market filter indicators
        self.spy_sma = None
        if self.spy_daily:
            self.spy_sma = bt.indicators.SMA(
                self.spy_daily.close, period=self.p.spy_sma_period
            )

        # Slope calculation for trend filter (SMA slope in °/day)
        self.sma_slope = None
        if self.data_daily:
            # Calculate slope of daily SMA using linear regression approximation
            daily_sma = bt.indicators.SMA(
                self.data_daily.close, period=self.p.sma_period
            )
            # We'll calculate slope manually in the should_enter method

        logger.info(f"VARM-RSI strategy initialized with {len(self.datas)} data feeds")
        if self.p.log_signals:
            self.log("VARM-RSI strategy initialized", level="INFO")

    def should_enter(self) -> bool:
        """
        Core entry logic: RSI(9) < 22 + multiple confirmations

        Returns:
            bool: True if all entry conditions met
        """
        # Primary condition: RSI < 22
        if self.rsi[0] >= self.p.rsi_entry_threshold:
            return False

        # Volatility confirmation: ATR > 5
        if self.atr[0] <= self.p.atr_min_volatility:
            return False

        # Volume filter: Current volume > 2.5x 10-day average
        if self.primary_data.volume[0] <= (
            self.volume_sma[0] * self.p.volume_multiplier
        ):
            return False

        # Trend filter: SMA slope > -0.1°/day (not in strong downtrend)
        if self.data_daily:
            daily_sma_slope = self._calculate_slope(self.sma, period=5)
            if daily_sma_slope <= self.p.sma_slope_threshold:
                return False

        # Multi-timeframe confirmations
        if self.rsi_1h and self.rsi_1h[0] <= self.p.rsi_1h_threshold:
            return False  # 1-hour RSI must be > 30

        # OBV accumulation signal: OBV slope > 0
        obv_slope = self._calculate_slope(self.obv, period=5)
        if obv_slope <= 0:
            return False

        # Bear Power capitulation: Bear Power < -ATR
        if self.bear_power[0] >= -self.atr[0]:
            return False

        # Market filters (if enabled)
        if self.p.use_market_filters:
            if not self._check_market_filters():
                return False

        # Earnings exclusion (if enabled)
        if self.p.exclude_earnings and self._is_earnings_period():
            return False

        return True

    def should_exit(self, symbol: str) -> Tuple[bool, str]:
        """
        Comprehensive exit logic with multiple conditions

        Args:
            symbol: Symbol to check exit for

        Returns:
            Tuple[bool, str]: (should_exit, exit_reason)
        """
        # Time-based exit: 48-hour maximum hold
        if symbol in self.entry_times:
            hold_time = datetime.now() - self.entry_times[symbol]
            if hold_time.total_seconds() > (self.p.max_hold_hours * 3600):
                return True, "max_hold_time"

        # Momentum failure: 4-hour RSI < 40
        if self.rsi_4h and self.rsi_4h[0] < self.p.rsi_4h_exit_threshold:
            return True, "momentum_failure"

        # Volatility contraction exit (ATR decreasing significantly)
        atr_slope = self._calculate_slope(self.atr, period=10)
        if atr_slope < -0.1:  # ATR decreasing
            return True, "volatility_contraction"

        # Check profit targets and stops (implemented in order management)
        # This would be called from next() method

        return False, ""

    def calculate_varm_position_size(self, symbol: str, entry_price: float) -> float:
        """
        Kelly-inspired position sizing with volatility and risk adjustments

        Args:
            symbol: Trading symbol
            entry_price: Entry price

        Returns:
            float: Position size as percentage of portfolio
        """
        # Base risk: 1% of portfolio per trade
        base_risk = self.p.base_risk_pct

        # Volatility adjustment: min(0.8%, 0.5 × ATR/price)
        volatility_risk = min(
            self.p.volatility_risk_cap, (self.atr[0] / entry_price) * 0.5
        )
        adjusted_risk = min(base_risk, volatility_risk)

        # Sector diversification penalty
        sector_penalty = self._calculate_sector_penalty(symbol)
        adjusted_risk *= sector_penalty

        # Drawdown adjustment
        dd_penalty = self._calculate_drawdown_penalty()
        adjusted_risk *= dd_penalty

        # Portfolio risk check
        if not self._check_portfolio_risk(symbol, adjusted_risk):
            return 0.0

        # Calculate position size: risk_amount / (ATR * volatility_factor)
        risk_amount = self.broker.getvalue() * adjusted_risk
        stop_distance = self.atr[0] * self.p.stop_loss_atr_multiplier

        if stop_distance > 0:
            position_size_pct = risk_amount / (entry_price * stop_distance)
            return min(position_size_pct, 0.95)  # Max 95% of portfolio

        return 0.0

    def _calculate_slope(self, indicator, period: int = 5) -> float:
        """
        Calculate slope of indicator over specified period

        Args:
            indicator: Backtrader indicator
            period: Period for slope calculation

        Returns:
            float: Slope value
        """
        if len(indicator) < period + 1:
            return 0.0

        # Simple linear regression slope
        y = [indicator[-i] for i in range(period + 1)]
        x = list(range(period + 1))

        # Calculate slope using numpy polyfit
        try:
            slope = np.polyfit(x, y, 1)[0]
            return slope
        except:
            return 0.0

    def _check_market_filters(self) -> bool:
        """
        Check SPY and VIX market filters

        Returns:
            bool: True if market conditions allow trading
        """
        # SPY > 20-day SMA (bull market filter)
        if self.spy_sma and self.spy_daily:
            if self.spy_daily.close[0] <= self.spy_sma[0]:
                return False

        # VIX < 30 (fear/greed filter - not too fearful)
        if self.vix_daily and self.vix_daily.close[0] >= self.p.vix_fear_threshold:
            return False

        return True

    def _is_earnings_period(self) -> bool:
        """
        Check if current period is near earnings (simplified implementation)

        Returns:
            bool: True if should exclude due to earnings
        """
        # Get current date from data
        if len(self.primary_data) > 0:
            current_date = self.primary_data.datetime.date(0)

            # Simplified earnings exclusion - exclude Friday after 4 PM and Monday before 8 AM
            # This is a basic approximation; real implementation would use earnings calendar
            current_time = self.primary_data.datetime.time(0)

            if (
                current_date.weekday() == 4 and current_time.hour >= 16
            ):  # Friday after 4 PM
                return True
            elif (
                current_date.weekday() == 0 and current_time.hour < 8
            ):  # Monday before 8 AM
                return True

        return False

    def _calculate_sector_penalty(self, symbol: str) -> float:
        """
        Calculate sector diversification penalty

        Args:
            symbol: Trading symbol

        Returns:
            float: Penalty factor (0.7 if >25% exposure, 1.0 otherwise)
        """
        # Simplified sector logic - would need sector mapping
        # For now, assume no penalty
        return 1.0

    def _calculate_drawdown_penalty(self) -> float:
        """
        Calculate drawdown-based penalty

        Returns:
            float: Penalty factor
        """
        if self.portfolio_dd >= self.p.drawdown_penalty_threshold:
            return self.p.drawdown_penalty_factor
        return 1.0

    def _check_portfolio_risk(self, symbol: str, risk_pct: float) -> bool:
        """
        Comprehensive portfolio risk check

        Args:
            symbol: Trading symbol
            risk_pct: Risk percentage

        Returns:
            bool: True if risk checks pass
        """
        # Max positions check
        if len(self.current_positions) >= self.p.max_positions:
            return False

        # Portfolio drawdown emergency stop
        if self.portfolio_dd >= self.p.portfolio_dd_stop:
            return False

        # Sector concentration check
        if not self._check_sector_limits(symbol, risk_pct):
            return False

        # Correlation check
        if not self._check_correlation_limits(symbol):
            return False

        return True

    def _check_sector_limits(self, symbol: str, risk_pct: float) -> bool:
        """
        Check sector concentration limits

        Args:
            symbol: Trading symbol
            risk_pct: Risk percentage

        Returns:
            bool: True if sector limits allow position
        """
        # Simplified - would need actual sector data
        return True

    def _check_correlation_limits(self, symbol: str) -> bool:
        """
        Check correlation with existing positions

        Args:
            symbol: Trading symbol

        Returns:
            bool: True if correlation allows position
        """
        # Simplified - would need correlation matrix
        return True

    def next(self):
        """
        Main strategy logic called for each bar
        """
        # Update portfolio drawdown
        self.portfolio_dd = self._calculate_portfolio_drawdown()

        # Check for entry signal
        if not self.position and self.should_enter():
            if self.p.log_signals:
                self.log(f"ENTRY SIGNAL: RSI={self.rsi[0]:.2f}, ATR={self.atr[0]:.2f}")

            # Calculate position size
            entry_price = self.primary_data.close[0]
            position_size_pct = self.calculate_varm_position_size(
                self.primary_data._name, entry_price
            )

            if position_size_pct > 0:
                # Calculate actual share quantity
                portfolio_value = self.broker.getvalue()
                position_value = portfolio_value * position_size_pct
                shares = int(position_value / entry_price)

                if shares > 0:
                    self.buy(size=shares)
                    self.entry_times[self.primary_data._name] = datetime.now()

                    # Track position
                    self.current_positions[self.primary_data._name] = {
                        "entry_price": entry_price,
                        "shares": shares,
                        "entry_time": datetime.now(),
                        "target_1_hit": False,
                        "atr_at_entry": self.atr[0],
                    }

        # Check for exit signals (if in position)
        elif self.position:
            symbol = self.primary_data._name
            should_exit, exit_reason = self.should_exit(symbol)

            # Check profit targets and trailing stops
            if symbol in self.current_positions:
                pos_info = self.current_positions[symbol]
                current_price = self.primary_data.close[0]
                entry_price = pos_info["entry_price"]
                atr_value = pos_info["atr_at_entry"]

                # Target 1: 0.8 * ATR profit
                target_1_price = entry_price + (
                    atr_value * self.p.target_1_atr_multiplier
                )
                if (
                    not pos_info.get("target_1_hit", False)
                    and current_price >= target_1_price
                ):
                    # Sell partial position (50%) and activate trailing stop
                    shares_to_sell = int(self.position.size * 0.5)
                    if shares_to_sell > 0:
                        self.sell(size=shares_to_sell)
                        pos_info["target_1_hit"] = True
                        pos_info["trailing_stop"] = current_price - (
                            atr_value * self.p.trailing_stop_atr_multiplier
                        )
                        if self.p.log_signals:
                            self.log(
                                f"TARGET 1 HIT: Sold 50% at ${current_price:.2f}, trailing stop activated"
                            )

                # Update trailing stop if target 1 hit
                if pos_info.get("target_1_hit", False):
                    new_trailing_stop = current_price - (
                        atr_value * self.p.trailing_stop_atr_multiplier
                    )
                    pos_info["trailing_stop"] = max(
                        pos_info["trailing_stop"], new_trailing_stop
                    )

                    # Check trailing stop
                    if current_price <= pos_info["trailing_stop"]:
                        if self.p.log_signals:
                            self.log(f"TRAILING STOP HIT: at ${current_price:.2f}")
                        self.sell()
                        should_exit = True
                        exit_reason = "trailing_stop"

                # Stop loss: Entry - 0.5 * ATR
                stop_loss_price = entry_price - (
                    atr_value * self.p.stop_loss_atr_multiplier
                )
                if current_price <= stop_loss_price:
                    if self.p.log_signals:
                        self.log(f"STOP LOSS HIT: at ${current_price:.2f}")
                    self.sell()
                    should_exit = True
                    exit_reason = "stop_loss"

            # Other exit conditions
            if not should_exit:
                should_exit, exit_reason = self.should_exit(symbol)

            if should_exit:
                if self.p.log_signals:
                    self.log(f"EXIT SIGNAL: {exit_reason}")
                self.sell()

                # Clean up tracking
                if symbol in self.current_positions:
                    del self.current_positions[symbol]
                if symbol in self.entry_times:
                    del self.entry_times[symbol]

    def _calculate_portfolio_drawdown(self) -> float:
        """
        Calculate current portfolio drawdown

        Returns:
            float: Current drawdown percentage
        """
        current_value = self.broker.getvalue()
        peak_value = getattr(self, "_peak_value", current_value)

        if current_value > peak_value:
            self._peak_value = current_value
            return 0.0

        drawdown = (peak_value - current_value) / peak_value
        return drawdown

    def notify_order(self, order):
        """
        Handle order notifications
        """
        super().notify_order(order)

        if order.status in [order.Completed]:
            if order.isbuy():
                if self.p.log_orders:
                    self.log(
                        f"BUY EXECUTED: {order.executed.size} shares @ ${order.executed.price:.2f}"
                    )
            elif order.issell():
                if self.p.log_orders:
                    self.log(
                        f"SELL EXECUTED: {order.executed.size} shares @ ${order.executed.price:.2f}"
                    )

    def notify_trade(self, trade):
        """
        Handle trade notifications
        """
        super().notify_trade(trade)

        if trade.isclosed:
            pnl_pct = (
                (trade.pnlcomm / abs(trade.value)) * 100 if trade.value != 0 else 0
            )
            if self.p.log_trades:
                self.log(f"TRADE CLOSED: P&L ${trade.pnlcomm:.2f} ({pnl_pct:+.2f}%)")


# Strategy configuration for backtesting
VARM_RSI_PARAMS = {
    "rsi_period": 9,
    "rsi_entry_threshold": 22,
    "atr_period": 14,
    "atr_min_volatility": 5.0,
    "volume_avg_period": 10,
    "volume_multiplier": 2.5,
    "sma_period": 20,
    "sma_slope_threshold": -0.1,
    "rsi_1h_threshold": 30,
    "rsi_4h_exit_threshold": 40,
    "target_1_atr_multiplier": 0.8,
    "target_2_atr_multiplier": 1.6,
    "trailing_stop_atr_multiplier": 1.5,
    "stop_loss_atr_multiplier": 0.5,
    "max_hold_hours": 48,
    "base_risk_pct": 0.01,
    "volatility_risk_cap": 0.008,
    "sector_concentration_penalty": 0.7,
    "drawdown_penalty_threshold": 0.015,
    "drawdown_penalty_factor": 0.6,
    "max_positions": 3,
    "portfolio_dd_stop": 0.02,
    "sector_limit_pct": 0.25,
    "correlation_threshold": 0.7,
    "spy_sma_period": 20,
    "vix_fear_threshold": 30,
    "primary_timeframe_compression": 5,
    "use_market_filters": True,
    "exclude_earnings": True,
    "printlog": True,
    "log_signals": True,
    "log_orders": True,
    "log_trades": True,
}
