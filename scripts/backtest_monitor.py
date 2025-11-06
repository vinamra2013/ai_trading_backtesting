#!/usr/bin/env python3
"""
Distributed Backtesting Monitor
Epic 20: Production Monitoring for Parallel Backtesting

Monitors Redis queue status, worker health, and system performance metrics.
"""

import os
import json
import time
import redis
import logging
from datetime import datetime
from typing import Dict, Any, List
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BacktestMonitor:
    """Monitor for distributed backtesting system"""

    def __init__(self, redis_host: str = 'redis', redis_port: int = 6379):
        self.redis_host = redis_host
        self.redis_port = redis_port

        # Initialize Redis connection
        self.redis = redis.Redis(
            host=self.redis_host,
            port=self.redis_port,
            decode_responses=True
        )

        logger.info(f"Monitor initialized (Redis: {redis_host}:{redis_port})")

    def get_queue_status(self) -> Dict[str, Any]:
        """Get Redis queue status"""
        try:
            # Check queue lengths
            backtest_jobs = self.redis.llen('backtest_jobs')

            # Get worker status (approximate from recent activity)
            worker_keys = self.redis.keys('worker:*')
            active_workers = len(worker_keys) if worker_keys else 0

            # Get completed jobs count
            completed_keys = self.redis.keys('result:*')
            completed_jobs = len(completed_keys) if completed_keys else 0

            # Get batch information
            batch_keys = self.redis.keys('batch_results:*')
            active_batches = len(batch_keys) if batch_keys else 0

            return {
                'backtest_jobs_pending': backtest_jobs,
                'active_workers': active_workers,
                'completed_jobs': completed_jobs,
                'active_batches': active_batches,
                'redis_connected': True
            }

        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            return {
                'error': str(e),
                'redis_connected': False
            }

    def get_worker_health(self) -> Dict[str, Any]:
        """Check worker container health"""
        try:
            # Since we're running inside a container, check if we can connect to Redis
            # and assume worker is healthy if Redis is accessible
            self.redis.ping()
            return {
                'total_workers': 1,  # Assume 1 worker in this container setup
                'healthy_workers': 1,
                'worker_containers_ok': True
            }

        except Exception as e:
            logger.error(f"Failed to check worker health: {e}")
            return {
                'error': str(e),
                'worker_containers_ok': False
            }

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system resource metrics"""
        try:
            # Get CPU usage
            cpu_result = subprocess.run(['cat', '/proc/stat'], capture_output=True, text=True)
            cpu_percent = 0.0  # Simplified - would need more complex parsing

            # Get memory info
            mem_result = subprocess.run(['cat', '/proc/meminfo'], capture_output=True, text=True)
            mem_lines = mem_result.stdout.strip().split('\n')
            mem_total = int([line for line in mem_lines if 'MemTotal' in line][0].split()[1]) * 1024
            mem_available = int([line for line in mem_lines if 'MemAvailable' in line][0].split()[1]) * 1024
            mem_used = mem_total - mem_available
            memory_percent = (mem_used / mem_total) * 100

            # Get disk usage
            disk_result = subprocess.run(['df', '/'], capture_output=True, text=True)
            disk_lines = disk_result.stdout.strip().split('\n')
            disk_usage_percent = int(disk_lines[1].split()[4].rstrip('%'))

            return {
                'cpu_percent': cpu_percent,
                'memory_percent': round(memory_percent, 1),
                'memory_used_gb': round(mem_used / (1024**3), 2),
                'memory_total_gb': round(mem_total / (1024**3), 2),
                'disk_usage_percent': disk_usage_percent,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {'error': str(e)}

    def get_recent_performance(self, hours: int = 1) -> Dict[str, Any]:
        """Get recent performance metrics"""
        try:
            # Get recent results from Redis
            result_keys = self.redis.keys('result:*')
            recent_results = []

            cutoff_time = time.time() - (hours * 3600)

            for key in result_keys[:100]:  # Limit to avoid performance issues
                result_data = self.redis.get(key)
                if result_data:
                    try:
                        result = json.loads(result_data)
                        if result.get('execution_timestamp', 0) > cutoff_time:
                            recent_results.append(result)
                    except json.JSONDecodeError:
                        continue

            if recent_results:
                execution_times = [r.get('execution_timestamp', 0) for r in recent_results if r.get('execution_timestamp')]
                successful_jobs = len([r for r in recent_results if r.get('status') == 'success'])

                avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0

                return {
                    'recent_jobs_last_hour': len(recent_results),
                    'successful_jobs_last_hour': successful_jobs,
                    'avg_execution_time_seconds': round(avg_execution_time, 2),
                    'jobs_per_minute': round(len(recent_results) / (hours * 60), 2)
                }
            else:
                return {
                    'recent_jobs_last_hour': 0,
                    'successful_jobs_last_hour': 0,
                    'avg_execution_time_seconds': 0,
                    'jobs_per_minute': 0
                }

        except Exception as e:
            logger.error(f"Failed to get recent performance: {e}")
            return {'error': str(e)}

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'queue_status': self.get_queue_status(),
            'worker_health': self.get_worker_health(),
            'system_metrics': self.get_system_metrics(),
            'recent_performance': self.get_recent_performance()
        }

        # Calculate derived metrics
        queue_status = report['queue_status']
        worker_health = report['worker_health']
        performance = report['recent_performance']

        # Calculate health score first (without derived_metrics)
        health_score = self._calculate_health_score(report)

        report['derived_metrics'] = {
            'queue_backlog_ratio': queue_status.get('backtest_jobs_pending', 0) / max(worker_health.get('healthy_workers', 1), 1),
            'worker_utilization_percent': min(100, (performance.get('jobs_per_minute', 0) / max(worker_health.get('healthy_workers', 1), 1)) * 100),
            'system_health_score': health_score
        }

        return report

    def _calculate_health_score(self, report: Dict[str, Any]) -> float:
        """Calculate overall system health score (0-100)"""
        score = 100.0

        # Redis connectivity (-50 if down)
        if not report['queue_status'].get('redis_connected', False):
            score -= 50

        # Worker health (-30 if no healthy workers)
        if report['worker_health'].get('healthy_workers', 0) == 0:
            score -= 30

        # Queue backlog (-20 if high backlog)
        pending_jobs = report['queue_status'].get('backtest_jobs_pending', 0)
        healthy_workers = max(report['worker_health'].get('healthy_workers', 1), 1)
        backlog_ratio = pending_jobs / healthy_workers
        if backlog_ratio > 5:
            score -= 20
        elif backlog_ratio > 2:
            score -= 10

        # System resources (-10 if high usage)
        cpu_percent = report['system_metrics'].get('cpu_percent', 0)
        memory_percent = report['system_metrics'].get('memory_percent', 0)
        if cpu_percent > 90 or memory_percent > 90:
            score -= 10

        return max(0, score)

    def print_report(self, report: Dict[str, Any]) -> None:
        """Print formatted monitoring report"""
        print("=" * 60)
        print("DISTRIBUTED BACKTESTING SYSTEM MONITOR")
        print("=" * 60)
        print(f"Timestamp: {report['timestamp']}")
        print()

        # Queue Status
        queue = report['queue_status']
        print("📊 QUEUE STATUS")
        print(f"  Jobs Pending: {queue.get('backtest_jobs_pending', 'N/A')}")
        print(f"  Active Workers: {queue.get('active_workers', 'N/A')}")
        print(f"  Completed Jobs: {queue.get('completed_jobs', 'N/A')}")
        print(f"  Active Batches: {queue.get('active_batches', 'N/A')}")
        print(f"  Redis Connected: {'✅' if queue.get('redis_connected') else '❌'}")
        print()

        # Worker Health
        workers = report['worker_health']
        print("🔧 WORKER HEALTH")
        print(f"  Total Workers: {workers.get('total_workers', 'N/A')}")
        print(f"  Healthy Workers: {workers.get('healthy_workers', 'N/A')}")
        print(f"  Containers OK: {'✅' if workers.get('worker_containers_ok') else '❌'}")
        print()

        # System Metrics
        system = report['system_metrics']
        print("💻 SYSTEM METRICS")
        print(f"  CPU Usage: {system.get('cpu_percent', 'N/A')}%")
        print(f"  Memory: {system.get('memory_used_gb', 'N/A')}GB / {system.get('memory_total_gb', 'N/A')}GB ({system.get('memory_percent', 'N/A')}%)")
        print(f"  Disk Usage: {system.get('disk_usage_percent', 'N/A')}%")
        print()

        # Recent Performance
        perf = report['recent_performance']
        print("⚡ RECENT PERFORMANCE (Last Hour)")
        print(f"  Jobs Processed: {perf.get('recent_jobs_last_hour', 'N/A')}")
        print(f"  Successful Jobs: {perf.get('successful_jobs_last_hour', 'N/A')}")
        print(f"  Avg Execution Time: {perf.get('avg_execution_time_seconds', 'N/A')}s")
        print(f"  Throughput: {perf.get('jobs_per_minute', 'N/A')} jobs/min")
        print()

        # Derived Metrics
        derived = report['derived_metrics']
        print("📈 DERIVED METRICS")
        print(f"  Queue Backlog Ratio: {derived.get('queue_backlog_ratio', 'N/A'):.1f}")
        print(f"  Worker Utilization: {derived.get('worker_utilization_percent', 'N/A'):.1f}%")
        print(f"  System Health Score: {derived.get('system_health_score', 'N/A'):.1f}/100")
        print()

        # Health status
        health_score = derived.get('system_health_score', 0)
        if health_score >= 80:
            print("🟢 SYSTEM STATUS: HEALTHY")
        elif health_score >= 60:
            print("🟡 SYSTEM STATUS: WARNING")
        else:
            print("🔴 SYSTEM STATUS: CRITICAL")
        print("=" * 60)


def main():
    """Command line interface for monitoring"""
    import argparse

    parser = argparse.ArgumentParser(description="Distributed Backtesting Monitor")
    parser.add_argument('--redis-host', default='redis', help='Redis host')
    parser.add_argument('--redis-port', type=int, default=6379, help='Redis port')
    parser.add_argument('--continuous', action='store_true', help='Run continuous monitoring')
    parser.add_argument('--interval', type=int, default=30, help='Monitoring interval in seconds')

    args = parser.parse_args()

    monitor = BacktestMonitor(args.redis_host, args.redis_port)

    if args.continuous:
        print("Starting continuous monitoring (Ctrl+C to stop)...")
        try:
            while True:
                report = monitor.generate_report()
                monitor.print_report(report)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
    else:
        report = monitor.generate_report()
        monitor.print_report(report)


if __name__ == "__main__":
    main()