# Ranking API router for strategy ranking operations (Epic 26 Story 2)

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from datetime import datetime

from backend.schemas.ranking import (
    RankingRequest,
    RankingResponse,
    RankingStatus,
    RankingResult,
    RankingListResponse,
    RankingFilter,
    RankingSummary,
)
from backend.services.ranking_service import get_ranking_service

router = APIRouter()


@router.post("/analyze", response_model=RankingResponse)
async def submit_ranking_analysis(
    request: RankingRequest,
    background_tasks: BackgroundTasks,
):
    """
    Submit a new strategy ranking analysis job.

    This endpoint triggers a background job to rank trading strategies
    using multi-criteria scoring with configurable weights.
    """
    try:
        service = get_ranking_service()

        job_id, message = service.submit_ranking_job(
            input_type=request.input_type,
            input_source=request.input_source,
            criteria_weights=request.criteria_weights,
            ranking_config=request.ranking_config,
        )

        return RankingResponse(
            job_id=job_id,
            status="running",
            message=message,
            created_at=datetime.now(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to submit ranking job: {str(e)}"
        )


@router.get("/status/{job_id}", response_model=RankingStatus)
async def get_ranking_job_status(job_id: str):
    """
    Get the status of a ranking job.

    Returns current progress, strategies processed, and any error messages.
    """
    service = get_ranking_service()
    status = service.get_ranking_status(job_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Ranking job {job_id} not found")

    return RankingStatus(**status)


@router.get("/results/{job_id}", response_model=RankingResult)
async def get_ranking_results(job_id: str):
    """
    Get the results of a completed ranking job.

    Returns the ranked list of strategies with individual scores and composite rankings.
    """
    service = get_ranking_service()
    results = service.get_ranking_results(job_id)

    if not results:
        # Check if job exists but is not completed
        status = service.get_ranking_status(job_id)
        if status:
            raise HTTPException(
                status_code=202,
                detail=f"Job {job_id} is {status['status']}, not yet completed",
            )
        else:
            raise HTTPException(
                status_code=404, detail=f"Ranking job {job_id} not found"
            )

    # Convert results to response format
    strategies = []
    for strategy_data in results["strategies"]:
        strategies.append(
            {
                "strategy_name": strategy_data["strategy_name"],
                "symbol": strategy_data["symbol"],
                "sharpe_ratio": strategy_data["sharpe_ratio"],
                "max_drawdown": strategy_data["max_drawdown"],
                "win_rate": strategy_data["win_rate"],
                "total_trades": strategy_data["total_trades"],
                "profit_factor": strategy_data["profit_factor"],
                "sharpe_score": strategy_data["sharpe_score"],
                "consistency_score": strategy_data["consistency_score"],
                "drawdown_score": strategy_data["drawdown_score"],
                "frequency_score": strategy_data["frequency_score"],
                "efficiency_score": strategy_data["efficiency_score"],
                "composite_score": strategy_data["composite_score"],
                "rank": strategy_data["rank"],
                "metadata": strategy_data["metadata"],
            }
        )

    return RankingResult(
        job_id=results["job_id"],
        input_type=results["input_type"],
        input_source=results["input_source"],
        strategies=strategies,
        total_strategies=results["total_strategies"],
        criteria_weights=results["criteria_weights"],
        summary=results["summary"],
        completed_at=results["completed_at"],
        execution_time_seconds=results["execution_time_seconds"],
    )


@router.get("/jobs", response_model=RankingListResponse)
async def list_ranking_jobs(
    input_type: Optional[str] = Query(None, description="Filter by input type"),
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
    List ranking jobs with optional filtering and pagination.

    Returns a paginated list of ranking jobs matching the specified criteria.
    """
    service = get_ranking_service()
    result = service.list_ranking_jobs(
        input_type=input_type,
        status=status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    # Convert to response format
    jobs = []
    for job_data in result["jobs"]:
        jobs.append(RankingStatus(**job_data))

    return RankingListResponse(
        jobs=jobs,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
    )


@router.delete("/jobs/{job_id}")
async def delete_ranking_job(job_id: str):
    """
    Delete a ranking job and its associated results.

    This permanently removes the job record and all ranking results.
    """
    service = get_ranking_service()
    success = service.delete_ranking_job(job_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Ranking job {job_id} not found")

    return {"message": f"Ranking job {job_id} and its results deleted successfully"}
