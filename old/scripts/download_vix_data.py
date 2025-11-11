#!/usr/bin/env python3
"""
VIX Data Download and Storage Script
Epic 24: VARM-RSI Strategy - VIX Market Filter Data

Downloads VIX data from yfinance and stores it in the platform's data structure.
Creates CSV files compatible with Backtrader data feeds.
"""

import yfinance as yf
import pandas as pd
import os
from pathlib import Path
from datetime import datetime, timedelta
import argparse


def download_vix_data(
    start_date="2020-01-01", end_date="2025-01-01", output_dir="data/csv/Daily/VIX"
):
    """
    Download VIX data and store in platform format

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        output_dir: Output directory path
    """
    print(f"Downloading VIX data from {start_date} to {end_date}...")

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Download VIX data
    vix_data = yf.download(
        "^VIX", start=start_date, end=end_date, interval="1d", progress=False
    )

    if vix_data is None or vix_data.empty:
        print("❌ No VIX data downloaded")
        return None

    print(f"✅ Downloaded {len(vix_data)} daily VIX bars")

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    start_formatted = start_date.replace("-", "")
    end_formatted = end_date.replace("-", "")
    filename = f"VIX_Daily_{start_formatted}_{end_formatted}.csv"
    filepath = os.path.join(output_dir, filename)

    # Handle MultiIndex columns from yfinance
    if isinstance(vix_data.columns, pd.MultiIndex):
        vix_data.columns = vix_data.columns.droplevel(1)

    # Prepare data for CSV storage (standardized format)
    # Standard format: datetime,open,high,low,close,volume
    csv_data = pd.DataFrame(
        {
            "datetime": vix_data.index.strftime("%Y-%m-%d %H:%M:%S"),
            "open": vix_data["Open"].round(2),
            "high": vix_data["High"].round(2),
            "low": vix_data["Low"].round(2),
            "close": vix_data["Close"].round(2),
            "volume": vix_data["Volume"].fillna(0),  # VIX has no volume, fill with 0
        }
    )

    # Save to CSV
    csv_data.to_csv(filepath, index=False)
    print(f"✅ Saved VIX data to: {filepath}")

    # Show data summary
    print(
        f"   Date range: {vix_data.index.min().date()} to {vix_data.index.max().date()}"
    )
    print(
        f"   VIX range: {vix_data['Close'].min():.1f} - {vix_data['Close'].max():.1f}"
    )

    return filepath


def verify_vix_data(filepath):
    """
    Verify the downloaded VIX data

    Args:
        filepath: Path to the CSV file
    """
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return

    # Load and verify data
    data = pd.read_csv(filepath)
    print(f"✅ Verification: {len(data)} rows loaded")

    # Check for VIX < 30 filter stats
    vix_close = data["close"]
    under_30 = (vix_close < 30).sum()
    pct_under_30 = (under_30 / len(vix_close)) * 100

    print(
        f"   VIX < 30 (filter active): {under_30}/{len(vix_close)} days ({pct_under_30:.1f}%)"
    )
    print(f"   Current VIX: {vix_close.iloc[-1]:.1f}")


def main():
    parser = argparse.ArgumentParser(
        description="Download VIX data for VARM-RSI strategy"
    )
    parser.add_argument("--start", default="2020-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2025-01-01", help="End date (YYYY-MM-DD)")
    parser.add_argument(
        "--output-dir", default="data/csv/VIX/Daily", help="Output directory"
    )

    args = parser.parse_args()

    print("VIX Data Download for VARM-RSI Strategy")
    print("=" * 40)

    # Download VIX data
    filepath = download_vix_data(args.start, args.end, args.output_dir)

    if filepath:
        print()
        # Verify the data
        verify_vix_data(filepath)

        print()
        print("🎯 VIX data ready for VARM-RSI strategy!")
        print(f"   File: {filepath}")
        print("   Use CSVData feed in Backtrader")


if __name__ == "__main__":
    main()
