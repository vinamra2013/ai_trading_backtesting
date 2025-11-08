#!/usr/bin/env python3
"""
Databento Zip Extractor and CSV Transformer

Extracts Databento zip files and transforms the data to match the existing
CSV format used in the trading platform.

Epic: Data Processing Pipeline

Features:
- Extract Databento zip files
- Transform timestamp format from ISO to simple format
- Match existing CSV column structure
- Organize output in data/csv/resolution/symbol/ structure
- Validate data integrity

Usage:
    python scripts/databento_zip_extractor.py --zip-file path/to/databento.zip --output-dir data/csv/1m

Author: AI Assistant
"""

import argparse
import logging
import os
import sys
import zipfile
import pandas as pd
import zstandard as zstd
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabentoZipExtractor:
    """
    Extracts and transforms Databento zip files to match existing CSV format.
    """

    # Expected columns in Databento format
    DATABENTO_COLUMNS = [
        "ts_event",
        "rtype",
        "publisher_id",
        "instrument_id",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "symbol",
    ]

    def __init__(self, zip_file: str, output_dir: str):
        """
        Initialize the extractor.

        Args:
            zip_file: Path to the Databento zip file
            output_dir: Base output directory (e.g., data/csv/1m)
        """
        self.zip_file = Path(zip_file)
        self.output_dir = Path(output_dir)
        self.extract_dir = self.zip_file.parent / f"{self.zip_file.stem}_extracted"

        if not self.zip_file.exists():
            raise FileNotFoundError(f"Zip file not found: {self.zip_file}")

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_zip(self) -> Path:
        """
        Extract the zip file to a temporary directory.

        Returns:
            Path to the extraction directory
        """
        logger.info(f"Extracting {self.zip_file} to {self.extract_dir}")

        with zipfile.ZipFile(self.zip_file, "r") as zip_ref:
            zip_ref.extractall(self.extract_dir)

        logger.info(f"Extraction complete. Files extracted to: {self.extract_dir}")
        return self.extract_dir

    def find_csv_files(self, extract_dir: Path) -> List[Path]:
        """
        Find all CSV and ZST files in the extracted directory.

        Args:
            extract_dir: Directory where zip was extracted

        Returns:
            List of CSV/ZST file paths
        """
        csv_files = list(extract_dir.rglob("*.csv"))
        zst_files = list(extract_dir.rglob("*.zst"))
        all_files = csv_files + zst_files
        logger.info(
            f"Found {len(all_files)} files ({len(csv_files)} CSV, {len(zst_files)} ZST): {[str(f) for f in all_files]}"
        )
        return all_files

    def transform_timestamp(self, ts_str: str) -> str:
        """
        Transform Databento timestamp format to match existing CSV format.

        Databento format: 2025-10-07T08:00:00.000000000Z
        Target format: 2025-10-07 08:00:00

        Args:
            ts_str: Timestamp string from Databento

        Returns:
            Transformed timestamp string
        """
        try:
            # Parse ISO format timestamp
            if "T" in ts_str:
                # Remove Z and split by T
                ts_clean = ts_str.replace("Z", "")
                date_part, time_part = ts_clean.split("T")

                # Remove microseconds from time part
                if "." in time_part:
                    time_part = time_part.split(".")[0]

                return f"{date_part} {time_part}"
            else:
                # Already in correct format
                return ts_str
        except Exception as e:
            logger.warning(f"Failed to parse timestamp '{ts_str}': {e}")
            return ts_str

    def process_zip_file(self) -> None:
        """
        Main processing function to extract and transform the zip file.
        Merge all monthly files for each symbol into one continuous file.
        """
        try:
            # Extract zip file
            extract_dir = self.extract_zip()

            # Find CSV and ZST files
            all_files = self.find_csv_files(extract_dir)

            if not all_files:
                logger.warning("No files found in the extracted zip file")
                return

            # Group files by symbol
            symbol_files = {}
            for file_path in all_files:
                symbol = self.extract_symbol_from_filename(file_path)
                if symbol:
                    if symbol not in symbol_files:
                        symbol_files[symbol] = []
                    symbol_files[symbol].append(file_path)

            # Process each symbol - merge all files into one continuous file
            for symbol, files in symbol_files.items():
                self.merge_symbol_files(symbol, files)

            # Clean up extraction directory
            logger.info(f"Cleaning up extraction directory: {extract_dir}")
            import shutil

            shutil.rmtree(extract_dir)

            logger.info("Processing complete!")

        except Exception as e:
            logger.error(f"Failed to process zip file: {e}")
            raise

    def extract_symbol_from_filename(self, file_path: Path) -> Optional[str]:
        """
        Extract symbol from filename.

        Args:
            file_path: Path to the file

        Returns:
            Symbol name or None if not found
        """
        filename = file_path.stem.upper()

        # Try to find symbol in filename parts
        parts = filename.split("_")
        for part in parts:
            # Look for uppercase strings that are likely stock symbols (2-5 chars)
            if 2 <= len(part) <= 5 and part.isupper() and part.isalpha():
                return part

        # Try to extract from data if filename doesn't contain it
        try:
            if file_path.suffix == ".zst":
                with open(file_path, "rb") as f:
                    with zstd.open(f, "rt") as zf_stream:
                        df = pd.read_csv(zf_stream, nrows=1)
            else:
                df = pd.read_csv(file_path, nrows=1)

            if "symbol" in df.columns and not df.empty:
                return str(df["symbol"].iloc[0]).upper()
        except Exception:
            pass

        return None

    def merge_symbol_files(self, symbol: str, symbol_files: List[Path]) -> None:
        """
        Merge all files for a symbol into one continuous CSV file.

        Args:
            symbol: Symbol name (e.g., 'SPY', 'QQQ')
            symbol_files: List of data files for this symbol (CSV or ZST)
        """
        logger.info(
            f"Merging {len(symbol_files)} {symbol} files into one continuous file"
        )

        try:
            # Sort files by date for proper chronological order
            symbol_files.sort(key=lambda x: str(x))

            all_dataframes = []

            for file_path in symbol_files:
                logger.debug(f"Processing {symbol} file: {file_path}")

                try:
                    # Handle ZST decompression
                    if file_path.suffix == ".zst":
                        with open(file_path, "rb") as f:
                            with zstd.open(f, "rt") as zf_stream:
                                df = pd.read_csv(zf_stream)
                    else:
                        df = pd.read_csv(file_path)

                    # Check if file has data
                    if df.empty:
                        logger.warning(f"Skipping empty {symbol} file: {file_path}")
                        continue

                    # Transform timestamp if needed
                    if "ts_event" in df.columns:
                        df["ts_event"] = (
                            df["ts_event"].astype(str).apply(self.transform_timestamp)
                        )

                    all_dataframes.append(df)

                except Exception as e:
                    logger.warning(f"Failed to process {file_path}: {e}")
                    continue

            if not all_dataframes:
                logger.error(f"No {symbol} data could be processed")
                return

            # Concatenate all dataframes
            logger.info(f"Concatenating all {symbol} dataframes")
            combined_df = pd.concat(all_dataframes, ignore_index=True)

            # Sort by timestamp and remove duplicates
            if "ts_event" in combined_df.columns:
                combined_df["ts_event"] = pd.to_datetime(combined_df["ts_event"])
                combined_df = combined_df.sort_values("ts_event").drop_duplicates()
                combined_df["ts_event"] = combined_df["ts_event"].dt.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

            # Create symbol subdirectory
            symbol_dir = self.output_dir / symbol
            symbol_dir.mkdir(parents=True, exist_ok=True)

            # Generate output filename with full date range
            if "ts_event" in combined_df.columns and not combined_df.empty:
                start_date = pd.to_datetime(combined_df["ts_event"].min()).strftime(
                    "%Y%m%d"
                )
                end_date = pd.to_datetime(combined_df["ts_event"].max()).strftime(
                    "%Y%m%d"
                )
                output_filename = f"{symbol}_1m_{start_date}_{end_date}.csv"
            else:
                today = datetime.now().strftime("%Y%m%d")
                output_filename = f"{symbol}_1m_{today}_{today}.csv"

            output_file = symbol_dir / output_filename

            # Save combined data
            combined_df.to_csv(output_file, index=False)
            logger.info(
                f"✅ Merged {symbol} data saved to: {output_file} ({len(combined_df)} rows)"
            )

        except Exception as e:
            logger.error(f"Failed to merge {symbol} files: {e}")
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract and transform Databento zip files to match existing CSV format"
    )
    parser.add_argument(
        "--zip-file", required=True, help="Path to the Databento zip file"
    )
    parser.add_argument(
        "--output-dir",
        default="data/csv/1m",
        help="Base output directory (default: data/csv/1m)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create extractor and process
    extractor = DatabentoZipExtractor(args.zip_file, args.output_dir)
    extractor.process_zip_file()


if __name__ == "__main__":
    main()
