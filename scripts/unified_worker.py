#!/usr/bin/env python3
"""
Unified Worker for AI Trading Platform
Epic 20/26: Parallel Backtesting Orchestrator & Quant Director Operations

Docker container worker that processes multiple job types from Redis queues:
- Backtest jobs (backtest_jobs)
- Discovery jobs (discovery_jobs)
- Ranking jobs (ranking_jobs)
- Data processing jobs (data_processing_queue)

This replaces separate specialized workers with a single unified worker.
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

# Add backend to path for database access
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "backend"))
sys.path.insert(0, os.path.join(project_root, "scripts"))
sys.path.insert(0, os.path.join(project_root, "utils"))

# Import job handlers
from scripts.symbol_discovery import SymbolDiscoveryEngine
from scripts.databento_zip_extractor import DatabentoZipExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - UNIFIED-WORKER - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class UnifiedJob:
    """Unified job specification for all job types"""

    job_type: str  # 'backtest', 'discovery', 'ranking', 'data'
    job_id: str
    payload: Dict[str, Any]


class UnifiedWorker:
    """Unified worker that handles multiple job types"""

    def __init__(self):
        """Initialize the unified worker"""
        self.redis_client = None
        self.running = True
        self.worker_id = os.getenv("WORKER_ID", f"worker_{int(time.time())}")

        # Job type to queue mapping
        self.queues = {
            "backtest": "backtest_jobs",
            "discovery": "discovery_jobs",
            "ranking": "ranking_jobs",
            "data": "data_processing_queue",
        }

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def connect_redis(self):
        """Connect to Redis"""
        try:
            redis_host = os.getenv("REDIS_HOST", "redis")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))

            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )

            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {redis_host}:{redis_port}")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def process_backtest_job(self, job: UnifiedJob) -> Dict[str, Any]:
        """Process a backtest job"""
        logger.info(f"Processing backtest job {job.job_id}")

        try:
            # Import backtest dependencies
            from scripts.run_backtest import run_single_backtest

            payload = job.payload

            # Run the backtest
            result = run_single_backtest(
                symbol=payload["symbol"],
                strategy_path=payload["strategy_path"],
                start_date=payload["start_date"],
                end_date=payload["end_date"],
                strategy_params=payload.get("strategy_params"),
                mlflow_config=payload.get("mlflow_config"),
                batch_id=payload.get("batch_id"),
            )

            return {
                "status": "completed",
                "result": result,
                "message": "Backtest completed successfully",
            }

        except Exception as e:
            logger.error(f"Backtest job {job.job_id} failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "message": f"Backtest failed: {str(e)}",
            }

    def process_discovery_job(self, job: UnifiedJob) -> Dict[str, Any]:
        """Process a discovery job"""
        logger.info(f"Processing discovery job {job.job_id}")

        try:
            payload = job.payload

            # Create discovery engine
            engine = SymbolDiscoveryEngine()

            # Run discovery based on scanner type
            scanner_name = payload.get("scanner_name", "high_volume")
            parameters = payload.get("parameters", {})
            filters = payload.get("filters", {})

            # Use the discover_symbols method which handles the full workflow
            results = engine.discover_symbols(scanner_name, save_to_db=False)

            # Apply additional filters if provided
            if filters:
                results = engine.apply_filters(results)

            # Convert DiscoveredSymbol objects to dictionaries for JSON serialization
            import json
            from datetime import datetime

            def serialize_symbol(symbol):
                """Convert DiscoveredSymbol to JSON-serializable dict"""
                data = symbol.__dict__.copy()
                # Convert datetime objects to ISO format strings
                for key, value in data.items():
                    if isinstance(value, datetime):
                        data[key] = value.isoformat()
                return data

            results_dict = [serialize_symbol(symbol) for symbol in results]

            return {
                "status": "completed",
                "results": results_dict,
                "message": f"Discovery scan completed: {len(results)} symbols found",
            }

        except Exception as e:
            logger.error(f"Discovery job {job.job_id} failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "message": f"Discovery failed: {str(e)}",
            }

    def process_ranking_job(self, job: UnifiedJob) -> Dict[str, Any]:
        """Process a ranking job"""
        logger.info(f"Processing ranking job {job.job_id}")

        try:
            # Import ranking dependencies
            from scripts.strategy_ranker import StrategyRanker

            payload = job.payload

            # Create ranker and run analysis
            ranker = StrategyRanker()
            results = ranker.analyze_strategies(
                input_source=payload.get("input_source"),
                ranking_criteria=payload.get("ranking_criteria", {}),
                filters=payload.get("filters", {}),
            )

            return {
                "status": "completed",
                "results": results,
                "message": f"Strategy ranking completed: {len(results)} strategies ranked",
            }

        except Exception as e:
            logger.error(f"Ranking job {job.job_id} failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "message": f"Ranking failed: {str(e)}",
            }

    def process_data_job(self, job: UnifiedJob) -> Dict[str, Any]:
        """Process a data processing job"""
        logger.info(f"Processing data job {job.job_id}")

        try:
            payload = job.payload

            # Create extractor
            extractor = DatabentoZipExtractor(
                payload["zip_file_path"], payload["output_dir"]
            )

            # Process the zip file
            extractor.process_zip_file()

            return {
                "status": "completed",
                "zip_file": payload["zip_file_path"],
                "output_dir": payload["output_dir"],
                "message": "Data processing completed successfully",
            }

        except Exception as e:
            logger.error(f"Data job {job.job_id} failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "zip_file": payload.get("zip_file_path"),
                "output_dir": payload.get("output_dir"),
                "message": f"Data processing failed: {str(e)}",
            }

    def process_job(self, job: UnifiedJob) -> Dict[str, Any]:
        """Route job to appropriate handler based on job type"""
        if job.job_type == "backtest":
            return self.process_backtest_job(job)
        elif job.job_type == "discovery":
            return self.process_discovery_job(job)
        elif job.job_type == "ranking":
            return self.process_ranking_job(job)
        elif job.job_type == "data":
            return self.process_data_job(job)
        else:
            return {
                "status": "failed",
                "error": f"Unknown job type: {job.job_type}",
                "message": f"Unsupported job type: {job.job_type}",
            }

    def run(self):
        """Main worker loop"""
        logger.info(f"Starting Unified Worker {self.worker_id}")

        try:
            self.connect_redis()

            logger.info("Worker started, monitoring all job queues...")

            while self.running:
                try:
                    # Check all queues for jobs (round-robin)
                    job_found = False

                    for job_type, queue_name in self.queues.items():
                        try:
                            # Try to get a job from this queue
                            result = self.redis_client.bzpopmin(queue_name, timeout=1)

                            if result:
                                queue_name, job_data_str, score = result
                                logger.info(
                                    f"Received {job_type} job from queue: {queue_name}"
                                )

                                try:
                                    job_data = json.loads(job_data_str)
                                    job = UnifiedJob(
                                        job_type=job_type,
                                        job_id=job_data.get(
                                            "job_id", f"unknown_{int(time.time())}"
                                        ),
                                        payload=job_data,
                                    )

                                    # Process the job
                                    result = self.process_job(job)

                                    # Store result
                                    result_key = f"{job_type}_job_result:{job.job_id}"
                                    self.redis_client.setex(
                                        result_key,
                                        86400,  # 24 hours
                                        json.dumps(result),
                                    )

                                    # Update job status
                                    self._update_job_status(
                                        job.job_id,
                                        job_type,
                                        result["status"],
                                        result["message"],
                                    )

                                    if result["status"] == "completed":
                                        logger.info(
                                            f"Successfully processed {job_type} job: {job.job_id}"
                                        )
                                    else:
                                        logger.error(
                                            f"Failed to process {job_type} job: {job.job_id}"
                                        )

                                    job_found = True
                                    break  # Process one job at a time

                                except json.JSONDecodeError as e:
                                    logger.error(
                                        f"Invalid job data in {queue_name}: {e}"
                                    )
                                except Exception as e:
                                    logger.error(
                                        f"Error processing job from {queue_name}: {e}"
                                    )

                        except redis.ResponseError:
                            # Queue might be empty, continue to next queue
                            continue

                    # If no job was found, wait a bit before checking again
                    if not job_found:
                        time.sleep(0.1)

                except redis.ConnectionError:
                    logger.warning("Redis connection lost, attempting to reconnect...")
                    time.sleep(5)
                    try:
                        self.connect_redis()
                    except Exception:
                        logger.error("Failed to reconnect to Redis")

                except Exception as e:
                    logger.error(f"Error in worker loop: {e}")
                    time.sleep(1)

        except Exception as e:
            logger.error(f"Fatal error in unified worker: {e}")
            raise
        finally:
            logger.info(f"Unified Worker {self.worker_id} shutting down")

    def _update_job_status(self, job_id: str, job_type: str, status: str, message: str):
        """Update job status in Redis"""
        try:
            if self.redis_client:
                key = f"{job_type}_job:{job_id}"
                job_data = {
                    "status": status,
                    "message": message,
                    "updated_at": time.time(),
                }
                self.redis_client.hmset(key, job_data)
                # Set expiration (24 hours)
                self.redis_client.expire(key, 86400)
        except Exception as e:
            logger.warning(f"Failed to update job status: {e}")


def main():
    """Main entry point"""
    worker = UnifiedWorker()
    worker.run()


if __name__ == "__main__":
    main()
