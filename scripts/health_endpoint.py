#!/usr/bin/env python3
"""
Health Check Endpoint - HTTP endpoint for health monitoring.

Epic 8.4: Health Monitoring
US-8.4: Health monitoring endpoint (/health)
"""

import sys
import os
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent))

from scripts.utils.health_monitor import HealthMonitor
import json
from datetime import datetime

# Simple HTTP server for health checks
def create_health_response():
    """Create health check response."""
    try:
        health_monitor = HealthMonitor()
        health_response = health_monitor.get_health_response()
        
        # Add additional system information
        health_response['system_info'] = {
            'platform': sys.platform,
            'python_version': sys.version,
            'timestamp': datetime.now().isoformat(),
            'uptime': 'N/A'  # Would calculate actual uptime
        }
        
        return health_response
        
    except Exception as e:
        return {
            'status': 'critical',
            'message': f'Health check failed: {str(e)}',
            'timestamp': datetime.now().isoformat(),
            'http_status': 503,
            'error': str(e)
        }

def health_endpoint_handler():
    """Simple health endpoint handler."""
    response = create_health_response()
    http_status = response.get('http_status', 503)
    
    # Return JSON response
    return json.dumps(response, indent=2), http_status

if __name__ == "__main__":
    # Test the health endpoint
    response, status_code = health_endpoint_handler()
    print(f"HTTP Status: {status_code}")
    print("Response:")
    print(response)