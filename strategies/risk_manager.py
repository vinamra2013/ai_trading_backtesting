#!/usr/bin/env python3
"""
Risk Management Framework for Backtrader Strategies
Epic 13: US-13.3 - Risk Management Framework

Provides comprehensive risk controls for trading strategies:
- Position size limits (max shares, max dollar value, max % of portfolio)
- Loss limits (daily loss, total drawdown)
- Concentration limits (max % in single position)
- Leverage limits
- Risk violation logging and alerts

All strategies should integrate RiskManager to ensure safety.
"""

import logging
from datetime import datetime, date
from typing import Dict, Tuple, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RiskManager:
    """
    Risk management for Backtrader strategies.

    Enforces configurable risk limits and logs violations.
    Integrates with BaseStrategy to protect capital.
    """

    def __init__(self, strategy, config: Optional[Dict] = None):
        """
        Initialize risk manager.

        Args:
            strategy: Backtrader strategy instance
            config: Optional configuration dict overriding defaults
        """
        self.strategy = strategy
        self.config = config or {}

        # Risk limits (configurable)
        self.daily_loss_limit = self.config.get('daily_loss_limit', 0.02)        # 2% max daily loss
        self.max_drawdown = self.config.get('max_drawdown', 0.20)                 # 20% max drawdown
        self.max_position_pct = self.config.get('max_position_pct', 0.25)        # 25% max single position
        self.max_leverage = self.config.get('max_leverage', 2.0)                  # 2x max leverage
        self.max_positions = self.config.get('max_positions', 10)                 # Max open positions
        self.max_position_shares = self.config.get('max_position_shares', 10000) # Max shares per position

        # Tracking variables
        self.initial_portfolio_value = strategy.broker.getvalue()
        self.peak_value = self.initial_portfolio_value
        self.daily_start_value = self.initial_portfolio_value
        self.current_date = None

        # Risk event log
        self.risk_events = []

        logger.info(f"RiskManager initialized with initial value: ${self.initial_portfolio_value:,.2f}")
        logger.info(f"  Daily loss limit: {self.daily_loss_limit*100}%")
        logger.info(f"  Max drawdown: {self.max_drawdown*100}%")
        logger.info(f"  Max position: {self.max_position_pct*100}%")
        logger.info(f"  Max leverage: {self.max_leverage}x")

    # ===================================================================
    # Position Size Checks
    # ===================================================================

    def check_position_size(self, size: int, price: float, data=None) -> Tuple[bool, str]:
        """
        Check if proposed position size violates limits.

        Checks:
        - Position value vs portfolio percentage limit
        - Absolute share count limit
        - Leverage limit

        Args:
            size: Number of shares to trade
            price: Price per share
            data: Optional data feed for multi-symbol strategies

        Returns:
            (allowed, message) tuple
        """
        portfolio_value = self.strategy.broker.getvalue()
        position_value = abs(size) * price

        # Check 1: Position percentage limit
        position_pct = position_value / portfolio_value if portfolio_value > 0 else 0

        if position_pct > self.max_position_pct:
            msg = f"Position size ${position_value:,.2f} ({position_pct*100:.1f}%) exceeds {self.max_position_pct*100}% limit"
            self._log_risk_event('POSITION_SIZE_EXCEEDED', msg, 'WARNING')
            return False, msg

        # Check 2: Absolute share count limit
        if abs(size) > self.max_position_shares:
            msg = f"Position size {abs(size)} shares exceeds {self.max_position_shares} limit"
            self._log_risk_event('SHARE_COUNT_EXCEEDED', msg, 'WARNING')
            return False, msg

        # Check 3: Leverage limit
        current_leverage = self._calculate_leverage()
        new_leverage = (self._get_total_position_value() + position_value) / portfolio_value

        if new_leverage > self.max_leverage:
            msg = f"Leverage {new_leverage:.2f}x would exceed {self.max_leverage}x limit"
            self._log_risk_event('LEVERAGE_EXCEEDED', msg, 'WARNING')
            return False, msg

        return True, "OK"

    def check_concentration(self, size: int, price: float, data=None) -> Tuple[bool, str]:
        """
        Check if position would create excessive concentration.

        Args:
            size: Number of shares
            price: Price per share
            data: Data feed

        Returns:
            (allowed, message) tuple
        """
        portfolio_value = self.strategy.broker.getvalue()
        position_value = abs(size) * price

        # Get current position if exists
        if data:
            current_position = self.strategy.getposition(data)
            current_value = abs(current_position.size * price) if current_position else 0
        else:
            current_value = 0

        # Calculate new total position value
        new_position_value = current_value + position_value
        concentration = new_position_value / portfolio_value if portfolio_value > 0 else 0

        if concentration > self.max_position_pct:
            msg = f"Concentration {concentration*100:.1f}% exceeds {self.max_position_pct*100}% limit"
            self._log_risk_event('CONCENTRATION_EXCEEDED', msg, 'WARNING')
            return False, msg

        return True, "OK"

    def check_max_positions(self) -> Tuple[bool, str]:
        """
        Check if we've reached maximum number of open positions.

        Returns:
            (allowed, message) tuple
        """
        open_positions = self._count_open_positions()

        if open_positions >= self.max_positions:
            msg = f"Already at maximum {self.max_positions} open positions"
            self._log_risk_event('MAX_POSITIONS_REACHED', msg, 'INFO')
            return False, msg

        return True, "OK"

    # ===================================================================
    # Loss Limit Checks
    # ===================================================================

    def check_daily_loss(self) -> Tuple[bool, str]:
        """
        Check if daily loss limit has been exceeded.

        Returns:
            (allowed, message) tuple
        """
        current_value = self.strategy.broker.getvalue()

        # Reset daily tracking if new day
        self._check_new_day()

        # Calculate daily loss
        daily_loss = (self.daily_start_value - current_value) / self.daily_start_value if self.daily_start_value > 0 else 0

        if daily_loss > self.daily_loss_limit:
            msg = f"Daily loss {daily_loss*100:.2f}% exceeds {self.daily_loss_limit*100}% limit"
            self._log_risk_event('DAILY_LOSS_EXCEEDED', msg, 'CRITICAL')
            return False, msg

        return True, "OK"

    def check_drawdown(self) -> Tuple[bool, str]:
        """
        Check if maximum drawdown has been exceeded.

        Returns:
            (allowed, message) tuple
        """
        current_value = self.strategy.broker.getvalue()

        # Update peak
        if current_value > self.peak_value:
            self.peak_value = current_value

        # Calculate drawdown
        drawdown = (self.peak_value - current_value) / self.peak_value if self.peak_value > 0 else 0

        if drawdown > self.max_drawdown:
            msg = f"Drawdown {drawdown*100:.2f}% exceeds {self.max_drawdown*100}% limit"
            self._log_risk_event('MAX_DRAWDOWN_EXCEEDED', msg, 'CRITICAL')
            return False, msg

        return True, "OK"

    # ===================================================================
    # Master Risk Check
    # ===================================================================

    def can_trade(self, size: int, price: float, data=None, check_all: bool = True) -> Tuple[bool, str]:
        """
        Master risk check - validates all risk constraints.

        Args:
            size: Number of shares to trade
            price: Price per share
            data: Optional data feed
            check_all: If True, run all checks (position + loss limits)

        Returns:
            (allowed, message) tuple - False if any check fails
        """
        # Position size checks
        allowed, msg = self.check_position_size(size, price, data)
        if not allowed:
            return False, msg

        allowed, msg = self.check_concentration(size, price, data)
        if not allowed:
            return False, msg

        # Only for new positions
        if not self.strategy.is_invested(data):
            allowed, msg = self.check_max_positions()
            if not allowed:
                return False, msg

        # Loss limit checks (if enabled)
        if check_all:
            allowed, msg = self.check_daily_loss()
            if not allowed:
                return False, msg

            allowed, msg = self.check_drawdown()
            if not allowed:
                return False, msg

        return True, "OK"

    # ===================================================================
    # Daily Reset
    # ===================================================================

    def reset_daily(self):
        """Reset daily tracking variables. Call at start of new day."""
        self.daily_start_value = self.strategy.broker.getvalue()
        logger.info(f"Daily reset: Starting value ${self.daily_start_value:,.2f}")

    def _check_new_day(self):
        """Auto-reset daily tracking if new day detected."""
        if hasattr(self.strategy, 'datas') and len(self.strategy.datas) > 0:
            current_date = self.strategy.datas[0].datetime.date(0)

            if self.current_date is None:
                self.current_date = current_date
                self.daily_start_value = self.strategy.broker.getvalue()

            elif current_date > self.current_date:
                self.current_date = current_date
                self.reset_daily()

    # ===================================================================
    # Helper Methods
    # ===================================================================

    def _calculate_leverage(self) -> float:
        """Calculate current portfolio leverage."""
        portfolio_value = self.strategy.broker.getvalue()
        total_position_value = self._get_total_position_value()

        return total_position_value / portfolio_value if portfolio_value > 0 else 0

    def _get_total_position_value(self) -> float:
        """Get total value of all open positions."""
        total = 0.0

        for data in self.strategy.datas:
            position = self.strategy.getposition(data)
            if position and position.size != 0:
                total += abs(position.size * data.close[0])

        return total

    def _count_open_positions(self) -> int:
        """Count number of open positions."""
        count = 0

        for data in self.strategy.datas:
            position = self.strategy.getposition(data)
            if position and position.size != 0:
                count += 1

        return count

    def _log_risk_event(self, event_type: str, description: str, severity: str = 'INFO'):
        """
        Log risk management event.

        Args:
            event_type: Type of risk event
            description: Event description
            severity: INFO, WARNING, CRITICAL
        """
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'description': description,
            'severity': severity,
            'portfolio_value': self.strategy.broker.getvalue(),
        }

        self.risk_events.append(event)

        if severity == 'CRITICAL':
            logger.error(f"RISK EVENT [{severity}]: {event_type} - {description}")
        elif severity == 'WARNING':
            logger.warning(f"RISK EVENT [{severity}]: {event_type} - {description}")
        else:
            logger.info(f"RISK EVENT [{severity}]: {event_type} - {description}")

    # ===================================================================
    # Reporting
    # ===================================================================

    def get_risk_summary(self) -> Dict:
        """
        Get summary of risk metrics.

        Returns:
            Dictionary with current risk metrics
        """
        current_value = self.strategy.broker.getvalue()
        drawdown = (self.peak_value - current_value) / self.peak_value if self.peak_value > 0 else 0
        daily_loss = (self.daily_start_value - current_value) / self.daily_start_value if self.daily_start_value > 0 else 0
        leverage = self._calculate_leverage()
        open_positions = self._count_open_positions()

        return {
            'portfolio_value': current_value,
            'initial_value': self.initial_portfolio_value,
            'peak_value': self.peak_value,
            'current_drawdown': drawdown,
            'daily_loss': daily_loss,
            'leverage': leverage,
            'open_positions': open_positions,
            'risk_events_count': len(self.risk_events),
            'limits': {
                'daily_loss_limit': self.daily_loss_limit,
                'max_drawdown': self.max_drawdown,
                'max_position_pct': self.max_position_pct,
                'max_leverage': self.max_leverage,
                'max_positions': self.max_positions,
            }
        }

    def get_risk_events(self, severity: Optional[str] = None) -> list:
        """
        Get risk event log.

        Args:
            severity: Filter by severity (INFO, WARNING, CRITICAL)

        Returns:
            List of risk events
        """
        if severity:
            return [e for e in self.risk_events if e['severity'] == severity]
        return self.risk_events


if __name__ == "__main__":
    print("RiskManager Framework - Ready for use")
    print("\nUsage:")
    print("  from strategies.risk_manager import RiskManager")
    print("  class MyStrategy(BaseStrategy):")
    print("      def __init__(self):")
    print("          super().__init__()")
    print("          self.risk_manager = RiskManager(self)")
    print("      def next(self):")
    print("          size = self.calculate_position_size(price)")
    print("          can_trade, msg = self.risk_manager.can_trade(size, price)")
    print("          if can_trade:")
    print("              self.buy(size=size)")
