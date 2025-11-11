#!/usr/bin/env python3
"""
Data File Scanner Service

Scans the data/csv directory structure and catalogs all data files with metadata.
Used by the Data Files Management UI to display available data files.

Epic 26: Script-to-API Conversion for Quant Director Operations
Story 5 & 7: Data Files Management UI Page

Features:
- Recursively scan data/csv directory for CSV files
- Parse filename patterns: {symbol}_{timeframe}_{start}_{end}.csv
- Extract metadata: symbol, timeframe, date range, file size, quality status
- Run data quality checks
- Return structured data for UI consumption

Author: AI Assistant
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

# Import metadata cache manager
from utils.metadata_cache import get_cache_manager

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataFileScanner:
    """
    Scans and catalogs data files in the data/csv directory structure.
    """

    def __init__(self, data_dir: str = "data/csv"):
        """
        Initialize the scanner.

        Args:
            data_dir: Root directory containing CSV data files
        """
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            logger.warning(f"Data directory does not exist: {data_dir}")
            self.data_dir.mkdir(parents=True, exist_ok=True)

    def scan_data_files(self) -> List[Dict]:
        """
        Scan all data files and return metadata.
        Uses caching to improve performance on subsequent calls.

        Returns:
            List of dictionaries containing file metadata
        """
        logger.info(f"Scanning data files in: {self.data_dir}")

        # Try to load from cache first
        cache_manager = get_cache_manager()
        cached_data = cache_manager.load_directory_cache(str(self.data_dir))

        if cached_data:
            logger.info("Using cached directory metadata")
            return cached_data.get("files", [])

        # Cache miss - scan files and create cache
        logger.info("Cache miss - scanning data files")
        data_files = []

        # Find all CSV files in the directory structure
        for csv_file in self.data_dir.rglob("*.csv"):
            try:
                metadata = self.extract_file_metadata(csv_file)
                if metadata:
                    data_files.append(metadata)
            except Exception as e:
                logger.warning(f"Failed to process {csv_file}: {e}")
                continue

        logger.info(f"Found {len(data_files)} data files")

        # Cache the results
        cache_data = {
            "files": data_files,
            "total_files": len(data_files),
            "total_size_mb": sum(f.get("file_size_mb", 0) for f in data_files),
            "last_scan": datetime.now().isoformat(),
        }
        cache_manager.save_directory_cache(str(self.data_dir), cache_data)

        return data_files

    def extract_file_metadata(self, file_path: Path) -> Optional[Dict]:
        """
        Extract metadata from a single data file.
        Uses caching to improve performance on subsequent calls.

        Args:
            file_path: Path to the CSV file

        Returns:
            Dictionary with file metadata or None if invalid
        """
        # Try to load from cache first
        cache_manager = get_cache_manager()
        cached_metadata = cache_manager.load_file_cache(str(file_path))

        if cached_metadata:
            logger.debug(f"Using cached metadata for {file_path}")
            return cached_metadata

        # Cache miss - extract metadata and cache it
        try:
            # Parse filename to extract components
            symbol, timeframe, start_date, end_date = self.parse_filename(
                file_path.name
            )

            if not all([symbol, timeframe, start_date, end_date]):
                logger.warning(f"Could not parse filename: {file_path.name}")
                return None

            # Get file statistics
            file_stats = file_path.stat()
            file_size_bytes = file_stats.st_size
            last_modified = datetime.fromtimestamp(file_stats.st_mtime)

            # Read file to get data statistics
            data_stats = self.get_data_statistics(file_path)

            # Run quality checks
            quality_score, quality_status = self.run_quality_checks(
                file_path, data_stats
            )

            # Calculate date range coverage
            date_range_days = (
                self.calculate_date_range_days(start_date, end_date, timeframe)
                if all([start_date, end_date, timeframe])
                else None
            )

            # Calculate expected data points based on timeframe
            expected_data_points = (
                self.calculate_expected_data_points(start_date, end_date, timeframe)
                if all([start_date, end_date, timeframe])
                else None
            )

            metadata = {
                "file_path": str(file_path),
                "relative_path": str(file_path.relative_to(self.data_dir)),
                "symbol": symbol,
                "timeframe": timeframe,
                "start_date": start_date,
                "end_date": end_date,
                "file_size_bytes": file_size_bytes,
                "file_size_mb": round(file_size_bytes / (1024 * 1024), 2),
                "last_modified": last_modified.isoformat(),
                "row_count": data_stats.get("row_count", 0),
                "date_range_days": date_range_days,
                "expected_data_points": expected_data_points,
                "quality_score": quality_score,
                "quality_status": quality_status,
                "has_required_columns": data_stats.get("has_required_columns", False),
                "data_start_date": data_stats.get("data_start_date"),
                "data_end_date": data_stats.get("data_end_date"),
                "avg_volume": data_stats.get("avg_volume"),
                "price_range": data_stats.get("price_range"),
            }

            # Cache the metadata
            cache_manager.save_file_cache(str(file_path), metadata)

            return metadata

        except Exception as e:
            logger.error(f"Failed to extract metadata from {file_path}: {e}")
            return None

    def parse_filename(
        self, filename: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """
        Parse filename to extract symbol, timeframe, start_date, end_date.

        Expected format: {SYMBOL}_{TIMEFRAME}_{START_DATE}_{END_DATE}.csv
        Example: SPY_1m_20240101_20241231.csv

        Args:
            filename: CSV filename

        Returns:
            Tuple of (symbol, timeframe, start_date, end_date)
        """
        if not filename.endswith(".csv"):
            return None, None, None, None

        # Remove .csv extension
        name = filename[:-4]

        # Split by underscores
        parts = name.split("_")

        if len(parts) != 4:
            return None, None, None, None

        symbol, timeframe, start_date, end_date = parts

        # Validate symbol (should be uppercase letters)
        if not symbol.isupper() or not symbol.isalpha():
            return None, None, None, None

        # Validate timeframe (common formats)
        valid_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]
        if timeframe not in valid_timeframes:
            return None, None, None, None

        # Validate dates (should be YYYYMMDD format)
        if not (self.is_valid_date(start_date) and self.is_valid_date(end_date)):
            return None, None, None, None

        return symbol, timeframe, start_date, end_date

    def is_valid_date(self, date_str: str) -> bool:
        """
        Check if date string is in YYYYMMDD format and valid.

        Args:
            date_str: Date string to validate

        Returns:
            True if valid date
        """
        if len(date_str) != 8:
            return False

        try:
            datetime.strptime(date_str, "%Y%m%d")
            return True
        except ValueError:
            return False

    def get_data_statistics(self, file_path: Path) -> Dict:
        """
        Read CSV file and extract basic statistics.

        Args:
            file_path: Path to CSV file

        Returns:
            Dictionary with data statistics
        """
        try:
            # Read first few rows to check structure
            df_sample = pd.read_csv(file_path, nrows=5)

            if df_sample.empty:
                return {"row_count": 0, "has_required_columns": False}

            # Check for required columns
            required_cols = ["datetime", "open", "high", "low", "close", "volume"]
            has_required = all(col in df_sample.columns for col in required_cols)

            if not has_required:
                return {"row_count": 0, "has_required_columns": False}

            # Read full file for statistics
            df = pd.read_csv(file_path, parse_dates=["datetime"])

            stats = {
                "row_count": len(df),
                "has_required_columns": True,
                "data_start_date": df["datetime"].min().isoformat()
                if not df.empty
                else None,
                "data_end_date": df["datetime"].max().isoformat()
                if not df.empty
                else None,
                "avg_volume": df["volume"].mean() if "volume" in df.columns else None,
                "price_range": {
                    "min": df["low"].min() if "low" in df.columns else None,
                    "max": df["high"].max() if "high" in df.columns else None,
                }
                if all(col in df.columns for col in ["low", "high"])
                else None,
            }

            return stats

        except Exception as e:
            logger.warning(f"Failed to read data statistics from {file_path}: {e}")
            return {"row_count": 0, "has_required_columns": False}

    def run_quality_checks(
        self, file_path: Path, data_stats: Dict
    ) -> Tuple[float, str]:
        """
        Run quality checks on the data file.

        Args:
            file_path: Path to CSV file
            data_stats: Basic data statistics

        Returns:
            Tuple of (quality_score, quality_status)
        """
        score = 100.0
        issues = []

        try:
            # Check if file has required columns
            if not data_stats.get("has_required_columns", False):
                score -= 50
                issues.append("Missing required columns")

            # Check if file has data
            if data_stats.get("row_count", 0) == 0:
                score -= 50
                issues.append("Empty file")

            # Read full data for deeper checks
            if (
                data_stats.get("has_required_columns")
                and data_stats.get("row_count", 0) > 0
            ):
                df = pd.read_csv(file_path, parse_dates=["datetime"])

                # Check for chronological order
                if not df["datetime"].is_monotonic_increasing:
                    score -= 10
                    issues.append("Not in chronological order")

                # Check for missing values in critical columns
                critical_cols = ["datetime", "open", "high", "low", "close"]
                for col in critical_cols:
                    if col in df.columns:
                        missing_pct = df[col].isnull().sum() / len(df) * 100
                        if missing_pct > 5:
                            score -= 20
                            issues.append(
                                f"High missing values in {col} ({missing_pct:.1f}%)"
                            )

                # Check for zero/null prices
                price_cols = ["open", "high", "low", "close"]
                for col in price_cols:
                    if col in df.columns:
                        zero_pct = (df[col] == 0).sum() / len(df) * 100
                        if zero_pct > 1:
                            score -= 15
                            issues.append(f"Zero values in {col} ({zero_pct:.1f}%)")

                # Check volume reasonableness
                if "volume" in df.columns:
                    negative_volume = (df["volume"] < 0).sum()
                    if negative_volume > 0:
                        score -= 10
                        issues.append("Negative volume values")

        except Exception as e:
            logger.warning(f"Quality check failed for {file_path}: {e}")
            score -= 30
            issues.append("Quality check error")

        # Determine status based on score
        if score >= 90:
            status = "Excellent"
        elif score >= 75:
            status = "Good"
        elif score >= 60:
            status = "Fair"
        else:
            status = "Poor"

        return round(score, 1), status

    def calculate_date_range_days(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
        timeframe: Optional[str],
    ) -> Optional[int]:
        """
        Calculate the number of days in the date range.

        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            timeframe: Timeframe (affects expected data points)

        Returns:
            Number of days in range
        """
        if not all([start_date, end_date]):
            return None

        try:
            start = datetime.strptime(str(start_date), "%Y%m%d")
            end = datetime.strptime(str(end_date), "%Y%m%d")
            return (end - start).days + 1
        except:
            return None

    def calculate_expected_data_points(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
        timeframe: Optional[str],
    ) -> Optional[int]:
        """
        Calculate the expected number of data points based on date range and timeframe.

        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            timeframe: Timeframe (1d, 1h, 5m, etc.)

        Returns:
            Expected number of data points
        """
        if not all([start_date, end_date, timeframe]):
            return None

        try:
            start = datetime.strptime(str(start_date), "%Y%m%d")
            end = datetime.strptime(str(end_date), "%Y%m%d")
            days = (end - start).days + 1

            # Calculate expected data points based on timeframe
            if timeframe == "1d":
                return days
            elif timeframe == "1h":
                return days * 24
            elif timeframe == "5m":
                return days * 24 * 12  # 12 five-minute bars per hour
            elif timeframe == "1m":
                return days * 24 * 60  # 60 one-minute bars per hour
            else:
                # For unknown timeframes, return days as fallback
                return days
        except:
            return None


def main():
    """Main entry point for testing."""
    import json

    scanner = DataFileScanner()
    files = scanner.scan_data_files()

    print(f"Found {len(files)} data files:")
    for file_info in files[:5]:  # Show first 5
        print(json.dumps(file_info, indent=2, default=str))

    if len(files) > 5:
        print(f"... and {len(files) - 5} more files")


if __name__ == "__main__":
    main()
