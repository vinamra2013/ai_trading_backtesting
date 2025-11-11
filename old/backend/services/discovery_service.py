# Discovery service for managing symbol discovery jobs and results (Epic 26 Story 1)

import os
import json
import uuid
import redis
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from backend.utils.database import DatabaseManager, get_db_manager
from backend.models.discovery import DiscoveryJob, DiscoveryResult


@dataclass
class DiscoveryJobSpec:
    """Individual discovery job specification"""

    job_id: str
    scanner_name: str
    parameters: Optional[Dict[str, Any]] = None
    filters: Optional[Dict[str, Any]] = None
    priority: int = 0


class DiscoveryService:
    """Service for managing symbol discovery job submission and status tracking"""

    def __init__(self, redis_host: str = "redis", redis_port: int = 6379):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis = redis.Redis(
            host=self.redis_host, port=self.redis_port, decode_responses=True
        )
        self.db_manager = get_db_manager()

    def submit_discovery_job(
        self,
        scanner_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """
        Submit a new discovery job to the queue

        Args:
            scanner_name: Name of the scanner to run
            parameters: Scanner-specific parameters
            filters: Filtering criteria to apply

        Returns:
            Tuple of (job_id, message)
        """
        # Generate unique job ID
        job_id = f"discovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # Create database record
        session = self.db_manager.get_session()
        try:
            # Determine scanner type from scanner name
            scanner_type = self._get_scanner_type(scanner_name)

            discovery_job = DiscoveryJob(
                job_id=job_id,
                scanner_name=scanner_name,
                scanner_type=scanner_type,
                parameters=parameters or {},
                filters=filters or {},
                status="running",
                started_at=datetime.now(),
            )

            session.add(discovery_job)
            session.commit()

            # Submit job to Redis queue
            job_spec = DiscoveryJobSpec(
                job_id=job_id,
                scanner_name=scanner_name,
                parameters=parameters,
                filters=filters,
                priority=0,
            )

            job_json = json.dumps(
                {
                    "job_id": job_spec.job_id,
                    "scanner_name": job_spec.scanner_name,
                    "parameters": job_spec.parameters or {},
                    "filters": job_spec.filters or {},
                    "priority": job_spec.priority,
                }
            )

            result = self.redis.zadd("discovery_jobs", {job_json: -job_spec.priority})

            return (job_id, f"Submitted discovery job for scanner: {scanner_name}")

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def _get_scanner_type(self, scanner_name: str) -> str:
        """Map scanner name to scanner type"""
        scanner_mapping = {
            "high_volume": "volume_based",
            "most_active_stocks": "activity_based",
            "top_gainers": "performance_based",
            "top_losers": "performance_based",
            "most_active_etfs": "activity_based",
            "volatility_leaders": "volatility_based",
        }
        return scanner_mapping.get(scanner_name, "unknown")

    def get_discovery_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a discovery job

        Args:
            job_id: The job ID to query

        Returns:
            Discovery status information or None if not found
        """
        session = self.db_manager.get_session()
        try:
            job = (
                session.query(DiscoveryJob)
                .filter(DiscoveryJob.job_id == job_id)
                .first()
            )

            if not job:
                return None

            return {
                "job_id": job.job_id,
                "scanner_name": job.scanner_name,
                "scanner_type": job.scanner_type,
                "status": job.status,
                "progress": job.progress,
                "symbols_discovered": job.symbols_discovered,
                "symbols_filtered": job.symbols_filtered,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "error_message": job.error_message,
            }
        finally:
            session.close()

    def get_discovery_results(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the results of a completed discovery job

        Args:
            job_id: The job ID to query

        Returns:
            Discovery results or None if not found/completed
        """
        session = self.db_manager.get_session()
        try:
            # Get job info
            job = (
                session.query(DiscoveryJob)
                .filter(DiscoveryJob.job_id == job_id)
                .first()
            )
            if not job or job.status != "completed":
                return None

            # Get results
            results = (
                session.query(DiscoveryResult)
                .filter(DiscoveryResult.job_id == job_id)
                .all()
            )

            symbols = []
            for result in results:
                symbols.append(
                    {
                        "symbol": result.symbol,
                        "exchange": result.exchange,
                        "sector": result.sector,
                        "avg_volume": result.avg_volume,
                        "atr": result.atr,
                        "price": result.price,
                        "pct_change": result.pct_change,
                        "market_cap": result.market_cap,
                        "volume": result.volume,
                        "discovery_timestamp": result.discovery_timestamp,
                        "scanner_type": result.scanner_type,
                        "metadata": result.symbol_metadata,
                    }
                )

            return {
                "job_id": job.job_id,
                "scanner_name": job.scanner_name,
                "scanner_type": job.scanner_type,
                "symbols": symbols,
                "total_count": len(symbols),
                "filtered_count": job.symbols_filtered,
                "completed_at": job.completed_at,
                "execution_time_seconds": (
                    job.completed_at - job.started_at
                ).total_seconds()
                if job.completed_at and job.started_at
                else None,
            }
        finally:
            session.close()

    def list_discovery_jobs(
        self,
        scanner_name: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """
        List discovery jobs with optional filtering and pagination

        Args:
            scanner_name: Filter by scanner name
            status: Filter by status
            start_date: Filter by creation date start
            end_date: Filter by creation date end
            page: Page number (1-based)
            page_size: Number of results per page

        Returns:
            Paginated discovery jobs results
        """
        session = self.db_manager.get_session()
        try:
            query = session.query(DiscoveryJob)

            # Apply filters
            if scanner_name:
                query = query.filter(
                    DiscoveryJob.scanner_name.ilike(f"%{scanner_name}%")
                )
            if status:
                query = query.filter(DiscoveryJob.status == status)
            if start_date:
                query = query.filter(DiscoveryJob.created_at >= start_date)
            if end_date:
                query = query.filter(DiscoveryJob.created_at <= end_date)

            # Get total count
            total = query.count()

            # Apply pagination
            offset = (page - 1) * page_size
            jobs = (
                query.order_by(DiscoveryJob.created_at.desc())
                .offset(offset)
                .limit(page_size)
                .all()
            )

            # Convert to dict format
            job_list = []
            for job in jobs:
                job_list.append(
                    {
                        "job_id": job.job_id,
                        "scanner_name": job.scanner_name,
                        "scanner_type": job.scanner_type,
                        "status": job.status,
                        "progress": job.progress,
                        "symbols_discovered": job.symbols_discovered,
                        "symbols_filtered": job.symbols_filtered,
                        "created_at": job.created_at,
                        "started_at": job.started_at,
                        "completed_at": job.completed_at,
                        "error_message": job.error_message,
                    }
                )

            total_pages = (total + page_size - 1) // page_size

            return {
                "jobs": job_list,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }
        finally:
            session.close()

    def update_discovery_results(
        self,
        job_id: str,
        status: str,
        symbols_discovered: int = 0,
        symbols_filtered: int = 0,
        result_data: Optional[List[Dict[str, Any]]] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Update discovery results (called by workers)

        Args:
            job_id: The job ID to update
            status: New status
            symbols_discovered: Number of symbols discovered
            symbols_filtered: Number of symbols after filtering
            result_data: Discovery results data
            error_message: Error message if failed

        Returns:
            True if update was successful
        """
        session = self.db_manager.get_session()
        try:
            job = (
                session.query(DiscoveryJob)
                .filter(DiscoveryJob.job_id == job_id)
                .first()
            )

            if not job:
                return False

            # Update job status
            job.status = status
            job.symbols_discovered = symbols_discovered
            job.symbols_filtered = symbols_filtered
            job.result_data = result_data

            if error_message:
                job.error_message = error_message

            if status in ["completed", "failed"]:
                job.completed_at = datetime.now()

            # Store individual results if provided
            if result_data and status == "completed":
                for symbol_data in result_data:
                    result = DiscoveryResult(
                        job_id=job_id,
                        symbol=symbol_data["symbol"],
                        exchange=symbol_data["exchange"],
                        sector=symbol_data.get("sector"),
                        avg_volume=symbol_data.get("avg_volume"),
                        atr=symbol_data.get("atr"),
                        price=symbol_data.get("price"),
                        pct_change=symbol_data.get("pct_change"),
                        market_cap=symbol_data.get("market_cap"),
                        volume=symbol_data.get("volume"),
                        scanner_type=job.scanner_type,
                        symbol_metadata=symbol_data.get("metadata"),
                    )
                    session.add(result)

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def delete_discovery_job(self, job_id: str) -> bool:
        """
        Delete a discovery job and its results

        Args:
            job_id: The job ID to delete

        Returns:
            True if deletion was successful
        """
        session = self.db_manager.get_session()
        try:
            # Delete results first (foreign key constraint)
            session.query(DiscoveryResult).filter(
                DiscoveryResult.job_id == job_id
            ).delete()

            # Delete job
            job = (
                session.query(DiscoveryJob)
                .filter(DiscoveryJob.job_id == job_id)
                .first()
            )
            if not job:
                return False

            session.delete(job)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()


# Global service instance
discovery_service = DiscoveryService()


def get_discovery_service() -> DiscoveryService:
    """Get the global discovery service instance"""
    return discovery_service
