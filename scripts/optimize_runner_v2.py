#!/usr/bin/env python3
"""
V2 Parallel Optimization System - CLI Client
Command-line interface for running parallel strategy optimizations with real-time monitoring.
"""

import os
import sys
import time
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
import requests
from datetime import datetime

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class OptimizationRunner:
    """CLI client for V2 parallel optimization system."""

    def __init__(self, backend_url: str = "http://localhost:8230"):
        """
        Initialize the optimization runner.

        Args:
            backend_url: URL of the FastAPI backend
        """
        self.backend_url = backend_url
        self.session = requests.Session()
        self.timeout = 30  # 30 second timeout for requests

    def run_optimization(self, config_path: str, max_concurrent: int = 4) -> str:
        """
        Run a parallel optimization from config file.

        Args:
            config_path: Path to optimization config YAML file
            max_concurrent: Maximum concurrent jobs

        Returns:
            Batch ID for monitoring
        """
        logger.info(f"Starting optimization with config: {config_path}")

        # Validate config file exists
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")

        # Submit optimization request
        url = f"{self.backend_url}/api/optimization/run-parallel"
        payload = {"config_path": config_path, "max_concurrent": max_concurrent}

        try:
            logger.info("Submitting optimization request to backend...")
            response = self.session.post(url, json=payload)
            response.raise_for_status()

            result = response.json()
            batch_id = result["batch_id"]
            total_jobs = result["total_jobs"]

            logger.info(f"Optimization started successfully!")
            logger.info(f"Batch ID: {batch_id}")
            logger.info(f"Total jobs: {total_jobs}")

            return batch_id

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to submit optimization: {e}")
            raise

    def monitor_batch(self, batch_id: str, poll_interval: int = 5) -> Dict[str, Any]:
        """
        Monitor an optimization batch until completion.

        Args:
            batch_id: Batch ID to monitor
            poll_interval: Seconds between status checks

        Returns:
            Final batch results
        """
        logger.info(f"Monitoring batch: {batch_id}")
        logger.info(f"Polling interval: {poll_interval} seconds")

        url = f"{self.backend_url}/api/optimization/batches/{batch_id}"

        last_status = None
        start_time = time.time()

        try:
            while True:
                # Get batch status
                response = self.session.get(url)
                response.raise_for_status()
                batch_data = response.json()["batch"]

                # Extract status info
                status = batch_data["status"]
                completed = batch_data["completed_jobs"]
                total = batch_data["total_jobs"]
                created_at = batch_data["created_at"]

                # Show progress update
                if status != last_status or completed != getattr(
                    self, "_last_completed", 0
                ):
                    elapsed = time.time() - start_time
                    progress_pct = (completed / total * 100) if total > 0 else 0

                    logger.info(
                        f"[{status.upper()}] {completed}/{total} jobs completed ({progress_pct:.1f}%) - {elapsed:.0f}s elapsed"
                    )

                    if batch_data.get("best_result"):
                        logger.info(f"Best result so far: {batch_data['best_result']}")

                    last_status = status
                    self._last_completed = completed

                # Check if completed
                if status in ["completed", "failed"]:
                    logger.info(f"Batch {batch_id} finished with status: {status}")

                    if status == "failed":
                        logger.error("Optimization failed!")
                    else:
                        logger.info("Optimization completed successfully!")

                    # Get final results
                    results_url = f"{self.backend_url}/api/optimization/batches/{batch_id}/results"
                    try:
                        results_response = self.session.get(results_url)
                        results_response.raise_for_status()
                        results = results_response.json()
                        return results
                    except requests.exceptions.RequestException:
                        logger.warning("Could not fetch final results")
                        return batch_data

                # Wait before next poll
                time.sleep(poll_interval)

        except KeyboardInterrupt:
            logger.info("Monitoring interrupted by user")
            return {"batch_id": batch_id, "status": "interrupted"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to monitor batch: {e}")
            raise

    def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """
        Get current status of a batch (single request).

        Args:
            batch_id: Batch ID to check

        Returns:
            Batch status data
        """
        url = f"{self.backend_url}/api/optimization/batches/{batch_id}"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()["batch"]
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get batch status: {e}")
            raise

    def cancel_batch(self, batch_id: str) -> bool:
        """
        Cancel a running optimization batch.

        Args:
            batch_id: Batch ID to cancel

        Returns:
            True if cancelled successfully
        """
        url = f"{self.backend_url}/api/optimization/batches/{batch_id}"

        try:
            response = self.session.delete(url)
            response.raise_for_status()
            logger.info(f"Batch {batch_id} cancelled successfully")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to cancel batch: {e}")
            return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="V2 Parallel Optimization System - CLI Client"
    )

    # Mutually exclusive action groups
    action_group = parser.add_mutually_exclusive_group(required=True)

    action_group.add_argument(
        "--config", "-c", type=str, help="Path to optimization config YAML file"
    )

    action_group.add_argument(
        "--monitor", "-m", type=str, help="Monitor existing batch ID"
    )

    action_group.add_argument(
        "--status", "-s", type=str, help="Get status of batch ID (single request)"
    )

    action_group.add_argument("--cancel", type=str, help="Cancel running batch ID")

    # Optional arguments
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=4,
        help="Maximum concurrent jobs (default: 4)",
    )

    parser.add_argument(
        "--backend-url",
        type=str,
        default="http://localhost:8230",
        help="FastAPI backend URL (default: http://localhost:8230)",
    )

    parser.add_argument(
        "--poll-interval",
        type=int,
        default=5,
        help="Status polling interval in seconds (default: 5)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize runner
    runner = OptimizationRunner(args.backend_url)

    try:
        if args.config:
            # Run optimization
            batch_id = runner.run_optimization(args.config, args.max_concurrent)

            # Automatically monitor the batch
            logger.info("Starting automatic monitoring...")
            results = runner.monitor_batch(batch_id, args.poll_interval)

            # Display final results
            print("\n" + "=" * 60)
            print("OPTIMIZATION RESULTS")
            print("=" * 60)
            print(json.dumps(results, indent=2))

        elif args.monitor:
            # Monitor existing batch
            results = runner.monitor_batch(args.monitor, args.poll_interval)

            # Display results
            print("\n" + "=" * 60)
            print("MONITORING RESULTS")
            print("=" * 60)
            print(json.dumps(results, indent=2))

        elif args.status:
            # Get batch status
            status = runner.get_batch_status(args.status)
            print(json.dumps(status, indent=2))

        elif args.cancel:
            # Cancel batch
            success = runner.cancel_batch(args.cancel)
            if success:
                print(f"Batch {args.cancel} cancelled successfully")
            else:
                print(f"Failed to cancel batch {args.cancel}")
                sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
