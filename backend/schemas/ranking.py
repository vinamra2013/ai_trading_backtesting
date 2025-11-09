# Pydantic schemas for strategy ranking API (Epic 26 Story 2)

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime


class RankingRequest(BaseModel):
    """Request model for triggering a strategy ranking analysis"""

    input_type: str = Field(
        ...,
        description="Input source type",
        examples=["csv", "database", "results_dir"],
    )
    input_source: Optional[str] = Field(
        None,
        description="Input source path or query parameters",
        examples=["results/backtests/latest.csv", "results/backtests/"],
    )
    criteria_weights: Optional[Dict[str, float]] = Field(
        default_factory=lambda: {
            "sharpe_ratio": 40.0,
            "consistency": 20.0,
            "drawdown_control": 20.0,
            "trade_frequency": 10.0,
            "capital_efficiency": 10.0,
        },
        description="Scoring weights for ranking criteria (must sum to 100)",
    )
    ranking_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional ranking configuration",
        examples=[
            {
                "consistency": {"window_days": 30, "min_periods": 10},
                "drawdown_control": {"max_drawdown_weight": 1.0},
                "trade_frequency": {"optimal_trades_per_month": 20},
            }
        ],
    )

    @validator("input_type")
    def validate_input_type(cls, v):
        valid_types = ["csv", "database", "results_dir"]
        if v not in valid_types:
            raise ValueError(f"Input type must be one of: {', '.join(valid_types)}")
        return v

    @validator("criteria_weights")
    def validate_weights(cls, v):
        if v:
            total = sum(v.values())
            if abs(total - 100.0) > 0.1:  # Allow small floating point errors
                raise ValueError(f"Criteria weights must sum to 100, got {total}")
        return v


class RankingResponse(BaseModel):
    """Response model for ranking job submission"""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Current job status")
    message: str = Field(..., description="Status message")
    created_at: datetime = Field(..., description="Job creation timestamp")
    estimated_completion: Optional[datetime] = Field(
        None, description="Estimated completion time"
    )


class RankingStatus(BaseModel):
    """Ranking job status information"""

    job_id: str
    input_type: str
    input_source: Optional[str]
    status: str
    progress: float = Field(..., ge=0.0, le=100.0)
    total_strategies: int = 0
    ranked_strategies: int = 0
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class RankedStrategy(BaseModel):
    """Individual ranked strategy information"""

    strategy_name: str
    symbol: Optional[str] = None

    # Performance metrics
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    total_trades: Optional[int] = None
    profit_factor: Optional[float] = None

    # Individual scores (0-100 scale)
    sharpe_score: Optional[float] = None
    consistency_score: Optional[float] = None
    drawdown_score: Optional[float] = None
    frequency_score: Optional[float] = None
    efficiency_score: Optional[float] = None

    # Composite score and ranking
    composite_score: float
    rank: int

    metadata: Optional[Dict[str, Any]] = None


class RankingResult(BaseModel):
    """Ranking results with summary"""

    job_id: str
    input_type: str
    input_source: Optional[str]
    strategies: List[RankedStrategy]
    total_strategies: int
    criteria_weights: Dict[str, float]
    summary: Dict[str, Any]
    completed_at: datetime
    execution_time_seconds: float


class RankingListResponse(BaseModel):
    """Paginated response for ranking job list"""

    jobs: List[RankingStatus]
    total: int
    page: int
    page_size: int
    total_pages: int


class RankingFilter(BaseModel):
    """Filter parameters for ranking job queries"""

    input_type: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)


class RankingSummary(BaseModel):
    """Ranking summary statistics"""

    total_strategies_ranked: int
    unique_strategies: int
    unique_symbols: int
    top_strategy: Dict[str, Any]
    score_distribution: Dict[str, float]
    scoring_weights: Dict[str, float]
