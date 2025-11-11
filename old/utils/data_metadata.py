#!/usr/bin/env python3
"""
Data Metadata Extraction Utilities

Utilities for extracting and processing metadata from Databento-processed data files.
Used by the Data Files Management UI and other components.

Epic 26: Script-to-API Conversion for Quant Director Operations
Story 5 & 7: Data Files Management UI Page

Features:
- Parse filename patterns from Databento processing
- Extract comprehensive file metadata
- Validate data quality and integrity
- Generate statistics for UI display

Author: AI Assistant
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np

# Import metadata cache manager
from utils.metadata_cache import get_cache_manager

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataMetadataExtractor:
    """
    Extract and process metadata from data files.
    """

    # Valid timeframes supported by the system
    VALID_TIMEFRAMES = {
        "1m": {"name": "1 Minute", "expected_points_per_day": 1440},
        "5m": {"name": "5 Minutes", "expected_points_per_day": 288},
        "15m": {"name": "15 Minutes", "expected_points_per_day": 96},
        "30m": {"name": "30 Minutes", "expected_points_per_day": 48},
        "1h": {"name": "1 Hour", "expected_points_per_day": 24},
        "4h": {"name": "4 Hours", "expected_points_per_day": 6},
        "1d": {"name": "Daily", "expected_points_per_day": 1},
        "1w": {"name": "Weekly", "expected_points_per_day": 0.14},  # ~1 per week
        "1M": {"name": "Monthly", "expected_points_per_day": 0.033},  # ~1 per month
    }

    def __init__(self):
        """Initialize the metadata extractor."""
        pass

    def extract_file_metadata(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Extract comprehensive metadata from a data file.
        Uses caching to improve performance on subsequent calls.

        Args:
            file_path: Path to the CSV file

        Returns:
            Dictionary with comprehensive metadata or None if invalid
        """
        # Try to load from cache first
        cache_manager = get_cache_manager()
        cached_metadata = cache_manager.load_file_cache(str(file_path))

        if cached_metadata:
            logger.debug(f"Using cached metadata for {file_path}")
            return cached_metadata

        # Cache miss - extract metadata and cache it
        try:
            # Basic file information
            file_stats = file_path.stat()
            file_size_bytes = file_stats.st_size
            last_modified = datetime.fromtimestamp(file_stats.st_mtime)

            # Parse filename
            filename_info = self.parse_filename(file_path.name)
            if not filename_info:
                return None

            symbol, timeframe, start_date, end_date = filename_info

            # Read and analyze data
            data_analysis = self.analyze_data_file(file_path)

            # Calculate quality metrics
            quality_metrics = self.calculate_quality_metrics(data_analysis, timeframe)

            # Generate comprehensive metadata
            metadata = {
                # File information
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_size_bytes": file_size_bytes,
                "file_size_mb": round(file_size_bytes / (1024 * 1024), 2),
                "last_modified": last_modified.isoformat(),
                "last_modified_human": last_modified.strftime("%Y-%m-%d %H:%M:%S"),
                # Parsed filename information
                "symbol": symbol,
                "timeframe": timeframe,
                "timeframe_name": self.VALID_TIMEFRAMES.get(timeframe, {}).get(
                    "name", timeframe
                ),
                "start_date": start_date,
                "end_date": end_date,
                # Date range information
                "date_range_days": self.calculate_date_range_days(start_date, end_date),
                "expected_data_points": self.calculate_expected_data_points(
                    start_date, end_date, timeframe
                ),
                # Data analysis results
                "data_analysis": data_analysis,
                # Quality metrics
                "quality_metrics": quality_metrics,
                # Summary statistics
                "summary": self.generate_summary_stats(data_analysis, quality_metrics),
            }

            # Cache the metadata
            cache_manager.save_file_cache(str(file_path), metadata)

            return metadata

        except Exception as e:
            logger.error(f"Failed to extract metadata from {file_path}: {e}")
            return None

    def parse_filename(self, filename: str) -> Optional[Tuple[str, str, str, str]]:
        """
        Parse filename to extract symbol, timeframe, start_date, end_date.

        Expected format: {SYMBOL}_{TIMEFRAME}_{START_DATE}_{END_DATE}.csv
        Example: SPY_1m_20240101_20241231.csv

        Args:
            filename: CSV filename

        Returns:
            Tuple of (symbol, timeframe, start_date, end_date) or None if invalid
        """
        if not filename.endswith(".csv"):
            return None

        # Remove .csv extension
        name = filename[:-4]

        # Split by underscores
        parts = name.split("_")

        if len(parts) != 4:
            return None

        symbol, timeframe, start_date, end_date = parts

        # Validate symbol (should be uppercase letters)
        if not symbol.isupper() or not symbol.isalpha() or len(symbol) > 5:
            return None

        # Validate timeframe
        if timeframe not in self.VALID_TIMEFRAMES:
            return None

        # Validate dates (should be YYYYMMDD format)
        if not (self.is_valid_date(start_date) and self.is_valid_date(end_date)):
            return None

        # Validate date range (end should be after start)
        if start_date >= end_date:
            return None

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

    def analyze_data_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of the data file.

        Args:
            file_path: Path to CSV file

        Returns:
            Dictionary with data analysis results
        """
        try:
            # Read first few rows to check structure
            df_sample = pd.read_csv(file_path, nrows=10)

            if df_sample.empty:
                return {"error": "Empty file", "row_count": 0}

            # Check for required columns
            required_cols = ["datetime", "open", "high", "low", "close", "volume"]
            missing_cols = [
                col for col in required_cols if col not in df_sample.columns
            ]

            if missing_cols:
                return {
                    "error": f"Missing required columns: {missing_cols}",
                    "row_count": 0,
                    "has_required_columns": False,
                }

            # Read full file for analysis
            df = pd.read_csv(file_path, parse_dates=["datetime"])

            analysis = {
                "row_count": len(df),
                "has_required_columns": True,
                "columns": list(df.columns),
                "data_types": {col: str(df[col].dtype) for col in df.columns},
                "date_range": {
                    "start": df["datetime"].min().isoformat() if not df.empty else None,
                    "end": df["datetime"].max().isoformat() if not df.empty else None,
                },
                "statistics": {},
                "data_quality": {},
            }

            # Basic statistics
            if not df.empty:
                numeric_cols = ["open", "high", "low", "close", "volume"]
                for col in numeric_cols:
                    if col in df.columns:
                        analysis["statistics"][col] = {
                            "count": df[col].count(),
                            "mean": float(df[col].mean()),
                            "std": float(df[col].std()),
                            "min": float(df[col].min()),
                            "max": float(df[col].max()),
                            "zeros": int((df[col] == 0).sum()),
                            "negatives": int((df[col] < 0).sum())
                            if col != "volume"
                            else 0,
                        }

                # Volume-specific checks
                if "volume" in df.columns:
                    analysis["statistics"]["volume"]["negative_volume"] = int(
                        (df["volume"] < 0).sum()
                    )

                # Data quality checks
                if "datetime" in df.columns:
                    datetime_col = df["datetime"]
                    analysis["data_quality"] = {
                        "chronological_order": datetime_col.is_monotonic_increasing
                        if hasattr(datetime_col, "is_monotonic_increasing")
                        else False,
                        "duplicate_timestamps": datetime_col.duplicated().sum()
                        if hasattr(datetime_col, "duplicated")
                        else 0,
                        "missing_timestamps": self.check_missing_timestamps(
                            datetime_col
                            if isinstance(datetime_col, pd.Series)
                            else pd.Series()
                        ),
                        "price_consistency": self.check_price_consistency(df),
                        "outliers": self.detect_outliers(df),
                    }
                else:
                    analysis["data_quality"] = {
                        "chronological_order": False,
                        "duplicate_timestamps": 0,
                        "missing_timestamps": {
                            "gaps": 0,
                            "expected_points": 0,
                            "missing_percentage": 0,
                        },
                        "price_consistency": {"consistent": False, "issues": 0},
                        "outliers": {"outliers_detected": 0, "severity": "unknown"},
                    }

            return analysis

        except Exception as e:
            logger.warning(f"Failed to analyze data file {file_path}: {e}")
            return {"error": str(e), "row_count": 0}

    def check_missing_timestamps(self, datetime_series: pd.Series) -> Dict[str, Any]:
        """
        Check for missing timestamps in the data.

        Args:
            datetime_series: Series of datetime values

        Returns:
            Dictionary with missing timestamp analysis
        """
        if datetime_series.empty:
            return {"gaps": 0, "expected_points": 0, "missing_percentage": 0}

        try:
            # Sort and remove duplicates
            clean_times = datetime_series.drop_duplicates().sort_values()

            if len(clean_times) < 2:
                return {
                    "gaps": 0,
                    "expected_points": len(clean_times),
                    "missing_percentage": 0,
                }

            # Calculate expected intervals (simplified - assumes regular intervals)
            time_diffs = clean_times.diff().dropna()
            median_diff = time_diffs.median()

            # Count gaps larger than expected
            gaps = (time_diffs > median_diff * 2).sum()

            return {
                "gaps": int(gaps),
                "expected_points": len(clean_times),
                "missing_percentage": round(gaps / len(clean_times) * 100, 2)
                if len(clean_times) > 0
                else 0,
            }

        except Exception:
            return {"gaps": 0, "expected_points": 0, "missing_percentage": 0}

    def check_price_consistency(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Check price consistency (high >= low, close between high/low, etc.).

        Args:
            df: DataFrame with OHLC data

        Returns:
            Dictionary with consistency check results
        """
        if df.empty:
            return {"consistent": True, "issues": 0}

        issues = 0

        try:
            # High should be >= Low
            invalid_hl = (df["high"] < df["low"]).sum()
            issues += invalid_hl

            # Open should be between Low and High
            invalid_open = ((df["open"] < df["low"]) | (df["open"] > df["high"])).sum()
            issues += invalid_open

            # Close should be between Low and High
            invalid_close = (
                (df["close"] < df["low"]) | (df["close"] > df["high"])
            ).sum()
            issues += invalid_close

            return {
                "consistent": issues == 0,
                "issues": int(issues),
                "invalid_high_low": int(invalid_hl),
                "invalid_open": int(invalid_open),
                "invalid_close": int(invalid_close),
            }

        except Exception:
            return {"consistent": False, "issues": -1}

    def detect_outliers(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect potential outliers in price data.

        Args:
            df: DataFrame with price data

        Returns:
            Dictionary with outlier detection results
        """
        if df.empty:
            return {"outliers_detected": 0, "severity": "none"}

        try:
            outliers = 0

            # Simple outlier detection using IQR method
            for col in ["open", "high", "low", "close"]:
                if col in df.columns:
                    Q1 = df[col].quantile(0.25)
                    Q3 = df[col].quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR

                    col_outliers = (
                        (df[col] < lower_bound) | (df[col] > upper_bound)
                    ).sum()
                    outliers += col_outliers

            severity = "none"
            if outliers > len(df) * 0.01:  # More than 1% outliers
                severity = "low"
            if outliers > len(df) * 0.05:  # More than 5% outliers
                severity = "high"

            return {
                "outliers_detected": int(outliers),
                "severity": severity,
                "percentage": round(outliers / len(df) * 100, 2) if len(df) > 0 else 0,
            }

        except Exception:
            return {"outliers_detected": 0, "severity": "unknown"}

    def calculate_quality_metrics(
        self, data_analysis: Dict, timeframe: str
    ) -> Dict[str, Any]:
        """
        Calculate overall quality metrics based on data analysis.

        Args:
            data_analysis: Results from data analysis
            timeframe: Timeframe of the data

        Returns:
            Dictionary with quality metrics
        """
        if "error" in data_analysis:
            return {
                "overall_score": 0,
                "status": "Error",
                "issues": [data_analysis["error"]],
            }

        score = 100
        issues = []

        # Check required columns
        if not data_analysis.get("has_required_columns", False):
            score -= 50
            issues.append("Missing required columns")

        # Check data completeness
        row_count = data_analysis.get("row_count", 0)
        if row_count == 0:
            score -= 50
            issues.append("No data rows")
        elif row_count < 100:
            score -= 20
            issues.append("Very few data points")

        # Check chronological order
        if not data_analysis.get("data_quality", {}).get("chronological_order", True):
            score -= 15
            issues.append("Not in chronological order")

        # Check for duplicates
        duplicates = data_analysis.get("data_quality", {}).get(
            "duplicate_timestamps", 0
        )
        if duplicates > 0:
            score -= 10
            issues.append(f"{duplicates} duplicate timestamps")

        # Check price consistency
        consistency = data_analysis.get("data_quality", {}).get("price_consistency", {})
        if not consistency.get("consistent", True):
            issues_count = consistency.get("issues", 0)
            score -= min(issues_count * 2, 20)  # Max 20 points deduction
            issues.append(f"{issues_count} price consistency issues")

        # Check for outliers
        outliers = data_analysis.get("data_quality", {}).get("outliers", {})
        if outliers.get("severity") == "high":
            score -= 15
            issues.append("High number of outliers detected")

        # Determine status
        if score >= 90:
            status = "Excellent"
        elif score >= 75:
            status = "Good"
        elif score >= 60:
            status = "Fair"
        else:
            status = "Poor"

        return {
            "overall_score": score,
            "status": status,
            "issues": issues,
            "issue_count": len(issues),
        }

    def calculate_date_range_days(
        self, start_date: str, end_date: str
    ) -> Optional[int]:
        """
        Calculate the number of days in the date range.

        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format

        Returns:
            Number of days in range
        """
        try:
            start = datetime.strptime(start_date, "%Y%m%d")
            end = datetime.strptime(end_date, "%Y%m%d")
            return (end - start).days + 1
        except:
            return None

    def calculate_expected_data_points(
        self, start_date: str, end_date: str, timeframe: str
    ) -> Optional[int]:
        """
        Calculate expected number of data points for the date range and timeframe.

        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            timeframe: Timeframe identifier

        Returns:
            Expected number of data points
        """
        days = self.calculate_date_range_days(start_date, end_date)
        if not days or timeframe not in self.VALID_TIMEFRAMES:
            return None

        points_per_day = self.VALID_TIMEFRAMES[timeframe]["expected_points_per_day"]
        return int(days * points_per_day)

    def generate_summary_stats(
        self, data_analysis: Dict, quality_metrics: Dict
    ) -> Dict[str, Any]:
        """
        Generate summary statistics for UI display.

        Args:
            data_analysis: Data analysis results
            quality_metrics: Quality metrics

        Returns:
            Dictionary with summary statistics
        """
        summary = {
            "total_rows": data_analysis.get("row_count", 0),
            "quality_score": quality_metrics.get("overall_score", 0),
            "quality_status": quality_metrics.get("status", "Unknown"),
            "issues_count": quality_metrics.get("issue_count", 0),
        }

        # Add data range info
        date_range = data_analysis.get("date_range", {})
        if date_range.get("start") and date_range.get("end"):
            summary["data_period"] = (
                f"{date_range['start'][:10]} to {date_range['end'][:10]}"
            )

        # Add key statistics
        stats = data_analysis.get("statistics", {})
        if "close" in stats:
            close_stats = stats["close"]
            summary["price_range"] = (
                f"${close_stats['min']:.2f} - ${close_stats['max']:.2f}"
            )
            summary["avg_price"] = f"${close_stats['mean']:.2f}"

        if "volume" in stats:
            vol_stats = stats["volume"]
            summary["avg_volume"] = f"{vol_stats['mean']:,.0f}"

        return summary


def extract_metadata_from_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to extract metadata from a single file.

    Args:
        file_path: Path to the data file

    Returns:
        Metadata dictionary or None if extraction fails
    """
    extractor = DataMetadataExtractor()
    return extractor.extract_file_metadata(Path(file_path))


def scan_directory_for_metadata(data_dir: str) -> List[Dict[str, Any]]:
    """
    Scan a directory and extract metadata from all valid data files.

    Args:
        data_dir: Directory to scan

    Returns:
        List of metadata dictionaries
    """
    extractor = DataMetadataExtractor()
    data_path = Path(data_dir)

    metadata_list = []
    for csv_file in data_path.rglob("*.csv"):
        metadata = extractor.extract_file_metadata(csv_file)
        if metadata:
            metadata_list.append(metadata)

    return metadata_list


if __name__ == "__main__":
    # Test the extractor
    import sys

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        metadata = extract_metadata_from_file(file_path)
        if metadata:
            import json

            print(json.dumps(metadata, indent=2, default=str))
        else:
            print("Failed to extract metadata")
    else:
        # Scan current directory for CSV files
        metadata_list = scan_directory_for_metadata(".")
        print(f"Found {len(metadata_list)} data files")
        for metadata in metadata_list[:3]:  # Show first 3
            print(f"- {metadata['file_name']}: {metadata['summary']}")
