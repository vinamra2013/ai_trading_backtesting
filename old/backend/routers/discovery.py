# Discovery API router for symbol discovery operations (Epic 26 Story 1)

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from datetime import datetime

from backend.schemas.discovery import (
    DiscoveryRequest,
    DiscoveryResponse,
    DiscoveryStatus,
    DiscoveryResult,
    DiscoveryListResponse,
    DiscoveryFilter,
)
from backend.services.discovery_service import get_discovery_service

router = APIRouter()


@router.post("/scan", response_model=DiscoveryResponse)
async def submit_discovery_scan(
    request: DiscoveryRequest,
    background_tasks: BackgroundTasks,
):
    """
    Submit a new symbol discovery scan job.

    This endpoint triggers a background job to scan for tradeable symbols
    using the specified scanner type and filtering criteria.
    """
    try:
        service = get_discovery_service()

        job_id, message = service.submit_discovery_job(
            scanner_name=request.scanner_name,
            parameters=request.parameters,
            filters=request.filters,
        )

        return DiscoveryResponse(
            job_id=job_id,
            status="running",
            message=message,
            created_at=datetime.now(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to submit discovery job: {str(e)}"
        )


@router.get("/status/{job_id}", response_model=DiscoveryStatus)
async def get_discovery_job_status(job_id: str):
    """
    Get the status of a discovery job.

    Returns current progress, symbols discovered, and any error messages.
    """
    service = get_discovery_service()
    status = service.get_discovery_status(job_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Discovery job {job_id} not found")

    return DiscoveryStatus(**status)


@router.get("/results/{job_id}", response_model=DiscoveryResult)
async def get_discovery_results(job_id: str):
    """
    Get the results of a completed discovery job.

    Returns the list of discovered and filtered symbols with their metadata.
    """
    service = get_discovery_service()
    results = service.get_discovery_results(job_id)

    if not results:
        # Check if job exists but is not completed
        status = service.get_discovery_status(job_id)
        if status:
            raise HTTPException(
                status_code=202,
                detail=f"Job {job_id} is {status['status']}, not yet completed",
            )
        else:
            raise HTTPException(
                status_code=404, detail=f"Discovery job {job_id} not found"
            )

    # Convert results to response format
    symbols = []
    for symbol_data in results["symbols"]:
        symbols.append(
            {
                "symbol": symbol_data["symbol"],
                "exchange": symbol_data["exchange"],
                "sector": symbol_data["sector"],
                "avg_volume": symbol_data["avg_volume"],
                "atr": symbol_data["atr"],
                "price": symbol_data["price"],
                "pct_change": symbol_data["pct_change"],
                "market_cap": symbol_data["market_cap"],
                "volume": symbol_data["volume"],
                "discovery_timestamp": symbol_data["discovery_timestamp"],
                "scanner_type": symbol_data["scanner_type"],
                "metadata": symbol_data["metadata"],
            }
        )

    return DiscoveryResult(
        job_id=results["job_id"],
        scanner_name=results["scanner_name"],
        scanner_type=results["scanner_type"],
        symbols=symbols,
        total_count=results["total_count"],
        filtered_count=results["filtered_count"],
        completed_at=results["completed_at"],
        execution_time_seconds=results["execution_time_seconds"],
    )


@router.get("/jobs", response_model=DiscoveryListResponse)
async def list_discovery_jobs(
    scanner_name: Optional[str] = Query(None, description="Filter by scanner name"),
    status: Optional[str] = Query(None, description="Filter by job status"),
    start_date: Optional[str] = Query(
        None, description="Filter by start date (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = Query(
        None, description="Filter by end date (YYYY-MM-DD)"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
):
    """
    List discovery jobs with optional filtering and pagination.

    Returns a paginated list of discovery jobs matching the specified criteria.
    """
    service = get_discovery_service()
    result = service.list_discovery_jobs(
        scanner_name=scanner_name,
        status=status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    # Convert to response format
    jobs = []
    for job_data in result["jobs"]:
        jobs.append(DiscoveryStatus(**job_data))

    return DiscoveryListResponse(
        jobs=jobs,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
    )


@router.delete("/jobs/{job_id}")
async def delete_discovery_job(job_id: str):
    """
    Delete a discovery job and its associated results.

    This permanently removes the job record and all discovered symbols.
    """
    service = get_discovery_service()
    success = service.delete_discovery_job(job_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Discovery job {job_id} not found")

    return {"message": f"Discovery job {job_id} and its results deleted successfully"}
