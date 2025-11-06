#!/usr/bin/env python3
"""
Parallel Backtest Orchestrator
Epic 20: US-20.1 - Backtest Orchestration Engine

Orchestrates parallel execution of multiple symbol-strategy combinations using multiprocessing.
"""

import argparse
import json
import logging
import os
import sys
import time
import uuid
import redis
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import multiprocessing as mp

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import pandas as pd
import tqdm

# Import with explicit path handling
try:
    from scripts.run_backtest import BacktestRunner
    from utils.results_consolidator import ResultsConsolidator
except ImportError as e:
    # Fallback for when running from different directories
    sys.path.insert(0, os.path.join(project_root, 'scripts'))
    sys.path.insert(0, os.path.join(project_root, 'utils'))
    from run_backtest import BacktestRunner
    from results_consolidator import ResultsConsolidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class BacktestJob:
    """Individual backtest job specification"""
    job_id: str
    symbol: str
    strategy_path: str
    start_date: str
    end_date: str
    strategy_params: Optional[Dict[str, Any]] = None
    mlflow_config: Optional[Dict[str, Any]] = None
    batch_id: Optional[str] = None
    priority: int = 0  # Higher priority = processed first (0 = normal, >0 = high priority)

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for serialization"""
        return {
            'job_id': self.job_id,
            'symbol': self.symbol,
            'strategy_path': self.strategy_path,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'strategy_params': self.strategy_params or {},
            'mlflow_config': self.mlflow_config or {},
            'batch_id': self.batch_id,
            'priority': self.priority
        }


class ParallelBacktestOrchestrator:
    """Orchestrates parallel backtest execution across multiple symbol-strategy combinations"""

    def __init__(self, config_path: str = 'config/backtest_config.yaml',
                 redis_host: str = 'redis', redis_port: int = 6379,
                 max_workers: Optional[int] = None, worker_timeout: int = 300):
        """
        Initialize the orchestrator

        Args:
            config_path: Path to backtest configuration file
            redis_host: Redis host for job queue
            redis_port: Redis port for job queue
            max_workers: Maximum number of parallel workers (for progress tracking)
        """
        self.config_path = config_path
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.max_workers = max_workers or min(mp.cpu_count(), 8)  # Cap at 8 workers
        self.batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # Initialize Redis connection
        self.redis = redis.Redis(
            host=self.redis_host,
            port=self.redis_port,
            decode_responses=True
        )

        # Initialize components
        self.results_consolidator = ResultsConsolidator()

        # Load configuration
        self.config = self._load_config()
        self.mlflow_config = self._load_mlflow_config()

        logger.info(f"Initialized orchestrator with Redis queue ({redis_host}:{redis_port}), batch_id: {self.batch_id}")

    def _load_config(self) -> Dict[str, Any]:
        """Load backtest configuration"""
        try:
            import yaml
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {self.config_path}")
            return config
        except Exception as e:
            logger.warning(f"Could not load config from {self.config_path}: {e}")
            return {}

    def _load_mlflow_config(self) -> Dict[str, Any]:
        """Load MLflow configuration"""
        mlflow_config_path = 'config/mlflow_config.yaml'
        try:
            import yaml
            with open(mlflow_config_path, 'r') as f:
                mlflow_config = yaml.safe_load(f)
            logger.info(f"Loaded MLflow configuration from {mlflow_config_path}")
            return mlflow_config
        except Exception as e:
            logger.warning(f"Could not load MLflow config from {mlflow_config_path}: {e}")
            return {}

    def _validate_inputs(self, symbols: List[str], strategies: List[str]) -> Tuple[List[str], List[str]]:
        """Validate and normalize input symbols and strategies"""
        # Validate symbols
        if not symbols:
            raise ValueError("No symbols provided")

        # Validate strategies
        validated_strategies = []
        for strategy in strategies:
            strategy_path = Path(strategy)
            if not strategy_path.exists():
                strategy_path = Path('strategies') / strategy
                if not strategy_path.exists():
                    strategy_path = strategy_path.with_suffix('.py')

            if not strategy_path.exists():
                raise FileNotFoundError(f"Strategy file not found: {strategy}")

            validated_strategies.append(str(strategy_path))

        logger.info(f"Validated {len(symbols)} symbols and {len(validated_strategies)} strategies")
        return symbols, validated_strategies

    def _generate_job_matrix(self, symbols: List[str], strategies: List[str],
                            strategy_params: Optional[Dict[str, Dict]] = None,
                            priority: int = 0) -> List[BacktestJob]:
        """Generate matrix of all symbol-strategy combinations"""
        jobs = []
        strategy_params = strategy_params or {}

        for symbol in symbols:
            for strategy_path in strategies:
                # Extract strategy name for job ID
                strategy_name = Path(strategy_path).stem

                job_id = f"{self.batch_id}_{symbol}_{strategy_name}"

                # Get strategy-specific parameters if provided
                params = strategy_params.get(strategy_name, {})

                # Extract MLflow parameters from config
                mlflow_config = {
                    'enabled': True,
                    'project': self.mlflow_config.get('project', {}).get('defaults', {}).get('project', 'Default'),
                    'asset_class': self.mlflow_config.get('project', {}).get('defaults', {}).get('asset_class', 'Equities'),
                    'strategy_family': self.mlflow_config.get('project', {}).get('defaults', {}).get('strategy_family', 'Unknown'),
                    'team': 'quant_research',
                    'status': 'research'
                }

                job = BacktestJob(
                    job_id=job_id,
                    symbol=symbol,
                    strategy_path=strategy_path,
                    start_date=self.config.get('start_date', '2020-01-01'),
                    end_date=self.config.get('end_date', '2024-12-31'),
                    strategy_params=params,
                    mlflow_config=mlflow_config,  # Enable MLflow with extracted parameters
                    batch_id=self.batch_id,
                    priority=priority
                )
                jobs.append(job)

        logger.info(f"Generated {len(jobs)} backtest jobs")
        return jobs

    def execute_batch(self, symbols: List[str], strategies: List[str],
                       strategy_params: Optional[Dict[str, Dict]] = None,
                       show_progress: bool = True, timeout: int = 600,
                       priority: int = 0) -> pd.DataFrame:
        """
        Execute batch of parallel backtests using Redis queue

        Args:
            symbols: List of symbols to test
            strategies: List of strategy file paths
            strategy_params: Optional strategy-specific parameters
            show_progress: Whether to show progress bar
            timeout: Timeout per job in seconds

        Returns:
            Consolidated results DataFrame
        """
        start_time = time.time()

        # Validate inputs
        symbols, strategies = self._validate_inputs(symbols, strategies)

        # Generate job matrix
        jobs = self._generate_job_matrix(symbols, strategies, strategy_params, priority)

        logger.info(f"Submitting {len(jobs)} backtest jobs to Redis queue")

        # Submit all jobs to Redis priority queue (sorted set)
        for job in jobs:
            try:
                job_json = json.dumps(job.to_dict())
                # Use negative priority so higher priority (larger number) comes first
                self.redis.zadd('backtest_jobs', {job_json: -job.priority})
                logger.debug(f"Submitted job {job.job_id} to queue (priority: {job.priority})")
            except Exception as e:
                logger.error(f"Failed to submit job {job.job_id}: {e}")

        # Wait for results
        results = []
        failed_jobs = []
        completed_jobs = set()
        progress_bar = None

        if show_progress:
            progress_bar = tqdm.tqdm(total=len(jobs), desc="Running backtests", unit="backtest")

        while len(completed_jobs) < len(jobs):
            try:
                # Check for completed results
                for job in jobs:
                    if job.job_id in completed_jobs:
                        continue

                    result_key = f"result:{job.job_id}"
                    result_data = self.redis.get(result_key)

                    if result_data:
                        try:
                            result = json.loads(result_data)
                            if result.get('status') == 'success':
                                results.append(result)
                            else:
                                failed_jobs.append((job, result))
                                logger.warning(f"Backtest failed: {job.job_id}")

                            completed_jobs.add(job.job_id)
                            self.redis.delete(result_key)  # Clean up

                            if progress_bar:
                                progress_bar.update(1)

                        except json.JSONDecodeError as e:
                            logger.error(f"Invalid result data for job {job.job_id}: {e}")

                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > (len(jobs) * timeout):
                    logger.warning(f"Batch timeout exceeded ({len(jobs) * timeout}s)")
                    break

                # Small delay to avoid busy waiting
                time.sleep(0.1)

            except redis.ConnectionError:
                logger.warning("Redis connection lost, retrying...")
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error checking results: {e}")
                time.sleep(0.1)

        if progress_bar:
            progress_bar.close()

        # Log summary
        execution_time = time.time() - start_time
        success_count = len(results)
        failure_count = len(failed_jobs)

        logger.info(f"Batch {self.batch_id} completed in {execution_time:.1f}s")
        logger.info(f"Results: {success_count} successful, {failure_count} failed")

        if failed_jobs:
            logger.warning("Failed jobs:")
            for job, error in failed_jobs[:5]:  # Show first 5 failures
                logger.warning(f"  - {job.job_id}: {error.get('error', 'Unknown error')}")
            if len(failed_jobs) > 5:
                logger.warning(f"  ... and {len(failed_jobs) - 5} more")

        # Consolidate results
        consolidated_df = self.results_consolidator.consolidate(results)

        # Add batch metadata
        consolidated_df['batch_id'] = self.batch_id
        consolidated_df['execution_time_seconds'] = execution_time
        consolidated_df['total_jobs'] = len(jobs)
        consolidated_df['successful_jobs'] = success_count
        consolidated_df['failed_jobs'] = failure_count

        return consolidated_df

    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status"""
        return {
            'batch_id': self.batch_id,
            'max_workers': self.max_workers,
            'cpu_count': mp.cpu_count(),
            'config_path': self.config_path,
            'timestamp': datetime.now().isoformat()
        }


# Note: execute_backtest_worker function removed - now handled by Docker workers via Redis


def main():
    """Command line interface for parallel backtest orchestrator"""
    parser = argparse.ArgumentParser(description="Parallel Backtest Orchestrator")
    parser.add_argument('--symbols', nargs='+', required=True,
                        help='List of symbols to backtest')
    parser.add_argument('--strategies', nargs='+', required=True,
                        help='List of strategy file paths')
    parser.add_argument('--max-workers', type=int, default=None,
                        help='Maximum number of parallel workers (for progress tracking)')
    parser.add_argument('--output', type=str, default=None,
                        help='Output CSV file path for results')
    parser.add_argument('--config', type=str, default='config/backtest_config.yaml',
                        help='Backtest configuration file path')
    parser.add_argument('--strategy-params', type=str, default=None,
                        help='JSON file with strategy-specific parameters')
    parser.add_argument('--redis-host', type=str, default='redis',
                        help='Redis host for job queue')
    parser.add_argument('--redis-port', type=int, default=6379,
                        help='Redis port for job queue')
    parser.add_argument('--timeout', type=int, default=600,
                        help='Timeout per job in seconds')
    parser.add_argument('--priority', type=int, default=0,
                        help='Job priority (higher = processed first, default: 0)')

    args = parser.parse_args()

    # Load strategy parameters if provided
    strategy_params = None
    if args.strategy_params:
        with open(args.strategy_params, 'r') as f:
            strategy_params = json.load(f)

    # Initialize orchestrator
    orchestrator = ParallelBacktestOrchestrator(
        config_path=args.config,
        redis_host=args.redis_host,
        redis_port=args.redis_port,
        max_workers=args.max_workers
    )

    # Execute batch
    try:
        results_df = orchestrator.execute_batch(
            symbols=args.symbols,
            strategies=args.strategies,
            strategy_params=strategy_params,
            timeout=args.timeout,
            priority=args.priority
        )

        # Display summary
        print(f"\n{'='*60}")
        print(f"PARALLEL BACKTEST RESULTS - Batch {orchestrator.batch_id}")
        print(f"{'='*60}")
        print(f"Total backtests: {len(results_df)}")
        if not results_df.empty:
            print(f"Execution time: {results_df['execution_time_seconds'].iloc[0]:.1f} seconds")
            print(f"Successful: {results_df['successful_jobs'].iloc[0]}")
            print(f"Failed: {results_df['failed_jobs'].iloc[0]}")
            print(f"Average time per backtest: {results_df['execution_time_seconds'].iloc[0] / len(results_df):.1f}s")

            print(f"\nTop 5 strategies by Sharpe Ratio:")
            top_strategies = results_df.nlargest(5, 'sharpe_ratio')[['symbol', 'strategy', 'sharpe_ratio', 'max_drawdown']]
            print(top_strategies.to_string(index=False))

        # Save results if requested
        if args.output:
            results_df.to_csv(args.output, index=False)
            print(f"\nResults saved to: {args.output}")

    except Exception as e:
        logger.error(f"Orchestrator failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()