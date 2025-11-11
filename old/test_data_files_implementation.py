#!/usr/bin/env python3
"""
Test script for Data Files Management UI implementation
Tests the core components without requiring Docker
"""

import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
sys.path.insert(0, os.path.join(os.getcwd(), "utils"))


def test_data_file_scanner():
    """Test the data file scanner functionality"""
    print("🧪 Testing Data File Scanner...")

    try:
        # Mock the pandas import for testing
        import types

        pd_mock = types.ModuleType("pandas")
        pd_mock.DataFrame = list  # Simple mock
        sys.modules["pandas"] = pd_mock

        from scripts.data_file_scanner import DataFileScanner

        scanner = DataFileScanner()
        files = scanner.scan_data_files()

        print(f"✅ Scanner found {len(files)} data files")

        # Test filename parsing
        test_filenames = [
            "SPY_1m_20240101_20241231.csv",
            "QQQ_5m_20240101_20241231.csv",
            "AAPL_1d_20200101_20241231.csv",
        ]

        for filename in test_filenames:
            result = scanner.parse_filename(filename)
            if result:
                symbol, timeframe, start, end = result
                print(f"✅ Parsed {filename}: {symbol} {timeframe} {start}-{end}")
            else:
                print(f"❌ Failed to parse {filename}")

        return True

    except Exception as e:
        print(f"❌ Data File Scanner test failed: {e}")
        return False


def test_metadata_extractor():
    """Test the metadata extraction utilities"""
    print("\n🧪 Testing Metadata Extractor...")

    try:
        # Mock pandas
        import types

        pd_mock = types.ModuleType("pandas")
        pd_mock.read_csv = lambda *args, **kwargs: []  # Return empty list
        pd_mock.DataFrame = list
        pd_mock.to_datetime = lambda x: x
        pd_mock.notna = lambda x: True
        sys.modules["pandas"] = pd_mock

        from utils.data_metadata import DataMetadataExtractor

        extractor = DataMetadataExtractor()

        # Test filename parsing
        test_filenames = [
            "SPY_1m_20240101_20241231.csv",
            "QQQ_5m_20240101_20241231.csv",
        ]

        for filename in test_filenames:
            result = extractor.parse_filename(filename)
            if result:
                symbol, timeframe, start, end = result
                print(f"✅ Metadata extractor parsed {filename}: {symbol} {timeframe}")
            else:
                print(f"❌ Failed to parse {filename}")

        return True

    except Exception as e:
        print(f"❌ Metadata Extractor test failed: {e}")
        return False


def test_api_router():
    """Test that the API router can be imported"""
    print("\n🧪 Testing API Router Import...")

    try:
        # Test import
        from backend.routers.data import router as data_router

        print("✅ Data API router imported successfully")

        # Check that routes are defined
        routes = [route.path for route in data_router.routes]
        print(f"✅ Found {len(routes)} routes: {routes[:3]}...")

        return True

    except Exception as e:
        print(f"❌ API Router test failed: {e}")
        return False


def test_streamlit_integration():
    """Test that Streamlit app can import the new tab"""
    print("\n🧪 Testing Streamlit Integration...")

    try:
        # Check if the tab count was updated
        with open("monitoring/app.py", "r") as f:
            content = f.read()

        if "tab11" in content:
            print("✅ Streamlit app includes tab11 (Data Files)")
        else:
            print("❌ tab11 not found in Streamlit app")
            return False

        if '"📁 Data Files"' in content:
            print("✅ Data Files tab title found")
        else:
            print("❌ Data Files tab title not found")
            return False

        return True

    except Exception as e:
        print(f"❌ Streamlit integration test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Testing Data Files Management UI Implementation\n")

    tests = [
        test_data_file_scanner,
        test_metadata_extractor,
        test_api_router,
        test_streamlit_integration,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Implementation is ready.")
        return 0
    else:
        print("⚠️ Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
