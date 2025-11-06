#!/usr/bin/env python3
"""
Backtest Worker for Parallel Execution
Epic 20: Parallel Backtesting Orchestrator

Docker container worker that processes individual backtest jobs from Redis queue.
"""

import os
import json
import time
import redis
import logging
import signal
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - WORKER-%(name)s - %(levelname)s - %(message)s'
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
    priority: int = 0

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
            'batch_id': self.batch_id
        }


class BacktestWorker:
    """Docker container worker for parallel backtest execution"""

    def __init__(self):
        self.worker_id = f"worker_{os.getpid()}"
        self.redis_host = os.getenv('REDIS_HOST', 'redis')
        self.redis_port = int(os.getenv('REDIS_PORT', 6379))
        self.mlflow_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://mlflow:5000')

        # Initialize Redis connection
        self.redis = redis.Redis(
            host=self.redis_host,
            port=self.redis_port,
            decode_responses=True
        )

        # Wait for MLflow to be ready (if MLflow is enabled)
        self._wait_for_services()

        # Graceful shutdown handling
        self.running = True
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        logger.info(f"Worker {self.worker_id} initialized (Redis: {self.redis_host}:{self.redis_port})")

    def _wait_for_services(self):
        """Wait for dependent services to be ready"""
        import time
        import urllib.request

        # Wait for Redis
        logger.info("Waiting for Redis...")
        for i in range(30):  # 30 attempts, 1 second each
            try:
                self.redis.ping()
                logger.info("✅ Redis is ready")
                break
            except redis.ConnectionError:
                logger.debug(f"Redis not ready, attempt {i+1}/30")
                time.sleep(1)
        else:
            logger.warning("⚠️ Redis not available, continuing anyway")

        # Wait for MLflow (only if we might use it)
        logger.info("Waiting for MLflow...")
        for i in range(30):  # 30 attempts, 1 second each
            try:
                req = urllib.request.Request(f"{self.mlflow_uri}/health")
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        logger.info("✅ MLflow is ready")
                        break
            except Exception as e:
                logger.debug(f"MLflow not ready, attempt {i+1}/30: {e}")
                time.sleep(1)
        else:
            logger.warning("⚠️ MLflow not available, MLflow features will be disabled")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Worker {self.worker_id} received signal {signum}, shutting down...")
        self.running = False

    def _parse_job(self, job_data: str) -> BacktestJob:
        """Parse job data from Redis queue"""
        try:
            data = json.loads(job_data)
            return BacktestJob(**data)
        except Exception as e:
            raise ValueError(f"Invalid job data: {e}")

    def _execute_backtest(self, job: BacktestJob) -> Dict[str, Any]:
        """Execute single backtest job"""
        logger.info(f"Worker {self.worker_id} executing: {job.symbol} with {Path(job.strategy_path).name}")

        try:
            # Import backtest runner dynamically
            sys.path.insert(0, '/app')
            from scripts.run_backtest import BacktestRunner

            # Initialize backtest runner
            runner = BacktestRunner()

            # Execute backtest
            mlflow_kwargs = job.mlflow_config or {}
            mlflow_enabled = mlflow_kwargs.pop('enabled', False)

            result = runner.run(
                strategy_path=job.strategy_path,
                symbols=[job.symbol],
                start_date=job.start_date,
                end_date=job.end_date,
                strategy_params=job.strategy_params,
                mlflow_enabled=mlflow_enabled,
                **mlflow_kwargs
            )

            # Add job metadata
            result['job_id'] = job.job_id
            result['batch_id'] = job.batch_id
            result['worker_id'] = self.worker_id
            result['symbol'] = job.symbol
            result['strategy_path'] = job.strategy_path
            result['execution_timestamp'] = time.time()
            result['status'] = 'success'

            logger.info(f"Worker {self.worker_id} completed: {job.job_id} - result keys: {list(result.keys())}")
            return result

        except Exception as e:
            error_details = {
                'job_id': job.job_id,
                'batch_id': job.batch_id,
                'worker_id': self.worker_id,
                'symbol': job.symbol,
                'strategy': job.strategy_path,
                'status': 'failed',
                'error': str(e),
                'traceback': traceback.format_exc(),
                'execution_timestamp': time.time()
            }
            logger.error(f"Worker {self.worker_id} failed: {job.job_id} - {e}")
            return error_details

    def _store_result(self, result: Dict[str, Any]) -> None:
        """Store result in Redis for orchestrator pickup"""
        try:
            if not isinstance(result, dict):
                raise ValueError(f"Result is not a dict: {type(result)}")

            if 'job_id' not in result:
                raise ValueError(f"Result missing job_id: {list(result.keys())}")

            result_key = f"result:{result['job_id']}"

            # Try to serialize to check if it's valid JSON
            json_str = json.dumps(result)
            logger.debug(f"Result JSON size: {len(json_str)} bytes")

            success = self.redis.set(result_key, json_str, ex=3600)  # 1 hour expiry
            if success:
                logger.info(f"✅ Stored result for job {result['job_id']}")
            else:
                logger.error(f"❌ Failed to store result in Redis for job {result['job_id']}")

            # Add to results set for batch tracking
            if result.get('batch_id'):
                self.redis.sadd(f"batch_results:{result['batch_id']}", result['job_id'])

        except Exception as e:
            logger.error(f"Failed to store result for job {result.get('job_id', 'unknown')}: {e}")
            logger.error(f"Result type: {type(result)}")
            if isinstance(result, dict):
                logger.error(f"Result keys: {list(result.keys())}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def run(self):
        """Main worker loop"""
        logger.info(f"Worker {self.worker_id} starting job processing loop")

        while self.running:
            try:
                # Get highest priority job from sorted set
                # Use ZPOPMAX if available (Redis 5.0+), otherwise fallback to ZREVRANGE + ZREM
                job = None
                try:
                    # Try BZPOPMAX first (atomic operation, Redis 5.0+)
                    job_data = self.redis.bzpopmax('backtest_jobs', timeout=30)
                    if job_data:
                        queue_name, job_json, score = job_data
                        job = self._parse_job(job_json)
                except (redis.ResponseError, AttributeError):
                    # Fallback for older Redis versions without BZPOPMAX
                    job_data = self.redis.zrevrange('backtest_jobs', 0, 0, withscores=True)
                    if job_data:
                        job_json, score = job_data[0]
                        # Atomically remove the job
                        removed = self.redis.zrem('backtest_jobs', job_json)
                        if removed:
                            job = self._parse_job(job_json)

                if job:
                    # Execute backtest
                    result = self._execute_backtest(job)

                    # Store result
                    self._store_result(result)

                else:
                    # Timeout - check if we should still be running
                    logger.debug(f"Worker {self.worker_id} waiting for jobs...")

            except redis.ConnectionError:
                logger.warning(f"Worker {self.worker_id} Redis connection lost, retrying in 5 seconds...")
                time.sleep(5)
            except Exception as e:
                logger.error(f"Unexpected error in worker {self.worker_id} loop: {e}")
                time.sleep(1)

        logger.info(f"Worker {self.worker_id} shutdown complete")

    def health_check(self) -> bool:
        """Health check for container monitoring"""
        try:
            # Check Redis connection
            self.redis.ping()
            return True
        except Exception:
            return False


def main():
    """Entry point for worker container"""
    worker = BacktestWorker()
    worker.run()


if __name__ == "__main__":
    main()