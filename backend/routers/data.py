# Data Processing API Router
"""
Data Processing API endpoints for the AI Trading Platform.

Epic 26: Script-to-API Conversion for Quant Director Operations
Story 5 & 7: Data Files Management UI Page

Provides endpoints for:
- Processing Databento zip files
- Retrieving data file metadata
- Managing data files (delete, reprocess)
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import pandas as pd

# Import utilities
from scripts.databento_zip_extractor import DatabentoZipExtractor
from scripts.data_file_scanner import DataFileScanner
from utils.data_metadata import DataMetadataExtractor
from utils.metadata_cache import get_cache_manager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/data",
    tags=["data"],
    responses={404: {"description": "Not found"}},
)


# Pydantic models
class DataFileMetadata(BaseModel):
    """Metadata for a data file."""

    file_path: str
    relative_path: str
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    file_size_bytes: int
    file_size_mb: float
    last_modified: str
    row_count: int
    date_range_days: Optional[int]
    expected_data_points: Optional[int]
    quality_score: float
    quality_status: str
    has_required_columns: bool
    data_start_date: Optional[str]
    data_end_date: Optional[str]
    avg_volume: Optional[float]
    price_range: Optional[Dict[str, float]]


class DataProcessingRequest(BaseModel):
    """Request model for data processing."""

    zip_file_path: str = Field(..., description="Path to the Databento zip file")
    output_dir: Optional[str] = Field(
        "data/csv/1m", description="Output directory for processed data"
    )


class DataProcessingResponse(BaseModel):
    """Response model for data processing."""

    job_id: str
    status: str
    message: str
    zip_file: str
    output_dir: str


class DataFileListResponse(BaseModel):
    """Response model for data file listing."""

    files: List[DataFileMetadata]
    total_files: int
    total_size_mb: float
    last_scan: str


class DataFileDeleteRequest(BaseModel):
    """Request model for deleting data files."""

    file_path: str = Field(..., description="Path to the data file to delete")
    confirm: bool = Field(False, description="Confirmation flag")


# Global variables for job tracking (in production, use Redis/database)
processing_jobs = {}


@router.get("/files", response_model=DataFileListResponse)
async def list_data_files(data_dir: str = "data/csv"):
    """
    List all data files with metadata.

    Args:
        data_dir: Directory to scan for data files

    Returns:
        List of data files with metadata
    """
    try:
        # Scan for data files
        scanner = DataFileScanner(data_dir)
        files_data = scanner.scan_data_files()

        # Calculate totals
        total_files = len(files_data)
        total_size_mb = sum(file.get("file_size_mb", 0) for file in files_data)

        response = DataFileListResponse(
            files=files_data,
            total_files=total_files,
            total_size_mb=round(total_size_mb, 2),
            last_scan=datetime.now().isoformat(),
        )

        return response

    except Exception as e:
        logger.error(f"Failed to list data files: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list data files: {str(e)}"
        )


@router.get("/files/{file_path:path}/metadata")
async def get_file_metadata(file_path: str):
    """
    Get detailed metadata for a specific file.

    Args:
        file_path: Path to the data file

    Returns:
        Detailed metadata for the file
    """
    try:
        # Validate file path (prevent directory traversal)
        abs_path = Path(file_path).resolve()
        data_dir = Path("data/csv").resolve()

        if not str(abs_path).startswith(str(data_dir)):
            raise HTTPException(
                status_code=403, detail="Access denied: invalid file path"
            )

        if not abs_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        # Extract metadata
        extractor = DataMetadataExtractor()
        metadata = extractor.extract_file_metadata(abs_path)

        if not metadata:
            raise HTTPException(
                status_code=400, detail="Failed to extract metadata from file"
            )

        return metadata

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file metadata: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get file metadata: {str(e)}"
        )


@router.post("/process", response_model=DataProcessingResponse)
async def process_databento_zip(request: DataProcessingRequest):
    """
    Process a Databento zip file using Redis queue.

    Args:
        request: Processing request with zip file path and output directory

    Returns:
        Job ID and status information
    """
    try:
        import redis

        zip_path = Path(request.zip_file_path)
        output_dir = Path(request.output_dir)

        # Validate inputs
        if not zip_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Zip file not found: {zip_path}"
            )

        if not zip_path.suffix.lower() == ".zip":
            raise HTTPException(status_code=400, detail="File must be a .zip file")

        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate job ID
        job_id = f"data_process_{int(datetime.now().timestamp())}_{zip_path.stem}"

        # Connect to Redis
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_client = redis.Redis(
            host=redis_host, port=redis_port, decode_responses=True
        )

        # Create job specification
        job_spec = {
            "job_id": job_id,
            "zip_file_path": str(zip_path),
            "output_dir": str(output_dir),
        }

        # Submit job to Redis queue
        job_json = json.dumps(job_spec)
        redis_client.zadd("data_processing_queue", {job_json: 1})  # Score of 1 for FIFO

        # Store job status
        job_key = f"data_job:{job_id}"
        redis_client.hmset(
            job_key,
            {
                "status": "queued",
                "message": "Job queued for processing",
                "zip_file": str(zip_path),
                "output_dir": str(output_dir),
                "created_at": datetime.now().isoformat(),
            },
        )
        redis_client.expire(job_key, 86400)  # 24 hours

        response = DataProcessingResponse(
            job_id=job_id,
            status="queued",
            message="Data processing job queued successfully",
            zip_file=str(zip_path),
            output_dir=str(output_dir),
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to queue data processing job: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to queue processing job: {str(e)}"
        )


@router.post("/process/upload")
async def process_uploaded_zip(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    output_dir: str = Form("data/csv/1m"),
):
    """
    Process an uploaded Databento zip file.

    Args:
        file: Uploaded zip file
        output_dir: Output directory for processed data

    Returns:
        Job ID and status information
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith(".zip"):
            raise HTTPException(status_code=400, detail="File must be a .zip file")

        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_zip_path = temp_file.name

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate job ID
        job_id = f"data_upload_{int(datetime.now().timestamp())}_{file.filename.replace('.zip', '')}"

        # Store job info
        processing_jobs[job_id] = {
            "status": "queued",
            "zip_file": temp_zip_path,
            "output_dir": str(output_path),
            "original_filename": file.filename,
            "created_at": datetime.now().isoformat(),
            "progress": 0,
            "message": "Upload processing job queued",
        }

        # Add background task
        background_tasks.add_task(
            process_zip_background, job_id, temp_zip_path, str(output_path)
        )

        return {
            "job_id": job_id,
            "status": "queued",
            "message": f"Processing uploaded file: {file.filename}",
            "output_dir": str(output_path),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process uploaded file: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process upload: {str(e)}"
        )


@router.get("/process/{job_id}")
async def get_processing_status(job_id: str):
    """
    Get the status of a data processing job.

    Args:
        job_id: Job ID to check

    Returns:
        Job status information
    """
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job_info = processing_jobs[job_id].copy()

    # Add estimated completion time for running jobs
    if job_info["status"] == "running":
        # Estimate based on progress (rough estimate)
        progress = job_info.get("progress", 0)
        if progress > 0:
            job_info["estimated_completion"] = (
                f"~{int((100 - progress) / 10)} minutes remaining"
            )
        else:
            job_info["estimated_completion"] = "Calculating..."

    return job_info


@router.delete("/files/{file_path:path}")
async def delete_data_file(file_path: str, confirm: bool = False):
    """
    Delete a data file.

    Args:
        file_path: Path to the data file to delete
        confirm: Confirmation flag

    Returns:
        Deletion confirmation
    """
    try:
        # Validate file path (prevent directory traversal)
        abs_path = Path(file_path).resolve()
        data_dir = Path("data/csv").resolve()

        if not str(abs_path).startswith(str(data_dir)):
            raise HTTPException(
                status_code=403, detail="Access denied: invalid file path"
            )

        if not abs_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        if not confirm:
            raise HTTPException(
                status_code=400,
                detail="Deletion not confirmed. Set confirm=true to delete the file.",
            )

        # Delete the file
        file_size = abs_path.stat().st_size
        abs_path.unlink()

        logger.info(f"Deleted data file: {abs_path}")

        # Invalidate cache for the deleted file and directory
        cache_manager = get_cache_manager()
        cache_manager.invalidate_file_cache(str(abs_path))
        cache_manager.invalidate_directory_cache(str(data_dir))

        return {
            "message": "File deleted successfully",
            "file_path": str(abs_path),
            "file_size_bytes": file_size,
            "deleted_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file {file_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.get("/stats")
async def get_data_stats(data_dir: str = "data/csv"):
    """
    Get statistics about the data files.

    Args:
        data_dir: Directory to analyze

    Returns:
        Data statistics
    """
    try:
        scanner = DataFileScanner(data_dir)
        files_data = scanner.scan_data_files()

        # Calculate statistics
        stats = {
            "total_files": len(files_data),
            "total_size_mb": sum(f.get("file_size_mb", 0) for f in files_data),
            "symbols": list(
                set(f.get("symbol") for f in files_data if f.get("symbol"))
            ),
            "timeframes": list(
                set(f.get("timeframe") for f in files_data if f.get("timeframe"))
            ),
            "quality_distribution": {
                "excellent": len(
                    [f for f in files_data if f.get("quality_status") == "Excellent"]
                ),
                "good": len(
                    [f for f in files_data if f.get("quality_status") == "Good"]
                ),
                "fair": len(
                    [f for f in files_data if f.get("quality_status") == "Fair"]
                ),
                "poor": len(
                    [f for f in files_data if f.get("quality_status") == "Poor"]
                ),
            },
            "last_updated": datetime.now().isoformat(),
        }

        return stats

    except Exception as e:
        logger.error(f"Failed to get data stats: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get statistics: {str(e)}"
        )


# Background task function
def process_zip_background(job_id: str, zip_path: str, output_dir: str):
    """
    Background task to process a Databento zip file.

    Args:
        job_id: Job identifier
        zip_path: Path to zip file
        output_dir: Output directory
    """
    try:
        # Update job status
        processing_jobs[job_id]["status"] = "running"
        processing_jobs[job_id]["message"] = "Starting zip extraction..."

        logger.info(f"Starting background processing for job {job_id}")

        # Create extractor
        extractor = DatabentoZipExtractor(zip_path, output_dir)

        # Update progress
        processing_jobs[job_id]["progress"] = 10
        processing_jobs[job_id]["message"] = "Extracting zip file..."

        # Process the zip file
        extractor.process_zip_file()

        # Update final status
        processing_jobs[job_id]["status"] = "completed"
        processing_jobs[job_id]["progress"] = 100
        processing_jobs[job_id]["message"] = "Processing completed successfully"
        processing_jobs[job_id]["completed_at"] = datetime.now().isoformat()

        # Invalidate directory cache since new files were added
        cache_manager = get_cache_manager()
        cache_manager.invalidate_directory_cache(output_dir)

        logger.info(f"Completed background processing for job {job_id}")

        # Clean up temporary file if it was uploaded
        if zip_path.startswith("/tmp/") and os.path.exists(zip_path):
            try:
                os.unlink(zip_path)
                logger.info(f"Cleaned up temporary file: {zip_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {zip_path}: {e}")

    except Exception as e:
        # Update job status on error
        processing_jobs[job_id]["status"] = "failed"
        processing_jobs[job_id]["message"] = f"Processing failed: {str(e)}"
        processing_jobs[job_id]["error"] = str(e)
        processing_jobs[job_id]["failed_at"] = datetime.now().isoformat()

        logger.error(f"Background processing failed for job {job_id}: {e}")

        # Clean up temporary file on error
        if zip_path.startswith("/tmp/") and os.path.exists(zip_path):
            try:
                os.unlink(zip_path)
            except Exception:
                pass
