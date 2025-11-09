# MLflow client service for programmatic access to experiments and runs (Epic 25 Story 6)

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import redis
import pandas as pd

try:
    import mlflow
    from mlflow.entities import Experiment, Run, RunInfo, RunData

    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    mlflow = None

from backend.schemas.mlflow import (
    MLflowExperiment,
    MLflowRun,
    MLflowRunInfo,
    MLflowRunData,
    MLflowExperimentsResponse,
    MLflowRunsResponse,
    MLflowRunDetailResponse,
)

logger = logging.getLogger(__name__)


class MLflowClientService:
    """Service for programmatic access to MLflow experiments and runs with caching"""

    def __init__(
        self,
        tracking_uri: str = "http://172.25.0.6:5000",
        redis_host: str = "redis",
        redis_port: int = 6379,
        cache_ttl_seconds: int = 300,  # 5 minutes default
    ):
        self.tracking_uri = tracking_uri
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.cache_ttl = cache_ttl_seconds

        # Initialize Redis for caching
        self.redis = redis.Redis(
            host=self.redis_host, port=self.redis_port, decode_responses=True
        )

        # Initialize MLflow client
        self.mlflow_available = False
        if MLFLOW_AVAILABLE:
            try:
                mlflow.set_tracking_uri(tracking_uri)
                # Test connection
                mlflow.search_experiments()
                self.mlflow_available = True
                logger.info(
                    f"MLflow client initialized with tracking URI: {tracking_uri}"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize MLflow client: {e}")
                self.mlflow_available = False
        else:
            logger.warning("MLflow package not available")

    def _get_cache_key(self, key: str) -> str:
        """Generate cache key with namespace"""
        return f"mlflow:{key}"

    def _get_cached_data(self, cache_key: str) -> Optional[Any]:
        """Retrieve data from Redis cache"""
        try:
            cached = self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Failed to retrieve cached data for key {cache_key}: {e}")
        return None

    def _set_cached_data(
        self, cache_key: str, data: Any, ttl: Optional[int] = None
    ) -> None:
        """Store data in Redis cache"""
        try:
            ttl = ttl or self.cache_ttl
            self.redis.setex(cache_key, ttl, json.dumps(data))
        except Exception as e:
            logger.warning(f"Failed to cache data for key {cache_key}: {e}")

    def _clear_cache_pattern(self, pattern: str) -> None:
        """Clear cache keys matching a pattern"""
        try:
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
        except Exception as e:
            logger.warning(f"Failed to clear cache pattern {pattern}: {e}")

    def list_experiments(self) -> MLflowExperimentsResponse:
        """
        List all MLflow experiments

        Returns:
            MLflowExperimentsResponse: List of experiments with metadata
        """
        if not self.mlflow_available:
            raise RuntimeError("MLflow client not available")

        cache_key = self._get_cache_key("experiments")
        cached_data = self._get_cached_data(cache_key)

        if cached_data:
            experiments = [MLflowExperiment(**exp) for exp in cached_data]
            return MLflowExperimentsResponse(experiments=experiments)

        try:
            # Get experiments from MLflow
            mlflow_experiments = mlflow.search_experiments()

            experiments = []
            for exp in mlflow_experiments:
                experiment = MLflowExperiment(
                    experiment_id=exp.experiment_id,
                    name=exp.name,
                    lifecycle_stage=exp.lifecycle_stage,
                    artifact_location=exp.artifact_location,
                    creation_time=datetime.fromtimestamp(exp.creation_time / 1000)
                    if exp.creation_time
                    else None,
                    last_update_time=datetime.fromtimestamp(exp.last_update_time / 1000)
                    if exp.last_update_time
                    else None,
                )
                experiments.append(experiment)

            # Cache the results (convert datetime to string for JSON serialization)
            cache_data = []
            for exp in experiments:
                exp_dict = exp.dict()
                if exp_dict.get("creation_time"):
                    exp_dict["creation_time"] = exp_dict["creation_time"].isoformat()
                if exp_dict.get("last_update_time"):
                    exp_dict["last_update_time"] = exp_dict[
                        "last_update_time"
                    ].isoformat()
                cache_data.append(exp_dict)
            self._set_cached_data(cache_key, cache_data)

            return MLflowExperimentsResponse(experiments=experiments)

        except Exception as e:
            logger.error(f"Failed to list MLflow experiments: {e}")
            raise RuntimeError(f"Failed to retrieve experiments: {str(e)}")

    def get_experiment_runs(
        self,
        experiment_id: str,
        page: int = 1,
        page_size: int = 50,
        order_by: Optional[List[str]] = None,
    ) -> MLflowRunsResponse:
        """
        Get runs for a specific experiment with pagination

        Args:
            experiment_id: MLflow experiment ID
            page: Page number (1-based)
            page_size: Number of runs per page
            order_by: List of columns to order by

        Returns:
            MLflowRunsResponse: Paginated list of runs
        """
        if not self.mlflow_available:
            raise RuntimeError("MLflow client not available")

        cache_key = self._get_cache_key(
            f"runs:{experiment_id}:page_{page}:size_{page_size}"
        )
        cached_data = self._get_cached_data(cache_key)

        if cached_data:
            runs = [MLflowRun(**run) for run in cached_data["runs"]]
            return MLflowRunsResponse(
                runs=runs,
                total=cached_data["total"],
                page=page,
                page_size=page_size,
                total_pages=cached_data["total_pages"],
            )

        try:
            # Default ordering by start time descending
            if not order_by:
                order_by = ["start_time DESC"]

            # Get runs from MLflow (returns pandas DataFrame)
            mlflow_runs_df = mlflow.search_runs(
                experiment_ids=[experiment_id],
                order_by=order_by,
                max_results=page_size * page,  # Get enough for pagination
            )

            # Convert DataFrame to our schema
            runs = []
            for idx, run_row in mlflow_runs_df.iterrows():
                # Extract run info from DataFrame columns
                run_info = MLflowRunInfo(
                    run_id=run_row["run_id"],
                    run_uuid=run_row.get(
                        "run_uuid", run_row["run_id"]
                    ),  # Fallback if run_uuid not available
                    experiment_id=str(run_row["experiment_id"]),
                    user_id=run_row.get("user_id", "unknown"),
                    status=run_row["status"],
                    start_time=pd.to_datetime(run_row["start_time"])
                    if pd.notna(run_row["start_time"])
                    else None,
                    end_time=pd.to_datetime(run_row["end_time"])
                    if pd.notna(run_row["end_time"])
                    else None,
                    artifact_uri=run_row.get("artifact_uri", ""),
                    lifecycle_stage=run_row.get("lifecycle_stage", "active"),
                )

                # Extract metrics, params, and tags from DataFrame
                metrics = {}
                params = {}
                tags = {}

                # Parse metrics (columns starting with 'metrics.')
                for col in mlflow_runs_df.columns:
                    if col.startswith("metrics."):
                        metric_name = col[8:]  # Remove 'metrics.' prefix
                        if pd.notna(run_row[col]):
                            metrics[metric_name] = float(run_row[col])

                # Parse params (columns starting with 'params.')
                for col in mlflow_runs_df.columns:
                    if col.startswith("params."):
                        param_name = col[7:]  # Remove 'params.' prefix
                        if pd.notna(run_row[col]):
                            params[param_name] = str(run_row[col])

                # Parse tags (columns starting with 'tags.')
                for col in mlflow_runs_df.columns:
                    if col.startswith("tags."):
                        tag_name = col[5:]  # Remove 'tags.' prefix
                        if pd.notna(run_row[col]):
                            tags[tag_name] = str(run_row[col])

                run_data = MLflowRunData(metrics=metrics, params=params, tags=tags)

                mlflow_run = MLflowRun(info=run_info, data=run_data)
                runs.append(mlflow_run)

            # Calculate pagination info
            total = len(runs)  # Note: This is approximate since we limited results
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_runs = runs[start_idx:end_idx]

            total_pages = (total + page_size - 1) // page_size

            # Cache the results (convert datetime to string for JSON serialization)
            cache_runs = []
            for run in paginated_runs:
                run_dict = run.dict()
                # Convert datetime objects to ISO format strings
                if run_dict["info"].get("start_time"):
                    run_dict["info"]["start_time"] = run_dict["info"][
                        "start_time"
                    ].isoformat()
                if run_dict["info"].get("end_time"):
                    run_dict["info"]["end_time"] = run_dict["info"][
                        "end_time"
                    ].isoformat()
                cache_runs.append(run_dict)

            cache_data = {
                "runs": cache_runs,
                "total": total,
                "total_pages": total_pages,
            }
            self._set_cached_data(cache_key, cache_data)

            return MLflowRunsResponse(
                runs=paginated_runs,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            )

        except Exception as e:
            logger.error(f"Failed to get runs for experiment {experiment_id}: {e}")
            raise RuntimeError(f"Failed to retrieve experiment runs: {str(e)}")

    def get_run_details(self, run_id: str) -> MLflowRunDetailResponse:
        """
        Get detailed information for a specific run

        Args:
            run_id: MLflow run ID

        Returns:
            MLflowRunDetailResponse: Complete run details
        """
        if not self.mlflow_available:
            raise RuntimeError("MLflow client not available")

        cache_key = self._get_cache_key(f"run:{run_id}")
        cached_data = self._get_cached_data(cache_key)

        if cached_data:
            run = MLflowRun(**cached_data)
            return MLflowRunDetailResponse(run=run)

        try:
            # Get run from MLflow
            mlflow_run = mlflow.get_run(run_id)

            run_info = MLflowRunInfo(
                run_id=mlflow_run.info.run_id,
                run_uuid=getattr(
                    mlflow_run.info, "run_uuid", mlflow_run.info.run_id
                ),  # Fallback if run_uuid not available
                experiment_id=mlflow_run.info.experiment_id,
                user_id=mlflow_run.info.user_id,
                status=mlflow_run.info.status,
                start_time=datetime.fromtimestamp(mlflow_run.info.start_time / 1000)
                if mlflow_run.info.start_time
                else None,
                end_time=datetime.fromtimestamp(mlflow_run.info.end_time / 1000)
                if mlflow_run.info.end_time
                else None,
                artifact_uri=mlflow_run.info.artifact_uri,
                lifecycle_stage=mlflow_run.info.lifecycle_stage,
            )

            # Extract metrics, params, and tags
            metrics = (
                {k: v for k, v in mlflow_run.data.metrics.items()}
                if mlflow_run.data.metrics
                else {}
            )
            params = (
                {k: v for k, v in mlflow_run.data.params.items()}
                if mlflow_run.data.params
                else {}
            )
            tags = (
                {k: v for k, v in mlflow_run.data.tags.items()}
                if mlflow_run.data.tags
                else {}
            )

            run_data = MLflowRunData(metrics=metrics, params=params, tags=tags)

            run = MLflowRun(info=run_info, data=run_data)

            # Cache the result
            self._set_cached_data(cache_key, run.dict())

            return MLflowRunDetailResponse(run=run)

        except Exception as e:
            logger.error(f"Failed to get run details for {run_id}: {e}")
            raise RuntimeError(f"Failed to retrieve run details: {str(e)}")

    def invalidate_experiment_cache(self, experiment_id: Optional[str] = None) -> None:
        """
        Invalidate cache for experiments and runs

        Args:
            experiment_id: Specific experiment to invalidate, or None for all
        """
        try:
            if experiment_id:
                # Clear specific experiment cache
                self._clear_cache_pattern(
                    self._get_cache_key(f"runs:{experiment_id}:*")
                )
                self._clear_cache_pattern(
                    self._get_cache_key(f"run:*")
                )  # Individual runs might be affected
            else:
                # Clear all MLflow cache
                self._clear_cache_pattern(self._get_cache_key("*"))
        except Exception as e:
            logger.warning(f"Failed to invalidate MLflow cache: {e}")


# Global service instance
_mlflow_service = None


def get_mlflow_service() -> MLflowClientService:
    """Get the global MLflow service instance"""
    global _mlflow_service
    if _mlflow_service is None:
        _mlflow_service = MLflowClientService()
    return _mlflow_service
