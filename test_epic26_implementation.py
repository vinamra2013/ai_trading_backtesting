#!/usr/bin/env python3
"""
Test script for Discovery and Ranking API endpoints (Epic 26 Stories 1 & 2)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Test that all modules can be imported"""
    try:
        # Test model imports
        from backend.models.discovery import (
            DiscoveryJob,
            DiscoveryResult,
            RankingJob,
            RankingResult,
        )

        print("✅ Models imported successfully")

        # Test schema imports
        from backend.schemas.discovery import (
            DiscoveryRequest,
            DiscoveryResponse,
            DiscoveryStatus,
        )
        from backend.schemas.ranking import (
            RankingRequest,
            RankingResponse,
            RankingStatus,
        )

        print("✅ Schemas imported successfully")

        # Test service imports
        from backend.services.discovery_service import (
            DiscoveryService,
            get_discovery_service,
        )
        from backend.services.ranking_service import RankingService, get_ranking_service

        print("✅ Services imported successfully")

        # Test router imports
        from backend.routers.discovery import router as discovery_router
        from backend.routers.ranking import router as ranking_router

        print("✅ Routers imported successfully")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_api_structure():
    """Test that API endpoints are properly defined"""
    try:
        from backend.routers.discovery import router as discovery_router
        from backend.routers.ranking import router as ranking_router

        # Check discovery endpoints
        discovery_routes = [route.path for route in discovery_router.routes]
        expected_discovery = [
            "/scan",
            "/status/{job_id}",
            "/results/{job_id}",
            "/jobs",
            "/jobs/{job_id}",
        ]
        for route in expected_discovery:
            if route not in discovery_routes:
                print(f"❌ Missing discovery route: {route}")
                return False

        # Check ranking endpoints
        ranking_routes = [route.path for route in ranking_router.routes]
        expected_ranking = [
            "/analyze",
            "/status/{job_id}",
            "/results/{job_id}",
            "/jobs",
            "/jobs/{job_id}",
        ]
        for route in expected_ranking:
            if route not in ranking_routes:
                print(f"❌ Missing ranking route: {route}")
                return False

        print("✅ API structure validated")
        return True

    except Exception as e:
        print(f"❌ API structure test failed: {e}")
        return False


def test_schema_validation():
    """Test that schemas work correctly"""
    try:
        from backend.schemas.discovery import DiscoveryRequest
        from backend.schemas.ranking import RankingRequest

        # Test discovery request
        discovery_req = DiscoveryRequest(
            scanner_name="high_volume",
            parameters={"number_of_rows": 50},
            filters={"liquidity": {"min_avg_volume": 1000000}},
        )
        assert discovery_req.scanner_name == "high_volume"
        print("✅ Discovery schema validation passed")

        # Test ranking request
        ranking_req = RankingRequest(
            input_type="csv",
            input_source="results/backtests/latest.csv",
            criteria_weights={
                "sharpe_ratio": 40.0,
                "consistency": 20.0,
                "drawdown_control": 20.0,
                "trade_frequency": 10.0,
                "capital_efficiency": 10.0,
            },
        )
        assert ranking_req.input_type == "csv"
        print("✅ Ranking schema validation passed")

        return True

    except Exception as e:
        print(f"❌ Schema validation failed: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Testing Epic 26 Stories 1 & 2 Implementation")
    print("=" * 50)

    all_passed = True

    # Run tests
    all_passed &= test_imports()
    all_passed &= test_api_structure()
    all_passed &= test_schema_validation()

    print("=" * 50)
    if all_passed:
        print("🎉 All tests passed! Implementation ready for deployment.")
        print("\n📋 Next steps:")
        print(
            "1. Run Alembic migration: docker exec backtrader-engine alembic upgrade head"
        )
        print("2. Start platform: ./scripts/start.sh")
        print("3. Test endpoints: curl http://localhost:8000/docs")
        print("4. Submit discovery job: POST /api/discovery/scan")
        print("5. Submit ranking job: POST /api/ranking/analyze")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)
