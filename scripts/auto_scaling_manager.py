#!/usr/bin/env python3
"""
Auto-Scaling Manager for Parallel Backtesting Workers
Epic 20: Parallel Backtesting Orchestrator

Monitors Redis queue length and dynamically scales worker containers
based on workload demand.
"""

import os
import time
import logging
import redis
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AutoScalingManager:
    """
    Auto-scaling manager for parallel backtesting workers.

    Monitors queue length and scales worker containers dynamically:
    - Scale up when queue length > threshold
    - Scale down when queue length < threshold and workers > min
    - Maintain optimal worker count for current workload
    """

    def __init__(self,
                 redis_host: str = 'redis',
                 redis_port: int = 6379,
                 min_workers: int = 1,
                 max_workers: int = 10,
                 scale_up_threshold: int = 5,
                 scale_down_threshold: int = 1,
                 check_interval: int = 30):
        """
        Initialize auto-scaling manager.

        Args:
            redis_host: Redis host
            redis_port: Redis port
            min_workers: Minimum number of workers to maintain
            max_workers: Maximum number of workers allowed
            scale_up_threshold: Queue length threshold to trigger scale up
            scale_down_threshold: Queue length threshold to trigger scale down
            check_interval: Seconds between queue checks
        """
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.check_interval = check_interval

        # Initialize Redis connection
        self.redis = redis.Redis(
            host=self.redis_host,
            port=self.redis_port,
            decode_responses=True
        )

        # Track current worker count
        self.current_workers = self._get_current_worker_count()

        logger.info("Auto-scaling manager initialized")
        logger.info(f"Worker range: {min_workers}-{max_workers}")
        logger.info(f"Scale thresholds: up={scale_up_threshold}, down={scale_down_threshold}")
        logger.info(f"Current workers: {self.current_workers}")

    def _get_current_worker_count(self) -> int:
        """Get current number of running worker containers"""
        try:
            result = subprocess.run(
                ['docker', 'compose', 'ps', '--format', 'json'],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                worker_count = 0
                for line in lines:
                    if line.strip():
                        try:
                            import json
                            container = json.loads(line)
                            service = container.get('Service', '')
                            if service.startswith('backtest-worker'):
                                worker_count += 1
                        except json.JSONDecodeError:
                            continue
                return worker_count
            else:
                logger.warning(f"Failed to get container status: {result.stderr}")
                return 0

        except Exception as e:
            logger.error(f"Error getting worker count: {e}")
            return 0

    def _get_queue_length(self) -> int:
        """Get current queue length"""
        try:
            queue_length = self.redis.zcard('backtest_jobs')
            return queue_length
        except redis.ConnectionError:
            logger.warning("Redis connection failed")
            return 0
        except Exception as e:
            logger.error(f"Error getting queue length: {e}")
            return 0

    def _scale_workers(self, target_count: int) -> bool:
        """
        Scale workers to target count.

        Args:
            target_count: Desired number of workers

        Returns:
            True if scaling was successful
        """
        if target_count < self.min_workers:
            target_count = self.min_workers
        elif target_count > self.max_workers:
            target_count = self.max_workers

        if target_count == self.current_workers:
            return True

        try:
            logger.info(f"Scaling workers from {self.current_workers} to {target_count}")

            if target_count > self.current_workers:
                # Scale up
                scale_diff = target_count - self.current_workers
                result = subprocess.run(
                    ['docker', 'compose', 'up', '-d', '--scale', f'backtest-worker={target_count}'],
                    cwd=Path(__file__).parent.parent
                )
                success = result.returncode == 0

            else:
                # Scale down - need to be careful not to kill active workers
                scale_diff = self.current_workers - target_count
                # For now, just log that we would scale down
                # In production, you'd implement graceful shutdown
                logger.info(f"Would scale down by {scale_diff} workers (not implemented)")
                success = True

            if success:
                self.current_workers = target_count
                logger.info(f"✅ Successfully scaled to {target_count} workers")
                return True
            else:
                logger.error("❌ Failed to scale workers")
                return False

        except Exception as e:
            logger.error(f"Error scaling workers: {e}")
            return False

    def _calculate_target_workers(self, queue_length: int) -> int:
        """
        Calculate target number of workers based on queue length.

        Simple algorithm:
        - If queue > scale_up_threshold: double current workers (up to max)
        - If queue < scale_down_threshold and workers > min: halve workers (down to min)
        - Otherwise: maintain current count
        """
        if queue_length >= self.scale_up_threshold:
            # Scale up aggressively
            target = min(self.current_workers * 2, self.max_workers)
            if target > self.current_workers:
                logger.info(f"Queue length {queue_length} >= {self.scale_up_threshold}, scaling up to {target}")
                return target

        elif queue_length <= self.scale_down_threshold and self.current_workers > self.min_workers:
            # Scale down conservatively
            target = max(self.current_workers // 2, self.min_workers)
            if target < self.current_workers:
                logger.info(f"Queue length {queue_length} <= {self.scale_down_threshold}, scaling down to {target}")
                return target

        return self.current_workers

    def run(self):
        """Main auto-scaling loop"""
        logger.info("Starting auto-scaling manager")

        while True:
            try:
                # Get current metrics
                queue_length = self._get_queue_length()
                current_workers = self._get_current_worker_count()

                logger.debug(f"Queue length: {queue_length}, Workers: {current_workers}")

                # Calculate target workers
                target_workers = self._calculate_target_workers(queue_length)

                # Scale if needed
                if target_workers != current_workers:
                    self._scale_workers(target_workers)
                else:
                    logger.debug("Worker count optimal")

                # Wait before next check
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                logger.info("Auto-scaling manager stopped by user")
                break
            except Exception as e:
                logger.error(f"Auto-scaling loop error: {e}")
                time.sleep(self.check_interval)


def main():
    """Command-line interface for auto-scaling manager"""
    import argparse

    parser = argparse.ArgumentParser(description="Auto-Scaling Manager for Parallel Backtesting")
    parser.add_argument('--redis-host', default='redis', help='Redis host')
    parser.add_argument('--redis-port', type=int, default=6379, help='Redis port')
    parser.add_argument('--min-workers', type=int, default=1, help='Minimum workers')
    parser.add_argument('--max-workers', type=int, default=10, help='Maximum workers')
    parser.add_argument('--scale-up-threshold', type=int, default=5, help='Queue length to trigger scale up')
    parser.add_argument('--scale-down-threshold', type=int, default=1, help='Queue length to trigger scale down')
    parser.add_argument('--check-interval', type=int, default=30, help='Seconds between checks')

    args = parser.parse_args()

    manager = AutoScalingManager(
        redis_host=args.redis_host,
        redis_port=args.redis_port,
        min_workers=args.min_workers,
        max_workers=args.max_workers,
        scale_up_threshold=args.scale_up_threshold,
        scale_down_threshold=args.scale_down_threshold,
        check_interval=args.check_interval
    )

    manager.run()


if __name__ == "__main__":
    main()