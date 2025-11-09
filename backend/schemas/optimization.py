# Pydantic schemas for optimization API requests and responses (Epic 25 Story 5)

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime


class ParameterSpaceItem(BaseModel):
    """Individual parameter definition for optimization"""

    type: str = Field(
        ..., description="Parameter type: 'int', 'float', or 'categorical'"
    )
    low: Optional[Union[int, float]] = Field(
        None, description="Lower bound for int/float parameters"
    )
    high: Optional[Union[int, float]] = Field(
        None, description="Upper bound for int/float parameters"
    )
    choices: Optional[List[Any]] = Field(
        None, description="List of choices for categorical parameters"
    )

    @validator("type")
    def validate_type(cls, v):
        if v not in ["int", "float", "categorical"]:
            raise ValueError("Parameter type must be 'int', 'float', or 'categorical'")
        return v

    @validator("low", "high")
    def validate_bounds(cls, v, values):
        param_type = values.get("type")
        if param_type in ["int", "float"] and v is None:
            raise ValueError(
                f"Parameters of type '{param_type}' require 'low' and 'high' bounds"
            )
        return v

    @validator("choices")
    def validate_choices(cls, v, values):
        param_type = values.get("type")
        if param_type == "categorical" and (v is None or len(v) == 0):
            raise ValueError("Categorical parameters require non-empty 'choices' list")
        return v


class OptimizationRequest(BaseModel):
    """Request model for launching an optimization job"""

    strategy: str = Field(..., description="Strategy name or file path")
    symbols: List[str] = Field(..., description="List of symbols to optimize on")
    parameter_space: Dict[str, ParameterSpaceItem] = Field(
        ..., description="Parameter space definition for optimization"
    )
    objective_metric: str = Field(
        "sharpe_ratio",
        description="Metric to optimize (e.g., 'sharpe_ratio', 'total_return', 'max_drawdown')",
    )
    max_trials: int = Field(
        50, ge=1, le=500, description="Maximum number of optimization trials to run"
    )
    timeframe: str = Field("1d", description="Timeframe for backtests")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    optimization_method: str = Field(
        "grid", description="Optimization method: 'grid', 'random', 'bayesian'"
    )

    @validator("parameter_space")
    def validate_parameter_space(cls, v):
        if not v:
            raise ValueError("Parameter space cannot be empty")
        return v


class OptimizationResponse(BaseModel):
    """Response model for optimization job submission"""

    job_id: str = Field(..., description="Unique optimization job identifier")
    status: str = Field(..., description="Current job status")
    message: str = Field(..., description="Status message")
    mlflow_experiment_id: Optional[str] = Field(
        None, description="MLflow experiment ID for tracking"
    )
    created_at: datetime = Field(..., description="Job creation timestamp")


class OptimizationStatus(BaseModel):
    """Optimization job status information"""

    id: int
    job_id: str
    strategy_name: str
    status: str
    objective_metric: str
    max_trials: int
    current_trial: Optional[int] = None
    best_metric_value: Optional[float] = None
    best_parameters: Optional[Dict[str, Any]] = None
    mlflow_experiment_id: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class OptimizationListResponse(BaseModel):
    """Paginated response for optimization job list"""

    optimizations: List[OptimizationStatus]
    total: int
    page: int
    page_size: int
    total_pages: int


class OptimizationDetailResponse(BaseModel):
    """Detailed optimization result response"""

    id: int
    job_id: str
    strategy_name: str
    parameter_space: Dict[str, Any]
    objective_metric: str
    max_trials: int
    optimization_method: str
    status: str
    current_trial: Optional[int] = None
    best_metric_value: Optional[float] = None
    best_parameters: Optional[Dict[str, Any]] = None
    best_result_id: Optional[int] = None
    mlflow_experiment_id: Optional[str] = None
    trials_completed: Optional[int] = None
    trials_data: Optional[List[Dict[str, Any]]] = None  # Trial results
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class OptimizationFilter(BaseModel):
    """Filter parameters for optimization queries"""

    strategy: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)


class OptimizationTrial(BaseModel):
    """Individual optimization trial result"""

    trial_id: int
    parameters: Dict[str, Any]
    metrics: Dict[str, float]
    backtest_id: Optional[int] = None
    mlflow_run_id: Optional[str] = None
    completed_at: datetime
