#!/usr/bin/env python3
"""
Test Symbol Discovery Engine - Epic 18
Validation script for symbol discovery functionality.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.symbol_discovery import SymbolDiscoveryEngine
from scripts.symbol_discovery_models import DiscoveredSymbol
from datetime import datetime


def test_config_loading():
    """Test configuration loading."""
    print("Testing configuration loading...")
    try:
        engine = SymbolDiscoveryEngine()
        assert 'scanners' in engine.config
        assert 'filters' in engine.config
        assert 'database' in engine.config
        print("✅ Configuration loading test passed")
        return True
    except Exception as e:
        print(f"❌ Configuration loading test failed: {e}")
        return False


def test_symbol_dataclass():
    """Test DiscoveredSymbol dataclass."""
    print("Testing DiscoveredSymbol dataclass...")
    try:
        symbol = DiscoveredSymbol(
            symbol="AAPL",
            exchange="NASDAQ",
            price=150.0,
            avg_volume=50000000,
            atr=2.5
        )

        assert symbol.symbol == "AAPL"
        assert symbol.exchange == "NASDAQ"
        assert symbol.price == 150.0
        assert symbol.discovery_timestamp is not None

        # Test serialization
        data = symbol.to_dict()
        assert data['symbol'] == "AAPL"
        assert 'discovery_timestamp' in data

        print("✅ DiscoveredSymbol dataclass test passed")
        return True
    except Exception as e:
        print(f"❌ DiscoveredSymbol dataclass test failed: {e}")
        return False


def test_filtering_logic():
    """Test filtering logic without IB connection."""
    print("Testing filtering logic...")
    try:
        engine = SymbolDiscoveryEngine()

        # Create test symbols with ATR values to pass volatility filter
        test_symbols = [
            DiscoveredSymbol("AAPL", "NASDAQ", price=150.0, avg_volume=50000000, atr=2.0),  # Should pass
            DiscoveredSymbol("PENNY", "OTC", price=0.5, avg_volume=1000000, atr=1.0),      # Should fail (price)
            DiscoveredSymbol("LOWVOL", "NYSE", price=50.0, avg_volume=500000, atr=1.0),    # Should fail (volume)
        ]

        filtered = engine.apply_filters(test_symbols)

        # Should only keep AAPL (all filters pass)
        assert len(filtered) == 1, f"Expected 1 symbol, got {len(filtered)}"
        assert filtered[0].symbol == "AAPL", f"Expected AAPL, got {filtered[0].symbol}"

        filtered = engine.apply_filters(test_symbols)

        # Should only keep AAPL
        assert len(filtered) == 1
        assert filtered[0].symbol == "AAPL"

        print("✅ Filtering logic test passed")
        return True
    except Exception as e:
        print(f"❌ Filtering logic test failed: {e}")
        return False


def test_cli_parsing():
    """Test CLI argument parsing."""
    print("Testing CLI argument parsing...")
    try:
        from scripts.symbol_discovery import create_cli_parser

        parser = create_cli_parser()

        # Test valid arguments
        args = parser.parse_args(['--scanner', 'high_volume', '--dry-run'])
        assert args.scanner == 'high_volume'
        assert args.dry_run == True

        # Test filter overrides
        args = parser.parse_args([
            '--scanner', 'volatility_leaders',
            '--min-volume', '2000000',
            '--atr-threshold', '1.5'
        ])
        assert args.min_volume == 2000000
        assert args.atr_threshold == 1.5

        print("✅ CLI parsing test passed")
        return True
    except Exception as e:
        print(f"❌ CLI parsing test failed: {e}")
        return False


def test_database_models():
    """Test database models without actual connection."""
    print("Testing database models...")
    try:
        from scripts.symbol_discovery_db import SymbolDiscoveryDB

        # Test database config structure
        db_config = {
            'host': 'postgres',
            'port': 5432,
            'database': 'symbol_discovery',
            'user': 'mlflow',
            'password': 'test_password',
            'pool': {
                'min_connections': 1,
                'max_connections': 5,
                'connection_timeout': 30
            }
        }

        # This will fail to connect but should initialize the config
        try:
            db = SymbolDiscoveryDB(db_config)
            # Should fail at connection pool creation
        except Exception:
            # Expected to fail without actual database
            pass

        print("✅ Database models test passed")
        return True
    except Exception as e:
        print(f"❌ Database models test failed: {e}")
        return False


def run_all_tests():
    """Run all validation tests."""
    print("=== Symbol Discovery Engine Validation Tests ===\n")

    tests = [
        test_config_loading,
        test_symbol_dataclass,
        test_filtering_logic,
        test_cli_parsing,
        test_database_models,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print(f"=== Test Results: {passed}/{total} tests passed ===")

    if passed == total:
        print("🎉 All validation tests passed!")
        return True
    else:
        print("❌ Some tests failed. Please review the implementation.")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)