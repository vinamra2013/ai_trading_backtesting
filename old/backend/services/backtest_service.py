# Backtest service for managing backtest jobs and results (Epic 25 Stories 3 & 4)

import os
import json
import uuid
import redis
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from backend.utils.database import DatabaseManager, get_db_manager
from backend.models.backtest import Backtest


@dataclass
class BacktestJob:
    """Individual backtest job specification (matches parallel_backtest.py)"""

    job_id: str
    symbol: str
    strategy_path: str
    start_date: str
    end_date: str
    strategy_params: Optional[Dict[str, Any]] = None
    mlflow_config: Optional[Dict[str, Any]] = None
    batch_id: Optional[str] = None
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for serialization"""
        return {
            "job_id": self.job_id,
            "symbol": self.symbol,
            "strategy_path": self.strategy_path,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "strategy_params": self.strategy_params or {},
            "mlflow_config": self.mlflow_config or {},
            "batch_id": self.batch_id,
            "priority": self.priority,
        }


class BacktestService:
    """Service for managing backtest job submission and status tracking"""

    def __init__(self, redis_host: str = "redis", redis_port: int = 6379):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis = redis.Redis(
            host=self.redis_host, port=self.redis_port, decode_responses=True
        )
        self.db_manager = get_db_manager()

    def _validate_strategy(self, strategy: str) -> str:
        """Validate and normalize strategy path like parallel_backtest.py does"""
        strategy_path = Path(strategy)
        if not strategy_path.exists():
            strategy_path = Path("strategies") / strategy
            if not strategy_path.exists():
                strategy_path = strategy_path.with_suffix(".py")

        if not strategy_path.exists():
            raise FileNotFoundError(f"Strategy file not found: {strategy}")

        return str(strategy_path)

    def submit_backtest(
        self,
        strategy: str,
        symbols: List[str],
        parameters: Optional[Dict[str, Any]],
        timeframe: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Tuple[str, str]:
        # Validate date range to prevent performance issues
        if start_date and end_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            days_diff = (end_dt - start_dt).days
            if days_diff > 365:  # Limit to 1 year for API backtests
                raise ValueError(
                    f"Date range too long: {days_diff} days. Maximum allowed is 365 days for API backtests."
                )
        """
        Submit a new backtest job to the queue

        Args:
            strategy: Strategy name or path
            symbols: List of symbols to test
            parameters: Strategy parameters
            timeframe: Timeframe for backtest
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Tuple of (job_id, message)
        """
        # Validate strategy
        validated_strategy = self._validate_strategy(strategy)

        # Set default dates if not provided
        start_date = start_date or "2020-01-01"
        end_date = end_date or "2024-12-31"

        # Generate unique job ID
        job_id = (
            f"api_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        )

        # Create database record
        session = self.db_manager.get_session()
        try:
            backtest = self.db_manager.create_backtest(
                session=session,
                strategy_name=strategy,  # Store original name for API queries
                symbols=symbols,
                parameters=parameters or {},
                timeframe=timeframe,
                status="running",
                started_at=datetime.now(),
            )

            # Submit jobs to Redis queue for each symbol
            batch_id = f"batch_{job_id}"
            jobs_submitted = 0

            for symbol in symbols:
                job = BacktestJob(
                    job_id=f"{job_id}_{symbol}",
                    symbol=symbol,
                    strategy_path=validated_strategy,  # Use validated full path
                    start_date=start_date or "2020-01-01",
                    end_date=end_date or "2024-12-31",
                    strategy_params=parameters or {},
                    mlflow_config={
                        "enabled": True,
                        "project": "api_backtests",
                        "asset_class": "Equities",
                        "strategy_family": Path(validated_strategy).stem,
                        "team": "api_users",
                        "status": "research",
                    },
                    batch_id=batch_id,
                    priority=0,
                )

                # Submit to Redis queue
                job_json = json.dumps(job.to_dict())
                print(f"DEBUG: Submitting job to Redis: {job_json[:100]}...")
                result = self.redis.zadd("backtest_jobs", {job_json: -job.priority})
                print(f"DEBUG: Redis ZADD result: {result}")
                jobs_submitted += 1

            session.commit()
            return (
                job_id,
                f"Submitted {jobs_submitted} backtest jobs for {len(symbols)} symbols",
            )

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_backtest_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a backtest job

        Args:
            job_id: The job ID to query

        Returns:
            Backtest status information or None if not found
        """
        session = self.db_manager.get_session()
        try:
            # Find backtest by job_id (stored in strategy_name for API jobs)
            backtest = (
                session.query(Backtest)
                .filter(Backtest.strategy_name.like(f"%{job_id}%"))
                .first()
            )

            if not backtest:
                return None

            return {
                "id": backtest.id,
                "job_id": job_id,
                "strategy_name": backtest.strategy_name,
                "symbols": backtest.symbols,
                "status": backtest.status,
                "created_at": backtest.created_at,
                "started_at": backtest.started_at,
                "completed_at": backtest.completed_at,
                "mlflow_run_id": backtest.mlflow_run_id,
                "metrics": backtest.metrics,
            }
        finally:
            session.close()

    def list_backtests(
        self,
        strategy: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """
        List backtests with optional filtering and pagination

        Args:
            strategy: Filter by strategy name
            status: Filter by status
            start_date: Filter by creation date start
            end_date: Filter by creation date end
            page: Page number (1-based)
            page_size: Number of results per page

        Returns:
            Paginated backtest results
        """
        session = self.db_manager.get_session()
        try:
            query = session.query(Backtest)

            # Apply filters
            if strategy:
                query = query.filter(Backtest.strategy_name.ilike(f"%{strategy}%"))
            if status:
                query = query.filter(Backtest.status == status)
            if start_date:
                query = query.filter(Backtest.created_at >= start_date)
            if end_date:
                query = query.filter(Backtest.created_at <= end_date)

            # Get total count
            total = query.count()

            # Apply pagination
            offset = (page - 1) * page_size
            backtests = (
                query.order_by(Backtest.created_at.desc())
                .offset(offset)
                .limit(page_size)
                .all()
            )

            # Convert to dict format
            backtest_list = []
            for bt in backtests:
                backtest_list.append(
                    {
                        "id": bt.id,
                        "strategy_name": bt.strategy_name,
                        "symbols": bt.symbols,
                        "status": bt.status,
                        "created_at": bt.created_at,
                        "started_at": bt.started_at,
                        "completed_at": bt.completed_at,
                        "mlflow_run_id": bt.mlflow_run_id,
                    }
                )

            total_pages = (total + page_size - 1) // page_size

            return {
                "backtests": backtest_list,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }
        finally:
            session.close()

    def get_backtest_details(self, backtest_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific backtest

        Args:
            backtest_id: The backtest ID to query

        Returns:
            Detailed backtest information or None if not found
        """
        session = self.db_manager.get_session()
        try:
            backtest = (
                session.query(Backtest).filter(Backtest.id == backtest_id).first()
            )

            if not backtest:
                return None

            return {
                "id": backtest.id,
                "strategy_name": backtest.strategy_name,
                "symbols": backtest.symbols,
                "parameters": backtest.parameters,
                "timeframe": backtest.timeframe,
                "status": backtest.status,
                "metrics": backtest.metrics,
                "mlflow_run_id": backtest.mlflow_run_id,
                "created_at": backtest.created_at,
                "started_at": backtest.started_at,
                "completed_at": backtest.completed_at,
            }
        finally:
            session.close()

    def update_backtest_results(
        self,
        job_id: str,
        status: str,
        metrics: Optional[Dict[str, Any]] = None,
        mlflow_run_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Update backtest results (called by workers)

        Args:
            job_id: The job ID to update
            status: New status
            metrics: Backtest metrics
            mlflow_run_id: MLflow run ID
            error_message: Error message if failed

        Returns:
            True if update was successful
        """
        session = self.db_manager.get_session()
        try:
            # Find backtest by job_id pattern
            backtest = (
                session.query(Backtest)
                .filter(Backtest.strategy_name.like(f"%{job_id}%"))
                .first()
            )

            if not backtest:
                return False

            # Update fields using setattr (SQLAlchemy Column objects)
            setattr(backtest, "status", status)
            if metrics:
                setattr(backtest, "metrics", metrics)
            if mlflow_run_id:
                setattr(backtest, "mlflow_run_id", mlflow_run_id)
            if status in ["completed", "failed"]:
                setattr(backtest, "completed_at", datetime.now())

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def delete_backtest(self, backtest_id: int) -> bool:
        """
        Delete a backtest by ID

        Args:
            backtest_id: The backtest ID to delete

        Returns:
            True if deletion was successful
        """
        session = self.db_manager.get_session()
        try:
            backtest = (
                session.query(Backtest).filter(Backtest.id == backtest_id).first()
            )

            if not backtest:
                return False

            session.delete(backtest)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()


# Global service instance
backtest_service = BacktestService()


def get_backtest_service() -> BacktestService:
    """Get the global backtest service instance"""
    return backtest_service
