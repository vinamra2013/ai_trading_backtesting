# Analytics API router for portfolio ranking and performance metrics (Epic 25 Story 7)

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.schemas.analytics import (
    PortfolioAnalyticsRequest,
    PortfolioAnalyticsResponse,
    PortfolioAnalyticsError,
)
from backend.services.analytics import get_analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/portfolio", response_model=PortfolioAnalyticsResponse)
async def get_portfolio_analytics(
    strategy_filter: Optional[str] = Query(
        None, description="Filter by strategy name (partial match)"
    ),
    symbol_filter: Optional[str] = Query(None, description="Filter by symbol"),
    days_back: int = Query(90, ge=1, le=365, description="Number of days to look back"),
    min_completed_backtests: int = Query(
        1, ge=1, description="Minimum completed backtests required"
    ),
):
    """
    Get portfolio-level analytics and strategy rankings

    Computes aggregate statistics across completed backtests including Sharpe ratios,
    returns, drawdowns, and win rates. Ranks strategies by performance metrics.

    Optional filters allow analysis of specific strategies or symbols.
    """
    try:
        service = get_analytics_service()
        result = service.get_portfolio_analytics(
            strategy_filter=strategy_filter,
            symbol_filter=symbol_filter,
            days_back=days_back,
            min_completed_backtests=min_completed_backtests,
        )

        # Check if result contains an error
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return PortfolioAnalyticsResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to compute portfolio analytics: {str(e)}"
        )
