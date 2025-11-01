#!/usr/bin/env python3
"""
Data Download Script - Wrapper around LEAN CLI for Interactive Brokers data download.

US-3.1: Historical Data Download
US-3.2: Efficient Data Storage (via LEAN)
"""

import argparse
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import os
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataDownloader:
    """Wrapper for LEAN CLI data download from Interactive Brokers."""

    def __init__(self, env_file: str = ".env"):
        """
        Initialize downloader with IB credentials from .env file.

        Args:
            env_file: Path to .env file containing IB credentials
        """
        load_dotenv(env_file)
        self.ib_username = os.getenv("IB_USERNAME")
        self.ib_account = os.getenv("IB_ACCOUNT")
        self.ib_password = os.getenv("IB_PASSWORD")

        if not all([self.ib_username, self.ib_account, self.ib_password]):
            raise ValueError(
                "Missing IB credentials in .env file. "
                "Required: IB_USERNAME, IB_ACCOUNT, IB_PASSWORD"
            )

    def download(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        data_type: str = "Trade",
        resolution: str = "Daily",
        security_type: str = "Equity",
        market: str = "USA"
    ) -> bool:
        """
        Download historical data from Interactive Brokers using LEAN CLI.

        Args:
            symbols: List of ticker symbols (e.g., ['SPY', 'AAPL'])
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            data_type: Data type (Trade, Quote)
            resolution: Resolution (Daily, Hour, Minute, Second)
            security_type: Security type (Equity, Option, Future, etc.)
            market: Market identifier (USA, etc.)

        Returns:
            True if download successful, False otherwise
        """
        # Convert date format from YYYY-MM-DD to YYYYMMDD
        start = datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y%m%d")
        end = datetime.strptime(end_date, "%Y-%m-%d").strftime("%Y%m%d")

        # Join symbols with comma
        tickers = ",".join(symbols)

        # Build LEAN CLI command
        cmd = [
            "lean", "data", "download",
            "--data-provider-historical", "Interactive Brokers",
            "--data-type", data_type,
            "--resolution", resolution,
            "--security-type", security_type,
            "--ticker", tickers,
            "--market", market,
            "--start", start,
            "--end", end,
            "--ib-user-name", self.ib_username,
            "--ib-account", self.ib_account,
            "--ib-password", self.ib_password
        ]

        logger.info(f"Downloading {tickers} from {start_date} to {end_date}")
        logger.info(f"Resolution: {resolution}, Data Type: {data_type}")

        try:
            # Run LEAN CLI command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            logger.info("Download completed successfully")
            logger.debug(result.stdout)
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Download failed: {e}")
            logger.error(f"STDERR: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during download: {e}")
            return False

    def download_with_resume(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        **kwargs
    ) -> bool:
        """
        Download data with automatic resume capability.

        If download fails, this method can be called again and will resume
        from where it left off (LEAN handles this internally).

        Args:
            symbols: List of ticker symbols
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            **kwargs: Additional arguments passed to download()

        Returns:
            True if download successful, False otherwise
        """
        logger.info("Starting download with resume capability")

        # Download each symbol individually for better error handling
        success_count = 0
        failed_symbols = []

        for symbol in symbols:
            logger.info(f"Downloading {symbol}...")
            success = self.download([symbol], start_date, end_date, **kwargs)

            if success:
                success_count += 1
            else:
                failed_symbols.append(symbol)
                logger.warning(f"Failed to download {symbol}, continuing...")

        # Summary
        logger.info(f"Download summary: {success_count}/{len(symbols)} successful")
        if failed_symbols:
            logger.warning(f"Failed symbols: {', '.join(failed_symbols)}")
            return False

        return True


def main():
    """Command-line interface for data download."""
    parser = argparse.ArgumentParser(
        description="Download historical data from Interactive Brokers using LEAN"
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        required=True,
        help="Ticker symbols to download (e.g., SPY AAPL MSFT)"
    )
    parser.add_argument(
        "--start",
        required=True,
        help="Start date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--end",
        required=True,
        help="End date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--data-type",
        default="Trade",
        choices=["Trade", "Quote"],
        help="Data type to download (default: Trade)"
    )
    parser.add_argument(
        "--resolution",
        default="Daily",
        choices=["Daily", "Hour", "Minute", "Second"],
        help="Data resolution (default: Daily)"
    )
    parser.add_argument(
        "--security-type",
        default="Equity",
        help="Security type (default: Equity)"
    )
    parser.add_argument(
        "--market",
        default="USA",
        help="Market identifier (default: USA)"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Enable resume capability (downloads symbols individually)"
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to .env file with IB credentials (default: .env)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        # Initialize downloader
        downloader = DataDownloader(env_file=args.env_file)

        # Download data
        if args.resume:
            success = downloader.download_with_resume(
                symbols=args.symbols,
                start_date=args.start,
                end_date=args.end,
                data_type=args.data_type,
                resolution=args.resolution,
                security_type=args.security_type,
                market=args.market
            )
        else:
            success = downloader.download(
                symbols=args.symbols,
                start_date=args.start,
                end_date=args.end,
                data_type=args.data_type,
                resolution=args.resolution,
                security_type=args.security_type,
                market=args.market
            )

        if success:
            logger.info("✓ Download completed successfully")
            sys.exit(0)
        else:
            logger.error("✗ Download failed")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
