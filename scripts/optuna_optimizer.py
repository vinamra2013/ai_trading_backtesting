#!/usr/bin/env python3
"""
Optuna Optimizer Engine (US-17.10)
Epic 17: AI-Native Research Lab

Implements intelligent Bayesian hyperparameter optimization for trading strategies
with MLflow integration and distributed execution support.
"""

import os
import sys
import json
import yaml
import logging
from typing import Dict, List, Any, Optional, Callable, Union
from pathlib import Path
import subprocess
import tempfile
import time
from datetime import datetime

import optuna
from optuna.samplers import TPESampler
from optuna.pruners import MedianPruner
from optuna.study import Study
from optuna.trial import Trial
import mlflow
from mlflow.tracking import MlflowClient
import threading
import queue

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.mlflow_logger import MLflowBacktestLogger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OptunaOptimizer:
    """
    Bayesian optimization engine for trading strategy parameters using Optuna.

    Features:
    - Intelligent parameter search with TPE sampler
    - Early stopping with median pruner
    - MLflow experiment tracking integration
    - Parent-child run structure for optimization studies
    - Distributed execution support
    - Parameter constraints and validation
    """

    def __init__(self, config_path: str = "config/optuna_config.yaml"):
        """
        Initialize the Optuna optimizer.

        Args:
            config_path: Path to Optuna configuration file
        """
        self.config = self._load_config(config_path)
        self.mlflow_client = MlflowClient(tracking_uri=self.config['optuna']['logging'].get('mlflow_tracking_uri', 'http://mlflow:5000'))
        self.logger = MLflowBacktestLogger(tracking_uri=self.config['optuna']['logging'].get('mlflow_tracking_uri', 'http://mlflow:5000'))

        # Initialize sampler and pruner
        self.sampler = self._create_sampler()
        self.pruner = self._create_pruner()

        # Async logging setup
        self._async_logging = self.config['optuna']['logging'].get('async_logging', True)
        if self._async_logging:
            self._log_queue = queue.Queue()
            self._log_thread = threading.Thread(target=self._async_log_worker, daemon=True)
            self._log_thread.start()
            logger.info("Async MLflow logging enabled")
        else:
            logger.info("Synchronous MLflow logging enabled")

        logger.info("OptunaOptimizer initialized with config: %s", config_path)

    def _async_log_worker(self):
        """Worker thread for asynchronous MLflow logging."""
        while True:
            try:
                # Get log task from queue with timeout
                log_task = self._log_queue.get(timeout=1.0)
                if log_task is None:  # Shutdown signal
                    break

                # Execute the logging function
                func, args, kwargs = log_task
                func(*args, **kwargs)

                self._log_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error("Error in async logging worker: %s", e)

    def _log_async(self, func, *args, **kwargs):
        """Submit a logging task to the async worker."""
        if self._async_logging:
            self._log_queue.put((func, args, kwargs))
        else:
            # Synchronous logging
            func(*args, **kwargs)

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load Optuna configuration from YAML file."""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def _create_sampler(self) -> TPESampler:
        """Create TPE sampler with configured parameters."""
        sampler_config = self.config['optuna']['sampler']
        return TPESampler(
            n_startup_trials=sampler_config['n_startup_trials'],
            n_ei_candidates=sampler_config.get('n_ei_candidates', 24),
            multivariate=sampler_config.get('multivariate', False)
        )

    def _create_pruner(self) -> MedianPruner:
        """Create median pruner with configured parameters."""
        pruner_config = self.config['optuna']['pruner']
        return MedianPruner(
            n_startup_trials=pruner_config['n_startup_trials'],
            n_warmup_steps=pruner_config.get('n_warmup_steps', 10),
            interval_steps=pruner_config.get('interval_steps', 1)
        )

    def create_study(self, study_name: str, direction: str = "maximize") -> Study:
        """
        Create a new Optuna study with MLflow storage.

        Args:
            study_name: Unique name for the study
            direction: Optimization direction ('maximize' or 'minimize')

        Returns:
            Optuna Study object
        """
        storage_url = self.config['optuna']['storage']['url']
        storage = optuna.storages.RDBStorage(url=storage_url)

        study = optuna.create_study(
            study_name=study_name,
            storage=storage,
            sampler=self.sampler,
            pruner=self.pruner,
            direction=direction,
            load_if_exists=True
        )

        logger.info("Created study: %s", study_name)
        return study

    def optimize_strategy(
        self,
        strategy_path: str,
        param_space: Dict[str, Any],
        study_name: str,
        symbols: List[str],
        start_date: str,
        end_date: str,
        n_trials: int = 100,
        metric: str = "sharpe_ratio",
        project: str = "optimization",
        asset_class: str = "equities",
        strategy_family: str = "unknown",
        n_jobs: int = 1,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run Bayesian optimization for a trading strategy.

        Args:
            strategy_path: Path to strategy module
            param_space: Parameter space definition
            study_name: Name for the optimization study
            symbols: List of symbols to test
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            n_trials: Number of optimization trials
            metric: Metric to optimize
            project: Project name for MLflow tagging
            asset_class: Asset class for tagging
            strategy_family: Strategy family for tagging
            n_jobs: Number of parallel workers
            timeout: Timeout in seconds

        Returns:
            Dictionary with optimization results
        """
        logger.info("Starting optimization for strategy: %s", strategy_path)
        logger.info("Study name: %s, Trials: %d, Metric: %s", study_name, n_trials, metric)

        # Create or load study
        study = self.create_study(study_name)

        # Create objective function
        objective_fn = self._create_objective_function(
            strategy_path=strategy_path,
            param_space=param_space,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            metric=metric,
            project=project,
            asset_class=asset_class,
            strategy_family=strategy_family
        )

        # Run optimization
        optimization_config = self.config['optuna']['optimization']
        study.optimize(
            objective_fn,
            n_trials=min(n_trials, optimization_config.get('n_trials', 100)),
            n_jobs=min(n_jobs, optimization_config.get('n_jobs', 4)),
            timeout=timeout or optimization_config.get('timeout', 3600),
            show_progress_bar=self.config['optuna']['optimization'].get('show_progress_bar', True)
        )

        # Get results
        results = {
            'study_name': study_name,
            'best_params': study.best_params,
            'best_value': study.best_value,
            'best_trial': study.best_trial.number,
            'n_trials': len(study.trials),
            'metric': metric,
            'completed_at': datetime.now().isoformat()
        }

        logger.info("Optimization completed. Best %s: %.4f", metric, study.best_value)
        logger.info("Best parameters: %s", study.best_params)

        return results

    def _create_objective_function(
        self,
        strategy_path: str,
        param_space: Dict[str, Any],
        symbols: List[str],
        start_date: str,
        end_date: str,
        metric: str,
        project: str,
        asset_class: str,
        strategy_family: str
    ) -> Callable[[Trial], float]:
        """
        Create objective function for Optuna optimization.

        Args:
            strategy_path: Path to strategy module
            param_space: Parameter space definition
            symbols: List of symbols
            start_date: Start date
            end_date: End date
            metric: Metric to optimize
            project: Project name
            asset_class: Asset class
            strategy_family: Strategy family

        Returns:
            Objective function for Optuna
        """

        def objective(trial: Trial) -> float:
            # Sample parameters from the search space
            params = self._sample_parameters(trial, param_space)

            # Run backtest with sampled parameters
            result = self._run_backtest(
                strategy_path=strategy_path,
                params=params,
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                project=project,
                asset_class=asset_class,
                strategy_family=strategy_family,
                trial_number=trial.number
            )

            # Extract the metric to optimize
            if result and 'performance' in result:
                metric_value = self._extract_metric(result['performance'], metric)
                if metric_value is not None:
                    logger.info("Trial %d: %s = %.4f, Params: %s",
                               trial.number, metric, metric_value, params)
                    return metric_value
                else:
                    logger.warning("Trial %d: Metric '%s' not found in results", trial.number, metric)
                    return float('-inf')  # Penalize missing metrics
            else:
                logger.error("Trial %d: Backtest failed or returned no results", trial.number)
                return float('-inf')

        return objective

    def _sample_parameters(self, trial: Trial, param_space: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sample parameters from the search space using Optuna suggest methods.

        Args:
            trial: Optuna trial object
            param_space: Parameter space definition

        Returns:
            Dictionary of sampled parameters
        """
        params = {}

        for param_name, param_config in param_space.items():
            param_type = param_config.get('type', 'float')

            if param_type == 'int':
                params[param_name] = trial.suggest_int(
                    param_name,
                    param_config.get('low', 0),
                    param_config.get('high', 100),
                    step=param_config.get('step', 1)
                )
            elif param_type == 'float':
                params[param_name] = trial.suggest_float(
                    param_name,
                    param_config.get('low', 0.0),
                    param_config.get('high', 1.0),
                    step=param_config.get('step'),
                    log=param_config.get('log', False)
                )
            elif param_type == 'categorical':
                params[param_name] = trial.suggest_categorical(
                    param_name,
                    param_config.get('choices', [])
                )
            else:
                logger.warning("Unknown parameter type '%s' for %s, using float", param_type, param_name)
                params[param_name] = trial.suggest_float(
                    param_name,
                    param_config.get('low', 0.0),
                    param_config.get('high', 1.0)
                )

        # Apply strategy-specific constraints
        self._apply_parameter_constraints(params)

        return params

    def _apply_parameter_constraints(self, params: Dict[str, Any]) -> None:
        """
        Apply strategy-specific parameter constraints to ensure valid combinations.

        Args:
            params: Parameter dictionary to modify in-place
        """
        # SMA Crossover constraints: fast_period < slow_period
        if 'fast_period' in params and 'slow_period' in params:
            if params['fast_period'] >= params['slow_period']:
                # Swap them to ensure fast < slow
                params['fast_period'], params['slow_period'] = params['slow_period'], params['fast_period']

        # Ensure minimum periods for technical indicators
        for param_name in ['fast_period', 'slow_period', 'rsi_period']:
            if param_name in params:
                params[param_name] = max(params[param_name], 2)  # Minimum period of 2

    def _run_backtest(
        self,
        strategy_path: str,
        params: Dict[str, Any],
        symbols: List[str],
        start_date: str,
        end_date: str,
        project: str,
        asset_class: str,
        strategy_family: str,
        trial_number: int
    ) -> Optional[Dict[str, Any]]:
        """
        Run a single backtest with given parameters.

        Args:
            strategy_path: Path to strategy module
            params: Strategy parameters
            symbols: List of symbols
            start_date: Start date
            end_date: End date
            project: Project name
            asset_class: Asset class
            strategy_family: Strategy family
            trial_number: Optuna trial number

        Returns:
            Backtest results dictionary or None if failed
        """
        param_file = None
        result_file = None

        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(params, f)
                param_file = f.name

            with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
                result_file = f.name

            # Build command - skip MLflow logging for optimization trials to reduce overhead
            cmd = [
                'python3', 'scripts/run_backtest.py',
                '--strategy', strategy_path,
                '--symbols', ','.join(symbols),
                '--start', start_date,
                '--end', end_date,
                # '--mlflow',  # Skip MLflow logging for optimization trials
                '--project', project,
                '--asset-class', asset_class,
                '--strategy-family', strategy_family,
                '--params-file', param_file,
                '--output-json', result_file
            ]

            # Run backtest
            logger.debug("Running command: %s", ' '.join(cmd))
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config['optuna']['constraints'].get('timeout_per_trial', 300)
            )

            # Try to read results from the output file
            if os.path.exists(result_file):
                try:
                    with open(result_file, 'r') as f:
                        backtest_results = json.load(f)
                    return backtest_results
                except (json.JSONDecodeError, IOError) as e:
                    logger.error("Failed to read result file %s: %s", result_file, e)
                    return None

            # No results file found
            logger.warning("Result file %s was not created", result_file)
            if result.returncode != 0:
                logger.warning("Backtest failed with return code %d", result.returncode)
                logger.debug("STDERR: %s", result.stderr[-500:] if result.stderr else "No stderr")

            return None
            if result.returncode != 0:
                logger.warning("Backtest failed with return code %d", result.returncode)
                logger.warning("STDERR: %s", result.stderr[-1000:] if result.stderr else "No stderr")
                logger.warning("STDOUT: %s", result.stdout[-1000:] if result.stdout else "No stdout")

            return None

        except subprocess.TimeoutExpired:
            logger.error("Backtest timed out for trial %d", trial_number)
            return None
        except Exception as e:
            logger.error("Error running backtest for trial %d: %s", trial_number, e)
            return None
        finally:
            # Clean up temporary files
            for f in [param_file, result_file]:
                if f and os.path.exists(f):
                    try:
                        os.unlink(f)
                    except OSError:
                        pass

    def _extract_metric(self, metrics: Dict[str, Any], metric_name: str) -> Optional[float]:
        """
        Extract the specified metric from backtest results.

        Args:
            metrics: Metrics dictionary from backtest
            metric_name: Name of metric to extract

        Returns:
            Metric value or None if not found
        """
        # Handle common metric name variations
        metric_map = {
            'sharpe_ratio': ['sharpe_ratio', 'sharpe', 'Sharpe Ratio'],
            'sortino_ratio': ['sortino_ratio', 'sortino', 'Sortino Ratio'],
            'total_return': ['total_return', 'total_return_pct', 'Total Return'],
            'profit_factor': ['profit_factor', 'Profit Factor'],
            'max_drawdown': ['max_drawdown', 'max_dd', 'Max Drawdown'],
            'calmar_ratio': ['calmar_ratio', 'calmar', 'Calmar Ratio'],
            'win_rate': ['win_rate', 'winning_trades_pct', 'Win Rate']
        }

        possible_names = metric_map.get(metric_name, [metric_name])

        for name in possible_names:
            if name in metrics:
                value = metrics[name]
                # Ensure it's a number
                if isinstance(value, (int, float)):
                    return float(value)
                elif isinstance(value, str):
                    # Try to parse string numbers
                    try:
                        return float(value.strip('%').strip())
                    except ValueError:
                        continue

        logger.warning("Metric '%s' not found in results. Available metrics: %s", metric_name, list(metrics.keys()))
        return None

    def get_study_results(self, study_name: str) -> Dict[str, Any]:
        """
        Get comprehensive results from a completed study.

        Args:
            study_name: Name of the study

        Returns:
            Study results dictionary
        """
        storage_url = self.config['optuna']['storage']['url']
        storage = optuna.storages.RDBStorage(url=storage_url)

        study = optuna.load_study(study_name=study_name, storage=storage)

        return {
            'study_name': study_name,
            'best_params': study.best_params,
            'best_value': study.best_value,
            'best_trial': study.best_trial.number,
            'n_trials': len(study.trials),
            'direction': study.direction.name,
            'trials': [
                {
                    'number': t.number,
                    'value': t.value,
                    'params': t.params,
                    'state': t.state.name
                }
                for t in study.trials
            ]
        }


def main():
    """Command-line interface for Optuna optimization."""
    import argparse

    parser = argparse.ArgumentParser(description="Optuna Strategy Optimizer")
    parser.add_argument("--strategy", required=True, help="Path to strategy module")
    parser.add_argument("--param-space", required=True, help="JSON file with parameter space")
    parser.add_argument("--study-name", required=True, help="Name for the optimization study")
    parser.add_argument("--symbols", required=True, help="Comma-separated list of symbols")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--metric", default="sharpe_ratio", help="Metric to optimize")
    parser.add_argument("--n-trials", type=int, default=100, help="Number of trials")
    parser.add_argument("--project", default="optimization", help="Project name")
    parser.add_argument("--asset-class", default="equities", help="Asset class")
    parser.add_argument("--strategy-family", default="unknown", help="Strategy family")
    parser.add_argument("--n-jobs", type=int, default=1, help="Number of parallel jobs")
    parser.add_argument("--config", default="config/optuna_config.yaml", help="Optuna config file")

    args = parser.parse_args()

    # Load parameter space
    with open(args.param_space, 'r') as f:
        param_space = json.load(f)

    # Initialize optimizer
    optimizer = OptunaOptimizer(args.config)

    # Run optimization
    results = optimizer.optimize_strategy(
        strategy_path=args.strategy,
        param_space=param_space,
        study_name=args.study_name,
        symbols=args.symbols.split(','),
        start_date=args.start,
        end_date=args.end,
        n_trials=args.n_trials,
        metric=args.metric,
        project=args.project,
        asset_class=args.asset_class,
        strategy_family=args.strategy_family,
        n_jobs=args.n_jobs
    )

    # Print results
    print("\n" + "="*50)
    print("OPTIMIZATION RESULTS")
    print("="*50)
    print(f"Study: {results['study_name']}")
    print(f"Best {args.metric}: {results['best_value']:.4f}")
    print(f"Best parameters: {results['best_params']}")
    print(f"Trials completed: {results['n_trials']}")
    print("="*50)


if __name__ == "__main__":
    main()