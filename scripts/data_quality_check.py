#!/usr/bin/env python3
"""
Data Quality Check Script - Validate downloaded data quality.

US-3.3: Data Quality Checks
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataValidator:
    """Validates quality of downloaded market data."""

    def __init__(self, data_dir: str = "data"):
        """
        Initialize validator.

        Args:
            data_dir: Root directory containing LEAN data
        """
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise ValueError(f"Data directory does not exist: {data_dir}")

    def find_symbol_data(self, symbol: str) -> Optional[Path]:
        """
        Find data file for given symbol in LEAN data directory.

        Args:
            symbol: Ticker symbol

        Returns:
            Path to data file if found, None otherwise
        """
        # LEAN stores data in various formats, search common locations
        possible_paths = [
            self.data_dir / "equity" / "usa" / "daily" / f"{symbol.lower()}.zip",
            self.data_dir / "equity" / "usa" / "minute" / symbol.lower(),
            self.data_dir / "processed" / f"{symbol}.csv",
            self.data_dir / "raw" / f"{symbol}.csv",
        ]

        for path in possible_paths:
            if path.exists():
                return path

        return None

    def load_symbol_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Load data for symbol into pandas DataFrame.

        Args:
            symbol: Ticker symbol

        Returns:
            DataFrame with OHLCV data, or None if not found
        """
        data_path = self.find_symbol_data(symbol)
        if not data_path:
            logger.warning(f"No data found for {symbol}")
            return None

        try:
            # Try to read as CSV (common format)
            if data_path.suffix == ".csv":
                df = pd.read_csv(data_path, parse_dates=[0])
            else:
                logger.warning(f"Unsupported format for {symbol}: {data_path.suffix}")
                return None

            # Standardize column names
            df.columns = df.columns.str.lower()
            required_cols = ['open', 'high', 'low', 'close', 'volume']

            if not all(col in df.columns for col in required_cols):
                logger.warning(f"Missing required columns for {symbol}")
                return None

            return df

        except Exception as e:
            logger.error(f"Error loading data for {symbol}: {e}")
            return None

    def check_missing_dates(
        self,
        df: pd.DataFrame,
        symbol: str
    ) -> Tuple[int, List[str]]:
        """
        Check for missing trading days.

        Args:
            df: DataFrame with date index
            symbol: Ticker symbol

        Returns:
            Tuple of (count of missing dates, list of missing dates)
        """
        if df.empty:
            return 0, []

        # Get date column (first column or index)
        if 'date' in df.columns:
            dates = pd.to_datetime(df['date'])
        elif isinstance(df.index, pd.DatetimeIndex):
            dates = df.index
        else:
            dates = pd.to_datetime(df.iloc[:, 0])

        # Generate expected trading days (Monday-Friday, excluding holidays)
        start = dates.min()
        end = dates.max()
        expected_dates = pd.bdate_range(start=start, end=end)

        # Find missing dates
        actual_dates = set(dates.dt.date if hasattr(dates, 'dt') else [d.date() for d in dates])
        expected_dates_set = set(expected_dates.date)
        missing = sorted(expected_dates_set - actual_dates)

        return len(missing), [str(d) for d in missing[:10]]  # Return first 10

    def check_ohlcv_consistency(self, df: pd.DataFrame) -> Tuple[int, List[int]]:
        """
        Check OHLCV relationship consistency.

        Validates:
        - High >= Open, Close, Low
        - Low <= Open, Close, High
        - Volume >= 0

        Args:
            df: DataFrame with OHLCV columns

        Returns:
            Tuple of (count of violations, list of row indices with violations)
        """
        violations = []

        # Check High >= Open, Close, Low
        high_violations = (
            (df['high'] < df['open']) |
            (df['high'] < df['close']) |
            (df['high'] < df['low'])
        )

        # Check Low <= Open, Close, High
        low_violations = (
            (df['low'] > df['open']) |
            (df['low'] > df['close']) |
            (df['low'] > df['high'])
        )

        # Combine violations
        all_violations = high_violations | low_violations
        violation_indices = df[all_violations].index.tolist()

        return len(violation_indices), violation_indices[:10]

    def check_zero_volume(self, df: pd.DataFrame) -> Tuple[int, List[int]]:
        """
        Check for zero or negative volume bars.

        Args:
            df: DataFrame with volume column

        Returns:
            Tuple of (count of zero/negative volume bars, list of row indices)
        """
        zero_volume = (df['volume'] <= 0)
        zero_indices = df[zero_volume].index.tolist()

        return len(zero_indices), zero_indices[:10]

    def check_gaps(
        self,
        df: pd.DataFrame,
        max_gap_days: int = 5
    ) -> Tuple[int, List[Tuple[str, str, int]]]:
        """
        Check for gaps exceeding maximum allowed days.

        Args:
            df: DataFrame with date column
            max_gap_days: Maximum allowed gap in trading days

        Returns:
            Tuple of (count of gaps, list of (start_date, end_date, gap_days))
        """
        if df.empty or len(df) < 2:
            return 0, []

        # Get dates
        if 'date' in df.columns:
            dates = pd.to_datetime(df['date']).sort_values()
        else:
            dates = pd.to_datetime(df.iloc[:, 0]).sort_values()

        # Calculate gaps in business days
        gaps = []
        for i in range(len(dates) - 1):
            start = dates.iloc[i]
            end = dates.iloc[i + 1]
            gap_days = len(pd.bdate_range(start=start, end=end)) - 1

            if gap_days > max_gap_days:
                gaps.append((str(start.date()), str(end.date()), gap_days))

        return len(gaps), gaps[:10]

    def calculate_quality_score(
        self,
        total_bars: int,
        missing_dates: int,
        ohlcv_violations: int,
        zero_volume_bars: int,
        gaps: int
    ) -> float:
        """
        Calculate overall quality score (0.0 to 1.0).

        Args:
            total_bars: Total number of bars
            missing_dates: Count of missing dates
            ohlcv_violations: Count of OHLCV violations
            zero_volume_bars: Count of zero volume bars
            gaps: Count of large gaps

        Returns:
            Quality score between 0.0 and 1.0
        """
        if total_bars == 0:
            return 0.0

        # Calculate penalties (weighted)
        missing_penalty = (missing_dates / total_bars) * 0.4
        ohlcv_penalty = (ohlcv_violations / total_bars) * 0.3
        volume_penalty = (zero_volume_bars / total_bars) * 0.2
        gap_penalty = (gaps / max(1, total_bars / 100)) * 0.1  # Normalize gaps

        total_penalty = min(1.0, missing_penalty + ohlcv_penalty + volume_penalty + gap_penalty)
        quality_score = 1.0 - total_penalty

        return round(quality_score, 3)

    def validate_symbol(
        self,
        symbol: str,
        max_gap_days: int = 5
    ) -> Dict:
        """
        Run all quality checks for a symbol.

        Args:
            symbol: Ticker symbol
            max_gap_days: Maximum allowed gap in trading days

        Returns:
            Dictionary with quality metrics
        """
        logger.info(f"Validating {symbol}...")

        df = self.load_symbol_data(symbol)
        if df is None:
            return {
                "symbol": symbol,
                "status": "not_found",
                "quality_score": 0.0
            }

        # Run checks
        total_bars = len(df)
        missing_count, missing_dates = self.check_missing_dates(df, symbol)
        ohlcv_count, ohlcv_indices = self.check_ohlcv_consistency(df)
        zero_vol_count, zero_vol_indices = self.check_zero_volume(df)
        gap_count, gap_details = self.check_gaps(df, max_gap_days)

        # Calculate quality score
        quality_score = self.calculate_quality_score(
            total_bars, missing_count, ohlcv_count, zero_vol_count, gap_count
        )

        result = {
            "symbol": symbol,
            "status": "validated",
            "total_bars": total_bars,
            "missing_dates": missing_count,
            "missing_dates_sample": missing_dates,
            "ohlcv_violations": ohlcv_count,
            "ohlcv_violations_sample": ohlcv_indices,
            "zero_volume_bars": zero_vol_count,
            "zero_volume_sample": zero_vol_indices,
            "gaps": gap_count,
            "gaps_sample": gap_details,
            "quality_score": quality_score
        }

        # Log summary
        logger.info(f"{symbol}: Quality Score = {quality_score:.3f}")
        if missing_count > 0:
            logger.warning(f"  - {missing_count} missing dates")
        if ohlcv_count > 0:
            logger.warning(f"  - {ohlcv_count} OHLCV violations")
        if zero_vol_count > 0:
            logger.warning(f"  - {zero_vol_count} zero volume bars")
        if gap_count > 0:
            logger.warning(f"  - {gap_count} large gaps")

        return result

    def validate(
        self,
        symbols: List[str],
        max_gap_days: int = 5
    ) -> Dict:
        """
        Validate multiple symbols and generate report.

        Args:
            symbols: List of ticker symbols
            max_gap_days: Maximum allowed gap in trading days

        Returns:
            Dictionary with validation results for all symbols
        """
        results = {}
        quality_scores = []

        for symbol in symbols:
            result = self.validate_symbol(symbol, max_gap_days)
            results[symbol] = result

            if result["status"] == "validated":
                quality_scores.append(result["quality_score"])

        # Calculate overall quality
        overall_quality = np.mean(quality_scores) if quality_scores else 0.0

        return {
            "timestamp": datetime.now().isoformat(),
            "symbols": results,
            "overall_quality": round(overall_quality, 3),
            "validated_count": len([r for r in results.values() if r["status"] == "validated"]),
            "not_found_count": len([r for r in results.values() if r["status"] == "not_found"])
        }


def main():
    """Command-line interface for data quality checks."""
    parser = argparse.ArgumentParser(
        description="Validate quality of downloaded market data"
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        required=True,
        help="Ticker symbols to validate (e.g., SPY AAPL MSFT)"
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Root directory containing data (default: data)"
    )
    parser.add_argument(
        "--max-gap-days",
        type=int,
        default=5,
        help="Maximum allowed gap in trading days (default: 5)"
    )
    parser.add_argument(
        "--report-format",
        choices=["json", "dict"],
        default="dict",
        help="Output format (default: dict)"
    )
    parser.add_argument(
        "--output",
        help="Output file path (optional, prints to stdout if not specified)"
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
        # Initialize validator
        validator = DataValidator(data_dir=args.data_dir)

        # Validate symbols
        results = validator.validate(args.symbols, args.max_gap_days)

        # Output results
        if args.report_format == "json":
            output = json.dumps(results, indent=2)
        else:
            output = str(results)

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output)
            logger.info(f"Report saved to {args.output}")
        else:
            print(output)

        # Exit code based on overall quality
        if results["overall_quality"] < 0.9:
            logger.warning("⚠ Overall quality below 0.9")
            sys.exit(1)
        else:
            logger.info("✓ Data quality validation passed")
            sys.exit(0)

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
