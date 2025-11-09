# Pydantic schemas for analytics API requests and responses (Epic 25 Story 7)

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class PortfolioAnalyticsRequest(BaseModel):
    """Request model for portfolio analytics"""

    strategy_filter: Optional[str] = Field(
        None, description="Filter by strategy name (partial match)"
    )
    symbol_filter: Optional[str] = Field(None, description="Filter by symbol")
    days_back: int = Field(90, ge=1, le=365, description="Number of days to look back")
    min_completed_backtests: int = Field(
        1, ge=1, description="Minimum completed backtests required"
    )


class PortfolioStatistics(BaseModel):
    """Portfolio-level aggregate statistics"""

    average_return: float = Field(
        ..., description="Average total return across strategies"
    )
    median_return: float = Field(
        ..., description="Median total return across strategies"
    )
    best_return: float = Field(..., description="Best total return")
    worst_return: float = Field(..., description="Worst total return")
    portfolio_volatility: float = Field(
        ..., description="Portfolio return volatility (standard deviation)"
    )
    average_sharpe_ratio: float = Field(..., description="Average Sharpe ratio")
    best_sharpe_ratio: float = Field(..., description="Best Sharpe ratio")
    average_max_drawdown: float = Field(..., description="Average maximum drawdown")
    worst_max_drawdown: float = Field(..., description="Worst maximum drawdown")
    average_win_rate: float = Field(..., description="Average win rate")
    best_win_rate: float = Field(..., description="Best win rate")
    portfolio_win_rate: float = Field(
        ..., description="Portfolio win rate (strategies with positive returns)"
    )
    total_strategies_analyzed: int = Field(
        ..., description="Total number of strategies analyzed"
    )


class StrategyRanking(BaseModel):
    """Individual strategy performance data"""

    strategy_name: str = Field(..., description="Strategy name")
    symbols: List[str] = Field(..., description="Symbols tested")
    total_return: float = Field(..., description="Total return percentage")
    sharpe_ratio: float = Field(..., description="Sharpe ratio")
    max_drawdown: float = Field(..., description="Maximum drawdown percentage")
    win_rate: float = Field(..., description="Win rate percentage")
    trade_count: int = Field(..., description="Total number of trades")
    completed_at: datetime = Field(..., description="When backtest completed")
    mlflow_run_id: Optional[str] = Field(None, description="MLflow run ID")


class PortfolioAnalyticsResponse(BaseModel):
    """Response model for portfolio analytics"""

    portfolio_statistics: PortfolioStatistics = Field(
        ..., description="Aggregate portfolio statistics"
    )
    strategy_rankings: List[StrategyRanking] = Field(
        ..., description="Ranked list of strategies by Sharpe ratio"
    )
    backtest_count: int = Field(..., description="Number of backtests analyzed")
    time_window_days: int = Field(..., description="Time window in days")
    filters_applied: Dict[str, Any] = Field(..., description="Applied filters")
    generated_at: datetime = Field(..., description="When analytics were generated")


class PortfolioAnalyticsError(BaseModel):
    """Error response for portfolio analytics"""

    error: str = Field(..., description="Error message")
    backtest_count: Optional[int] = Field(
        None, description="Number of backtests found (if applicable)"
    )
