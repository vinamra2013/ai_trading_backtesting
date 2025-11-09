# Pydantic schemas for MLflow API requests and responses (Epic 25 Story 6)

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class MLflowExperiment(BaseModel):
    """MLflow experiment information"""

    experiment_id: str = Field(..., description="Unique experiment identifier")
    name: str = Field(..., description="Experiment name")
    lifecycle_stage: str = Field(
        ..., description="Experiment lifecycle stage (active/archived)"
    )
    artifact_location: Optional[str] = Field(
        None, description="Artifact storage location"
    )
    creation_time: Optional[datetime] = Field(
        None, description="Experiment creation timestamp"
    )
    last_update_time: Optional[datetime] = Field(
        None, description="Last update timestamp"
    )


class MLflowRunInfo(BaseModel):
    """MLflow run info structure"""

    run_id: str = Field(..., description="Unique run identifier")
    run_uuid: str = Field(..., description="Run UUID")
    experiment_id: str = Field(..., description="Parent experiment ID")
    user_id: str = Field(..., description="User who created the run")
    status: str = Field(
        ..., description="Run status (RUNNING, SCHEDULED, FINISHED, FAILED, KILLED)"
    )
    start_time: Optional[datetime] = Field(None, description="Run start time")
    end_time: Optional[datetime] = Field(None, description="Run end time")
    artifact_uri: str = Field(..., description="Artifact storage URI")
    lifecycle_stage: str = Field(..., description="Run lifecycle stage")


class MLflowRunData(BaseModel):
    """MLflow run data containing parameters, metrics, and tags"""

    metrics: Dict[str, float] = Field(default_factory=dict, description="Run metrics")
    params: Dict[str, str] = Field(default_factory=dict, description="Run parameters")
    tags: Dict[str, Any] = Field(default_factory=dict, description="Run tags")


class MLflowRun(BaseModel):
    """Complete MLflow run information"""

    info: MLflowRunInfo = Field(..., description="Run metadata")
    data: MLflowRunData = Field(..., description="Run data (metrics, params, tags)")


class MLflowExperimentsResponse(BaseModel):
    """Response for listing MLflow experiments"""

    experiments: List[MLflowExperiment] = Field(..., description="List of experiments")


class MLflowRunsResponse(BaseModel):
    """Response for listing runs in an experiment"""

    runs: List[MLflowRun] = Field(..., description="List of runs")
    total: int = Field(..., description="Total number of runs")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of runs per page")
    total_pages: int = Field(..., description="Total number of pages")


class MLflowRunDetailResponse(BaseModel):
    """Response for detailed run information"""

    run: MLflowRun = Field(..., description="Complete run details")


class MLflowErrorResponse(BaseModel):
    """Error response for MLflow API failures"""

    error: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")
