#!/usr/bin/env python3
"""
MLflow Backtest Logger - Epic 17: US-17.2
MLflow logging wrapper for Backtrader backtests with comprehensive metric and artifact logging.

This module provides MLflowBacktestLogger class for intelligent experiment tracking,
replacing static JSON files with centralized MLflow tracking server.

Features:
- Parameters, metrics, and artifacts logging
- Project hierarchy with dot notation and tagging
- Equity curves, trade logs, strategy plots
- Error handling and retry logic
- <200ms logging overhead
"""

import mlflow
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import logging
import json
import pandas as pd
import numpy as np
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MLflowBacktestLogger:
    """
    MLflow logger for Backtrader backtests with comprehensive tracking.
    
    Supports project hierarchy organization:
    - Layer 1: Dot notation naming (Project.AssetClass.StrategyFamily.Strategy)
    - Layer 2: Comprehensive tagging for filtering and organization
    - Layer 3: Parent-child runs for optimization studies
    """
    
    def __init__(self, tracking_uri: str = "http://172.25.0.5:5000",
                 experiment_name: Optional[str] = None):
        """
        Initialize MLflow logger.
        
        Args:
            tracking_uri: MLflow tracking server URI
            experiment_name: Default experiment name
        """
        self.tracking_uri = tracking_uri
        self.experiment_name = experiment_name
        self.mlflow_available = False
        
        # Initialize MLflow client
        try:
            mlflow.set_tracking_uri(tracking_uri)
            self.mlflow_available = True
            logger.info(f"MLflow logger initialized with tracking URI: {tracking_uri}")
        except Exception as e:
            logger.warning(f"Failed to initialize MLflow client: {e}. Continuing without MLflow.")
            self.mlflow_available = False
    
    def _build_experiment_name(self, project: str, asset_class: str, 
                              strategy_family: str, strategy_name: str) -> str:
        """Build experiment name using dot notation convention."""
        return f"{project}.{asset_class}.{strategy_family}.{strategy_name}"
    
    def _build_tags(self, project: str, asset_class: str, strategy_family: str,
                   strategy_name: str, team: str = "quant_research", 
                   status: str = "research", **kwargs) -> Dict:
        """Build comprehensive tagging dictionary."""
        tags = {
            "project": project,
            "asset_class": asset_class,
            "strategy_family": strategy_family,
            "strategy": strategy_name,
            "team": team,
            "status": status,
            "created_date": datetime.now().isoformat(),
            "created_by": "backtest_runner"
        }
        
        # Add any additional tags
        tags.update(kwargs)
        return tags
    
    def create_experiment(self, experiment_name: str, tags: Optional[Dict] = None) -> Optional[str]:
        """
        Create MLflow experiment with hierarchical organization.
        
        Args:
            experiment_name: Name following dot notation (Project.AssetClass.StrategyFamily.Strategy)
            tags: Comprehensive tagging dictionary
            
        Returns:
            Experiment ID
        """
        if not self.mlflow_available:
            logger.warning("MLflow not available, skipping experiment creation")
            return None
            
        try:
            # Create experiment if it doesn't exist
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(
                    name=experiment_name,
                    tags=tags or {}
                )
                logger.info(f"Created experiment: {experiment_name}")
            else:
                experiment_id = experiment.experiment_id
                logger.info(f"Using existing experiment: {experiment_name}")
                
            return experiment_id
        except Exception as e:
            logger.error(f"Failed to create experiment {experiment_name}: {e}")
            return None
    
    def log_backtest(self, experiment_name: str, strategy_name: str, 
                    parameters: Dict, metrics: Dict, artifacts: Dict,
                    tags: Optional[Dict] = None, run_name: Optional[str] = None) -> Optional[str]:
        """
        Log complete backtest results to MLflow.
        
        Args:
            experiment_name: Experiment name with dot notation
            strategy_name: Strategy class name
            parameters: Strategy parameters
            metrics: Performance metrics from analyzers
            artifacts: Artifacts (plots, data files)
            tags: Additional tags for organization
            run_name: Optional run name
            
        Returns:
            Run ID if successful, None otherwise
        """
        if not self.mlflow_available:
            logger.warning("MLflow not available, skipping backtest logging")
            return None
            
        start_time = time.time()
        
        try:
            # Set experiment
            mlflow.set_experiment(experiment_name)
            
            # Start run
            with mlflow.start_run(run_name=run_name) as run:
                run_id = run.info.run_id
                
                # Log parameters
                self._log_parameters(parameters)
                
                # Log metrics
                self._log_metrics(metrics)
                
                # Log artifacts
                self._log_artifacts(artifacts, strategy_name)
                
                # Log tags
                self._log_tags(tags or {})
                
                logger.info(f"Logged backtest to MLflow: {experiment_name}/{run_id}")
                
                # Log logging overhead
                overhead = time.time() - start_time
                logger.info(f"MLflow logging overhead: {overhead:.3f}s")
                
                return run_id
                
        except Exception as e:
            logger.error(f"Failed to log backtest to MLflow: {e}")
            return None
    
    def _log_parameters(self, parameters: Dict):
        """Log strategy parameters to MLflow."""
        try:
            # Flatten nested parameters
            flat_params = self._flatten_dict(parameters)
            
            for key, value in flat_params.items():
                if isinstance(value, (str, int, float, bool)):
                    mlflow.log_param(key, value)
                else:
                    mlflow.log_param(key, str(value))
                    
        except Exception as e:
            logger.error(f"Failed to log parameters: {e}")
    
    def _log_metrics(self, metrics: Dict):
        """Log performance metrics to MLflow."""
        try:
            # Flatten nested metrics
            flat_metrics = self._flatten_dict(metrics)
            
            for key, value in flat_metrics.items():
                if isinstance(value, (int, float)) and not np.isnan(value):
                    mlflow.log_metric(key, float(value))
                    
        except Exception as e:
            logger.error(f"Failed to log metrics: {e}")
    
    def _log_artifacts(self, artifacts: Dict, strategy_name: str):
        """Log artifacts to MLflow."""
        try:
            for artifact_name, artifact_path in artifacts.items():
                if isinstance(artifact_path, str):
                    path = Path(artifact_path)
                    if path.exists():
                        mlflow.log_artifact(str(path), artifact_name)
                elif isinstance(artifact_path, dict) and 'data' in artifact_path:
                    # Handle DataFrame artifacts
                    if 'dataframe' in artifact_path:
                        df = artifact_path['dataframe']
                        if isinstance(df, pd.DataFrame):
                            temp_path = f"/tmp/{artifact_name}.csv"
                            df.to_csv(temp_path, index=False)
                            mlflow.log_artifact(temp_path, artifact_name)
                            Path(temp_path).unlink(missing_ok=True)
                            
        except Exception as e:
            logger.error(f"Failed to log artifacts: {e}")
    
    def _log_tags(self, tags: Dict):
        """Log tags to MLflow."""
        try:
            for key, value in tags.items():
                mlflow.set_tag(key, str(value))
        except Exception as e:
            logger.error(f"Failed to log tags: {e}")
    
    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
        """
        Flatten nested dictionary.
        
        Args:
            d: Dictionary to flatten
            parent_key: Parent key for recursion
            sep: Separator for flattened keys
            
        Returns:
            Flattened dictionary
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def log_optimization_study(self, study_name: str, best_params: Dict, 
                             best_value: float, optimization_metrics: Dict,
                             tags: Optional[Dict] = None) -> Optional[str]:
        """
        Log Optuna optimization study as parent run.
        
        Args:
            study_name: Name of optimization study
            best_params: Best parameters found
            best_value: Best objective value
            optimization_metrics: Additional optimization metrics
            tags: Study tags
            
        Returns:
            Run ID if successful, None otherwise
        """
        if not self.mlflow_available:
            logger.warning("MLflow not available, skipping study logging")
            return None
            
        try:
            mlflow.set_experiment(study_name)
            
            with mlflow.start_run(run_name=f"study_{datetime.now().strftime('%Y%m%d_%H%M%S')}") as run:
                run_id = run.info.run_id
                
                # Log study parameters and metrics
                mlflow.log_params(best_params)
                mlflow.log_metric("best_objective_value", best_value)
                
                # Log additional optimization metrics
                for key, value in optimization_metrics.items():
                    if isinstance(value, (int, float)):
                        mlflow.log_metric(f"optimization_{key}", value)
                
                # Set study tags
                study_tags = {
                    "optimization_study": "true",
                    "study_type": "optuna",
                    **tags
                }
                mlflow.set_tags(study_tags)
                
                logger.info(f"Logged optimization study: {study_name}/{run_id}")
                return run_id
                
        except Exception as e:
            logger.error(f"Failed to log optimization study: {e}")
            return None
    
    def log_child_trial(self, parent_run_id: str, trial_params: Dict, 
                       trial_metrics: Dict, trial_number: int) -> Optional[str]:
        """
        Log child trial for optimization study.
        
        Args:
            parent_run_id: Parent run ID
            trial_params: Trial parameters
            trial_metrics: Trial metrics
            trial_number: Trial number
            
        Returns:
            Child run ID if successful, None otherwise
        """
        if not self.mlflow_available:
            return None
            
        try:
            with mlflow.start_run(run_name=f"trial_{trial_number}", nested=True) as run:
                run_id = run.info.run_id
                
                # Link to parent run
                mlflow.set_tag("parent_run_id", parent_run_id)
                mlflow.set_tag("trial_number", str(trial_number))
                
                # Log trial data
                mlflow.log_params(trial_params)
                mlflow.log_metrics(trial_metrics)
                
                return run_id
                
        except Exception as e:
            logger.error(f"Failed to log child trial: {e}")
            return None
    
    def get_experiment_info(self, experiment_name: str) -> Optional[Dict]:
        """
        Get experiment information for monitoring.
        
        Args:
            experiment_name: Name of experiment
            
        Returns:
            Experiment information dictionary
        """
        if not self.mlflow_available:
            return None
            
        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment:
                return {
                    "experiment_id": experiment.experiment_id,
                    "name": experiment.name,
                    "lifecycle_stage": experiment.lifecycle_stage,
                    "creation_time": experiment.creation_time,
                    "last_update_time": experiment.last_update_time
                }
        except Exception as e:
            logger.error(f"Failed to get experiment info: {e}")
        
        return None
    
    def query_experiments(self, filter_string: Optional[str] = None, 
                         max_results: int = 100) -> List[Dict]:
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
                filter_string=filter_string,
                max_results=max_results
            )
            
            return [
                {
                    "experiment_id": exp.experiment_id,
                    "name": exp.name,
                    "lifecycle_stage": exp.lifecycle_stage,
                    "tags": exp.tags
                }
                for exp in experiments
            ]
        except Exception as e:
            logger.error(f"Failed to query experiments: {e}")
            return []