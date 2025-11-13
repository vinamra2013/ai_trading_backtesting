"""
V2 Parallel Optimization System - Optimization API Router
FastAPI router for optimization endpoints with real-time monitoring.
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from backend.services.optimization_service import OptimizationService
from backend.services.backtest_service import BacktestService
from backend.schemas.optimization import (
    OptimizationRequest,
    OptimizationResponse,
    BatchStatusResponse,
    BatchResultsResponse,
    ErrorResponse
)
from backend.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/run-parallel",
    response_model=OptimizationResponse,
    summary="Start parallel optimization",
    description="Generate parameter combinations and submit parallel backtest jobs"
)
async def run_parallel_optimization(
    request: OptimizationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> OptimizationResponse:
    """
    Start a parallel optimization run.

    This endpoint:
    1. Parses the optimization config file
    2. Generates all parameter combinations
    3. Creates an optimization batch
    4. Submits individual backtest jobs
    5. Returns batch ID for monitoring

    The actual job execution happens in the background.
    """
    try:
        # Initialize services
        opt_service = OptimizationService(db)
        backtest_service = BacktestService(db)

        # Generate parameter combinations
        combinations = opt_service.generate_parameter_combinations(request.config_path)

        # Create optimization batch
        batch_id = opt_service.create_optimization_batch(request.config_path, combinations)

        # Submit jobs in background
        background_tasks.add_task(
            _submit_optimization_jobs,
            opt_service,
            backtest_service,
            batch_id,
            combinations,
            request.config_path,
            request.max_concurrent
        )

        logger.info(f"Started parallel optimization batch {batch_id} with {len(combinations)} jobs")

        return OptimizationResponse(
            batch_id=batch_id,
            total_jobs=len(combinations),
            message=f"Optimization started with {len(combinations)} parameter combinations"
        )

    except FileNotFoundError as e:
        logger.error(f"Config file not found: {e}")
        raise HTTPException(status_code=404, detail=f"Config file not found: {e}")
    except ValueError as e:
        logger.error(f"Invalid configuration: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid configuration: {e}")
    except Exception as e:
        logger.error(f"Failed to start optimization: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/batches/{batch_id}",
    response_model=BatchStatusResponse,
    summary="Get batch status",
    description="Get real-time status and progress of an optimization batch"
)
async def get_batch_status(
    batch_id: str,
    db: Session = Depends(get_db)
) -> BatchStatusResponse:
    """
    Get the current status of an optimization batch.

    Returns:
    - Batch metadata (total jobs, completed, status)
    - Current best result
    - Estimated completion time
    - Job status summaries
    """
    try:
        opt_service = OptimizationService(db)
        batch_status = opt_service.get_batch_status(batch_id)

        if not batch_status:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

        # Get job summaries (simplified for API response)
        # In a real implementation, you might want to paginate this
        jobs_summary = []  # Simplified - could add job details here

        return BatchStatusResponse(
            batch=batch_status,
            jobs=jobs_summary
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get batch status: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/batches/{batch_id}/results",
    response_model=BatchResultsResponse,
    summary="Get batch results",
    description="Get final results and analysis for a completed optimization batch"
)
async def get_batch_results(
    batch_id: str,
    db: Session = Depends(get_db)
) -> BatchResultsResponse:
    """
    Get the final results of an optimization batch.

    Returns:
    - All backtest results with success criteria evaluation
    - Parameter performance analysis
    - Best performing parameter set
    """
    try:
        # This would aggregate results from the database
        # For now, return a placeholder response
        # In a real implementation, you'd query BacktestResult table

        return BatchResultsResponse(
            batch_id=batch_id,
            total_results=0,
            passed_criteria=0,
            best_result=None,
            results=[],
            parameter_analysis={}
        )

    except Exception as e:
        logger.error(f"Failed to get batch results: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete(
    "/batches/{batch_id}",
    summary="Cancel batch",
    description="Cancel a running optimization batch and mark jobs as cancelled"
)
async def cancel_batch(
    batch_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Cancel an optimization batch.

    This will:
    1. Mark the batch as cancelled
    2. Cancel any queued jobs
    3. Leave running jobs to complete (or could force stop them)
    """
    try:
        opt_service = OptimizationService(db)
        success = opt_service.cancel_batch(batch_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

        return {"message": f"Batch {batch_id} cancelled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel batch: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Background task function
def _submit_optimization_jobs(
    opt_service: OptimizationService,
    backtest_service: BacktestService,
    batch_id: str,
    combinations: List[Dict[str, Any]],
    config_path: str,
    max_concurrent: int
):
    """
    Background task to submit optimization jobs.

    This runs in the background to avoid blocking the API response.
    """
    try:
        logger.info(f"Starting background job submission for batch {batch_id}")

        # Load full config for job submission
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Submit jobs with concurrency control
        job_ids = opt_service.submit_backtest_jobs(
            batch_id=batch_id,
            combinations=combinations,
            config=config,
            max_concurrent=max_concurrent
        )

        logger.info(f"Successfully submitted {len(job_ids)} jobs for batch {batch_id}")

        # Note: In a production system, you might want to start
        # a job queue processor here to actually execute the jobs

    except Exception as e:
        logger.error(f"Failed to submit jobs for batch {batch_id}: {e}")
        # Mark batch as failed
    except Exception as e:
        logger.error(f"Failed to submit jobs for batch {batch_id}: {e}")
        # Mark batch as failed
        try:
            opt_service.cancel_batch(batch_id)
        except Exception:
            pass  # Already logged
