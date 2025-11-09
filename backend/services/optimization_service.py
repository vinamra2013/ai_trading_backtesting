# Optimization service for managing parameter optimization jobs (Epic 25 Story 5)

import os
import json
import uuid
import itertools
import random
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Iterator
from dataclasses import dataclass

try:
    import optuna

    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    optuna = None

try:
    from scripts.mlflow_logger import MLflowBacktestLogger

    MLFLOW_LOGGER_AVAILABLE = True
except ImportError:
    MLFLOW_LOGGER_AVAILABLE = False
    MLflowBacktestLogger = None

from backend.utils.database import DatabaseManager, get_db_manager
from backend.services.backtest_service import get_backtest_service
from backend.models.backtest import Optimization
from backend.schemas.optimization import (
    OptimizationRequest,
    ParameterSpaceItem,
    OptimizationTrial,
)

logger = logging.getLogger(__name__)


@dataclass
class OptimizationJob:
    """Optimization job specification"""

    job_id: str
    strategy: str
    symbols: List[str]
    parameter_space: Dict[str, ParameterSpaceItem]
    objective_metric: str
    max_trials: int
    timeframe: str
    start_date: Optional[str]
    end_date: Optional[str]
    optimization_method: str


class OptimizationService:
    """Service for managing optimization jobs and parameter search"""

    def __init__(self):
        self.db_manager = get_db_manager()
        self.backtest_service = get_backtest_service()
        self.mlflow_logger = None
        if MLFLOW_LOGGER_AVAILABLE:
            try:
                self.mlflow_logger = MLflowBacktestLogger()
                logger.info("MLflow logger initialized for optimization tracking")
            except Exception as e:
                logger.warning(f"Failed to initialize MLflow logger: {e}")
                self.mlflow_logger = None

    def _validate_strategy(self, strategy: str) -> str:
        """Validate and normalize strategy path"""
        strategy_path = Path(strategy)
        if not strategy_path.exists():
            strategy_path = Path("strategies") / strategy
            if not strategy_path.exists():
                strategy_path = strategy_path.with_suffix(".py")

        if not strategy_path.exists():
            raise FileNotFoundError(f"Strategy file not found: {strategy}")

        return str(strategy_path)

    def _generate_parameter_combinations(
        self,
        parameter_space: Dict[str, ParameterSpaceItem],
        method: str = "grid",
        max_trials: int = 50,
    ) -> Iterator[Dict[str, Any]]:
        """
        Generate parameter combinations based on optimization method

        Args:
            parameter_space: Parameter definitions
            method: 'grid', 'random', or 'bayesian'
            max_trials: Maximum number of combinations to generate

        Yields:
            Parameter combinations as dictionaries
        """
        if method == "grid":
            # Generate all possible combinations
            param_lists = []
            param_names = []

            for name, param_def in parameter_space.items():
                param_names.append(name)
                if param_def.type == "categorical":
                    param_lists.append(param_def.choices)
                elif param_def.type in ["int", "float"]:
                    # For grid search, we'll sample a few values
                    # In a real implementation, you might want more sophisticated grid generation
                    if param_def.type == "int":
                        step = max(1, int((param_def.high - param_def.low) / 5))
                        values = list(
                            range(int(param_def.low), int(param_def.high) + 1, step)
                        )
                    else:
                        values = [
                            param_def.low + i * (param_def.high - param_def.low) / 5
                            for i in range(6)
                        ]
                    param_lists.append(values)
                else:
                    raise ValueError(f"Unsupported parameter type: {param_def.type}")

            # Generate combinations, limited by max_trials
            combinations = list(itertools.product(*param_lists))
            random.shuffle(combinations)  # Randomize order

            for combo in combinations[:max_trials]:
                yield dict(zip(param_names, combo))

        elif method == "random":
            # Random sampling
            for _ in range(max_trials):
                params = {}
                for name, param_def in parameter_space.items():
                    if param_def.type == "categorical":
                        params[name] = random.choice(param_def.choices)
                    elif param_def.type == "int":
                        params[name] = random.randint(
                            int(param_def.low), int(param_def.high)
                        )
                    elif param_def.type == "float":
                        params[name] = random.uniform(param_def.low, param_def.high)
                yield params

        elif method == "bayesian":
            # Placeholder for Bayesian optimization
            # In a real implementation, this would use Optuna or similar
            if not OPTUNA_AVAILABLE:
                raise RuntimeError(
                    "Bayesian optimization requires Optuna. Install with: pip install optuna"
                )

            # For now, fall back to random sampling
            logger.warning(
                "Bayesian optimization not fully implemented, using random sampling"
            )
            yield from self._generate_parameter_combinations(
                parameter_space, "random", max_trials
            )

        else:
            raise ValueError(f"Unsupported optimization method: {method}")

    def submit_optimization(self, request: OptimizationRequest) -> Tuple[str, str]:
        """
        Submit a new optimization job

        Args:
            request: Optimization request parameters

        Returns:
            Tuple of (job_id, message)
        """
        # Validate strategy
        validated_strategy = self._validate_strategy(request.strategy)

        # Generate unique job ID
        job_id = (
            f"opt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        )

        # Create MLflow experiment for this optimization
        mlflow_experiment_id = None
        if self.mlflow_logger:
            try:
                experiment_name = f"optimization.{request.strategy}.{job_id}"
                mlflow_experiment_id = self.mlflow_logger.log_optimization_study(
                    study_name=experiment_name,
                    best_params={},  # Will be updated when optimization completes
                    best_value=0.0,  # Will be updated when optimization completes
                    optimization_metrics={
                        "max_trials": request.max_trials,
                        "optimization_method": request.optimization_method,
                        "objective_metric": request.objective_metric,
                        "symbols": len(request.symbols),
                    },
                    tags={
                        "optimization_job_id": job_id,
                        "strategy": request.strategy,
                        "status": "running",
                        "created_by": "api_backend",
                    },
                )
                logger.info(
                    f"Created MLflow experiment {mlflow_experiment_id} for optimization {job_id}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to create MLflow experiment for optimization {job_id}: {e}"
                )

        # Create database record
        session = self.db_manager.get_session()
        try:
            # Convert parameter space to dict for storage
            param_space_dict = {}
            for name, param_item in request.parameter_space.items():
                param_space_dict[name] = param_item.dict()

            optimization = self.db_manager.create_optimization(
                session=session,
                strategy_name=request.strategy,  # Store original name
                parameter_space=param_space_dict,
                objective_metric=request.objective_metric,
                status="running",
                started_at=datetime.now(),
                max_trials=request.max_trials,
                optimization_method=request.optimization_method,
                mlflow_experiment_id=mlflow_experiment_id,
            )
            # Convert parameter space to dict for storage
            param_space_dict = {}
            for name, param_item in request.parameter_space.items():
                param_space_dict[name] = param_item.dict()

            optimization = self.db_manager.create_optimization(
                session=session,
                strategy_name=request.strategy,  # Store original name
                parameter_space=param_space_dict,
                objective_metric=request.objective_metric,
                status="running",
                started_at=datetime.now(),
                max_trials=request.max_trials,
                optimization_method=request.optimization_method,
                mlflow_experiment_id=mlflow_experiment_id,
            )

            # Generate parameter combinations and submit backtests
            param_combinations = list(
                self._generate_parameter_combinations(
                    request.parameter_space,
                    request.optimization_method,
                    request.max_trials,
                )
            )

            jobs_submitted = 0
            for trial_num, params in enumerate(param_combinations, 1):
                try:
                    # Submit individual backtest
                    bt_job_id, _ = self.backtest_service.submit_backtest(
                        strategy=validated_strategy,  # Use validated path
                        symbols=request.symbols,
                        parameters=params,
                        timeframe=request.timeframe,
                        start_date=request.start_date,
                        end_date=request.end_date,
                    )

                    # Log trial to MLflow if experiment was created
                    if self.mlflow_logger and mlflow_experiment_id:
                        try:
                            self.mlflow_logger.log_child_trial(
                                parent_run_id=mlflow_experiment_id,
                                trial_params=params,
                                trial_metrics={},  # Will be updated when backtest completes
                                trial_number=trial_num,
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to log trial {trial_num} to MLflow: {e}"
                            )

                    jobs_submitted += 1
                    logger.info(
                        f"Submitted backtest {bt_job_id} for optimization {job_id} (trial {trial_num})"
                    )
                except Exception as e:
                    logger.error(f"Failed to submit backtest for params {params}: {e}")
                    continue

            session.commit()
            message = f"Submitted optimization job with {jobs_submitted} parameter combinations"
            return job_id, message

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_optimization_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of an optimization job

        Args:
            job_id: The optimization job ID

        Returns:
            Optimization status information or None if not found
        """
        session = self.db_manager.get_session()
        try:
            # Find optimization by job_id pattern
            optimization = (
                session.query(Optimization)
                .filter(Optimization.strategy_name.like(f"%{job_id}%"))
                .first()
            )

            if not optimization:
                return None

            # Count completed backtests for this optimization
            # This is a simplified approach - in production you'd want a more robust linking
            backtest_count = 0
            completed_count = 0

            # Get all backtests that might be part of this optimization
            # (This is approximate - you'd want better linking in production)
            backtests = session.query(Optimization).all()  # Placeholder

            return {
                "id": optimization.id,
                "job_id": job_id,
                "strategy_name": optimization.strategy_name,
                "status": optimization.status,
                "objective_metric": optimization.objective_metric,
                "max_trials": getattr(optimization, "max_trials", None),
                "current_trial": completed_count,
                "best_metric_value": optimization.best_metric_value,
                "best_parameters": optimization.best_parameters,
                "mlflow_experiment_id": optimization.mlflow_experiment_id,
                "created_at": optimization.created_at,
                "started_at": optimization.started_at,
                "completed_at": optimization.completed_at,
            }
        finally:
            session.close()

    def list_optimizations(
        self,
        strategy: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """
        List optimizations with optional filtering and pagination

        Args:
            strategy: Filter by strategy name
            status: Filter by status
            start_date: Filter by creation date start
            end_date: Filter by creation date end
            page: Page number (1-based)
            page_size: Number of results per page

        Returns:
            Paginated optimization results
        """
        session = self.db_manager.get_session()
        try:
            query = session.query(Optimization)

            # Apply filters
            if strategy:
                query = query.filter(Optimization.strategy_name.ilike(f"%{strategy}%"))
            if status:
                query = query.filter(Optimization.status == status)
            if start_date:
                query = query.filter(Optimization.created_at >= start_date)
            if end_date:
                query = query.filter(Optimization.created_at <= end_date)

            # Get total count
            total = query.count()

            # Apply pagination
            offset = (page - 1) * page_size
            optimizations = (
                query.order_by(Optimization.created_at.desc())
                .offset(offset)
                .limit(page_size)
                .all()
            )

            # Convert to dict format
            optimization_list = []
            for opt in optimizations:
                optimization_list.append(
                    {
                        "id": opt.id,
                        "job_id": f"opt_{opt.id}",  # Simplified job ID
                        "strategy_name": opt.strategy_name,
                        "status": opt.status,
                        "objective_metric": opt.objective_metric,
                        "max_trials": getattr(opt, "max_trials", None),
                        "current_trial": None,  # Would need to calculate
                        "best_metric_value": opt.best_metric_value,
                        "best_parameters": opt.best_parameters,
                        "mlflow_experiment_id": opt.mlflow_experiment_id,
                        "created_at": opt.created_at,
                        "started_at": opt.started_at,
                        "completed_at": opt.completed_at,
                    }
                )

            total_pages = (total + page_size - 1) // page_size

            return {
                "optimizations": optimization_list,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }
        finally:
            session.close()

    def get_optimization_details(
        self, optimization_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific optimization

        Args:
            optimization_id: The optimization ID to query

        Returns:
            Detailed optimization information or None if not found
        """
        session = self.db_manager.get_session()
        try:
            optimization = (
                session.query(Optimization)
                .filter(Optimization.id == optimization_id)
                .first()
            )

            if not optimization:
                return None

            return {
                "id": optimization.id,
                "job_id": f"opt_{optimization.id}",
                "strategy_name": optimization.strategy_name,
                "parameter_space": optimization.parameter_space,
                "objective_metric": optimization.objective_metric,
                "max_trials": getattr(optimization, "max_trials", None),
                "optimization_method": getattr(
                    optimization, "optimization_method", "grid"
                ),
                "status": optimization.status,
                "current_trial": None,  # Would need to calculate from backtests
                "best_metric_value": optimization.best_metric_value,
                "best_parameters": optimization.best_parameters,
                "best_result_id": optimization.best_result_id,
                "mlflow_experiment_id": optimization.mlflow_experiment_id,
                "trials_completed": None,  # Would need to calculate
                "trials_data": None,  # Would need to fetch from backtests
                "created_at": optimization.created_at,
                "started_at": optimization.started_at,
                "completed_at": optimization.completed_at,
            }
        finally:
            session.close()

    def update_optimization_results(
        self,
        job_id: str,
        status: str,
        best_parameters: Optional[Dict[str, Any]] = None,
        best_metric_value: Optional[float] = None,
        best_result_id: Optional[int] = None,
        mlflow_experiment_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Update optimization results (called when optimization completes)

        Args:
            job_id: The optimization job ID
            status: New status
            best_parameters: Best parameter combination found
            best_metric_value: Best metric value achieved
            best_result_id: ID of best backtest result
            mlflow_experiment_id: MLflow experiment ID
            error_message: Error message if failed

        Returns:
            True if update was successful
        """
        session = self.db_manager.get_session()
        try:
            # Find optimization by job_id pattern
            optimization = (
                session.query(Optimization)
                .filter(Optimization.strategy_name.like(f"%{job_id}%"))
                .first()
            )

            if not optimization:
                return False

            # Update fields using setattr (SQLAlchemy Column objects)
            setattr(optimization, "status", status)
            if best_parameters:
                setattr(optimization, "best_parameters", best_parameters)
            if best_metric_value is not None:
                setattr(optimization, "best_metric_value", best_metric_value)
            if best_result_id:
                setattr(optimization, "best_result_id", best_result_id)
            if mlflow_experiment_id:
                setattr(optimization, "mlflow_experiment_id", mlflow_experiment_id)
            if status in ["completed", "failed"]:
                setattr(optimization, "completed_at", datetime.now())

            # Update MLflow experiment with final results if available
            if (
                self.mlflow_logger
                and hasattr(optimization, "mlflow_experiment_id")
                and optimization.mlflow_experiment_id
                and status == "completed"
            ):
                try:
                    # Update the parent run with final optimization results
                    final_metrics = {
                        "final_best_value": best_metric_value or 0.0,
                        "total_trials_completed": getattr(
                            optimization, "max_trials", 0
                        ),
                        "optimization_status": "completed",
                    }
                    # Note: In a production system, you'd want to update the existing MLflow run
                    # rather than create a new one. This is a simplified approach.
                    logger.info(
                        f"Optimization {job_id} completed - best value: {best_metric_value}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to update MLflow experiment for completed optimization {job_id}: {e}"
                    )

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()


# Global service instance
optimization_service = OptimizationService()


def get_optimization_service() -> OptimizationService:
    """Get the global optimization service instance"""
    return optimization_service
