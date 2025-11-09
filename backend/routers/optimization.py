# Optimization API router for managing parameter optimization jobs (Epic 25 Story 5)

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.services.optimization_service import get_optimization_service
from backend.schemas.optimization import (
    OptimizationRequest,
    OptimizationResponse,
    OptimizationListResponse,
    OptimizationDetailResponse,
)

router = APIRouter(prefix="/optimization", tags=["optimization"])


@router.post("/run", response_model=OptimizationResponse)
async def run_optimization(request: OptimizationRequest):
    """
    Launch a new optimization job

    Triggers parameter optimization across multiple backtest runs to find optimal
    strategy parameters. Supports grid search, random sampling, and Bayesian optimization.
    """
    try:
        service = get_optimization_service()
        job_id, message = service.submit_optimization(request)

        return OptimizationResponse(
            job_id=job_id,
            status="running",
            message=message,
            mlflow_experiment_id=None,  # Will be set when optimization completes
            created_at=request.created_at if hasattr(request, "created_at") else None,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to submit optimization: {str(e)}"
        )


@router.get("", response_model=OptimizationListResponse)
async def list_optimizations(
    strategy: Optional[str] = Query(None, description="Filter by strategy name"),
    status: Optional[str] = Query(
        None, description="Filter by status (pending, running, completed, failed)"
    ),
    start_date: Optional[str] = Query(
        None, description="Filter by creation date start (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = Query(
        None, description="Filter by creation date end (YYYY-MM-DD)"
    ),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=100, description="Number of results per page"),
):
    """
    List optimization jobs with optional filtering and pagination

    Returns a paginated list of optimization jobs with their current status and results.
    """
    try:
        service = get_optimization_service()
        result = service.list_optimizations(
            strategy=strategy,
            status=status,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )
        return OptimizationListResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list optimizations: {str(e)}"
        )


@router.get("/{optimization_id}", response_model=OptimizationDetailResponse)
async def get_optimization(optimization_id: int):
    """
    Get detailed information about a specific optimization job

    Returns complete optimization details including parameter space, results,
    and all trial information.
    """
    try:
        service = get_optimization_service()
        optimization = service.get_optimization_details(optimization_id)

        if not optimization:
            raise HTTPException(status_code=404, detail="Optimization not found")

        return OptimizationDetailResponse(**optimization)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get optimization details: {str(e)}"
        )


@router.get("/status/{job_id}")
async def get_optimization_status(job_id: str):
    """
    Get the status of an optimization job by job ID

    This endpoint is useful for polling the status of a submitted optimization.
    """
    try:
        service = get_optimization_service()
        status = service.get_optimization_status(job_id)

        if not status:
            raise HTTPException(status_code=404, detail="Optimization job not found")

        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get optimization status: {str(e)}"
        )
