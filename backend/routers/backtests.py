# Backtest API router for managing backtest jobs (Epic 25 Stories 3 & 4)

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime

from backend.schemas.backtest import (
    BacktestRequest,
    BacktestResponse,
    BacktestListResponse,
    BacktestDetailResponse,
    BacktestFilter,
)
from backend.services.backtest_service import get_backtest_service

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    """
    Submit a new backtest job

    Triggers a backtest with the specified parameters and returns a job ID for tracking.
    The backtest will be processed asynchronously by worker containers.
    """
    try:
        service = get_backtest_service()
        job_id, message = service.submit_backtest(
            strategy=request.strategy,
            symbols=request.symbols,
            parameters=request.parameters,
            timeframe=request.timeframe,
            start_date=request.start_date,
            end_date=request.end_date,
        )

        return BacktestResponse(
            job_id=job_id, status="running", message=message, created_at=datetime.now()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to submit backtest: {str(e)}"
        )


@router.get("", response_model=BacktestListResponse)
async def list_backtests(
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
    List backtests with optional filtering and pagination

    Returns a paginated list of backtest jobs with their current status.
    """
    try:
        service = get_backtest_service()
        result = service.list_backtests(
            strategy=strategy,
            status=status,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )
        return BacktestListResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list backtests: {str(e)}"
        )


@router.get("/{backtest_id}", response_model=BacktestDetailResponse)
async def get_backtest(backtest_id: int):
    """
    Get detailed information about a specific backtest

    Returns complete backtest details including metrics, trades, and MLflow links.
    """
    try:
        service = get_backtest_service()
        backtest = service.get_backtest_details(backtest_id)

        if not backtest:
            raise HTTPException(status_code=404, detail="Backtest not found")

        return BacktestDetailResponse(**backtest)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get backtest details: {str(e)}"
        )


@router.get("/status/{job_id}")
async def get_backtest_status(job_id: str):
    """
    Get the status of a backtest job by job ID

    This endpoint is useful for polling the status of a submitted backtest.
    """
    try:
        service = get_backtest_service()
        status = service.get_backtest_status(job_id)

        if not status:
            raise HTTPException(status_code=404, detail="Backtest job not found")

        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get backtest status: {str(e)}"
        )


@router.delete("/{backtest_id}")
async def delete_backtest(backtest_id: int):
    """
    Delete a backtest by ID

    Permanently removes a backtest record from the database.
    """
    try:
        service = get_backtest_service()
        success = service.delete_backtest(backtest_id)

        if not success:
            raise HTTPException(status_code=404, detail="Backtest not found")

        return {"message": f"Backtest {backtest_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete backtest: {str(e)}"
        )
