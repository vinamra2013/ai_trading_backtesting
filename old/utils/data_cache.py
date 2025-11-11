"""
Data caching utilities for intraday resampled CSV files.
Epic 24: VARM-RSI performance optimization
"""

from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

import pandas as pd

logger = logging.getLogger(__name__)

Timeframe = Literal["1m", "5m", "1h", "4h", "1d"]  # type: ignore


@dataclass
class ResampleKey:
    symbol: str
    timeframe: str

    def path(self, base_dir: Path) -> Path:
        return base_dir / f"{self.symbol}_{self.timeframe}.csv"


def get_or_build_resampled_csv(
    source_path: Path,
    symbol: str,
    timeframe: str,
) -> Path:
    logger.debug(f"Processing cache for {symbol} {timeframe}")

    if not source_path.exists():
        logger.error(f"Source file not found: {source_path}")
        raise FileNotFoundError(str(source_path))

    if timeframe == "1m":
        logger.debug(f"Using source file directly for {symbol} 1m")
        return source_path

    key = ResampleKey(symbol=symbol, timeframe=timeframe)
    cache_root = source_path.parent.parent
    cache_path = key.path(cache_root)

    if cache_path.exists():
        logger.debug(f"Cache hit for {symbol} {timeframe}: {cache_path}")
        return cache_path

    logger.info(f"Cache miss for {symbol} {timeframe}, building cache")
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Use memory mapping for better performance with large files
    try:
        df = pd.read_csv(source_path, parse_dates=["datetime"], memory_map=True)
        df = df.set_index("datetime")
        logger.debug(f"Loaded {len(df)} rows for {symbol}")
    except Exception as e:
        logger.error(f"Failed to load CSV for {symbol}: {e}")
        raise

    rule_map = {
        "5m": "5T",
        "1h": "60T",
        "4h": "240T",
        "1d": "1D",
    }
    rule = rule_map[timeframe]

    try:
        # Preserve original column format for compatibility with data loaders
        # Aggregate OHLCV columns, keep first value for metadata columns
        agg_dict = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }

        # Preserve metadata columns (take first value)
        if "rtype" in df.columns:
            agg_dict["rtype"] = "first"
        if "publisher_id" in df.columns:
            agg_dict["publisher_id"] = "first"
        if "instrument_id" in df.columns:
            agg_dict["instrument_id"] = "first"
        if "symbol" in df.columns:
            agg_dict["symbol"] = "first"

        ohlcv = df.resample(rule).agg(agg_dict).dropna()
        logger.debug(f"Resampled {symbol} to {timeframe}: {len(ohlcv)} rows")
    except Exception as e:
        logger.error(f"Failed to resample {symbol} to {timeframe}: {e}")
        raise

    # Ensure we have a DataFrame (should be already)
    if not isinstance(ohlcv, pd.DataFrame):
        logger.error(f"Expected DataFrame, got {type(ohlcv)}")
        raise ValueError("Resampling did not return a DataFrame")

    # Reorder columns to match original format
    original_columns = df.columns.tolist()
    # Filter to only include columns that exist after resampling
    final_columns = [
        col for col in original_columns if col in ohlcv.columns and col != "datetime"
    ]

    # Reorder the DataFrame columns to match original order
    ohlcv = ohlcv[final_columns]

    ohlcv.index.name = "datetime"  # Use original index name
    ohlcv.to_csv(cache_path)
    logger.info(f"Cached {symbol} {timeframe} to {cache_path}")

    return cache_path


def _resample_single(args):
    """Helper function for parallel resampling (must be at module level for multiprocessing)"""
    tf, src_path, sym = args
    return tf, get_or_build_resampled_csv(src_path, sym, tf)


def get_or_build_multiple_resampled_csv(
    source_path: Path,
    symbol: str,
    timeframes: list[str],
    max_workers: int = 4,
) -> dict[str, Path]:
    """
    Build multiple resampled timeframes in parallel for better performance.

    Args:
        source_path: Path to source 1m CSV file
        symbol: Stock symbol
        timeframes: List of timeframes to resample (excluding 1m)
        max_workers: Maximum number of parallel workers

    Returns:
        Dict mapping timeframe to cached file path
    """
    logger.info(f"Building caches for {symbol} timeframes: {timeframes}")

    if not source_path.exists():
        raise FileNotFoundError(str(source_path))

    # Filter out 1m since it's not cached
    cache_timeframes = [tf for tf in timeframes if tf != "1m"]
    if not cache_timeframes:
        return {}

    results = {}

    # Check cache hits first (fast operation)
    for timeframe in cache_timeframes[
        :
    ]:  # Use slice copy for safe removal during iteration
        key = ResampleKey(symbol=symbol, timeframe=timeframe)
        cache_root = source_path.parent.parent
        cache_path = key.path(cache_root)

        if cache_path.exists():
            logger.debug(f"Cache hit for {symbol} {timeframe}")
            results[timeframe] = cache_path
            cache_timeframes.remove(timeframe)

    if not cache_timeframes:
        logger.info(f"All caches hit for {symbol}")
        return results

    # Process cache misses in parallel
    logger.info(
        f"Processing {len(cache_timeframes)} cache misses for {symbol} in parallel"
    )

    args_list = [(tf, source_path, symbol) for tf in cache_timeframes]

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_timeframe = {
            executor.submit(_resample_single, args): args[0] for args in args_list
        }

        for future in as_completed(future_to_timeframe):
            timeframe = future_to_timeframe[future]
            try:
                tf, path = future.result()
                results[tf] = path
                logger.debug(f"Completed parallel resampling for {symbol} {tf}")
            except Exception as e:
                logger.error(
                    f"Failed parallel resampling for {symbol} {timeframe}: {e}"
                )
                raise

    logger.info(f"Completed parallel caching for {symbol}: {list(results.keys())}")
    return results

    # Process cache misses in parallel
    logger.info(
        f"Processing {len(cache_timeframes)} cache misses for {symbol} in parallel"
    )

    args_list = [(tf, source_path, symbol) for tf in cache_timeframes]

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_timeframe = {
            executor.submit(_resample_single, args): args[0] for args in args_list
        }

        for future in as_completed(future_to_timeframe):
            timeframe = future_to_timeframe[future]
            try:
                tf, path = future.result()
                results[tf] = path
                logger.debug(f"Completed parallel resampling for {symbol} {tf}")
            except Exception as e:
                logger.error(
                    f"Failed parallel resampling for {symbol} {timeframe}: {e}"
                )
                raise

    logger.info(f"Completed parallel caching for {symbol}: {list(results.keys())}")
    return results
