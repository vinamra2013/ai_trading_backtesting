#!/usr/bin/env python3
"""
Incremental Data Update Script - Download only new data since last update.

US-3.4: Incremental Data Updates
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
import subprocess

from download_data import DataDownloader

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_last_date_for_symbol(symbol: str, data_dir: str = "data") -> str:
    """
    Detect the last date available for a symbol.

    Returns:
        Last date in YYYY-MM-DD format, or None if no data found
    """
    # TODO: Implement LEAN data directory parsing
    # For now, return yesterday as a safe default
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    logger.info(f"{symbol}: Using {yesterday} as start date")
    return yesterday


def main():
    parser = argparse.ArgumentParser(description="Incremental data update")
    parser.add_argument("--symbols", nargs="+", required=True, help="Symbols to update")
    parser.add_argument("--auto-detect-start", action="store_true", help="Auto-detect last date")
    args = parser.parse_args()

    downloader = DataDownloader()

    for symbol in args.symbols:
        if args.auto_detect_start:
            start = get_last_date_for_symbol(symbol)
        else:
            start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        end = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"Updating {symbol} from {start} to {end}")
        downloader.download([symbol], start, end)

if __name__ == "__main__":
    main()
