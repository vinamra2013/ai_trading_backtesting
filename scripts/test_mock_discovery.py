#!/usr/bin/env python3
"""
Mock Symbol Discovery Test - Epic 18
Demonstrates the complete symbol discovery workflow with mock data.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.symbol_discovery import SymbolDiscoveryEngine
from scripts.symbol_discovery_models import DiscoveredSymbol


def create_mock_scanner_results(scanner_name: str) -> list[DiscoveredSymbol]:
    """Create mock scanner results for testing."""
    mock_data = {
        'high_volume': [
            DiscoveredSymbol('AAPL', 'NASDAQ', sector='Technology', avg_volume=50000000, atr=2.5, price=150.0, pct_change=1.2, volume=30000000),
            DiscoveredSymbol('MSFT', 'NASDAQ', sector='Technology', avg_volume=28000000, atr=2.1, price=420.0, pct_change=1.8, volume=18000000),
            DiscoveredSymbol('AMZN', 'NASDAQ', sector='Consumer Cyclical', avg_volume=32000000, atr=2.8, price=155.0, pct_change=-0.3, volume=22000000),
            DiscoveredSymbol('TSLA', 'NASDAQ', sector='Consumer Cyclical', avg_volume=25000000, atr=3.2, price=250.0, pct_change=2.1, volume=15000000),
            DiscoveredSymbol('NVDA', 'NASDAQ', sector='Technology', avg_volume=45000000, atr=4.2, price=145.0, pct_change=3.5, volume=35000000),
        ],
        'top_gainers': [
            DiscoveredSymbol('NVDA', 'NASDAQ', sector='Technology', avg_volume=45000000, atr=4.2, price=145.0, pct_change=5.2, volume=35000000),
            DiscoveredSymbol('AMD', 'NASDAQ', sector='Technology', avg_volume=55000000, atr=3.8, price=165.0, pct_change=4.8, volume=40000000),
            DiscoveredSymbol('TSLA', 'NASDAQ', sector='Consumer Cyclical', avg_volume=25000000, atr=3.2, price=250.0, pct_change=4.1, volume=15000000),
        ],
        'volatility_leaders': [
            DiscoveredSymbol('TSLA', 'NASDAQ', sector='Consumer Cyclical', avg_volume=25000000, atr=3.2, price=250.0, pct_change=2.1, volume=15000000),
            DiscoveredSymbol('NVDA', 'NASDAQ', sector='Technology', avg_volume=45000000, atr=4.2, price=145.0, pct_change=3.5, volume=35000000),
            DiscoveredSymbol('AMD', 'NASDAQ', sector='Technology', avg_volume=55000000, atr=3.8, price=165.0, pct_change=4.2, volume=40000000),
        ]
    }

    return mock_data.get(scanner_name, [])


def test_mock_discovery_workflow():
    """Test the complete discovery workflow with mock data."""
    print("=== MOCK SYMBOL DISCOVERY TEST ===")
    print()

    # Initialize engine
    engine = SymbolDiscoveryEngine()

    # Test different scanners
    scanners_to_test = ['high_volume', 'top_gainers', 'volatility_leaders']

    for scanner_name in scanners_to_test:
        print(f"Testing scanner: {scanner_name}")
        print("-" * 40)

        # Get mock scanner results
        mock_symbols = create_mock_scanner_results(scanner_name)
        print(f"Mock scanner returned {len(mock_symbols)} symbols")

        # Apply filters (simulate what would happen in real scanning)
        filtered_symbols = engine.apply_filters(mock_symbols)
        print(f"After filtering: {len(filtered_symbols)} symbols passed")

        # Show sample results
        if filtered_symbols:
            print("Sample filtered symbols:")
            for symbol in filtered_symbols[:3]:  # Show first 3
                print(f"  {symbol.symbol} ({symbol.exchange}) - Vol: {symbol.avg_volume:,} - ATR: {symbol.atr} - Price: ${symbol.price}")
        print()

    print("✅ Mock discovery workflow test completed successfully!")


def test_file_output_generation():
    """Test that file output generation works correctly."""
    print("=== FILE OUTPUT GENERATION TEST ===")
    print()

    from scripts.symbol_discovery import save_to_csv, save_to_json
    from pathlib import Path
    import datetime

    # Create test data
    test_symbols = create_mock_scanner_results('high_volume')[:3]  # Use first 3 symbols

    # Create output directory
    output_dir = Path('data/discovered_symbols')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    scanner_name = 'test_mock'

    # Generate both formats
    csv_file = output_dir / f'{scanner_name}_{timestamp}.csv'
    json_file = output_dir / f'{scanner_name}_{timestamp}.json'

    save_to_csv(test_symbols, csv_file)
    save_to_json(test_symbols, json_file)

    print(f"✅ CSV file created: {csv_file} ({csv_file.stat().st_size} bytes)")
    print(f"✅ JSON file created: {json_file} ({json_file.stat().st_size} bytes)")
    print()

    # Show CSV content
    print("CSV Content Preview:")
    with open(csv_file, 'r') as f:
        lines = f.readlines()
        for line in lines[:4]:  # Show header + 3 data rows
            print(f"  {line.strip()}")
    print()

    print("✅ File output generation test completed!")


if __name__ == '__main__':
    test_mock_discovery_workflow()
    print()
    test_file_output_generation()