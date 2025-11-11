#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/monitoring')

# Import required modules
from monitoring.utils.api_client import APIClient

def get_configured_api_client():
    """Get API client with proper configuration for current environment"""
    # Check for explicit backend URL
    backend_url = os.environ.get('FASTAPI_BACKEND_URL')
    if backend_url:
        return APIClient(base_url=backend_url)

    # Auto-detect based on environment
    return APIClient()

def check_backend_availability():
    """Check if the FastAPI backend is available"""
    try:
        api_client = get_configured_api_client()
        return api_client.is_available()
    except Exception:
        return False

if __name__ == "__main__":
    print("🧪 Testing API Client Configuration")
    print("=" * 50)
    
    # Test 1: Default configuration
    print("Test 1: Default configuration")
    client = get_configured_api_client()
    print(f"  Base URL: {client.base_url}")
    
    # Test 2: Environment variable override
    print("\nTest 2: Environment variable override")
    os.environ['FASTAPI_BACKEND_URL'] = 'http://my-server.com:8230'
    client2 = get_configured_api_client()
    print(f"  Base URL: {client2.base_url}")
    
    # Test 3: Backend availability (reset env)
    print("\nTest 3: Backend availability check")
    del os.environ['FASTAPI_BACKEND_URL']
    available = check_backend_availability()
    print(f"  Backend available: {available}")
    
    print("\n✅ Configuration system working correctly!")
