#!/usr/bin/env python3
"""
Performance Monitor Utility - System performance tracking and monitoring.

Epic 7.5: Performance Monitoring
US-7.5: Order execution latency, data feed latency, system metrics
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import subprocess
import json

# Add parent directory to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from scripts.db_manager import DBManager

logger = logging.getLogger(__name__)

# Try to import psutil, fallback if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available - system metrics will be limited")


class PerformanceMonitor:
    """
    Performance monitoring system for trading platform.
    
    Tracks:
    - Order execution latency
    - Data feed latency
    - System resource usage (CPU, memory, disk)
    - Database performance
    - Backtest execution times
    """

    def __init__(self, db_path: str = None):
        """
        Initialize PerformanceMonitor.
        
        Args:
            db_path: Path to SQLite database (auto-detects if None)
        """
        # Auto-detect database path if not provided
        if db_path is None:
            # Try to find the project root and set correct database path
            script_dir = Path(__file__).parent.parent.parent  # Go up to project root
            db_path = str(script_dir / "data" / "sqlite" / "trades.db")
        
        self.db_manager = DBManager(db_path)
        self.is_monitoring = False
        self.monitoring_thread = None
        self.monitoring_interval = 30  # seconds
        
        # Performance thresholds for alerts
        self.thresholds = {
            'order_latency_ms': 1000,  # 1 second
            'data_feed_latency_ms': 500,  # 500ms
            'cpu_usage_percent': 80,
            'memory_usage_percent': 85,
            'disk_usage_percent': 90,
            'database_latency_ms': 100
        }
        
        logger.info("PerformanceMonitor initialized")

    def start_monitoring(self) -> None:
        """Start continuous performance monitoring."""
        if self.is_monitoring:
            logger.warning("Performance monitoring already running")
            return
        
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("Performance monitoring started")

    def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")

    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                self.collect_system_metrics()
                time.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)

    def collect_system_metrics(self) -> None:
        """Collect and record system performance metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.record_metric('CPU_USAGE', 'cpu_usage', cpu_percent, '%')
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.record_metric('MEMORY_USAGE', 'memory_usage', memory.percent, '%')
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.record_metric('DISK_USAGE', 'disk_usage', disk_percent, '%')
            
            # Database latency test
            db_latency = self._measure_database_latency()
            if db_latency:
                self.record_metric('DATABASE_LATENCY', 'query_latency', db_latency, 'ms')
            
            # Check thresholds and alert if needed
            self._check_thresholds()
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")

    def _measure_database_latency(self) -> Optional[float]:
        """Measure database query latency."""
        try:
            start_time = time.time()
            # Simple query to test database responsiveness
            self.db_manager.get_positions()
            end_time = time.time()
            return (end_time - start_time) * 1000  # Convert to milliseconds
        except Exception as e:
            logger.error(f"Database latency measurement failed: {e}")
            return None

    def _check_thresholds(self) -> None:
        """Check performance thresholds and log alerts."""
        try:
            latest_metrics = self.db_manager.get_latest_performance_metrics()
            
            # Check CPU usage
            cpu_key = 'CPU_USAGE_cpu_usage'
            if cpu_key in latest_metrics:
                cpu_value = latest_metrics[cpu_key]['value']
                if cpu_value > self.thresholds['cpu_usage_percent']:
                    logger.warning(f"High CPU usage: {cpu_value:.1f}% (threshold: {self.thresholds['cpu_usage_percent']}%)")
            
            # Check memory usage
            memory_key = 'MEMORY_USAGE_memory_usage'
            if memory_key in latest_metrics:
                memory_value = latest_metrics[memory_key]['value']
                if memory_value > self.thresholds['memory_usage_percent']:
                    logger.warning(f"High memory usage: {memory_value:.1f}% (threshold: {self.thresholds['memory_usage_percent']}%)")
            
            # Check disk usage
            disk_key = 'DISK_USAGE_disk_usage'
            if disk_key in latest_metrics:
                disk_value = latest_metrics[disk_key]['value']
                if disk_value > self.thresholds['disk_usage_percent']:
                    logger.warning(f"High disk usage: {disk_value:.1f}% (threshold: {self.thresholds['disk_usage_percent']}%)")
            
        except Exception as e:
            logger.error(f"Error checking thresholds: {e}")

    def record_order_latency(self, order_id: str, submit_time: datetime, fill_time: datetime, algorithm: str = 'live_strategy') -> bool:
        """
        Record order execution latency.
        
        Args:
            order_id: Order identifier
            submit_time: Order submission time
            fill_time: Order fill time
            algorithm: Algorithm name
            
        Returns:
            True if successful
        """
        try:
            latency_ms = (fill_time - submit_time).total_seconds() * 1000
            return self.record_metric(
                'ORDER_LATENCY', 
                f'order_{order_id}', 
                latency_ms, 
                'ms',
                algorithm,
                {'order_id': order_id, 'submit_time': submit_time.isoformat(), 'fill_time': fill_time.isoformat()}
            )
        except Exception as e:
            logger.error(f"Error recording order latency: {e}")
            return False

    def record_data_feed_latency(self, data_source: str, latency_ms: float, algorithm: str = 'live_strategy') -> bool:
        """
        Record data feed latency.
        
        Args:
            data_source: Source of data (e.g., 'IB', 'AlphaVantage')
            latency_ms: Latency in milliseconds
            algorithm: Algorithm name
            
        Returns:
            True if successful
        """
        return self.record_metric(
            'DATA_FEED_LATENCY',
            data_source,
            latency_ms,
            'ms',
            algorithm,
            {'data_source': data_source}
        )

    def record_backtest_time(self, backtest_name: str, execution_time_seconds: float, algorithm: str = None) -> bool:
        """
        Record backtest execution time.
        
        Args:
            backtest_name: Name of the backtest
            execution_time_seconds: Time taken in seconds
            algorithm: Algorithm name (optional)
            
        Returns:
            True if successful
        """
        return self.record_metric(
            'BACKTEST_TIME',
            backtest_name,
            execution_time_seconds,
            'seconds',
            algorithm,
            {'backtest_name': backtest_name}
        )

    def record_metric(
        self,
        metric_type: str,
        metric_name: str,
        metric_value: float,
        unit: str,
        algorithm: str = None,
        additional_data: Dict = None
    ) -> bool:
        """
        Record a performance metric to the database.
        
        Args:
            metric_type: Type of metric
            metric_name: Name of metric
            metric_value: Value of metric
            unit: Unit of measurement
            algorithm: Algorithm name (optional)
            additional_data: Additional context data
            
        Returns:
            True if successful
        """
        try:
            return self.db_manager.record_performance_metric(
                metric_type=metric_type,
                metric_name=metric_name,
                metric_value=metric_value,
                unit=unit,
                algorithm=algorithm,
                additional_data=additional_data
            )
        except Exception as e:
            logger.error(f"Error recording metric: {e}")
            return False

    def get_performance_summary(self, hours_back: int = 24) -> Dict[str, Any]:
        """
        Get performance summary for the last N hours.
        
        Args:
            hours_back: Number of hours to look back
            
        Returns:
            Dictionary with performance summary
        """
        try:
            metrics = self.db_manager.get_performance_metrics(hours_back=hours_back)
            
            if not metrics:
                return {'message': 'No performance data available'}
            
            # Group metrics by type
            summary = {}
            for metric in metrics:
                metric_type = metric['metric_type']
                if metric_type not in summary:
                    summary[metric_type] = []
                summary[metric_type].append(metric)
            
            # Calculate averages for each metric type
            result = {}
            for metric_type, type_metrics in summary.items():
                values = [m['metric_value'] for m in type_metrics]
                result[metric_type] = {
                    'count': len(values),
                    'average': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'latest': values[0] if values else 0,
                    'unit': type_metrics[0]['unit'] if type_metrics else ''
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {'error': str(e)}

    def get_performance_alerts(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """
        Get performance alerts based on threshold breaches.
        
        Args:
            hours_back: Number of hours to look back
            
        Returns:
            List of performance alerts
        """
        try:
            metrics = self.db_manager.get_performance_metrics(hours_back=hours_back)
            alerts = []
            
            for metric in metrics:
                alert = None
                
                # Check thresholds based on metric type
                if metric['metric_type'] == 'CPU_USAGE' and metric['metric_value'] > self.thresholds['cpu_usage_percent']:
                    alert = {
                        'type': 'HIGH_CPU_USAGE',
                        'message': f"CPU usage {metric['metric_value']:.1f}% exceeds threshold {self.thresholds['cpu_usage_percent']}%",
                        'severity': 'WARNING',
                        'timestamp': metric['timestamp'],
                        'value': metric['metric_value'],
                        'threshold': self.thresholds['cpu_usage_percent']
                    }
                
                elif metric['metric_type'] == 'MEMORY_USAGE' and metric['metric_value'] > self.thresholds['memory_usage_percent']:
                    alert = {
                        'type': 'HIGH_MEMORY_USAGE',
                        'message': f"Memory usage {metric['metric_value']:.1f}% exceeds threshold {self.thresholds['memory_usage_percent']}%",
                        'severity': 'WARNING',
                        'timestamp': metric['timestamp'],
                        'value': metric['metric_value'],
                        'threshold': self.thresholds['memory_usage_percent']
                    }
                
                elif metric['metric_type'] == 'DISK_USAGE' and metric['metric_value'] > self.thresholds['disk_usage_percent']:
                    alert = {
                        'type': 'HIGH_DISK_USAGE',
                        'message': f"Disk usage {metric['metric_value']:.1f}% exceeds threshold {self.thresholds['disk_usage_percent']}%",
                        'severity': 'WARNING',
                        'timestamp': metric['timestamp'],
                        'value': metric['metric_value'],
                        'threshold': self.thresholds['disk_usage_percent']
                    }
                
                elif metric['metric_type'] == 'ORDER_LATENCY' and metric['metric_value'] > self.thresholds['order_latency_ms']:
                    alert = {
                        'type': 'HIGH_ORDER_LATENCY',
                        'message': f"Order latency {metric['metric_value']:.1f}ms exceeds threshold {self.thresholds['order_latency_ms']}ms",
                        'severity': 'WARNING',
                        'timestamp': metric['timestamp'],
                        'value': metric['metric_value'],
                        'threshold': self.thresholds['order_latency_ms']
                    }
                
                elif metric['metric_type'] == 'DATA_FEED_LATENCY' and metric['metric_value'] > self.thresholds['data_feed_latency_ms']:
                    alert = {
                        'type': 'HIGH_DATA_FEED_LATENCY',
                        'message': f"Data feed latency {metric['metric_value']:.1f}ms exceeds threshold {self.thresholds['data_feed_latency_ms']}ms",
                        'severity': 'WARNING',
                        'timestamp': metric['timestamp'],
                        'value': metric['metric_value'],
                        'threshold': self.thresholds['data_feed_latency_ms']
                    }
                
                if alert:
                    alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting performance alerts: {e}")
            return []

    def cleanup_old_metrics(self, days_to_keep: int = 30) -> bool:
        """
        Clean up old performance metrics.
        
        Args:
            days_to_keep: Number of days of metrics to keep
            
        Returns:
            True if successful
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM performance_metrics 
                    WHERE timestamp < datetime('now', '-{} days')
                """.format(days_to_keep))
                deleted_count = cursor.rowcount
                logger.info(f"Cleaned up {deleted_count} old performance metrics")
                return True
        except Exception as e:
            logger.error(f"Error cleaning up old metrics: {e}")
            return False


# Context manager for timing operations
class PerformanceTimer:
    """Context manager for timing operations and recording metrics."""

    def __init__(self, monitor: PerformanceMonitor, metric_name: str, metric_type: str = 'OPERATION_TIME', algorithm: str = None):
        """
        Initialize performance timer.
        
        Args:
            monitor: PerformanceMonitor instance
            metric_name: Name of the metric
            metric_type: Type of metric
            algorithm: Algorithm name
        """
        self.monitor = monitor
        self.metric_name = metric_name
        self.metric_type = metric_type
        self.algorithm = algorithm
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            execution_time = time.time() - self.start_time
            self.monitor.record_metric(
                self.metric_type,
                self.metric_name,
                execution_time,
                'seconds',
                self.algorithm
            )


# Example usage
if __name__ == "__main__":
    # Initialize performance monitor
    monitor = PerformanceMonitor()
    
    # Start monitoring
    monitor.start_monitoring()
    
    try:
        # Example: Record some metrics
        monitor.record_data_feed_latency('IB', 250.5)
        monitor.record_backtest_time('test_strategy', 45.2)
        
        # Example: Use timer context manager
        with PerformanceTimer(monitor, 'database_query', 'DATABASE_LATENCY'):
            # Simulate some work
            time.sleep(0.1)
        
        # Get performance summary
        summary = monitor.get_performance_summary()
        print("Performance Summary:", json.dumps(summary, indent=2))
        
        # Get alerts
        alerts = monitor.get_performance_alerts()
        print("Performance Alerts:", json.dumps(alerts, indent=2))
        
        # Keep running for a bit
        time.sleep(5)
        
    finally:
        # Stop monitoring
        monitor.stop_monitoring()