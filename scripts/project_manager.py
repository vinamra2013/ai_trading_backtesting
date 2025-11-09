#!/usr/bin/env python3
"""
Project Manager - Epic 17: US-17.13
Project management utilities for experiment organization and querying.

This module provides ProjectManager class for intelligent experiment organization,
implementing the hybrid approach with dot notation naming and comprehensive tagging.

Features:
- Experiment creation with naming conventions
- Tag management utilities
- Query pattern library
- Example workflows for common use cases
"""

import mlflow
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
import logging
import re
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProjectManager:
    """
    Project management utilities for MLflow experiment organization.

    Implements hybrid approach:
    - Layer 1: Dot notation naming (Project.AssetClass.StrategyFamily.Strategy)
    - Layer 2: Comprehensive tagging for filtering and organization
    - Layer 3: Parent-child runs for optimization studies
    """

    def __init__(self, tracking_uri: Optional[str] = None):
        """
        Initialize project manager.

        Args:
            tracking_uri: MLflow tracking server URI. If None, uses environment variable
                         or defaults to Docker service name for container environments.
        """
        if tracking_uri is None:
            # Try environment variable first
            tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")

            # If not set, use Docker service name for container environments
            if not tracking_uri:
                import os

                if os.path.exists("/.dockerenv"):
                    tracking_uri = "http://mlflow:5000"
                else:
                    tracking_uri = "http://localhost:5000"

        self.tracking_uri = tracking_uri
        self.mlflow_available = False

        try:
            mlflow.set_tracking_uri(tracking_uri)
            self.mlflow_available = True
            logger.info(
                f"Project manager initialized with tracking URI: {tracking_uri}"
            )
        except Exception as e:
            logger.warning(
                f"Failed to initialize MLflow client: {e}. Continuing without MLflow."
            )
            self.mlflow_available = False

    # === NAMING CONVENTIONS ===

    def build_experiment_name(
        self, project: str, asset_class: str, strategy_family: str, strategy: str
    ) -> str:
        """
        Build experiment name using dot notation convention.

        Args:
            project: Project name (e.g., 'Q1_2025')
            asset_class: Asset class (e.g., 'Equities', 'Futures')
            strategy_family: Strategy family (e.g., 'MeanReversion', 'Momentum')
            strategy: Strategy name (e.g., 'SMACrossover')

        Returns:
            Experiment name in dot notation
        """
        return f"{project}.{asset_class}.{strategy_family}.{strategy}"

    def parse_experiment_name(self, experiment_name: str) -> Dict[str, str]:
        """
        Parse experiment name into components.

        Args:
            experiment_name: Experiment name in dot notation

        Returns:
            Dictionary with project, asset_class, strategy_family, strategy
        """
        parts = experiment_name.split(".")
        if len(parts) != 4:
            raise ValueError(
                f"Invalid experiment name format: {experiment_name}. Expected: Project.AssetClass.StrategyFamily.Strategy"
            )

        return {
            "project": parts[0],
            "asset_class": parts[1],
            "strategy_family": parts[2],
            "strategy": parts[3],
        }

    # === TAG MANAGEMENT ===

    def build_experiment_tags(
        self,
        project: str,
        asset_class: str,
        strategy_family: str,
        strategy: str,
        team: str = "quant_research",
        status: str = "research",
        **kwargs,
    ) -> Dict[str, str]:
        """
        Build comprehensive tagging dictionary for experiments.

        Args:
            project: Project name
            asset_class: Asset class
            strategy_family: Strategy family
            strategy: Strategy name
            team: Team responsible
            status: Experiment status (research, testing, production, archived)
            **kwargs: Additional tags

        Returns:
            Comprehensive tagging dictionary
        """
        tags = {
            "project": project,
            "asset_class": asset_class,
            "strategy_family": strategy_family,
            "strategy": strategy,
            "team": team,
            "status": status,
            "created_date": datetime.now().isoformat(),
            "created_by": "project_manager",
            "naming_convention": "dot_notation_v1",
        }

        # Add any additional tags
        tags.update(kwargs)
        return tags

    def build_run_tags(
        self,
        run_type: str = "backtest",
        optimization_trial: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, str]:
        """
        Build tagging dictionary for individual runs.

        Args:
            run_type: Type of run (backtest, optimization, analysis)
            optimization_trial: Trial number for optimization runs
            **kwargs: Additional tags

        Returns:
            Run tagging dictionary
        """
        tags = {
            "run_type": run_type,
            "run_timestamp": datetime.now().isoformat(),
            "run_by": "project_manager",
        }

        if optimization_trial is not None:
            tags["optimization_trial"] = str(optimization_trial)

        tags.update(kwargs)
        return tags

    # === EXPERIMENT MANAGEMENT ===

    def create_experiment(
        self,
        project: str,
        asset_class: str,
        strategy_family: str,
        strategy: str,
        team: str = "quant_research",
        status: str = "research",
        **kwargs,
    ) -> Optional[str]:
        """
        Create experiment with proper naming and tagging.

        Args:
            project: Project name
            asset_class: Asset class
            strategy_family: Strategy family
            strategy: Strategy name
            team: Team responsible
            status: Experiment status
            **kwargs: Additional experiment tags

        Returns:
            Experiment ID if successful, None otherwise
        """
        if not self.mlflow_available:
            logger.warning("MLflow not available, skipping experiment creation")
            return None

        experiment_name = self.build_experiment_name(
            project, asset_class, strategy_family, strategy
        )
        tags = self.build_experiment_tags(
            project, asset_class, strategy_family, strategy, team, status, **kwargs
        )

        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(
                    name=experiment_name, tags=tags
                )
                logger.info(f"Created experiment: {experiment_name}")
                return experiment_id
            else:
                logger.info(f"Experiment already exists: {experiment_name}")
                return experiment.experiment_id
        except Exception as e:
            logger.error(f"Failed to create experiment {experiment_name}: {e}")
            return None

    def get_or_create_experiment(
        self, experiment_name: str, tags: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Get existing experiment or create new one.

        Args:
            experiment_name: Experiment name
            tags: Experiment tags

        Returns:
            Experiment ID
        """
        if not self.mlflow_available:
            return None

        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(
                    name=experiment_name, tags=tags or {}
                )
                logger.info(f"Created experiment: {experiment_name}")
                return experiment_id
            else:
                return experiment.experiment_id
        except Exception as e:
            logger.error(f"Failed to get/create experiment {experiment_name}: {e}")
            return None

    # === QUERY PATTERNS ===

    def query_by_project(self, project: str, max_results: int = 100) -> List[Dict]:
        """
        Query experiments by project.

        Args:
            project: Project name
            max_results: Maximum results to return

        Returns:
            List of experiment information dictionaries
        """
        filter_string = f"name LIKE '{project}.%'"
        return self.query_experiments(filter_string, max_results)

    def query_by_asset_class(
        self, asset_class: str, max_results: int = 100
    ) -> List[Dict]:
        """
        Query experiments by asset class.

        Args:
            asset_class: Asset class name
            max_results: Maximum results to return

        Returns:
            List of experiment information dictionaries
        """
        filter_string = f"name LIKE '%.{asset_class}.%'"
        return self.query_experiments(filter_string, max_results)

    def query_by_strategy_family(
        self, strategy_family: str, max_results: int = 100
    ) -> List[Dict]:
        """
        Query experiments by strategy family.

        Args:
            strategy_family: Strategy family name
            max_results: Maximum results to return

        Returns:
            List of experiment information dictionaries
        """
        filter_string = f"name LIKE '%.{strategy_family}.%'"
        return self.query_experiments(filter_string, max_results)

    def query_by_team(self, team: str, max_results: int = 100) -> List[Dict]:
        """
        Query experiments by team.

        Args:
            team: Team name
            max_results: Maximum results to return

        Returns:
            List of experiment information dictionaries
        """
        filter_string = f"tags.team = '{team}'"
        return self.query_experiments(filter_string, max_results)

    def query_by_status(self, status: str, max_results: int = 100) -> List[Dict]:
        """
        Query experiments by status.

        Args:
            status: Experiment status
            max_results: Maximum results to return

        Returns:
            List of experiment information dictionaries
        """
        filter_string = f"tags.status = '{status}'"
        return self.query_experiments(filter_string, max_results)

    def query_recent_experiments(
        self, days: int = 7, max_results: int = 50
    ) -> List[Dict]:
        """
        Query recently created experiments.

        Args:
            days: Number of days to look back
            max_results: Maximum results to return

        Returns:
            List of experiment information dictionaries
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        filter_string = f"creation_time >= {int(cutoff_date.timestamp() * 1000)}"
        return self.query_experiments(filter_string, max_results)

    def query_experiments(
        self, filter_string: Optional[str] = None, max_results: int = 100
    ) -> List[Dict]:
        """
        Query experiments with optional filtering.

        Args:
            filter_string: MLflow filter string
            max_results: Maximum results to return

        Returns:
            List of experiment information dictionaries
        """
        if not self.mlflow_available:
            return []

        try:
            experiments = mlflow.search_experiments(
                filter_string=filter_string, max_results=max_results
            )

            return [
                {
                    "experiment_id": exp.experiment_id,
                    "name": exp.name,
                    "lifecycle_stage": exp.lifecycle_stage,
                    "tags": exp.tags,
                    "creation_time": exp.creation_time,
                    "last_update_time": exp.last_update_time,
                }
                for exp in experiments
            ]
        except Exception as e:
            logger.error(f"Failed to query experiments: {e}")
            return []

    # === RUN MANAGEMENT ===

    def query_runs_by_experiment(
        self,
        experiment_name: str,
        filter_string: Optional[str] = None,
        max_results: int = 100,
    ) -> List[Dict]:
        """
        Query runs within a specific experiment.

        Args:
            experiment_name: Name of experiment
            filter_string: Additional filter string
            max_results: Maximum results to return

        Returns:
            List of run information dictionaries
        """
        if not self.mlflow_available:
            return []

        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if not experiment:
                logger.warning(f"Experiment not found: {experiment_name}")
                return []

            # Build filter string
            base_filter = f"experiment_id = '{experiment.experiment_id}'"
            if filter_string:
                full_filter = f"{base_filter} AND {filter_string}"
            else:
                full_filter = base_filter

            runs = mlflow.search_runs(
                filter_string=full_filter, max_results=max_results
            )

            return [
                {
                    "run_id": run.info.run_id,
                    "experiment_id": run.info.experiment_id,
                    "status": run.info.status,
                    "start_time": run.info.start_time,
                    "end_time": run.info.end_time,
                    "metrics": run.data.metrics,
                    "params": run.data.params,
                    "tags": run.data.tags,
                }
                for run in runs
            ]
        except Exception as e:
            logger.error(f"Failed to query runs for experiment {experiment_name}: {e}")
            return []

    def get_best_run(
        self, experiment_name: str, metric: str, maximize: bool = True
    ) -> Optional[Dict]:
        """
        Get the best run for a given metric in an experiment.

        Args:
            experiment_name: Name of experiment
            metric: Metric name to optimize
            maximize: Whether to maximize (True) or minimize (False) the metric

        Returns:
            Best run information dictionary, or None if not found
        """
        runs = self.query_runs_by_experiment(experiment_name)

        if not runs:
            return None

        # Filter runs that have the metric
        valid_runs = [run for run in runs if metric in run.get("metrics", {})]

        if not valid_runs:
            return None

        # Find best run
        if maximize:
            best_run = max(valid_runs, key=lambda r: r["metrics"][metric])
        else:
            best_run = min(valid_runs, key=lambda r: r["metrics"][metric])

        return best_run

    # === UTILITY METHODS ===

    def validate_experiment_name(self, experiment_name: str) -> bool:
        """
        Validate experiment name format.

        Args:
            experiment_name: Experiment name to validate

        Returns:
            True if valid, False otherwise
        """
        pattern = r"^[^.]+\.[^.]+\.[^.]+\.[^.]+$"
        return bool(re.match(pattern, experiment_name))

    def list_projects(self) -> List[str]:
        """
        List all unique projects.

        Returns:
            List of project names
        """
        experiments = self.query_experiments()
        projects = set()

        for exp in experiments:
            try:
                parsed = self.parse_experiment_name(exp["name"])
                projects.add(parsed["project"])
            except ValueError:
                continue

        return sorted(list(projects))

    def list_asset_classes(self) -> List[str]:
        """
        List all unique asset classes.

        Returns:
            List of asset class names
        """
        experiments = self.query_experiments()
        asset_classes = set()

        for exp in experiments:
            try:
                parsed = self.parse_experiment_name(exp["name"])
                asset_classes.add(parsed["asset_class"])
            except ValueError:
                continue

        return sorted(list(asset_classes))

    def list_strategy_families(self) -> List[str]:
        """
        List all unique strategy families.

        Returns:
            List of strategy family names
        """
        experiments = self.query_experiments()
        strategy_families = set()

        for exp in experiments:
            try:
                parsed = self.parse_experiment_name(exp["name"])
                strategy_families.add(parsed["strategy_family"])
            except ValueError:
                continue

        return sorted(list(strategy_families))

    # === EXAMPLE WORKFLOWS ===

    def create_research_project(
        self, project_name: str, strategies: List[Tuple[str, str, str]]
    ) -> List[str]:
        """
        Example workflow: Create a research project with multiple strategies.

        Args:
            project_name: Name of the research project
            strategies: List of (asset_class, strategy_family, strategy) tuples

        Returns:
            List of created experiment IDs
        """
        experiment_ids = []

        for asset_class, strategy_family, strategy in strategies:
            exp_id = self.create_experiment(
                project=project_name,
                asset_class=asset_class,
                strategy_family=strategy_family,
                strategy=strategy,
                status="research",
                workflow="bulk_research_creation",
            )
            if exp_id:
                experiment_ids.append(exp_id)

        logger.info(
            f"Created {len(experiment_ids)} experiments for project {project_name}"
        )
        return experiment_ids

    def archive_old_experiments(self, days_threshold: int = 90) -> int:
        """
        Example workflow: Archive experiments older than threshold.

        Note: This is a placeholder implementation. Full archiving would require
        direct database access or MLflow client methods not available in current setup.

        Args:
            days_threshold: Age threshold in days

        Returns:
            Number of experiments that would be archived (0 for now)
        """
        # TODO: Implement proper experiment archiving when MLflow client methods are available
        logger.info(
            f"Archive functionality not yet implemented. Would archive experiments older than {days_threshold} days"
        )
        return 0

    def compare_strategies(
        self, project: str, metric: str = "sharpe_ratio"
    ) -> Dict[str, Any]:
        """
        Example workflow: Compare strategies within a project.

        Args:
            project: Project name
            metric: Metric to compare

        Returns:
            Comparison results dictionary
        """
        experiments = self.query_by_project(project)
        comparison = {}

        for exp in experiments:
            try:
                parsed = self.parse_experiment_name(exp["name"])
                strategy_key = f"{parsed['strategy_family']}.{parsed['strategy']}"

                best_run = self.get_best_run(exp["name"], metric)
                if best_run:
                    comparison[strategy_key] = {
                        "experiment_name": exp["name"],
                        "best_metric_value": best_run["metrics"].get(metric),
                        "run_id": best_run["run_id"],
                        "params": best_run["params"],
                    }
            except (ValueError, KeyError) as e:
                logger.warning(f"Skipping experiment {exp['name']}: {e}")

        return comparison
