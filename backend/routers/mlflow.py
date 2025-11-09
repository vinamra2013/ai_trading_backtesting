# MLflow API router for programmatic access to experiments and runs (Epic 25 Story 6)

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.services.mlflow_client import get_mlflow_service
from backend.schemas.mlflow import (
    MLflowExperimentsResponse,
    MLflowRunsResponse,
    MLflowRunDetailResponse,
    MLflowErrorResponse,
)

router = APIRouter(prefix="/mlflow", tags=["mlflow"])


@router.get("/experiments", response_model=MLflowExperimentsResponse)
async def list_experiments():
    """
    List all MLflow experiments

    Returns a list of all experiments with their metadata including lifecycle stage,
    creation time, and artifact locations.
    """
    try:
        service = get_mlflow_service()
        return service.list_experiments()
    except RuntimeError as e:
        if "MLflow client not available" in str(e):
            raise HTTPException(
                status_code=503,
                detail="MLflow service is not available. Please check MLflow server connectivity.",
            )
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve experiments: {str(e)}"
        )


@router.get("/runs/{experiment_id}", response_model=MLflowRunsResponse)
async def get_experiment_runs(
    experiment_id: str,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=100, description="Number of runs per page"),
    order_by: Optional[str] = Query(
        None,
        description="Comma-separated list of columns to order by (e.g., 'start_time DESC, metrics.sharpe_ratio DESC')",
    ),
):
    """
    Get runs for a specific experiment with pagination

    Returns paginated runs for the specified experiment, including metrics,
    parameters, and tags for each run.
    """
    try:
        service = get_mlflow_service()

        # Parse order_by parameter
        order_by_list = None
        if order_by:
            order_by_list = [col.strip() for col in order_by.split(",") if col.strip()]

        return service.get_experiment_runs(
            experiment_id=experiment_id,
            page=page,
            page_size=page_size,
            order_by=order_by_list,
        )
    except RuntimeError as e:
        if "MLflow client not available" in str(e):
            raise HTTPException(
                status_code=503,
                detail="MLflow service is not available. Please check MLflow server connectivity.",
            )
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve experiment runs: {str(e)}"
        )


@router.get("/runs/details/{run_id}", response_model=MLflowRunDetailResponse)
async def get_run_details(run_id: str):
    """
    Get detailed information for a specific run

    Returns complete run information including all metrics, parameters,
    tags, and metadata for the specified run ID.
    """
    try:
        service = get_mlflow_service()
        return service.get_run_details(run_id=run_id)
    except RuntimeError as e:
        if "MLflow client not available" in str(e):
            raise HTTPException(
                status_code=503,
                detail="MLflow service is not available. Please check MLflow server connectivity.",
            )
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # Check if it's a "run not found" error
        if "RESOURCE_DOES_NOT_EXIST" in str(e) or "run not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve run details: {str(e)}"
        )


@router.post("/cache/invalidate")
async def invalidate_cache(
    experiment_id: Optional[str] = Query(
        None, description="Specific experiment ID to invalidate, or omit for all"
    ),
):
    """
    Invalidate MLflow cache

    Clears cached experiment and run data. Useful after manual changes to MLflow data.
    """
    try:
        service = get_mlflow_service()
        service.invalidate_experiment_cache(experiment_id=experiment_id)

        message = "All MLflow cache invalidated"
        if experiment_id:
            message = f"Cache invalidated for experiment {experiment_id}"

        return {"message": message, "experiment_id": experiment_id}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to invalidate cache: {str(e)}"
        )
