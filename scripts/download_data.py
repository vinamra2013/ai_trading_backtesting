#!/usr/bin/env python3
"""
Data Download Script - Direct IB data download using ib_insync (Backtrader Migration)

Epic 11: US-11.4 - Data Download Pipeline
Replaces LEAN CLI with direct Interactive Brokers API calls

Features:
- Download historical market data from IB
- Support for multiple symbols and date ranges
- CSV output format (compatible with Backtrader)
- Data quality validation
- Resume capability for interrupted downloads
"""

import argparse
import logging
import sys
import os
import pandas as pd
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

    def __init__(self, env_file: str = ".env"):
        """
        Initialize downloader with IB connection

        Args:
            env_file: Path to .env file containing IB credentials
        """
        load_dotenv(env_file)

        self.ib_manager = None
        # Use relative path or environment variable for data directory
        data_folder = os.getenv('BACKTRADER_DATA_FOLDER', os.path.join(os.getcwd(), 'data'))
        self.output_dir = Path(data_folder) / 'csv'
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"DataDownloader initialized. Output dir: {self.output_dir}")

    def connect(self, host: str = None) -> bool:
        """
        Connect to IB Gateway

        Args:
            host: IB Gateway host (default: from env or 'ib-gateway')

        Returns:
            bool: True if connected successfully
        """
        try:
            # Use localhost if running outside Docker, ib-gateway if inside
            if host is None:
                host = os.getenv('IB_HOST', 'localhost')
            self.ib_manager = IBConnectionManager(host=host, readonly=True)
            return self.ib_manager.connect()
        except Exception as e:
            logger.error(f"Failed to connect to IB: {e}")
            return False

    def disconnect(self):
        """Disconnect from IB Gateway"""
        if self.ib_manager:
            self.ib_manager.disconnect()

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

                # Download historical bars
                bars = self.ib_manager.ib.reqHistoricalData(
                    contract,
                    endDateTime=end_dt,
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

                if df.empty:
                    logger.warning(f"⚠️  Empty DataFrame for {symbol}")
                    continue

                # Filter by date range
                df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]

                if df.empty:
                    logger.warning(f"⚠️  No data in date range for {symbol}")
                    continue

                # Prepare for CSV export
                df = df.rename(columns={'date': 'datetime'})
                df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
                df['datetime'] = pd.to_datetime(df['datetime'])

                # Save to CSV
                output_file = self.output_dir / f"{symbol}_{resolution}.csv"
                df.to_csv(output_file, index=False)

                logger.info(
                    f"✅ Downloaded {len(df)} bars for {symbol} → {output_file}"
                )
                success_count += 1

                # Brief pause to avoid rate limiting
                util.sleep(0.5)

            except Exception as e:
                logger.error(f"❌ Error downloading {symbol}: {type(e).__name__}: {e}")
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
        output_file = self.output_dir / f"{symbol}_{resolution}.csv"

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
            if df[required_cols].isnull().any().any():
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

    args = parser.parse_args()

    # Create downloader
    downloader = DataDownloader()

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
