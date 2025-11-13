"""
V2 Parallel Optimization System - Optimization Service
Handles parameter generation, batch management, and job submission for parallel optimization.
"""

import os
import yaml
import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
import uuid

from backend.models.database import (
    BacktestJob,
    OptimizationBatch,
    Strategy,
    SuccessCriteria,
)
from backend.schemas.optimization import OptimizationConfig, ParameterRange

logger = logging.getLogger(__name__)


class OptimizationService:
    """Service for managing parallel optimization workflows."""

    def __init__(self, db_session):
        """Initialize with database session."""
        self.db = db_session

    def generate_parameter_combinations(self, config_path: str) -> List[Dict[str, Any]]:
        """
        Generate all parameter combinations from optimization config file.

        Args:
            config_path: Path to YAML optimization configuration file

        Returns:
            List of parameter dictionaries, each representing one combination

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        logger.info(f"Generating parameter combinations from config: {config_path}")

        # Resolve config path - handle both absolute and relative paths
        if config_path.startswith("configs/"):
            config_path = os.path.join("/app", config_path)

        logger.info(f"Resolved config path: {config_path}")

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")

        try:
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file: {e}")

        # Logging will happen after parameters_data is determined

        # Validate config structure - check both top-level and under optimization
        parameters_data = None
        if "parameters" in config_data:
            parameters_data = config_data["parameters"]
        elif (
            "optimization" in config_data
            and "parameters" in config_data["optimization"]
        ):
            parameters_data = config_data["optimization"]["parameters"]

        if parameters_data is None:
            raise ValueError(
                "Config must contain 'parameters' section at top level or under 'optimization'"
            )

        logger.info(
            f"Successfully loaded config with {len(parameters_data)} parameter groups"
        )

        # Generate combinations using recursive approach
        param_ranges = {}
        for param_name, param_config in parameters_data.items():
            if not isinstance(param_config, dict) or "start" not in param_config:
                raise ValueError(f"Invalid parameter config for {param_name}")

            param_ranges[param_name] = ParameterRange(**param_config)

        # Generate all combinations
        combinations = self._generate_combinations(param_ranges)

        logger.info(
            f"Generated {len(combinations)} parameter combinations from {config_path}"
        )
        return combinations

    def _generate_combinations(
        self, param_ranges: Dict[str, ParameterRange]
    ) -> List[Dict[str, Any]]:
        """Recursively generate all parameter combinations."""
        if not param_ranges:
            return [{}]

        # Get first parameter
        param_name = next(iter(param_ranges))
        param_range = param_ranges[param_name]
        remaining_params = {k: v for k, v in param_ranges.items() if k != param_name}

        # Generate values for this parameter
        values = []
        current = param_range.start
        while (
            current <= param_range.end
            if param_range.step > 0
            else current >= param_range.end
        ):
            values.append(current)
            current += param_range.step

        # Generate combinations recursively
        combinations = []
        for value in values:
            sub_combinations = self._generate_combinations(remaining_params)
            for sub_combo in sub_combinations:
                combo = {param_name: value}
                combo.update(sub_combo)
                combinations.append(combo)

        return combinations

    def create_optimization_batch(
        self, config_path: str, combinations: List[Dict[str, Any]]
    ) -> str:
        """
        Create a new optimization batch record.

        Args:
            config_path: Path to the optimization config file
            combinations: List of parameter combinations

        Returns:
            Batch ID string
        """
        # Load config to get strategy info
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)

        strategy_name = config_data["strategy"]["name"]

        # Generate unique batch ID
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        random_suffix = str(uuid.uuid4())[:6]
        batch_id = f"opt_{timestamp}_{random_suffix}"

        # Create batch record
        batch = OptimizationBatch(
            id=batch_id,
            strategy_name=strategy_name,
            config_file=config_path,
            total_jobs=len(combinations),
            status="running",
        )

        self.db.add(batch)
        self.db.commit()

        logger.info(
            f"Created optimization batch {batch_id} with {len(combinations)} jobs for strategy {strategy_name}"
        )
        return batch_id

    def submit_backtest_jobs(
        self,
        batch_id: str,
        combinations: List[Dict[str, Any]],
        config: Dict[str, Any],
        max_concurrent: int = 4,
    ) -> List[int]:
        """
        Submit backtest jobs for parameter combinations.

        Args:
            batch_id: Batch identifier
            combinations: List of parameter combinations
            config: Full optimization config
            max_concurrent: Maximum concurrent jobs (for future use)

        Returns:
            List of job IDs
        """
        strategy_name = config["strategy"]["name"]
        lean_project_path = config["strategy"]["lean_project_path"]
        symbols = config.get("symbols", ["SPY"])
        start_date = config.get("start_date", "2020-01-01")
        end_date = config.get("end_date", "2024-01-01")

        job_ids = []

        for i, params in enumerate(combinations):
            # Create job record
            job = BacktestJob(
                batch_id=batch_id,
                strategy_name=strategy_name,
                lean_project_path=lean_project_path,
                parameters=params,
                symbols=symbols,
                status="queued",
            )

            self.db.add(job)
            self.db.flush()  # Get job ID

            job_ids.append(job.id)
            logger.debug(f"Created job {job.id} for batch {batch_id}")

        self.db.commit()

        logger.info(f"Submitted {len(job_ids)} backtest jobs for batch {batch_id}")
        return job_ids

    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of an optimization batch.

        Args:
            batch_id: Batch identifier

        Returns:
            Batch status dict or None if not found
        """
        batch = self.db.query(OptimizationBatch).filter_by(id=batch_id).first()
        if not batch:
            return None

        # Count completed jobs
        completed_count = (
            self.db.query(BacktestJob)
            .filter_by(batch_id=batch_id, status="completed")
            .count()
        )

        # Get best result so far - simplified for now
        # TODO: Implement proper best result query with JSON metrics
        best_result = None

        return {
            "batch_id": batch.id,
            "strategy_name": batch.strategy_name,
            "total_jobs": batch.total_jobs,
            "completed_jobs": completed_count,
            "status": batch.status,
            "created_at": batch.created_at,
            "completed_at": batch.completed_at,
            "best_result": best_result.parameters if best_result else None,
        }

    def cancel_batch(self, batch_id: str) -> bool:
        """
        Cancel an optimization batch and mark remaining jobs as cancelled.

        Args:
            batch_id: Batch identifier

        Returns:
            True if batch was cancelled, False if not found
        """
        batch = self.db.query(OptimizationBatch).filter_by(id=batch_id).first()
        if not batch:
            return False

        # Mark batch as failed
        batch.status = "failed"
        batch.completed_at = datetime.utcnow()

        # Cancel pending jobs
        self.db.query(BacktestJob).filter_by(batch_id=batch_id, status="queued").update(
            {"status": "failed", "error_message": "Batch cancelled"}
        )

        self.db.commit()

        self.db.commit()

        logger.info(f"Cancelled batch {batch_id}")
        return True
