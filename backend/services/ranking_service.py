# Ranking service for managing strategy ranking jobs and results (Epic 26 Story 2)

import os
import json
import uuid
import redis
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from backend.utils.database import DatabaseManager, get_db_manager
from backend.models.discovery import RankingJob, RankingResult


@dataclass
class RankingJobSpec:
    """Individual ranking job specification"""

    job_id: str
    input_type: str
    input_source: Optional[str] = None
    criteria_weights: Optional[Dict[str, float]] = None
    ranking_config: Optional[Dict[str, Any]] = None
    priority: int = 0


class RankingService:
    """Service for managing strategy ranking job submission and status tracking"""

    def __init__(self, redis_host: str = "redis", redis_port: int = 6379):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis = redis.Redis(
            host=self.redis_host, port=self.redis_port, decode_responses=True
        )
        self.db_manager = get_db_manager()

    def submit_ranking_job(
        self,
        input_type: str,
        input_source: Optional[str] = None,
        criteria_weights: Optional[Dict[str, float]] = None,
        ranking_config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """
        Submit a new ranking job to the queue

        Args:
            input_type: Type of input ('csv', 'database', 'results_dir')
            input_source: Input source path or parameters
            criteria_weights: Scoring weights for ranking criteria
            ranking_config: Additional ranking configuration

        Returns:
            Tuple of (job_id, message)
        """
        # Generate unique job ID
        job_id = (
            f"ranking_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        )

        # Set default criteria weights if not provided
        if not criteria_weights:
            criteria_weights = {
                "sharpe_ratio": 40.0,
                "consistency": 20.0,
                "drawdown_control": 20.0,
                "trade_frequency": 10.0,
                "capital_efficiency": 10.0,
            }

        # Create database record
        session = self.db_manager.get_session()
        try:
            ranking_job = RankingJob(
                job_id=job_id,
                input_type=input_type,
                input_source=input_source,
                criteria_weights=criteria_weights,
                ranking_config=ranking_config or {},
                status="running",
                started_at=datetime.now(),
            )

            session.add(ranking_job)
            session.commit()

            # Submit job to Redis queue
            job_spec = RankingJobSpec(
                job_id=job_id,
                input_type=input_type,
                input_source=input_source,
                criteria_weights=criteria_weights,
                ranking_config=ranking_config,
                priority=0,
            )

            job_json = json.dumps(
                {
                    "job_id": job_spec.job_id,
                    "input_type": job_spec.input_type,
                    "input_source": job_spec.input_source,
                    "criteria_weights": job_spec.criteria_weights,
                    "ranking_config": job_spec.ranking_config or {},
                    "priority": job_spec.priority,
                }
            )

            result = self.redis.zadd("ranking_jobs", {job_json: -job_spec.priority})

            return (job_id, f"Submitted ranking job for input type: {input_type}")

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_ranking_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a ranking job

        Args:
            job_id: The job ID to query

        Returns:
            Ranking status information or None if not found
        """
        session = self.db_manager.get_session()
        try:
            job = session.query(RankingJob).filter(RankingJob.job_id == job_id).first()

            if not job:
                return None

            return {
                "job_id": job.job_id,
                "input_type": job.input_type,
                "input_source": job.input_source,
                "status": job.status,
                "progress": job.progress,
                "total_strategies": job.total_strategies,
                "ranked_strategies": job.ranked_strategies,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "error_message": job.error_message,
            }
        finally:
            session.close()

    def get_ranking_results(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the results of a completed ranking job

        Args:
            job_id: The job ID to query

        Returns:
            Ranking results or None if not found/completed
        """
        session = self.db_manager.get_session()
        try:
            # Get job info
            job = session.query(RankingJob).filter(RankingJob.job_id == job_id).first()
            if not job or job.status != "completed":
                return None

            # Get results
            results = (
                session.query(RankingResult)
                .filter(RankingResult.job_id == job_id)
                .all()
            )

            strategies = []
            for result in results:
                strategies.append(
                    {
                        "strategy_name": result.strategy_name,
                        "symbol": result.symbol,
                        "sharpe_ratio": result.sharpe_ratio,
                        "max_drawdown": result.max_drawdown,
                        "win_rate": result.win_rate,
                        "total_trades": result.total_trades,
                        "profit_factor": result.profit_factor,
                        "sharpe_score": result.sharpe_score,
                        "consistency_score": result.consistency_score,
                        "drawdown_score": result.drawdown_score,
                        "frequency_score": result.frequency_score,
                        "efficiency_score": result.efficiency_score,
                        "composite_score": result.composite_score,
                        "rank": result.rank,
                        "metadata": result.strategy_metadata,
                    }
                )

            return {
                "job_id": job.job_id,
                "input_type": job.input_type,
                "input_source": job.input_source,
                "strategies": strategies,
                "total_strategies": len(strategies),
                "criteria_weights": job.criteria_weights,
                "summary": job.result_summary or {},
                "completed_at": job.completed_at,
                "execution_time_seconds": (
                    job.completed_at - job.started_at
                ).total_seconds()
                if job.completed_at and job.started_at
                else None,
            }
        finally:
            session.close()

    def list_ranking_jobs(
        self,
        input_type: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """
        List ranking jobs with optional filtering and pagination

        Args:
            input_type: Filter by input type
            status: Filter by status
            start_date: Filter by creation date start
            end_date: Filter by creation date end
            page: Page number (1-based)
            page_size: Number of results per page

        Returns:
            Paginated ranking jobs results
        """
        session = self.db_manager.get_session()
        try:
            query = session.query(RankingJob)

            # Apply filters
            if input_type:
                query = query.filter(RankingJob.input_type == input_type)
            if status:
                query = query.filter(RankingJob.status == status)
            if start_date:
                query = query.filter(RankingJob.created_at >= start_date)
            if end_date:
                query = query.filter(RankingJob.created_at <= end_date)

            # Get total count
            total = query.count()

            # Apply pagination
            offset = (page - 1) * page_size
            jobs = (
                query.order_by(RankingJob.created_at.desc())
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
                        "input_type": job.input_type,
                        "input_source": job.input_source,
                        "status": job.status,
                        "progress": job.progress,
                        "total_strategies": job.total_strategies,
                        "ranked_strategies": job.ranked_strategies,
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

    def update_ranking_results(
        self,
        job_id: str,
        status: str,
        total_strategies: int = 0,
        ranked_strategies: int = 0,
        result_data: Optional[List[Dict[str, Any]]] = None,
        result_summary: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Update ranking results (called by workers)

        Args:
            job_id: The job ID to update
            status: New status
            total_strategies: Total number of strategies processed
            ranked_strategies: Number of strategies ranked
            result_data: Ranking results data
            result_summary: Summary statistics
            error_message: Error message if failed

        Returns:
            True if update was successful
        """
        session = self.db_manager.get_session()
        try:
            job = session.query(RankingJob).filter(RankingJob.job_id == job_id).first()

            if not job:
                return False

            # Update job status
            job.status = status
            job.total_strategies = total_strategies
            job.ranked_strategies = ranked_strategies
            job.result_summary = result_summary

            if error_message:
                job.error_message = error_message

            if status in ["completed", "failed"]:
                job.completed_at = datetime.now()

            # Store individual results if provided
            if result_data and status == "completed":
                for strategy_data in result_data:
                    result = RankingResult(
                        job_id=job_id,
                        strategy_name=strategy_data["strategy_name"],
                        symbol=strategy_data.get("symbol"),
                        sharpe_ratio=strategy_data.get("sharpe_ratio"),
                        max_drawdown=strategy_data.get("max_drawdown"),
                        win_rate=strategy_data.get("win_rate"),
                        total_trades=strategy_data.get("total_trades"),
                        profit_factor=strategy_data.get("profit_factor"),
                        sharpe_score=strategy_data.get("sharpe_score"),
                        consistency_score=strategy_data.get("consistency_score"),
                        drawdown_score=strategy_data.get("drawdown_score"),
                        frequency_score=strategy_data.get("frequency_score"),
                        efficiency_score=strategy_data.get("efficiency_score"),
                        composite_score=strategy_data["composite_score"],
                        rank=strategy_data["rank"],
                        strategy_metadata=strategy_data.get("metadata"),
                    )
                    session.add(result)

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def delete_ranking_job(self, job_id: str) -> bool:
        """
        Delete a ranking job and its results

        Args:
            job_id: The job ID to delete

        Returns:
            True if deletion was successful
        """
        session = self.db_manager.get_session()
        try:
            # Delete results first (foreign key constraint)
            session.query(RankingResult).filter(RankingResult.job_id == job_id).delete()

            # Delete job
            job = session.query(RankingJob).filter(RankingJob.job_id == job_id).first()
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
ranking_service = RankingService()


def get_ranking_service() -> RankingService:
    """Get the global ranking service instance"""
    return ranking_service
