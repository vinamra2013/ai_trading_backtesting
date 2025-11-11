#!/usr/bin/env python3
"""
P&L Calculator Utility - Profit and Loss calculations for trading positions.

US-5.2: Live Trading Engine - P&L tracking and calculations
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Represents a trading position."""
    symbol: str
    quantity: int  # Positive for long, negative for short
    entry_price: float
    current_price: Optional[float] = None


@dataclass
class Trade:
    """Represents a completed trade."""
    symbol: str
    quantity: int
    price: float
    commission: float = 0.0
    timestamp: Optional[str] = None


class PnLCalculator:
    """
    Profit and Loss calculator for trading positions.

    Handles P&L calculations for both long and short positions,
    including commissions and fees.
    """

    def __init__(self, precision: int = 2):
        """
        Initialize PnLCalculator.

        Args:
            precision: Number of decimal places for rounding (default: 2)
        """
        self.precision = precision
        logger.info(f"PnLCalculator initialized with precision: {precision}")

    def _round(self, value: float) -> float:
        """
        Round value to configured precision.

        Args:
            value: Value to round

        Returns:
            Rounded value
        """
        decimal_value = Decimal(str(value))
        rounded = decimal_value.quantize(
            Decimal(10) ** -self.precision,
            rounding=ROUND_HALF_UP
        )
        return float(rounded)

    def calculate_position_pnl(
        self,
        position: Position,
        current_price: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate P&L for a single position.

        Args:
            position: Position object
            current_price: Current market price (overrides position.current_price)

        Returns:
            Dictionary with P&L details:
                - unrealized_pnl: Dollar P&L
                - unrealized_pnl_pct: Percentage P&L
                - cost_basis: Total cost basis
                - market_value: Current market value

        Raises:
            ValueError: If current price is not available
        """
        price = current_price if current_price is not None else position.current_price

        if price is None:
            raise ValueError(f"No current price available for {position.symbol}")

        # Calculate cost basis
        cost_basis = abs(position.quantity) * position.entry_price

        # Calculate market value
        market_value = abs(position.quantity) * price

        # Calculate P&L based on position type
        if position.quantity > 0:  # Long position
            unrealized_pnl = (price - position.entry_price) * position.quantity
        elif position.quantity < 0:  # Short position
            unrealized_pnl = (position.entry_price - price) * abs(position.quantity)
        else:  # No position
            unrealized_pnl = 0.0

        # Calculate percentage P&L
        if cost_basis > 0:
            unrealized_pnl_pct = (unrealized_pnl / cost_basis) * 100
        else:
            unrealized_pnl_pct = 0.0

        result = {
            'unrealized_pnl': self._round(unrealized_pnl),
            'unrealized_pnl_pct': self._round(unrealized_pnl_pct),
            'cost_basis': self._round(cost_basis),
            'market_value': self._round(market_value)
        }

        logger.debug(f"Position P&L for {position.symbol}: {result}")
        return result

    def calculate_unrealized_pnl(
        self,
        positions: List[Position],
        current_prices: Dict[str, float]
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate unrealized P&L for all positions.

        Args:
            positions: List of Position objects
            current_prices: Dictionary mapping symbols to current prices

        Returns:
            Dictionary mapping symbols to P&L details
        """
        results = {}

        for position in positions:
            if position.symbol not in current_prices:
                logger.warning(f"No price available for {position.symbol}, skipping")
                continue

            try:
                pnl = self.calculate_position_pnl(
                    position,
                    current_prices[position.symbol]
                )
                results[position.symbol] = pnl
            except Exception as e:
                logger.error(f"Error calculating P&L for {position.symbol}: {e}")
                continue

        # Calculate total P&L
        total_unrealized_pnl = sum(p['unrealized_pnl'] for p in results.values())
        total_cost_basis = sum(p['cost_basis'] for p in results.values())
        total_market_value = sum(p['market_value'] for p in results.values())

        if total_cost_basis > 0:
            total_pnl_pct = (total_unrealized_pnl / total_cost_basis) * 100
        else:
            total_pnl_pct = 0.0

        results['_total'] = {
            'unrealized_pnl': self._round(total_unrealized_pnl),
            'unrealized_pnl_pct': self._round(total_pnl_pct),
            'cost_basis': self._round(total_cost_basis),
            'market_value': self._round(total_market_value)
        }

        logger.info(f"Calculated P&L for {len(positions)} positions: "
                   f"Total P&L = ${total_unrealized_pnl:,.2f}")

        return results

    def calculate_realized_pnl(
        self,
        entry_price: float,
        exit_price: float,
        quantity: int,
        commission: float = 0.0,
        is_short: bool = False
    ) -> Dict[str, float]:
        """
        Calculate realized P&L for a completed trade.

        Args:
            entry_price: Entry price per share
            exit_price: Exit price per share
            quantity: Number of shares (positive)
            commission: Total commission and fees
            is_short: True if short position, False if long

        Returns:
            Dictionary with realized P&L details:
                - gross_pnl: P&L before commissions
                - net_pnl: P&L after commissions
                - commission: Total commission paid
                - gross_pnl_pct: Percentage P&L before commissions
                - net_pnl_pct: Percentage P&L after commissions
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        # Calculate gross P&L
        if is_short:
            gross_pnl = (entry_price - exit_price) * quantity
        else:
            gross_pnl = (exit_price - entry_price) * quantity

        # Calculate net P&L
        net_pnl = gross_pnl - commission

        # Calculate cost basis
        cost_basis = quantity * entry_price

        # Calculate percentages
        if cost_basis > 0:
            gross_pnl_pct = (gross_pnl / cost_basis) * 100
            net_pnl_pct = (net_pnl / cost_basis) * 100
        else:
            gross_pnl_pct = 0.0
            net_pnl_pct = 0.0

        result = {
            'gross_pnl': self._round(gross_pnl),
            'net_pnl': self._round(net_pnl),
            'commission': self._round(commission),
            'gross_pnl_pct': self._round(gross_pnl_pct),
            'net_pnl_pct': self._round(net_pnl_pct)
        }

        logger.debug(f"Realized P&L: {result}")
        return result

    def calculate_daily_pnl(
        self,
        starting_equity: float,
        current_equity: float
    ) -> Dict[str, float]:
        """
        Calculate daily P&L.

        Args:
            starting_equity: Portfolio equity at start of day
            current_equity: Current portfolio equity

        Returns:
            Dictionary with daily P&L:
                - daily_pnl: Dollar P&L for the day
                - daily_pnl_pct: Percentage P&L for the day
        """
        daily_pnl = current_equity - starting_equity

        if starting_equity > 0:
            daily_pnl_pct = (daily_pnl / starting_equity) * 100
        else:
            daily_pnl_pct = 0.0

        result = {
            'daily_pnl': self._round(daily_pnl),
            'daily_pnl_pct': self._round(daily_pnl_pct)
        }

        logger.info(f"Daily P&L: ${daily_pnl:,.2f} ({daily_pnl_pct:.2f}%)")
        return result

    def calculate_pnl_percentage(
        self,
        pnl: float,
        cost_basis: float
    ) -> float:
        """
        Calculate P&L as percentage of cost basis.

        Args:
            pnl: Dollar P&L
            cost_basis: Cost basis for the position/trade

        Returns:
            P&L percentage
        """
        if cost_basis <= 0:
            logger.warning(f"Invalid cost basis: {cost_basis}, returning 0%")
            return 0.0

        pnl_pct = (pnl / cost_basis) * 100
        return self._round(pnl_pct)

    def calculate_cost_basis(self, trades: List[Trade]) -> Dict[str, float]:
        """
        Calculate average cost basis from multiple trades.

        Handles both long and short positions with proper averaging.

        Args:
            trades: List of Trade objects

        Returns:
            Dictionary with cost basis details:
                - total_shares: Total shares (signed)
                - average_price: Volume-weighted average price
                - total_cost: Total cost including commissions
                - total_commission: Total commission paid
        """
        if not trades:
            return {
                'total_shares': 0,
                'average_price': 0.0,
                'total_cost': 0.0,
                'total_commission': 0.0
            }

        total_shares = 0
        weighted_price_sum = 0.0
        total_commission = 0.0

        for trade in trades:
            total_shares += trade.quantity
            weighted_price_sum += trade.quantity * trade.price
            total_commission += trade.commission

        # Calculate average price
        if total_shares != 0:
            average_price = abs(weighted_price_sum / total_shares)
        else:
            average_price = 0.0

        # Calculate total cost (including commissions)
        total_cost = abs(weighted_price_sum) + total_commission

        result = {
            'total_shares': total_shares,
            'average_price': self._round(average_price),
            'total_cost': self._round(total_cost),
            'total_commission': self._round(total_commission)
        }

        logger.debug(f"Cost basis calculated: {result}")
        return result

    def calculate_portfolio_metrics(
        self,
        positions: List[Position],
        current_prices: Dict[str, float],
        cash: float
    ) -> Dict[str, float]:
        """
        Calculate comprehensive portfolio metrics.

        Args:
            positions: List of Position objects
            current_prices: Dictionary mapping symbols to current prices
            cash: Available cash

        Returns:
            Dictionary with portfolio metrics:
                - total_equity: Total portfolio value
                - total_market_value: Total position market value
                - cash: Available cash
                - unrealized_pnl: Total unrealized P&L
                - unrealized_pnl_pct: Portfolio P&L percentage
                - long_exposure: Market value of long positions
                - short_exposure: Market value of short positions
                - net_exposure: Net market exposure
                - gross_exposure: Gross market exposure
        """
        pnl_results = self.calculate_unrealized_pnl(positions, current_prices)
        total_pnl = pnl_results.get('_total', {})

        total_market_value = total_pnl.get('market_value', 0.0)
        unrealized_pnl = total_pnl.get('unrealized_pnl', 0.0)
        total_cost_basis = total_pnl.get('cost_basis', 0.0)

        # Calculate exposures
        long_exposure = 0.0
        short_exposure = 0.0

        for position in positions:
            if position.symbol not in current_prices:
                continue

            market_value = abs(position.quantity) * current_prices[position.symbol]

            if position.quantity > 0:
                long_exposure += market_value
            elif position.quantity < 0:
                short_exposure += market_value

        net_exposure = long_exposure - short_exposure
        gross_exposure = long_exposure + short_exposure

        total_equity = cash + total_market_value

        # Calculate portfolio P&L percentage
        if total_cost_basis > 0:
            portfolio_pnl_pct = (unrealized_pnl / total_cost_basis) * 100
        else:
            portfolio_pnl_pct = 0.0

        result = {
            'total_equity': self._round(total_equity),
            'total_market_value': self._round(total_market_value),
            'cash': self._round(cash),
            'unrealized_pnl': self._round(unrealized_pnl),
            'unrealized_pnl_pct': self._round(portfolio_pnl_pct),
            'long_exposure': self._round(long_exposure),
            'short_exposure': self._round(short_exposure),
            'net_exposure': self._round(net_exposure),
            'gross_exposure': self._round(gross_exposure)
        }

        logger.info(f"Portfolio metrics: Equity=${total_equity:,.2f}, "
                   f"P&L=${unrealized_pnl:,.2f} ({portfolio_pnl_pct:.2f}%)")

        return result
