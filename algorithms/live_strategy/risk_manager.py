"""
Risk Manager Library for LEAN Algorithms

Epic 6: Risk Management System
Provides position sizing, loss limits, concentration limits, and risk metrics.

This library integrates with any LEAN algorithm to enforce risk controls before
every order and continuously monitor portfolio risk exposure.

Usage Example:
    from algorithms.live_strategy.risk_manager import RiskManager

    class MyAlgorithm(QCAlgorithm):
        def Initialize(self):
            # Initialize risk manager
            self.risk = RiskManager(
                algorithm=self,
                config_path="/app/config/risk_config.yaml"
            )

        def OnData(self, data):
            # Check daily loss limit
            if self.risk.check_loss_limit_breached():
                self.Liquidate()
                return

            # Check if we can open a position
            symbol = self.spy.Symbol
            quantity = 100
            price = data[symbol].Close

            if self.risk.can_open_position(symbol, quantity, price):
                self.MarketOrder(symbol, quantity)

            # Calculate risk metrics
            metrics = self.risk.calculate_metrics()
            self.Log(f"Portfolio heat: {metrics['portfolio_heat']}%")

Configuration:
    The risk manager reads from /app/config/risk_config.yaml with these key settings:
    - position_limits.max_position_size_pct: Max position as % of portfolio (default: 10%)
    - loss_limits.daily_loss_limit_pct: Daily loss limit % (default: 2%)
    - concentration_limits.max_concurrent_positions: Max open positions (default: 5)

    If the config file is not found, safe defaults are automatically applied.
"""

from typing import Dict, Optional, Tuple
import yaml
from pathlib import Path
import numpy as np
from datetime import datetime


class RiskManager:
    """
    Comprehensive risk management for LEAN trading algorithms.

    Epic 6: Risk Management System
    User Stories: US-6.1, US-6.2, US-6.3, US-6.5

    Features:
    - Position size limits as % of portfolio (US-6.1)
    - Daily loss limit monitoring and enforcement (US-6.2)
    - Concentration limits for max concurrent positions (US-6.3)
    - Risk metrics calculation including VaR and portfolio heat (US-6.5)
    - Trading halt/resume capability for emergency stops

    Integration:
    - Accesses algorithm.Portfolio for positions and equity
    - Uses algorithm.Time for timestamps
    - Logs via algorithm.Log() and algorithm.Error()
    """

    def __init__(self, algorithm, config_path: str = "/app/config/risk_config.yaml"):
        """
        Initialize risk manager with algorithm reference and configuration.

        Args:
            algorithm: Reference to the LEAN QCAlgorithm instance
            config_path: Path to risk_config.yaml file

        Raises:
            FileNotFoundError: If config file not found (uses defaults)
            ValueError: If config validation fails
        """
        self.algorithm = algorithm
        self.config_path = config_path

        # Load configuration
        self.config = self._load_config()

        # Initialize state tracking
        self.daily_starting_equity: float = algorithm.Portfolio.TotalPortfolioValue
        self.trading_enabled: bool = True
        self.risk_metrics_cache: Dict = {}
        self.last_metrics_update: Optional[datetime] = None

        # Extract key parameters from config
        self._extract_parameters()

        algorithm.Log(f"✓ RiskManager initialized with config: {config_path}")
        algorithm.Log(f"  - Max position size: {self.max_position_size_pct}% of portfolio")
        algorithm.Log(f"  - Daily loss limit: {self.daily_loss_limit_pct}%")
        algorithm.Log(f"  - Max concurrent positions: {self.max_concurrent_positions}")

    def _load_config(self) -> Dict:
        """
        Load risk configuration from YAML file.

        Returns:
            Dict: Configuration dictionary with defaults if file not found

        Epic 6: Configuration Management
        """
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                self.algorithm.Log(f"✓ Loaded risk config from {self.config_path}")
                return config
        except FileNotFoundError:
            self.algorithm.Error(f"Config file not found: {self.config_path}. Using defaults.")
            return self._default_config()
        except Exception as e:
            self.algorithm.Error(f"Error loading config: {e}. Using defaults.")
            return self._default_config()

    def _default_config(self) -> Dict:
        """
        Provide default risk configuration if file not found.

        Returns:
            Dict: Default configuration matching risk_config.yaml structure
        """
        return {
            'position_limits': {
                'enabled': True,
                'max_position_size_pct': 10,
                'min_position_size': 100,
                'check_before_entry': True
            },
            'loss_limits': {
                'enabled': True,
                'daily_loss_limit_pct': 2,
                'auto_liquidate': True
            },
            'concentration_limits': {
                'enabled': True,
                'max_concurrent_positions': 5,
                'allow_exits_when_at_limit': True
            },
            'risk_metrics': {
                'enabled': True,
                'var': {
                    'confidence_levels': [0.95, 0.99],
                    'lookback_days': 252
                },
                'heat': {
                    'max_heat_pct': 50
                }
            }
        }

    def _extract_parameters(self):
        """
        Extract and validate risk parameters from config.

        Sets instance variables for quick access to key parameters.
        """
        # Position limits
        pos_limits = self.config.get('position_limits', {})
        self.max_position_size_pct = pos_limits.get('max_position_size_pct', 10)
        self.min_position_size = pos_limits.get('min_position_size', 100)
        self.position_limits_enabled = pos_limits.get('enabled', True)

        # Loss limits
        loss_limits = self.config.get('loss_limits', {})
        self.daily_loss_limit_pct = loss_limits.get('daily_loss_limit_pct', 2)
        self.loss_limits_enabled = loss_limits.get('enabled', True)

        # Concentration limits
        conc_limits = self.config.get('concentration_limits', {})
        self.max_concurrent_positions = conc_limits.get('max_concurrent_positions', 5)
        self.allow_exits_when_at_limit = conc_limits.get('allow_exits_when_at_limit', True)
        self.concentration_limits_enabled = conc_limits.get('enabled', True)

        # Risk metrics
        metrics = self.config.get('risk_metrics', {})
        self.risk_metrics_enabled = metrics.get('enabled', True)

    def can_open_position(
        self,
        symbol,
        quantity: int,
        price: float
    ) -> bool:
        """
        Check if a new position can be opened based on risk limits.

        US-6.1: Position Size Limit - Max position size as % of portfolio
        US-6.3: Concentration Limit - Max concurrent positions

        Args:
            symbol: LEAN Symbol object for the security
            quantity: Number of shares to trade (signed: positive=buy, negative=sell)
            price: Current market price

        Returns:
            bool: True if position can be opened, False otherwise

        Logic:
        1. Check if trading is enabled (not halted)
        2. Validate position size doesn't exceed max % of portfolio
        3. Check minimum position size requirement
        4. Verify we haven't hit max concurrent positions limit
        5. Allow exits even if at concentration limit
        """
        # Trading halt check
        if not self.trading_enabled:
            self.algorithm.Log(f"✗ Trading halted - cannot open {symbol}")
            return False

        # Get portfolio value
        portfolio_value = self.algorithm.Portfolio.TotalPortfolioValue
        position_value = abs(quantity * price)

        # Determine if this is an entry or exit
        current_holdings = self.algorithm.Portfolio[symbol]
        is_entry = (quantity > 0 and current_holdings.Quantity >= 0) or \
                   (quantity < 0 and current_holdings.Quantity <= 0)

        # US-6.1: Position Size Limit Check
        if self.position_limits_enabled and is_entry:
            position_size_pct = (position_value / portfolio_value) * 100

            if position_size_pct > self.max_position_size_pct:
                self.algorithm.Log(
                    f"✗ Position size check failed: {symbol} position would be "
                    f"{position_size_pct:.2f}% of portfolio (max: {self.max_position_size_pct}%)"
                )
                return False

            # Minimum position check
            if position_value < self.min_position_size:
                self.algorithm.Log(
                    f"✗ Position too small: ${position_value:.2f} "
                    f"(min: ${self.min_position_size})"
                )
                return False

        # US-6.3: Concentration Limit Check
        if self.concentration_limits_enabled and is_entry:
            # Count current open positions
            open_positions = len([
                holding for holding in self.algorithm.Portfolio.Values
                if holding.Invested
            ])

            if open_positions >= self.max_concurrent_positions:
                self.algorithm.Log(
                    f"✗ Concentration limit reached: {open_positions} positions "
                    f"(max: {self.max_concurrent_positions})"
                )
                return False

        # All checks passed
        self.algorithm.Debug(
            f"✓ Risk checks passed for {symbol}: "
            f"{abs(quantity)} shares @ ${price:.2f} = ${position_value:,.2f}"
        )
        return True

    def check_loss_limit_breached(self) -> bool:
        """
        Check if daily loss limit has been breached.

        US-6.2: Daily Loss Limit - Track and enforce daily P&L limits

        Returns:
            bool: True if daily loss limit breached, False otherwise

        Logic:
        1. Calculate current portfolio value
        2. Compare to daily starting equity
        3. Calculate daily P&L percentage
        4. Return True if loss exceeds configured limit
        """
        if not self.loss_limits_enabled:
            return False

        # Get current portfolio value
        current_equity = self.algorithm.Portfolio.TotalPortfolioValue

        # Calculate daily P&L
        daily_pnl = current_equity - self.daily_starting_equity
        daily_pnl_pct = (daily_pnl / self.daily_starting_equity) * 100 \
                        if self.daily_starting_equity > 0 else 0

        # Check if loss limit breached
        if daily_pnl_pct < -self.daily_loss_limit_pct:
            self.algorithm.Error(
                f"⚠️ DAILY LOSS LIMIT BREACHED: {daily_pnl_pct:.2f}% "
                f"(limit: -{self.daily_loss_limit_pct}%)"
            )
            self.algorithm.Error(
                f"  Starting: ${self.daily_starting_equity:,.2f} → "
                f"Current: ${current_equity:,.2f} → "
                f"Loss: ${daily_pnl:,.2f}"
            )
            return True

        return False

    def calculate_metrics(self) -> Dict:
        """
        Calculate comprehensive risk metrics for the portfolio.

        US-6.5: Risk Metrics Calculation - VaR, heat, correlation, leverage

        Returns:
            Dict: Risk metrics including:
                - portfolio_heat: Total exposure as % of portfolio
                - var_95: Value at Risk at 95% confidence (simplified)
                - var_99: Value at Risk at 99% confidence (simplified)
                - leverage_ratio: Total position value / equity
                - num_positions: Number of open positions
                - largest_position_pct: Largest single position as % of portfolio

        Note: This is a simplified implementation. Production systems would use
        historical returns data for more accurate VaR calculations.
        """
        if not self.risk_metrics_enabled:
            return {}

        portfolio = self.algorithm.Portfolio
        portfolio_value = portfolio.TotalPortfolioValue

        if portfolio_value == 0:
            return {
                'portfolio_heat': 0.0,
                'var_95': 0.0,
                'var_99': 0.0,
                'leverage_ratio': 0.0,
                'num_positions': 0,
                'largest_position_pct': 0.0
            }

        # Calculate total exposure (sum of absolute position values)
        total_exposure = 0.0
        position_values = []

        for holding in portfolio.Values:
            if holding.Invested:
                position_value = abs(holding.HoldingsValue)
                total_exposure += position_value
                position_values.append(position_value)

        # Portfolio heat (total exposure as % of portfolio)
        portfolio_heat = (total_exposure / portfolio_value) * 100

        # Simplified VaR calculation (percentage-based)
        # In production, this would use historical returns and proper VaR models
        # Here we use a simplified approach: assume normal distribution
        daily_volatility = 0.015  # 1.5% daily volatility assumption
        var_95 = portfolio_value * daily_volatility * 1.645  # 95% confidence
        var_99 = portfolio_value * daily_volatility * 2.326  # 99% confidence

        # Leverage ratio (gross exposure / equity)
        leverage_ratio = total_exposure / portfolio_value if portfolio_value > 0 else 0.0

        # Largest position as % of portfolio
        largest_position_pct = 0.0
        if position_values:
            largest_position_pct = (max(position_values) / portfolio_value) * 100

        metrics = {
            'portfolio_heat': round(portfolio_heat, 2),
            'var_95': round(var_95, 2),
            'var_99': round(var_99, 2),
            'leverage_ratio': round(leverage_ratio, 2),
            'num_positions': len(position_values),
            'largest_position_pct': round(largest_position_pct, 2),
            'total_exposure': round(total_exposure, 2),
            'portfolio_value': round(portfolio_value, 2)
        }

        # Cache metrics for performance
        self.risk_metrics_cache = metrics
        self.last_metrics_update = self.algorithm.Time

        return metrics

    def halt_trading(self, reason: str = "Manual halt"):
        """
        Disable trading (emergency stop capability).

        Args:
            reason: Reason for halting trading (logged)

        This sets the trading_enabled flag to False, preventing all new
        position entries. Existing positions can still be closed.
        """
        self.trading_enabled = False
        self.algorithm.Error(f"🛑 TRADING HALTED: {reason}")
        self.algorithm.Log(
            "Trading is now disabled. Call resume_trading() to re-enable."
        )

    def resume_trading(self):
        """
        Re-enable trading after manual halt.

        Requires manual intervention to resume trading after a halt.
        This is a safety feature to prevent automatic restart after issues.
        """
        self.trading_enabled = True
        self.algorithm.Log("✓ Trading resumed (manual override)")

    def reset_daily_starting_equity(self):
        """
        Reset daily starting equity (call at market open).

        Should be called at the start of each trading day to reset
        the baseline for daily loss limit calculations.
        """
        self.daily_starting_equity = self.algorithm.Portfolio.TotalPortfolioValue
        self.algorithm.Debug(
            f"Daily starting equity reset: ${self.daily_starting_equity:,.2f}"
        )

    def get_status(self) -> Dict:
        """
        Get current risk manager status summary.

        Returns:
            Dict: Status summary including:
                - trading_enabled: Whether trading is enabled
                - daily_starting_equity: Starting equity for the day
                - current_equity: Current portfolio value
                - daily_pnl_pct: Daily P&L as percentage
                - loss_limit_remaining_pct: How much loss before hitting limit
                - metrics: Current risk metrics (if enabled)
        """
        current_equity = self.algorithm.Portfolio.TotalPortfolioValue
        daily_pnl = current_equity - self.daily_starting_equity
        daily_pnl_pct = (daily_pnl / self.daily_starting_equity) * 100 \
                        if self.daily_starting_equity > 0 else 0

        loss_limit_remaining_pct = self.daily_loss_limit_pct + daily_pnl_pct

        status = {
            'trading_enabled': self.trading_enabled,
            'daily_starting_equity': round(self.daily_starting_equity, 2),
            'current_equity': round(current_equity, 2),
            'daily_pnl_pct': round(daily_pnl_pct, 2),
            'loss_limit_remaining_pct': round(loss_limit_remaining_pct, 2),
            'metrics': self.risk_metrics_cache
        }

        return status
