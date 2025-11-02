#!/usr/bin/env python3
"""
Health Monitor Utility - System health checks and monitoring.

Epic 8.4: Health Monitoring
US-8.4: Health monitoring endpoint, dashboard page, system checks
"""

import logging
import time
import subprocess
import socket
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.db_manager import DBManager

logger = logging.getLogger(__name__)

# Try to import psutil, fallback if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available - system metrics will be limited")


class HealthStatus:
    """Health check status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class HealthCheck:
    """Individual health check result."""
    
    def __init__(self, name: str, status: str, message: str, details: Dict = None):
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'status': self.status,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }


class HealthMonitor:
    """
    Health monitoring system for trading platform.
    
    Performs comprehensive health checks on:
    - Database connectivity
    - IB Gateway connection
    - Disk space
    - Memory usage
    - System resources
    - Network connectivity
    """

    def __init__(self, db_path: str = None):
        """
        Initialize HealthMonitor.
        
        Args:
            db_path: Path to SQLite database (auto-detects if None)
        """
        # Auto-detect database path if not provided
        if db_path is None:
            # Try to find the project root and set correct database path
            script_dir = Path(__file__).parent.parent.parent  # Go up to project root
            db_path = str(script_dir / "data" / "sqlite" / "trades.db")
        
        self.db_path = db_path
        self.db_manager = None
        self.health_history = []
        
        # Health check thresholds
        self.thresholds = {
            'disk_usage_percent': 85,  # Warning at 85%, critical at 95%
            'memory_usage_percent': 80,  # Warning at 80%, critical at 90%
            'cpu_usage_percent': 90,  # Warning at 90%
            'database_response_time_ms': 1000,  # Warning if > 1 second
            'ib_gateway_port': 4001,
            'min_free_disk_gb': 1.0  # Critical if less than 1GB free
        }
        
        logger.info("HealthMonitor initialized")

    def get_db_manager(self) -> Optional[DBManager]:
        """Get database manager instance with error handling."""
        if self.db_manager is None:
            try:
                self.db_manager = DBManager(self.db_path)
            except Exception as e:
                logger.error(f"Failed to initialize DBManager: {e}")
                return None
        return self.db_manager

    def check_database_connectivity(self) -> HealthCheck:
        """Check database connectivity and performance."""
        try:
            db_manager = self.get_db_manager()
            if not db_manager:
                return HealthCheck(
                    "Database Connectivity",
                    HealthStatus.CRITICAL,
                    "Database manager initialization failed",
                    {"error": "DBManager not available"}
                )
            
            # Test database connection
            start_time = time.time()
            positions = db_manager.get_positions()
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Check response time
            if response_time > self.thresholds['database_response_time_ms']:
                status = HealthStatus.WARNING
                message = f"Database response time slow: {response_time:.1f}ms"
            else:
                status = HealthStatus.HEALTHY
                message = f"Database connected ({len(positions)} positions)"
            
            return HealthCheck(
                "Database Connectivity",
                status,
                message,
                {
                    "response_time_ms": response_time,
                    "positions_count": len(positions),
                    "database_path": self.db_path
                }
            )
            
        except Exception as e:
            return HealthCheck(
                "Database Connectivity",
                HealthStatus.CRITICAL,
                f"Database connection failed: {str(e)}",
                {"error": str(e)}
            )

    def check_ib_gateway(self) -> HealthCheck:
        """Check IB Gateway connectivity."""
        try:
            # Check if IB Gateway port is open
            port = self.thresholds['ib_gateway_port']
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                return HealthCheck(
                    "IB Gateway",
                    HealthStatus.HEALTHY,
                    f"IB Gateway connected on port {port}",
                    {"port": port, "host": "localhost"}
                )
            else:
                return HealthCheck(
                    "IB Gateway",
                    HealthStatus.CRITICAL,
                    f"IB Gateway not reachable on port {port}",
                    {"port": port, "host": "localhost", "error": "Connection refused"}
                )
                
        except Exception as e:
            return HealthCheck(
                "IB Gateway",
                HealthStatus.CRITICAL,
                f"IB Gateway check failed: {str(e)}",
                {"error": str(e)}
            )

    def check_disk_space(self) -> HealthCheck:
        """Check disk space usage."""
        if not PSUTIL_AVAILABLE:
            return HealthCheck(
                "Disk Space",
                HealthStatus.UNKNOWN,
                "Disk space check unavailable (psutil not installed)",
                {"error": "psutil not available"}
            )
        
        try:
            disk = psutil.disk_usage('/')
            free_gb = disk.free / (1024**3)
            used_percent = (disk.used / disk.total) * 100
            
            if free_gb < self.thresholds['min_free_disk_gb']:
                status = HealthStatus.CRITICAL
                message = f"Critical disk space: {free_gb:.1f}GB free ({used_percent:.1f}% used)"
            elif used_percent > self.thresholds['disk_usage_percent']:
                status = HealthStatus.WARNING
                message = f"Low disk space: {free_gb:.1f}GB free ({used_percent:.1f}% used)"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk space OK: {free_gb:.1f}GB free ({used_percent:.1f}% used)"
            
            return HealthCheck(
                "Disk Space",
                status,
                message,
                {
                    "free_gb": free_gb,
                    "used_percent": used_percent,
                    "total_gb": disk.total / (1024**3),
                    "threshold_gb": self.thresholds['min_free_disk_gb']
                }
            )
            
        except Exception as e:
            return HealthCheck(
                "Disk Space",
                HealthStatus.CRITICAL,
                f"Disk space check failed: {str(e)}",
                {"error": str(e)}
            )

    def check_memory_usage(self) -> HealthCheck:
        """Check memory usage."""
        if not PSUTIL_AVAILABLE:
            return HealthCheck(
                "Memory Usage",
                HealthStatus.UNKNOWN,
                "Memory check unavailable (psutil not installed)",
                {"error": "psutil not available"}
            )
        
        try:
            memory = psutil.virtual_memory()
            used_percent = memory.percent
            available_gb = memory.available / (1024**3)
            
            if used_percent > 90:
                status = HealthStatus.CRITICAL
                message = f"Critical memory usage: {used_percent:.1f}% ({available_gb:.1f}GB available)"
            elif used_percent > self.thresholds['memory_usage_percent']:
                status = HealthStatus.WARNING
                message = f"High memory usage: {used_percent:.1f}% ({available_gb:.1f}GB available)"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage OK: {used_percent:.1f}% ({available_gb:.1f}GB available)"
            
            return HealthCheck(
                "Memory Usage",
                status,
                message,
                {
                    "used_percent": used_percent,
                    "available_gb": available_gb,
                    "total_gb": memory.total / (1024**3),
                    "threshold_percent": self.thresholds['memory_usage_percent']
                }
            )
            
        except Exception as e:
            return HealthCheck(
                "Memory Usage",
                HealthStatus.CRITICAL,
                f"Memory check failed: {str(e)}",
                {"error": str(e)}
            )

    def check_cpu_usage(self) -> HealthCheck:
        """Check CPU usage."""
        if not PSUTIL_AVAILABLE:
            return HealthCheck(
                "CPU Usage",
                HealthStatus.UNKNOWN,
                "CPU check unavailable (psutil not installed)",
                {"error": "psutil not available"}
            )
        
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            
            if cpu_percent > self.thresholds['cpu_usage_percent']:
                status = HealthStatus.WARNING
                message = f"High CPU usage: {cpu_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"CPU usage OK: {cpu_percent:.1f}%"
            
            return HealthCheck(
                "CPU Usage",
                status,
                message,
                {
                    "cpu_percent": cpu_percent,
                    "threshold_percent": self.thresholds['cpu_usage_percent'],
                    "cpu_count": psutil.cpu_count()
                }
            )
            
        except Exception as e:
            return HealthCheck(
                "CPU Usage",
                HealthStatus.CRITICAL,
                f"CPU check failed: {str(e)}",
                {"error": str(e)}
            )

    def check_network_connectivity(self) -> HealthCheck:
        """Check network connectivity."""
        try:
            # Test connectivity to a reliable external service
            test_hosts = ['8.8.8.8', '1.1.1.1']  # Google DNS, Cloudflare DNS
            successful_pings = 0
            
            for host in test_hosts:
                try:
                    result = subprocess.run(
                        ['ping', '-c', '1', '-W', '3', host],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        successful_pings += 1
                        break
                except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                    continue
            
            if successful_pings > 0:
                return HealthCheck(
                    "Network Connectivity",
                    HealthStatus.HEALTHY,
                    "Network connectivity OK",
                    {"test_hosts": test_hosts, "successful_pings": successful_pings}
                )
            else:
                return HealthCheck(
                    "Network Connectivity",
                    HealthStatus.WARNING,
                    "Network connectivity issues detected",
                    {"test_hosts": test_hosts, "successful_pings": 0}
                )
                
        except Exception as e:
            return HealthCheck(
                "Network Connectivity",
                HealthStatus.WARNING,
                f"Network check failed: {str(e)}",
                {"error": str(e)}
            )

    def check_file_permissions(self) -> HealthCheck:
        """Check critical file permissions."""
        try:
            # Get project root directory
            script_dir = Path(__file__).parent.parent.parent  # Go up to project root
            
            critical_paths = [
                script_dir / "data" / "sqlite",
                script_dir / "logs",
                script_dir / "config",
                script_dir / "backups"
            ]
            
            permission_issues = []
            existing_paths = []
            
            for path in critical_paths:
                path_str = str(path)
                if path.exists():
                    existing_paths.append(path_str)
                    if not os.access(path, os.W_OK):
                        permission_issues.append(f"{path_str} (no write access)")
                else:
                    # Create missing directories if they should exist
                    if path.name in ['data', 'logs', 'backups']:
                        try:
                            path.mkdir(parents=True, exist_ok=True)
                            existing_paths.append(path_str)
                            logger.info(f"Created missing directory: {path_str}")
                        except Exception as create_error:
                            permission_issues.append(f"{path_str} (cannot create)")
                    else:
                        permission_issues.append(f"{path_str} (does not exist)")
            
            if permission_issues:
                return HealthCheck(
                    "File Permissions",
                    HealthStatus.WARNING,
                    f"Permission issues: {', '.join(permission_issues)}",
                    {"issues": permission_issues, "existing_paths": existing_paths}
                )
            else:
                return HealthCheck(
                    "File Permissions",
                    HealthStatus.HEALTHY,
                    "File permissions OK",
                    {"checked_paths": [str(p) for p in critical_paths], "existing_paths": existing_paths}
                )
                
        except Exception as e:
            return HealthCheck(
                "File Permissions",
                HealthStatus.WARNING,
                f"Permission check failed: {str(e)}",
                {"error": str(e)}
            )

    def run_all_checks(self) -> List[HealthCheck]:
        """Run all health checks."""
        checks = [
            self.check_database_connectivity(),
            self.check_ib_gateway(),
            self.check_disk_space(),
            self.check_memory_usage(),
            self.check_cpu_usage(),
            self.check_network_connectivity(),
            self.check_file_permissions()
        ]
        
        # Store in history
        self.health_history.append({
            'timestamp': datetime.now(),
            'checks': [check.to_dict() for check in checks]
        })
        
        # Keep only last 100 entries
        if len(self.health_history) > 100:
            self.health_history = self.health_history[-100:]
        
        return checks

    def get_overall_status(self, checks: List[HealthCheck] = None) -> Tuple[str, str]:
        """
        Get overall health status.
        
        Args:
            checks: List of health checks (if None, runs all checks)
            
        Returns:
            Tuple of (status, message)
        """
        if checks is None:
            checks = self.run_all_checks()
        
        # Count status types
        status_counts = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.WARNING: 0,
            HealthStatus.CRITICAL: 0,
            HealthStatus.UNKNOWN: 0
        }
        
        for check in checks:
            status_counts[check.status] += 1
        
        # Determine overall status
        if status_counts[HealthStatus.CRITICAL] > 0:
            return HealthStatus.CRITICAL, f"Critical issues detected ({status_counts[HealthStatus.CRITICAL]} checks failed)"
        elif status_counts[HealthStatus.WARNING] > 0:
            return HealthStatus.WARNING, f"Warnings detected ({status_counts[HealthStatus.WARNING]} checks with warnings)"
        elif status_counts[HealthStatus.HEALTHY] == len(checks):
            return HealthStatus.HEALTHY, "All systems healthy"
        else:
            return HealthStatus.UNKNOWN, "Health status unknown"

    def get_health_summary(self, hours_back: int = 24) -> Dict[str, Any]:
        """
        Get health summary for the last N hours.
        
        Args:
            hours_back: Number of hours to look back
            
        Returns:
            Dictionary with health summary
        """
        try:
            cutoff_time = datetime.now().timestamp() - (hours_back * 3600)
            recent_history = [
                entry for entry in self.health_history 
                if entry['timestamp'].timestamp() > cutoff_time
            ]
            
            if not recent_history:
                return {'message': 'No health data available'}
            
            # Analyze recent health data
            total_checks = 0
            healthy_checks = 0
            warning_checks = 0
            critical_checks = 0
            
            for entry in recent_history:
                for check in entry['checks']:
                    total_checks += 1
                    if check['status'] == HealthStatus.HEALTHY:
                        healthy_checks += 1
                    elif check['status'] == HealthStatus.WARNING:
                        warning_checks += 1
                    elif check['status'] == HealthStatus.CRITICAL:
                        critical_checks += 1
            
            uptime_percent = (healthy_checks / max(total_checks, 1)) * 100
            
            return {
                'total_checks': total_checks,
                'healthy_checks': healthy_checks,
                'warning_checks': warning_checks,
                'critical_checks': critical_checks,
                'uptime_percent': uptime_percent,
                'period_hours': hours_back,
                'last_check': recent_history[-1]['timestamp'].isoformat() if recent_history else None
            }
            
        except Exception as e:
            logger.error(f"Error getting health summary: {e}")
            return {'error': str(e)}

    def get_http_status_code(self, checks: List[HealthCheck] = None) -> int:
        """
        Get HTTP status code based on health checks.
        
        Args:
            checks: List of health checks (if None, runs all checks)
            
        Returns:
            HTTP status code (200 for healthy, 503 for unhealthy)
        """
        overall_status, _ = self.get_overall_status(checks)
        return 200 if overall_status == HealthStatus.HEALTHY else 503

    def get_health_response(self, checks: List[HealthCheck] = None) -> Dict[str, Any]:
        """
        Get health check response for HTTP endpoint.
        
        Args:
            checks: List of health checks (if None, runs all checks)
            
        Returns:
            Dictionary with health check response
        """
        if checks is None:
            checks = self.run_all_checks()
        
        overall_status, overall_message = self.get_overall_status(checks)
        
        return {
            'status': overall_status,
            'message': overall_message,
            'timestamp': datetime.now().isoformat(),
            'checks': [check.to_dict() for check in checks],
            'http_status': self.get_http_status_code(checks)
        }


# Example usage
if __name__ == "__main__":
    # Initialize health monitor
    health_monitor = HealthMonitor()
    
    # Run all health checks
    checks = health_monitor.run_all_checks()
    
    # Print results
    print("Health Check Results:")
    print("=" * 50)
    
    for check in checks:
        status_emoji = {
            HealthStatus.HEALTHY: "✅",
            HealthStatus.WARNING: "⚠️",
            HealthStatus.CRITICAL: "❌",
            HealthStatus.UNKNOWN: "❓"
        }
        
        print(f"{status_emoji.get(check.status, '❓')} {check.name}: {check.message}")
        if check.details:
            print(f"   Details: {check.details}")
    
    # Get overall status
    overall_status, overall_message = health_monitor.get_overall_status(checks)
    print(f"\nOverall Status: {overall_status.upper()}")
    print(f"Message: {overall_message}")
    
    # Get HTTP status code
    http_status = health_monitor.get_http_status_code(checks)
    print(f"HTTP Status Code: {http_status}")