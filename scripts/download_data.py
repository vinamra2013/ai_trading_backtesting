#!/usr/bin/env python3
"""
Data Download Script - Direct IB data download using ib_insync (Backtrader Migration)

Epic 11: US-11.4 - Data Download Pipeline
Replaces LEAN CLI with direct Interactive Brokers API calls

Features:
- Download historical market data from IB
- Support for multiple symbols and date ranges
- Organized folder structure: data/csv/resolution/symbol/
- CSV output format (compatible with Backtrader)
- Data quality validation
- Resume capability for interrupted downloads

Folder Structure:
data/
└── csv/
    ├── Daily/
    │   ├── SPY/
    │   │   ├── SPY_Daily_20200101_20241231.csv
    │   │   └── SPY_Daily_20240101_20241231.csv
    │   └── QQQ/
    │       └── QQQ_Daily_20200101_20241231.csv
    ├── Hourly/
    │   └── SPY/
    │       └── SPY_Hourly_20200101_20241231.csv
    └── Minute/
        └── SPY/
            └── SPY_Minute_20200101_20241231.csv
"""

import argparse
import logging
import sys
import os
import pandas as pd
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from ib_insync import IB, Stock, util

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.ib_connection import IBConnectionManager

# Setup logging
log_dir = os.path.join(os.getcwd(), 'logs')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'data_download.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DataDownloader:
    """Direct IB data downloader using ib_insync"""

    # Resolution mapping: user-friendly -> IB bar size
    RESOLUTION_MAP = {
        'Daily': '1 day',
        'Hour': '1 hour',
        'Minute': '1 min',
        '5Minute': '5 mins',
        '15Minute': '15 mins',
        '30Minute': '30 mins',
        'Second': '1 secs',
    }

    # Duration mapping: user-friendly -> IB duration
    DURATION_MAP = {
        'Daily': 'Y',      # Years for daily data
        'Hour': 'M',       # Months for hourly data
        'Minute': 'W',     # Weeks for minute data
        '5Minute': 'W',
        '15Minute': 'W',
        '30Minute': 'W',
        'Second': 'D',     # Days for second data
    }

    def __init__(self, env_file: str = ".env", client_id: int = 1):
        """
        Initialize downloader with IB connection

        Args:
            env_file: Path to .env file containing IB credentials
            client_id: IB client ID to use
        """
        load_dotenv(env_file)

        self.client_id = client_id
        self.ib_manager = None
        # Use relative path or environment variable for data directory
        data_folder = os.getenv('BACKTRADER_DATA_FOLDER', os.path.join(os.getcwd(), 'data'))
        self.base_data_dir = Path(data_folder)
        # Organized structure: data/csv/resolution/symbol/
        self.output_dir = None  # Will be set per symbol/resolution

        logger.info(f"DataDownloader initialized. Base data dir: {self.base_data_dir}")

    def _check_data_farm_connection(self) -> bool:
        """
        Check if data farm connections are working by attempting a simple market data request

        Returns:
            bool: True if data farm connections appear healthy
        """
        if not self.ib_manager or not self.ib_manager.ib:
            return False

        try:
            # Try to request market data for a simple contract - this will fail if data farms are broken
            contract = Stock('SPY', 'SMART', 'USD')
            self.ib_manager.ib.qualifyContracts(contract)

            # Request a small amount of historical data to test data farm connectivity
            bars = self.ib_manager.ib.reqHistoricalData(
                contract,
                endDateTime='',  # Empty string means current time
                durationStr='1 D',  # 1 day
                barSizeSetting='1 day',
                whatToShow='TRADES',
                useRTH=True,
                timeout=10  # Reasonable timeout
            )

            # If we get data back, data farms are working
            if bars and len(bars) > 0:
                logger.info("✅ Data farm connections verified")
                return True
            else:
                logger.error("❌ No data returned from data farm test - data farms appear broken")
                return False

        except Exception as e:
            logger.error(f"❌ Data farm connection check failed: {e}")
            return False

    def connect(self, host: Optional[str] = None, client_id: int = 1) -> bool:
        """
        Connect to IB Gateway

        Args:
            host: IB Gateway host (default: from env or 'ib-gateway')
            client_id: IB client ID to use

        Returns:
            bool: True if connected successfully
        """
        try:
            # Use localhost if running outside Docker, ib-gateway if inside
            if host is None:
                host = os.getenv('IB_HOST', 'ib-gateway')

            self.ib_manager = IBConnectionManager(host=host, client_id=client_id, readonly=True)
            success = self.ib_manager.connect()

            if success:
                logger.info("✅ Connected to IB Gateway")

            return success

        except Exception as e:
            logger.error(f"Failed to connect to IB: {e}")
            return False

    def disconnect(self):
        """Disconnect from IB Gateway"""
        if self.ib_manager:
            self.ib_manager.disconnect()

    def check_and_restart_ib_gateway(self) -> bool:
        """
        Check IB connection and restart gateway if data farm issues detected

        Returns:
            bool: True if restart was performed
        """
        if not self.ib_manager or not self.ib_manager.ib:
            return False

        # Check if connection is actually broken
        try:
            # Test connection by checking if we can get account info
            account = self.ib_manager.ib.accountSummary()
            if not account:
                logger.warning("⚠️  IB connection appears broken - no account summary available")
                return self._restart_gateway()
        except Exception as e:
            logger.warning(f"⚠️  IB connection test failed: {e}")
            return self._restart_gateway()

        # Check for data farm connection issues by looking at connection state
        try:
            # Check if IB is connected and has active data connections
            if not self.ib_manager.ib.isConnected():
                logger.warning("⚠️  IB not connected - restarting gateway...")
                return self._restart_gateway()
        except Exception as e:
            logger.warning(f"⚠️  Error checking IB connection state: {e}")
            return self._restart_gateway()

        return False

    def _restart_gateway(self) -> bool:
        """
        Internal method to restart the IB Gateway via Docker Compose

        Returns:
            bool: True if restart was successful
        """
        try:
            logger.warning("🔄 Restarting IB Gateway container...")
            result = subprocess.run(
                ['docker', 'compose', 'restart', 'ib-gateway'],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Run from project root
            )

            if result.returncode == 0:
                logger.info("✅ IB Gateway restarted successfully, waiting 30 seconds for initialization...")
                # Wait for gateway to initialize
                import time
                time.sleep(30)
                return True
            else:
                logger.error(f"❌ Failed to restart IB Gateway: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("❌ IB Gateway restart timed out")
            return False
        except Exception as e:
            logger.error(f"❌ Error restarting IB Gateway: {e}")
            return False

    def download(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        data_type: str = "Trade",
        resolution: str = "Daily",
        exchange: str = "SMART",
        currency: str = "USD"
    ) -> bool:
        """
        Download historical data from Interactive Brokers

        Args:
            symbols: List of ticker symbols (e.g., ['SPY', 'AAPL'])
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            data_type: Data type (Trade, Bid, Ask, Midpoint)
            resolution: Resolution (Daily, Hour, Minute, etc.)
            exchange: Exchange code (default: SMART routing)
            currency: Currency code (default: USD)

        Returns:
            True if all downloads successful, False otherwise
        """
        if not self.ib_manager or not self.ib_manager.is_connected:
            logger.error("Not connected to IB. Call connect() first.")
            return False

        # Check data farm connections immediately after connecting
        logger.info("Checking data farm connections...")
        if not self._check_data_farm_connection():
            logger.error("❌ Data farm connections appear broken - cannot proceed with download")
            logger.error("This usually means IB Gateway data farms are not available")
            return False

        # Validate resolution
        if resolution not in self.RESOLUTION_MAP:
            logger.error(
                f"Invalid resolution: {resolution}. "
                f"Valid options: {list(self.RESOLUTION_MAP.keys())}"
            )
            return False

        # Parse dates
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError as e:
            logger.error(f"Invalid date format. Use YYYY-MM-DD: {e}")
            return False

        # Calculate duration
        duration = self._calculate_duration(start_dt, end_dt, resolution)

        bar_size = self.RESOLUTION_MAP[resolution]
        what_to_show = data_type.upper() if data_type.upper() in ['TRADES', 'MIDPOINT', 'BID', 'ASK'] else 'TRADES'

        logger.info(f"Downloading {len(symbols)} symbols from {start_date} to {end_date}")
        logger.info(f"Resolution: {resolution} ({bar_size}), Data Type: {what_to_show}")

        success_count = 0
        for symbol in symbols:
            try:
                logger.info(f"\nProcessing {symbol}...")

                # Create contract
                contract = Stock(symbol, exchange, currency)
                qualified = self.ib_manager.ib.qualifyContracts(contract)

                if not qualified:
                    logger.error(f"❌ Could not qualify contract for {symbol}")
                    continue

                contract = qualified[0]
                logger.info(f"✅ Contract qualified: {contract.localSymbol}")

                # Check for data farm warnings before making request
                # Wait a moment for any warnings to appear
                import time
                time.sleep(1)

                # Check if data farm connections are working
                if not self._check_data_farm_connection():
                    logger.error("❌ Data farm connection broken during download - aborting")
                    return False

                # Download historical bars
                bars = self.ib_manager.ib.reqHistoricalData(
                    contract,
                    endDateTime=end_dt.date(),  # Convert datetime to date for IB API
                    durationStr=duration,
                    barSizeSetting=bar_size,
                    whatToShow=what_to_show,
                    useRTH=True,  # Regular trading hours only
                    formatDate=1   # String format
                )

                if not bars:
                    logger.warning(f"⚠️  No data returned for {symbol}")
                    continue

                # Convert to DataFrame
                df = util.df(bars)

                if df is None or len(df) == 0:
                    logger.warning(f"⚠️  No data available for {symbol}")
                    continue

                # Filter by date range (convert datetime to date for comparison)
                mask = (df['date'] >= start_dt.date()) & (df['date'] <= end_dt.date())
                df = df[mask]

                if len(df) == 0:
                    logger.warning(f"⚠️  No data in date range for {symbol}")
                    continue

                # Prepare for CSV export
                df = df.rename(columns={'date': 'datetime'})  # type: ignore
                df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
                df['datetime'] = pd.to_datetime(df['datetime']).dt.strftime('%Y-%m-%d %H:%M:%S')  # type: ignore

                # Create organized folder structure: data/csv/resolution/symbol/
                symbol_dir = self.base_data_dir / 'csv' / resolution / symbol
                symbol_dir.mkdir(parents=True, exist_ok=True)

                # Save to CSV with date range in filename for clarity
                date_suffix = f"_{start_date.replace('-', '')}_{end_date.replace('-', '')}"
                output_file = symbol_dir / f"{symbol}_{resolution}{date_suffix}.csv"
                df.to_csv(output_file, index=False)

                logger.info(
                    f"✅ Downloaded {len(df)} bars for {symbol} → {output_file}"
                )
                success_count += 1

                logger.info(
                    f"✅ Downloaded {len(df)} bars for {symbol} → {output_file}"
                )
                success_count += 1

                # Brief pause to avoid rate limiting
                util.sleep(0.5)

            except Exception as e:
                error_msg = str(e).lower()
                logger.error(f"❌ Error downloading {symbol}: {type(e).__name__}: {e}")

                # Detect data farm connection issues or timeouts
                connection_issues = any(indicator in error_msg for indicator in [
                    'farm', 'timeout', 'connection', 'broken', 'disconnected',
                    'no security definition', 'market data farm', 'hmds'
                ])

                if connection_issues:
                    logger.warning(f"⚠️  Connection issue detected: {e}")
                    # Attempt restart if not already tried for this session
                    if not hasattr(self, '_restart_attempted'):
                        self._restart_attempted = True
                        if self.check_and_restart_ib_gateway():
                            # Reconnect after restart
                            if self.connect(host=os.getenv('IB_HOST', 'localhost')):
                                logger.info("♻️  Reconnected after IB Gateway restart - retrying download...")
                                # Retry this symbol
                                continue
                            else:
                                logger.error("❌ Failed to reconnect after restart")
                        else:
                            logger.error("❌ Failed to restart IB Gateway")
                    else:
                        logger.warning("⚠️  Restart already attempted this session")

                # Continue to next symbol regardless
                continue

        logger.info(
            f"\n📊 Download complete: {success_count}/{len(symbols)} symbols successful"
        )
        return success_count == len(symbols)

    def _calculate_duration(
        self,
        start_dt: datetime,
        end_dt: datetime,
        resolution: str
    ) -> str:
        """
        Calculate IB duration string based on date range and resolution

        Args:
            start_dt: Start datetime
            end_dt: End datetime
            resolution: Data resolution

        Returns:
            str: IB-compatible duration string (e.g., "5 Y", "3 M", "2 W")
        """
        delta = end_dt - start_dt
        days = delta.days

        # Map resolution to appropriate duration unit
        if resolution == 'Daily':
            # Daily data: use years or days
            if days > 365:
                years = int(days / 365) + 1
                return f"{years} Y"
            else:
                return f"{days} D"

        elif resolution in ['Hour', '30Minute', '15Minute']:
            # Hourly data: use months or weeks
            if days > 90:
                months = int(days / 30) + 1
                return f"{months} M"
            else:
                weeks = int(days / 7) + 1
                return f"{weeks} W"

        elif resolution in ['Minute', '5Minute']:
            # Minute data: use weeks or days
            if days > 14:
                weeks = int(days / 7) + 1
                return f"{weeks} W"
            else:
                return f"{days} D"

        else:  # Second data
            # Second data: use days
            return f"{min(days, 7)} D"  # Max 7 days for second data

    def validate_data(self, symbol: str, resolution: str) -> bool:
        """
        Validate downloaded data quality

        Args:
            symbol: Stock symbol
            resolution: Data resolution

        Returns:
            bool: True if data passes quality checks
        """
        # Find the most recent file for this symbol/resolution
        symbol_dir = self.base_data_dir / 'csv' / resolution / symbol
        if not symbol_dir.exists():
            logger.error(f"Directory not found: {symbol_dir}")
            return False

        # Find the most recent CSV file (by modification time)
        csv_files = list(symbol_dir.glob(f"{symbol}_{resolution}_*.csv"))
        if not csv_files:
            logger.error(f"No CSV files found for {symbol} {resolution}")
            return False

        # Use the most recently modified file
        output_file = max(csv_files, key=lambda f: f.stat().st_mtime)

        if not output_file.exists():
            logger.error(f"File not found: {output_file}")
            return False

        try:
            df = pd.read_csv(output_file, parse_dates=['datetime'])

            # Check for required columns
            required_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                logger.error(f"Missing required columns in {symbol}")
                return False

            # Check for NaN values
            if df[required_cols].isnull().any(axis=None):  # type: ignore
                logger.warning(f"NaN values found in {symbol}")
                return False

            # Check OHLC consistency (high >= low, etc.)
            if not (df['high'] >= df['low']).all():
                logger.error(f"OHLC inconsistency in {symbol}: high < low")
                return False

            if not ((df['high'] >= df['open']) & (df['high'] >= df['close'])).all():
                logger.error(f"OHLC inconsistency in {symbol}: high < open/close")
                return False

            if not ((df['low'] <= df['open']) & (df['low'] <= df['close'])).all():
                logger.error(f"OHLC inconsistency in {symbol}: low > open/close")
                return False

            # Check for duplicate timestamps
            if df['datetime'].duplicated().any():
                logger.warning(f"Duplicate timestamps found in {symbol}")
                return False

            logger.info(f"✅ Data validation passed for {symbol} ({len(df)} rows)")
            return True

        except Exception as e:
            logger.error(f"Validation error for {symbol}: {e}")
            return False

    def list_available_data(self) -> None:
        """
        List all available data files in the organized structure
        """
        csv_dir = self.base_data_dir / 'csv'
        if not csv_dir.exists():
            logger.info("No data directory found")
            return

        logger.info("Available data files:")
        total_files = 0
        total_size = 0

        for resolution_dir in sorted(csv_dir.iterdir()):
            if resolution_dir.is_dir():
                logger.info(f"\n📁 Resolution: {resolution_dir.name}")
                res_files = 0
                res_size = 0

                for symbol_dir in sorted(resolution_dir.iterdir()):
                    if symbol_dir.is_dir():
                        files = list(symbol_dir.glob("*.csv"))
                        if files:
                            file_sizes = [f.stat().st_size for f in files]
                            dir_size = sum(file_sizes)
                            res_files += len(files)
                            res_size += dir_size
                            logger.info(f"  📄 {symbol_dir.name}: {len(files)} file(s), {dir_size/1024/1024:.1f} MB")

                if res_files > 0:
                    logger.info(f"  📊 {resolution_dir.name} total: {res_files} files, {res_size/1024/1024:.1f} MB")
                    total_files += res_files
                    total_size += res_size

        if total_files > 0:
            logger.info(f"\n📈 Grand total: {total_files} files, {total_size/1024/1024:.1f} MB")


def main():
    """Command-line interface for data downloader"""
    parser = argparse.ArgumentParser(
        description='Download historical market data from Interactive Brokers'
    )
    parser.add_argument(
        '--symbols',
        nargs='+',
        required=True,
        help='Stock symbols to download (e.g., SPY AAPL MSFT)'
    )
    parser.add_argument(
        '--start',
        required=True,
        help='Start date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end',
        required=True,
        help='End date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--resolution',
        default='Daily',
        choices=['Daily', 'Hour', 'Minute', '5Minute', '15Minute', '30Minute', 'Second'],
        help='Data resolution (default: Daily)'
    )
    parser.add_argument(
        '--data-type',
        default='Trade',
        choices=['Trade', 'Trades', 'Midpoint', 'Bid', 'Ask'],
        help='Data type (default: Trade)'
    )
    parser.add_argument(
        '--exchange',
        default='SMART',
        help='Exchange code (default: SMART)'
    )
    parser.add_argument(
        '--currency',
        default='USD',
        help='Currency code (default: USD)'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Run data quality validation after download'
    )
    parser.add_argument(
        '--client-id',
        type=int,
        default=10,
        help='IB client ID to use (default: 10)'
    )
    parser.add_argument(
        '--list-data',
        action='store_true',
        help='List all available data files and exit'
    )

    args = parser.parse_args()

    # Create downloader
    downloader = DataDownloader(client_id=args.client_id)

    # Handle list-data command
    if args.list_data:
        downloader.list_available_data()
        sys.exit(0)

    try:
        # Connect to IB
        logger.info("Connecting to Interactive Brokers...")
        if not downloader.connect():
            logger.error("Failed to connect to IB Gateway")
            sys.exit(1)

        # Download data
        success = downloader.download(
            symbols=args.symbols,
            start_date=args.start,
            end_date=args.end,
            data_type=args.data_type,
            resolution=args.resolution,
            exchange=args.exchange,
            currency=args.currency
        )

        # Validate if requested
        if args.validate and success:
            logger.info("\n🔍 Validating downloaded data...")
            all_valid = True
            for symbol in args.symbols:
                if not downloader.validate_data(symbol, args.resolution):
                    all_valid = False

            if all_valid:
                logger.info("✅ All data files passed validation")
            else:
                logger.warning("⚠️  Some data files failed validation")

        # Disconnect
        downloader.disconnect()

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Download interrupted by user")
        downloader.disconnect()
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {type(e).__name__}: {e}")
        downloader.disconnect()
        sys.exit(1)


if __name__ == '__main__':
    main()
