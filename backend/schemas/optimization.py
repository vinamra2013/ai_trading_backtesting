"""
V2 Parallel Optimization System - Pydantic Schemas
API request/response models for optimization and backtest endpoints.
"""

from pydantic import BaseModel, Field, validator, ConfigDict
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """Job status enumeration."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BatchStatus(str, Enum):
    """Batch status enumeration."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Strategy Schemas
class StrategyBase(BaseModel):
    """Base strategy model."""
    name: str = Field(..., description="Strategy name")
    category: str = Field(..., description="Strategy category (mean_reversion, momentum, etc.)")
    asset_class: str = Field(..., description="Asset class (etf, equity, futures, etc.)")
    lean_project_path: str = Field(..., description="LEAN project directory path")
    description: Optional[str] = Field(None, description="Strategy description")
    status: str = Field("planned", description="Strategy status")
    priority: int = Field(0, description="Strategy priority")


class StrategyResponse(StrategyBase):
    """Strategy response model."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Optimization Schemas
class ParameterRange(BaseModel):
    """Parameter range specification."""
    start: Union[int, float] = Field(..., description="Start value")
    end: Union[int, float] = Field(..., description="End value")
    step: Union[int, float] = Field(..., description="Step size")

    @validator('step')
    def step_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('step must be positive')
        return v


class OptimizationConfig(BaseModel):
    """Optimization configuration from YAML file."""
    strategy: Dict[str, Any] = Field(..., description="Strategy configuration")
    parameters: Dict[str, ParameterRange] = Field(..., description="Parameter ranges")
    symbols: List[str] = Field(default_factory=lambda: ["SPY"], description="Symbols to test")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")

    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')


class OptimizationRequest(BaseModel):
    """Request to start parallel optimization."""
    config_path: str = Field(..., description="Path to optimization config YAML file")
    max_concurrent: int = Field(4, ge=1, le=8, description="Maximum concurrent jobs")
    symbols: Optional[List[str]] = Field(None, description="Override symbols from config")


class OptimizationResponse(BaseModel):
    """Response from optimization start request."""
    batch_id: str = Field(..., description="Unique batch identifier")
    total_jobs: int = Field(..., description="Total number of jobs created")
    message: str = Field(..., description="Status message")


class BatchProgress(BaseModel):
    """Batch progress information."""
    batch_id: str
    strategy_name: str
    total_jobs: int
    completed_jobs: int
    status: BatchStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    best_result: Optional[Dict[str, Any]] = None


class BatchStatusResponse(BaseModel):
    """Batch status response."""
    batch: BatchProgress
    jobs: List[Dict[str, Any]] = Field(..., description="Job status summaries")


class BatchResultsResponse(BaseModel):
    """Batch results response."""
    batch_id: str
    total_results: int
    passed_criteria: int
    best_result: Optional[Dict[str, Any]] = None
    results: List[Dict[str, Any]] = Field(..., description="All results with criteria evaluation")
    parameter_analysis: Dict[str, Any] = Field(..., description="Parameter performance analysis")


# Backtest Schemas
class BacktestRequest(BaseModel):
    """Request to run individual backtest."""
    strategy_name: str = Field(..., description="Strategy name")
    lean_project_path: str = Field(..., description="LEAN project path")
    parameters: Dict[str, Any] = Field(..., description="Strategy parameters")
    symbols: List[str] = Field(default_factory=lambda: ["SPY"], description="Symbols to test")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")

    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')


class BacktestResponse(BaseModel):
    """Response from backtest submission."""
    job_id: int = Field(..., description="Job ID")
    container_id: str = Field(..., description="Docker container ID")
    message: str = Field(..., description="Status message")


class JobStatusResponse(BaseModel):
    """Job status response."""
    job_id: int
    batch_id: Optional[str]
    strategy_name: str
    status: JobStatus
    container_id: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    result_path: Optional[str]


# Result Schemas
class BacktestResultResponse(BaseModel):
    """Backtest result response."""
    job_id: int
    batch_id: Optional[str]
    parameters: Dict[str, Any]
    metrics: Dict[str, Any]
    meets_criteria: bool
    rejection_reasons: Optional[List[str]] = None
    qc_backtest_id: Optional[str] = None
    created_at: datetime


class SuccessCriteriaResponse(BaseModel):
    """Success criteria response."""
    strategy_name: str
    min_trades: int
    min_sharpe: float
    max_drawdown: float
    min_win_rate: float
    max_fee_pct: float
    min_avg_win: float
    max_fee_per_trade: Optional[float] = None


# Error Schemas
class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


# Analytics Schemas
class PortfolioAnalytics(BaseModel):
    """Portfolio analytics response."""
    total_strategies: int = Field(..., description="Total number of strategies")
    strategies_tested: int = Field(..., description="Number of strategies tested")
    best_performing: Dict[str, Any] = Field(..., description="Best performing strategy details")
# Analytics Schemas
class PortfolioAnalytics(BaseModel):
    """Portfolio analytics response."""
    total_strategies: int = Field(..., description="Total number of strategies")
    strategies_tested: int = Field(..., description="Number of strategies tested")
    best_performing: Dict[str, Any] = Field(..., description="Best performing strategy details")
    strategy_rankings: List[Dict[str, Any]] = Field(..., description="Strategy rankings")
    parameter_insights: Dict[str, Any] = Field(..., description="Parameter performance insights")
    generated_at: datetime = Field(..., description="Report generation timestamp")
