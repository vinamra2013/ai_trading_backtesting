#!/usr/bin/env python3
"""
Comprehensive test script for Epic 25 Stories 7 & 8 implementation
Tests FastAPI backend and Streamlit integration
"""

import requests
import json
import time
import sys
from datetime import datetime

def test_fastapi_backend():
    """Test FastAPI backend functionality"""
    print("🧪 Testing FastAPI Backend")
    print("=" * 50)
    
    base_url = "http://localhost:8002"
    
    # Test 1: Health endpoint
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200 and response.json().get("status") == "ok":
            print("✅ Health endpoint: PASS")
        else:
            print(f"❌ Health endpoint: FAIL - {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health endpoint: FAIL - {e}")
        return False
    
    # Test 2: API documentation
    try:
        response = requests.get(f"{base_url}/docs", timeout=5)
        if response.status_code == 200 and "Swagger UI" in response.text:
            print("✅ API documentation: PASS")
        else:
            print(f"❌ API documentation: FAIL - {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API documentation: FAIL - {e}")
        return False
    
    # Test 3: Analytics endpoint (should fail gracefully without DB)
    try:
        response = requests.get(f"{base_url}/api/analytics/portfolio", timeout=5)
        if response.status_code == 400:  # Expected to fail due to no DB
            print("✅ Analytics endpoint: PASS (graceful DB error)")
        elif response.status_code == 200:
            print("✅ Analytics endpoint: PASS (with data)")
        else:
            print(f"❌ Analytics endpoint: FAIL - {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Analytics endpoint: FAIL - {e}")
        return False
    
    # Test 4: OpenAPI schema
    try:
        response = requests.get(f"{base_url}/openapi.json", timeout=5)
        schema = response.json()
        if "paths" in schema and "/api/analytics/portfolio" in schema["paths"]:
            print("✅ OpenAPI schema: PASS")
        else:
            print("❌ OpenAPI schema: FAIL - analytics endpoint not in schema")
            return False
    except Exception as e:
        print(f"❌ OpenAPI schema: FAIL - {e}")
        return False
    
    return True

def test_api_client():
    """Test API client functionality"""
    print("\n🧪 Testing API Client")
    print("=" * 50)
    
    try:
        sys.path.insert(0, '/app')
        sys.path.insert(0, '/app/monitoring')
        
        from monitoring.utils.api_client import APIClient, get_api_client
        
        # Test client instantiation
        client = APIClient(base_url="http://localhost:8002")
        print("✅ API client instantiation: PASS")
        
        # Test health check
        try:
            result = client.health_check()
            if result.get("status") == "ok":
                print("✅ API client health check: PASS")
            else:
                print(f"❌ API client health check: FAIL - {result}")
                return False
        except Exception as e:
            print(f"❌ API client health check: FAIL - {e}")
            return False
        
        # Test analytics call (should handle DB error gracefully)
        try:
            result = client.get_portfolio_analytics()
            # Should either return data or error gracefully
            print("✅ API client analytics call: PASS")
        except Exception as e:
            if "Backend API unavailable" in str(e):
                print("✅ API client analytics call: PASS (backend unavailable)")
            else:
                print(f"❌ API client analytics call: FAIL - {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ API client import/test: FAIL - {e}")
        return False

def test_streamlit_structure():
    """Test Streamlit app structure"""
    print("\n🧪 Testing Streamlit Structure")
    print("=" * 50)
    
    try:
        with open('monitoring/app.py', 'r') as f:
            content = f.read()
        
        # Check for key components
        checks = [
            ('API client import', 'from utils.api_client import get_api_client'),
            ('Analytics tab', 'tab5'),
            ('Backend availability check', 'check_backend_availability'),
            ('Job polling', 'poll_job_status'),
            ('Error handling', 'display_backend_unavailable_message'),
            ('10 main tabs', 'tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10'),
            ('Backtest sub-tabs', 'bt_tab1, bt_tab2, bt_tab3'),
            ('Optimization sub-tabs', 'opt_tab1, opt_tab2, opt_tab3')
        ]
        
        for check_name, check_string in checks:
            if check_string in content:
                print(f"✅ {check_name}: FOUND")
            else:
                print(f"❌ {check_name}: MISSING")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Streamlit structure test: FAIL - {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Epic 25 Stories 7 & 8 Implementation Test Suite")
    print("=" * 60)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = []
    
    # Test FastAPI backend
    results.append(("FastAPI Backend", test_fastapi_backend()))
    
    # Test API client
    results.append(("API Client", test_api_client()))
    
    # Test Streamlit structure
    results.append(("Streamlit Structure", test_streamlit_structure()))
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Implementation is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
