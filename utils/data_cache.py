"""
Data caching utilities for intraday resampled CSV files.
Epic 24: VARM-RSI performance optimization
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

import pandas as pd

Timeframe = Literal["1m", "5m", "1h", "4h", "1d"]


@dataclass
class ResampleKey:
    symbol: str
    timeframe: Timeframe

    def path(self, base_dir: Path) -> Path:
        return base_dir / self.symbol / f"{self.symbol}_{self.timeframe}.csv"


def get_or_build_resampled_csv(
    source_path: Path,
    symbol: str,
    timeframe: Timeframe,
) -> Path:
    if not source_path.exists():
        raise FileNotFoundError(str(source_path))

    if timeframe == "1m":
        return source_path

    key = ResampleKey(symbol=symbol, timeframe=timeframe)
    cache_root = source_path.parent.parent
    cache_path = key.path(cache_root)

    if cache_path.exists():
        return cache_path

    cache_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(source_path, parse_dates=["ts_event"])
    df = df.set_index("ts_event")

    rule_map = {
        "5m": "5T",
        "1h": "60T",
        "4h": "240T",
        "1d": "1D",
    }
    rule = rule_map[timeframe]

    ohlcv = (
        df.resample(rule)
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        .dropna()
    )

    ohlcv.index.name = "datetime"
    ohlcv.to_csv(cache_path)

    return cache_path
