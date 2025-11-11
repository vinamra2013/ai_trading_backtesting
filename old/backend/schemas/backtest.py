# Pydantic schemas for backtest API requests and responses (Epic 25 Stories 3 & 4)

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class BacktestRequest(BaseModel):
    """Request model for triggering a new backtest"""

    strategy: str = Field(..., description="Strategy name or file path")
    symbols: List[str] = Field(..., description="List of symbols to backtest")
    parameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Strategy parameters"
    )
    timeframe: str = Field(default="1d", description="Timeframe (1m, 5m, 1h, 1d, etc.)")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")


class BacktestResponse(BaseModel):
    """Response model for backtest submission"""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Current job status")
    message: str = Field(..., description="Status message")
    created_at: datetime = Field(..., description="Job creation timestamp")


class BacktestStatus(BaseModel):
    """Backtest status information"""

    id: int
    strategy_name: str
    symbols: List[str]
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    mlflow_run_id: Optional[str] = None


class BacktestListResponse(BaseModel):
    """Paginated response for backtest list"""

    backtests: List[BacktestStatus]
    total: int
    page: int
    page_size: int
    total_pages: int


class BacktestDetailResponse(BaseModel):
    """Detailed backtest result response"""

    id: int
    strategy_name: str
    symbols: List[str]
    parameters: Dict[str, Any]
    timeframe: str
    status: str
    metrics: Optional[Dict[str, Any]] = None
    mlflow_run_id: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class BacktestFilter(BaseModel):
    """Filter parameters for backtest queries"""

    strategy: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
