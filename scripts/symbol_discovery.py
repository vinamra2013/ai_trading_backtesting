#!/usr/bin/env python3
"""
Symbol Discovery Engine - Epic 18
US-18.1: IB Scanner API Integration
US-18.2: Market Data Scanner Types
US-18.3: Filtering and Validation Logic
US-18.4: Data Output and Storage
US-18.5: Command Line Interface

Autonomous symbol discovery system using IB API scanner functionality.
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import asyncio

import yaml
import pandas as pd
import numpy as np
from ib_insync import IB, ScannerSubscription, ScanDataList, Contract

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.ib_connection import IBConnectionManager
from scripts.symbol_discovery_models import DiscoveredSymbol
from scripts.symbol_discovery_db import SymbolDiscoveryDB


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)





class SymbolDiscoveryEngine:
    """
    Main engine for autonomous symbol discovery using IB API scanners.
    """

    def __init__(self, config_path: str = "config/symbol_discovery_config.yaml"):
        """
        Initialize the symbol discovery engine.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.ib_manager: Optional[IBConnectionManager] = None
        self.db: Optional[SymbolDiscoveryDB] = None
        self.setup_logging()

        logger.info("Symbol Discovery Engine initialized")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def setup_logging(self):
        """Setup logging based on configuration."""
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO').upper())
        log_file = log_config.get('file', 'logs/symbol_discovery.log')

        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Create file handler
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')))

        # Add handler to logger
        logger.addHandler(file_handler)
        logger.setLevel(log_level)

    def connect_ib(self) -> bool:
        """
        Establish connection to IB Gateway.

        Returns:
            bool: True if connected successfully
        """
        try:
            self.ib_manager = IBConnectionManager(
                host='ib-gateway',
                port=8888,
                client_id=2  # Use different client ID from other connections
            )

            if self.ib_manager.connect():
                logger.info("✅ Connected to IB Gateway for symbol discovery")
                return True
            else:
                logger.error("❌ Failed to connect to IB Gateway")
                return False

        except Exception as e:
            logger.error(f"Error connecting to IB Gateway: {e}")
            return False

    def connect_db(self) -> bool:
        """
        Establish connection to PostgreSQL database.

        Returns:
            bool: True if connected successfully
        """
        try:
            from scripts.symbol_discovery_db import SymbolDiscoveryDB
            self.db = SymbolDiscoveryDB(self.config['database'])
            logger.info("✅ Connected to PostgreSQL database")
            return True
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            return False

    def disconnect_ib(self):
        """Disconnect from IB Gateway."""
        if self.ib_manager:
            self.ib_manager.disconnect()
            logger.info("Disconnected from IB Gateway")

    def disconnect_db(self):
        """Disconnect from database."""
        if self.db:
            self.db.close()
            logger.info("Disconnected from database")

    def run_scanner(self, scanner_name: str) -> List[DiscoveredSymbol]:
        """
        Run a specific scanner and return discovered symbols.

        Args:
            scanner_name: Name of scanner to run (from config)

        Returns:
            List of discovered symbols
        """
        if not self.ib_manager or not self.ib_manager.is_connected:
            logger.error("IB connection not available")
            return []

        scanner_config = self.config['scanners'].get(scanner_name)
        if not scanner_config:
            logger.error(f"Scanner '{scanner_name}' not found in configuration")
            return []

        logger.info(f"Running scanner: {scanner_name} - {scanner_config['description']}")

        try:
            # Create scanner subscription
            subscription = ScannerSubscription(
                scanCode=scanner_config['scan_code'],
                numberOfRows=scanner_config['parameters']['number_of_rows']
            )

            # Add scanner parameters
            params = scanner_config['parameters']
            if 'above_price' in params:
                subscription.abovePrice = params['above_price']
            if 'below_price' in params:
                subscription.belowPrice = params['below_price']
            if 'above_volume' in params:
                subscription.aboveVolume = params['above_volume']
            if 'instrument_type' in params:
                subscription.instrument = params['instrument_type']

            # Execute scanner
            scan_data_list: ScanDataList = self.ib_manager.ib.reqScannerData(subscription)

            # Wait for results with timeout
            timeout = 30  # seconds
            start_time = time.time()
            while not scan_data_list and (time.time() - start_time) < timeout:
                self.ib_manager.ib.sleep(1)

            if not scan_data_list:
                logger.warning(f"No scan results received for {scanner_name}")
                return []

            # Convert scan data to DiscoveredSymbol objects
            symbols = []
            for scan_data in scan_data_list:
                try:
                    # Extract symbol information from scan data
                    # ScanData typically has contractDetails attribute
                    contract_details = getattr(scan_data, 'contractDetails', None)
                    if contract_details and hasattr(contract_details, 'contract'):
                        contract = contract_details.contract
                        symbol_name = contract.symbol
                        exchange = contract.exchange or 'UNKNOWN'
                    else:
                        # Fallback: try to get symbol directly
                        symbol_name = getattr(scan_data, 'symbol', 'UNKNOWN')
                        exchange = getattr(scan_data, 'exchange', 'UNKNOWN')

                    symbol = DiscoveredSymbol(
                        symbol=symbol_name,
                        exchange=exchange,
                        sector=getattr(scan_data, 'sector', None),
                        avg_volume=getattr(scan_data, 'averageVolume', None),
                        price=getattr(scan_data, 'lastPrice', None),
                        pct_change=getattr(scan_data, 'changePercent', None),
                        volume=getattr(scan_data, 'volume', None)
                    )
                    symbols.append(symbol)
                except Exception as e:
                    logger.warning(f"Error processing scan data: {e}")
                    continue

            logger.info(f"Scanner {scanner_name} found {len(symbols)} symbols")
            return symbols

        except Exception as e:
            logger.error(f"Error running scanner {scanner_name}: {e}")
            return []

    def calculate_atr(self, symbol: str, period: int = 14) -> Optional[float]:
        """
        Calculate Average True Range (ATR) for volatility filtering.

        Args:
            symbol: Stock symbol
            period: ATR calculation period

        Returns:
            ATR value or None if calculation fails
        """
        if not self.ib_manager or not self.ib_manager.ib:
            logger.error("IB connection not available for ATR calculation")
            return None

        try:
            # Create contract for historical data
            contract = Contract(symbol=symbol, secType='STK', exchange='SMART', currency='USD')

            # Get historical data (30 days for ATR calculation)
            bars = self.ib_manager.ib.reqHistoricalData(
                contract,
                endDateTime='',
                durationStr='30 D',
                barSizeSetting='1 day',
                whatToShow='TRADES',
                useRTH=True,
                formatDate=1
            )

            if not bars:
                logger.warning(f"No historical data available for {symbol}")
                return None

            # Calculate True Range
            tr_values = []
            for i in range(1, len(bars)):
                high = bars[i].high
                low = bars[i].low
                prev_close = bars[i-1].close

                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                tr_values.append(tr)

            if len(tr_values) < period:
                logger.warning(f"Insufficient data for ATR calculation for {symbol}")
                return None

            # Calculate ATR (simple moving average of TR)
            atr = np.mean(tr_values[-period:])
            return float(atr)

        except Exception as e:
            logger.error(f"Error calculating ATR for {symbol}: {e}")
            return None

    def apply_filters(self, symbols: List[DiscoveredSymbol]) -> List[DiscoveredSymbol]:
        """
        Apply filtering logic to discovered symbols.

        Args:
            symbols: List of discovered symbols

        Returns:
            Filtered list of symbols
        """
        logger.info(f"Applying filters to {len(symbols)} symbols")

        filters_config = self.config['filters']
        filtered_symbols = []

        for symbol in symbols:
            try:
                # Liquidity filter
                if not self._passes_liquidity_filter(symbol, filters_config['liquidity']):
                    continue

                # Price range filter
                if not self._passes_price_filter(symbol, filters_config['price_range']):
                    continue

                # Exchange filter
                if not self._passes_exchange_filter(symbol, filters_config['exchanges']):
                    continue

                # Calculate ATR for volatility filter if not already provided
                if symbol.price and symbol.price > 0 and symbol.atr is None:
                    symbol.atr = self.calculate_atr(symbol.symbol, filters_config['volatility']['atr_period'])

                # Volatility filter (only if ATR is available)
                if symbol.atr is not None:
                    if not self._passes_volatility_filter(symbol, filters_config['volatility']):
                        continue

                filtered_symbols.append(symbol)

            except Exception as e:
                logger.warning(f"Error filtering symbol {symbol.symbol}: {e}")
                continue

        logger.info(f"Filtering complete: {len(filtered_symbols)} symbols passed all filters")
        return filtered_symbols

    def _passes_liquidity_filter(self, symbol: DiscoveredSymbol, config: Dict) -> bool:
        """Check if symbol passes liquidity filter."""
        min_volume = config.get('min_avg_volume', 1000000)
        if symbol.avg_volume and symbol.avg_volume >= min_volume:
            return True
        return False

    def _passes_volatility_filter(self, symbol: DiscoveredSymbol, config: Dict) -> bool:
        """Check if symbol passes volatility filter."""
        if symbol.atr is None:
            return False

        min_atr = config.get('min_atr', 0.5)
        max_atr = config.get('max_atr', 20.0)

        return min_atr <= symbol.atr <= max_atr

    def _passes_price_filter(self, symbol: DiscoveredSymbol, config: Dict) -> bool:
        """Check if symbol passes price range filter."""
        if symbol.price is None:
            return False

        min_price = config.get('min_price', 5.0)
        max_price = config.get('max_price', 500.0)

        return min_price <= symbol.price <= max_price

    def _passes_exchange_filter(self, symbol: DiscoveredSymbol, config: Dict) -> bool:
        """Check if symbol passes exchange filter."""
        allowed_exchanges = set(config.get('allowed', []))
        excluded_exchanges = set(config.get('excluded', []))

        if allowed_exchanges and symbol.exchange not in allowed_exchanges:
            return False

        if symbol.exchange in excluded_exchanges:
            return False

        return True

    def discover_symbols(self, scanner_name: str, save_to_db: bool = True) -> List[DiscoveredSymbol]:
        """
        Complete symbol discovery workflow.

        Args:
            scanner_name: Name of scanner to run
            save_to_db: Whether to save results to database

        Returns:
            List of filtered, validated symbols
        """
        logger.info(f"Starting symbol discovery with scanner: {scanner_name}")

        scan_id = None
        start_time = time.time()

        try:
            # Start scan tracking in database
            if save_to_db and self.db:
                scanner_config = self.config['scanners'].get(scanner_name, {})
                scan_id = self.db.start_scan(
                    scanner_name,
                    scanner_config.get('type', 'unknown'),
                    self.config.get('filters', {})
                )

            # Run scanner
            raw_symbols = self.run_scanner(scanner_name)
            if not raw_symbols:
                logger.warning("No symbols discovered from scanner")
                if save_to_db and self.db and scan_id:
                    self.db.fail_scan(scan_id, "No symbols discovered")
                return []

            # Apply filters
            filtered_symbols = self.apply_filters(raw_symbols)

            # Save to database
            if save_to_db and self.db and filtered_symbols:
                self.db.save_discovered_symbols(filtered_symbols, scanner_name, scan_id)

            # Complete scan tracking
            if save_to_db and self.db and scan_id:
                execution_time = time.time() - start_time
                self.db.complete_scan(
                    scan_id,
                    len(raw_symbols),
                    len(filtered_symbols),
                    execution_time
                )

            logger.info(f"Symbol discovery complete: {len(filtered_symbols)} symbols ready for use")
            return filtered_symbols

        except Exception as e:
            logger.error(f"Error during symbol discovery: {e}")
            if save_to_db and self.db and scan_id:
                self.db.fail_scan(scan_id, str(e))
            raise


def create_cli_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Symbol Discovery Engine - Autonomous symbol discovery using IB API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run high volume scanner with default filters
  python scripts/symbol_discovery.py --scanner high_volume

  # Run volatility scanner with custom ATR threshold
  python scripts/symbol_discovery.py --scanner volatility_leaders --atr-threshold 1.5

  # Run gainers scanner with custom volume filter
  python scripts/symbol_discovery.py --scanner top_gainers --min-volume 2000000

  # Output to JSON instead of CSV
  python scripts/symbol_discovery.py --scanner most_active_stocks --output json
        """
    )

    parser.add_argument(
        '--scanner',
        required=True,
        choices=['top_gainers', 'top_losers', 'high_volume', 'most_active_stocks', 'most_active_etfs', 'volatility_leaders'],
        help='Scanner type to run'
    )

    parser.add_argument(
        '--output',
        choices=['csv', 'json', 'both'],
        default='csv',
        help='Output format (default: csv)'
    )

    parser.add_argument(
        '--output-dir',
        default='data/discovered_symbols',
        help='Output directory (default: data/discovered_symbols)'
    )

    # Filter override arguments
    parser.add_argument(
        '--min-volume',
        type=int,
        help='Override minimum average volume filter'
    )

    parser.add_argument(
        '--atr-threshold',
        type=float,
        help='Override minimum ATR threshold'
    )

    parser.add_argument(
        '--min-price',
        type=float,
        help='Override minimum price filter'
    )

    parser.add_argument(
        '--max-price',
        type=float,
        help='Override maximum price filter'
    )

    parser.add_argument(
        '--exchanges',
        help='Override allowed exchanges (comma-separated)'
    )

    parser.add_argument(
        '--config',
        default='config/symbol_discovery_config.yaml',
        help='Path to configuration file'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without executing'
    )

    parser.add_argument(
        '--no-db',
        action='store_true',
        help='Skip database operations (file output only)'
    )

    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show discovery statistics instead of running scan'
    )

    return parser


def main():
    """Main entry point for command line execution."""
    parser = create_cli_parser()
    args = parser.parse_args()

    # Initialize engine
    try:
        engine = SymbolDiscoveryEngine(args.config)
    except Exception as e:
        logger.error(f"Failed to initialize engine: {e}")
        sys.exit(1)

    # Apply filter overrides from CLI args
    if args.min_volume:
        engine.config['filters']['liquidity']['min_avg_volume'] = args.min_volume
    if args.atr_threshold:
        engine.config['filters']['volatility']['min_atr'] = args.atr_threshold
    if args.min_price:
        engine.config['filters']['price_range']['min_price'] = args.min_price
    if args.max_price:
        engine.config['filters']['price_range']['max_price'] = args.max_price
    if args.exchanges:
        engine.config['filters']['exchanges']['allowed'] = args.exchanges.split(',')

        # Show statistics if requested
    if args.stats:
        if not engine.connect_db():
            logger.error("Failed to connect to database for statistics")
            sys.exit(1)
        try:
            if engine.db:
                stats = engine.db.get_discovery_stats()
                print("\n=== Symbol Discovery Statistics ===")
                print(f"Unique symbols discovered: {stats.get('unique_symbols', 0)}")
                print(f"Total discoveries: {stats.get('total_discoveries', 0)}")
                print(f"Scanner types used: {stats.get('scanner_types_used', 0)}")
                print(f"Average filter rate: {stats.get('avg_filter_rate', 0):.2%}")
                print(f"Total scanned: {stats.get('total_scanned', 0)}")
                print(f"Total filtered: {stats.get('total_filtered', 0)}")

                scanner_breakdown = stats.get('scanner_breakdown', {})
                if scanner_breakdown:
                    print("\nScanner Breakdown:")
                    for scanner, count in scanner_breakdown.items():
                        print(f"  {scanner}: {count}")

                # Recent discoveries
                recent = engine.db.get_recent_discovered_symbols(limit=10)
                if recent:
                    print(f"\nRecent Discoveries (last {len(recent)}):")
                    for symbol in recent:
                        print(f"  {symbol['symbol']} ({symbol['exchange']}) - {symbol['discovery_timestamp']}")

        finally:
            engine.disconnect_db()
        return

    if args.dry_run:
        logger.info("DRY RUN MODE - Configuration that would be used:")
        logger.info(f"Scanner: {args.scanner}")
        logger.info(f"Filters: {engine.config['filters']}")
        logger.info(f"Database: {'Disabled' if args.no_db else 'Enabled'}")
        return

    # Connect to services
    connections_ok = True

    if not engine.connect_ib():
        logger.error("Failed to connect to IB Gateway")
        connections_ok = False

    if not args.no_db and not engine.connect_db():
        logger.error("Failed to connect to database")
        connections_ok = False

    if not connections_ok:
        sys.exit(1)

    try:
        # Run discovery
        save_to_db = not args.no_db
        symbols = engine.discover_symbols(args.scanner, save_to_db=save_to_db)

        if not symbols:
            logger.warning("No symbols discovered")
            return

        # Output results
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if args.output in ['csv', 'both']:
            csv_file = output_dir / f"{args.scanner}_{timestamp}.csv"
            save_to_csv(symbols, csv_file)
            logger.info(f"Results saved to {csv_file}")

        if args.output in ['json', 'both']:
            json_file = output_dir / f"{args.scanner}_{timestamp}.json"
            save_to_json(symbols, json_file)
            logger.info(f"Results saved to {json_file}")

        # Summary
        logger.info(f"Discovery Summary: {len(symbols)} symbols found and filtered")

    except Exception as e:
        logger.error(f"Error during symbol discovery: {e}")
        sys.exit(1)

    finally:
        engine.disconnect_ib()
        if not args.no_db:
            engine.disconnect_db()


def save_to_csv(symbols: List[DiscoveredSymbol], filepath: Path):
    """Save symbols to CSV file."""
    data = [symbol.to_dict() for symbol in symbols]
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)


def save_to_json(symbols: List[DiscoveredSymbol], filepath: Path):
    """Save symbols to JSON file."""
    data = [symbol.to_dict() for symbol in symbols]
    import json
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


if __name__ == '__main__':
    main()