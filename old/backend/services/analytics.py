# Analytics service for portfolio ranking and performance metrics (Epic 25 Story 7)

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from datetime import datetime, timedelta
import statistics
import math

from backend.models.backtest import Backtest
from backend.utils.database import get_db_session


class AnalyticsService:
    """Service for computing portfolio-level analytics and strategy rankings"""

    def __init__(self):
        """Initialize analytics service"""
        pass

    def get_portfolio_analytics(
        self,
        strategy_filter: Optional[str] = None,
        symbol_filter: Optional[str] = None,
        days_back: int = 90,
        min_completed_backtests: int = 1,
    ) -> Dict[str, Any]:
        """
        Compute portfolio-level analytics across completed backtests

        Args:
            strategy_filter: Optional strategy name filter
            symbol_filter: Optional symbol filter
            days_back: Number of days to look back for backtests
            min_completed_backtests: Minimum number of completed backtests required

        Returns:
            Dictionary with portfolio analytics
        """
        with get_db_session() as session:
            # Build query for completed backtests within time window
            query = session.query(Backtest).filter(
                Backtest.status == "completed",
                Backtest.completed_at >= datetime.now() - timedelta(days=days_back),
                Backtest.metrics.isnot(None),
            )

            if strategy_filter:
                query = query.filter(
                    Backtest.strategy_name.ilike(f"%{strategy_filter}%")
                )

            if symbol_filter:
                # Filter by symbol in JSON array
                query = query.filter(
                    func.json_contains(Backtest.symbols, f'["{symbol_filter}"]')
                )

            backtests = query.all()

            if len(backtests) < min_completed_backtests:
                return {
                    "error": f"Insufficient data: found {len(backtests)} completed backtests, "
                    f"need at least {min_completed_backtests}",
                    "backtest_count": len(backtests),
                }

            # Extract metrics from all backtests
            strategy_metrics = []
            all_returns = []
            all_sharpe_ratios = []
            all_max_drawdowns = []
            all_win_rates = []

            for backtest in backtests:
                metrics = backtest.metrics or {}

                # Extract key metrics with fallbacks
                total_return = self._safe_float(
                    metrics.get("total_return", metrics.get("Total Net Profit", 0))
                )
                sharpe_ratio = self._safe_float(
                    metrics.get("sharpe_ratio", metrics.get("Sharpe Ratio", 0))
                )
                max_drawdown = self._safe_float(
                    metrics.get("max_drawdown", metrics.get("Drawdown", 0))
                )
                win_rate = self._safe_float(
                    metrics.get("win_rate", metrics.get("Win Rate", 0))
                )

                strategy_data = {
                    "strategy_name": backtest.strategy_name,
                    "symbols": backtest.symbols,
                    "total_return": total_return,
                    "sharpe_ratio": sharpe_ratio,
                    "max_drawdown": max_drawdown,
                    "win_rate": win_rate,
                    "trade_count": self._safe_int(
                        metrics.get("trade_count", metrics.get("Total Trades", 0))
                    ),
                    "completed_at": backtest.completed_at,
                    "mlflow_run_id": backtest.mlflow_run_id,
                }
                strategy_metrics.append(strategy_data)

                # Collect for portfolio aggregates
                all_returns.append(total_return)
                if sharpe_ratio != 0:  # Only include valid Sharpe ratios
                    all_sharpe_ratios.append(sharpe_ratio)
                if max_drawdown != 0:  # Only include valid drawdowns
                    all_max_drawdowns.append(max_drawdown)
                if win_rate != 0:  # Only include valid win rates
                    all_win_rates.append(win_rate)

            # Compute portfolio-level statistics
            portfolio_stats = self._compute_portfolio_statistics(
                all_returns, all_sharpe_ratios, all_max_drawdowns, all_win_rates
            )

            # Rank strategies by Sharpe ratio (descending)
            ranked_strategies = sorted(
                strategy_metrics, key=lambda x: x["sharpe_ratio"], reverse=True
            )

            return {
                "portfolio_statistics": portfolio_stats,
                "strategy_rankings": ranked_strategies,
                "backtest_count": len(backtests),
                "time_window_days": days_back,
                "filters_applied": {
                    "strategy": strategy_filter,
                    "symbol": symbol_filter,
                },
                "generated_at": datetime.now(),
            }

    def _compute_portfolio_statistics(
        self,
        returns: List[float],
        sharpe_ratios: List[float],
        max_drawdowns: List[float],
        win_rates: List[float],
    ) -> Dict[str, Any]:
        """Compute aggregate portfolio statistics"""

        if not returns:
            return {"error": "No return data available"}

        # Basic statistics
        avg_return = statistics.mean(returns) if returns else 0
        median_return = statistics.median(returns) if returns else 0
        best_return = max(returns) if returns else 0
        worst_return = min(returns) if returns else 0

        # Risk metrics
        portfolio_volatility = statistics.stdev(returns) if len(returns) > 1 else 0

        # Sharpe ratio statistics
        avg_sharpe = statistics.mean(sharpe_ratios) if sharpe_ratios else 0
        best_sharpe = max(sharpe_ratios) if sharpe_ratios else 0

        # Drawdown statistics
        avg_max_drawdown = statistics.mean(max_drawdowns) if max_drawdowns else 0
        worst_drawdown = max(max_drawdowns) if max_drawdowns else 0  # Most negative

        # Win rate statistics
        avg_win_rate = statistics.mean(win_rates) if win_rates else 0
        best_win_rate = max(win_rates) if win_rates else 0

        # Performance distribution
        positive_returns = len([r for r in returns if r > 0])
        win_rate_pct = (positive_returns / len(returns)) * 100 if returns else 0

        return {
            "average_return": round(avg_return, 4),
            "median_return": round(median_return, 4),
            "best_return": round(best_return, 4),
            "worst_return": round(worst_return, 4),
            "portfolio_volatility": round(portfolio_volatility, 4),
            "average_sharpe_ratio": round(avg_sharpe, 4),
            "best_sharpe_ratio": round(best_sharpe, 4),
            "average_max_drawdown": round(avg_max_drawdown, 4),
            "worst_max_drawdown": round(worst_drawdown, 4),
            "average_win_rate": round(avg_win_rate, 4),
            "best_win_rate": round(best_win_rate, 4),
            "portfolio_win_rate": round(win_rate_pct, 2),
            "total_strategies_analyzed": len(returns),
        }

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        """Safely convert value to float"""
        try:
            if isinstance(value, str):
                # Remove % sign if present
                value = value.replace("%", "").replace(",", "")
            return float(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        """Safely convert value to int"""
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default


# Global service instance
_analytics_service = None


def get_analytics_service() -> AnalyticsService:
    """Get or create analytics service instance"""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AnalyticsService()
    return _analytics_service
