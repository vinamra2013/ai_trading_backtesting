#!/usr/bin/env python3
"""
V2 Parallel Optimization System - Integration Test
Basic test to verify the system components work together.
"""

import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path


def test_backend_imports():
    """Test that all backend components can be imported."""
    print("🧪 Testing backend imports...")

    try:
        # Test basic imports
        from backend.schemas.optimization import (
            OptimizationRequest,
            OptimizationResponse,
        )
        from backend.models.database import Strategy, BacktestJob, OptimizationBatch
        from backend.services.optimization_service import OptimizationService
        from backend.services.backtest_service import BacktestService
        from backend.routers.optimization import router
        from backend.database import get_db, create_tables

        print("✅ All backend components import successfully")
        return True
    except Exception as e:
        print(f"❌ Backend import failed: {e}")
        return False


def test_cli_syntax():
    """Test that the CLI client has valid syntax."""
    print("🧪 Testing CLI client syntax...")

    try:
        # Try to import the CLI module
        import scripts.optimize_runner_v2 as cli

        print("✅ CLI client imports successfully")
        return True
    except Exception as e:
        print(f"❌ CLI import failed: {e}")
        return False


def test_config_parsing():
    """Test that optimization config files can be parsed."""
    print("🧪 Testing config file parsing...")

    # Create a test config file
    test_config = {
        "strategy": {
            "name": "Test Strategy",
            "lean_project_path": "STR-001_RSI_MeanReversion_ETF",
        },
        "parameters": {
            "rsi_period": {"start": 14, "end": 16, "step": 1},
            "entry_threshold": {"start": 25, "end": 30, "step": 5},
        },
        "symbols": ["SPY"],
        "start_date": "2020-01-01",
        "end_date": "2024-01-01",
    }

    try:
        import yaml
        from backend.services.optimization_service import OptimizationService

        # Write test config
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name

        # Test parsing
        opt_service = OptimizationService(None)  # No DB needed for parsing
        combinations = opt_service.generate_parameter_combinations(config_path)

        expected_combinations = 2 * 2  # 2 rsi_periods * 2 entry_thresholds
        if len(combinations) == expected_combinations:
            print(
                f"✅ Config parsing works: generated {len(combinations)} combinations"
            )
            return True
        else:
            print(
                f"❌ Config parsing failed: expected {expected_combinations}, got {len(combinations)}"
            )
            return False

    except Exception as e:
        print(f"❌ Config parsing test failed: {e}")
        return False
    finally:
        if "config_path" in locals():
            os.unlink(config_path)


def test_docker_compose():
    """Test that docker-compose configuration is valid."""
    print("🧪 Testing docker-compose configuration...")

    try:
        result = subprocess.run(
            ["docker", "compose", "config", "--quiet"],
            cwd="/home/vbhatnagar/code/ai_trading_backtesting",
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("✅ Docker Compose configuration is valid")
            return True
        else:
            print(f"❌ Docker Compose config error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Docker Compose test failed: {e}")
        return False


def main():
    """Run all integration tests."""
    print("🚀 V2 Parallel Optimization System - Integration Tests")
    print("=" * 60)

    tests = [
        test_backend_imports,
        test_cli_syntax,
        test_config_parsing,
        test_docker_compose,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! System is ready for deployment.")
        return 0
    else:
        print("❌ Some tests failed. Please fix issues before deployment.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
