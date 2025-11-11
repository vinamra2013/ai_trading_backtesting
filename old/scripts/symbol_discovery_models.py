#!/usr/bin/env python3
"""
Symbol Discovery Data Models
Epic 18: Symbol Discovery Engine

Shared data models and types for symbol discovery functionality.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any


@dataclass
class DiscoveredSymbol:
    """Represents a discovered symbol with all metadata."""
    symbol: str
    exchange: str
    sector: Optional[str] = None
    avg_volume: Optional[float] = None
    atr: Optional[float] = None
    price: Optional[float] = None
    pct_change: Optional[float] = None
    market_cap: Optional[float] = None
    volume: Optional[float] = None
    discovery_timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.discovery_timestamp is None:
            self.discovery_timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert datetime to ISO format for JSON serialization
        if isinstance(data['discovery_timestamp'], datetime):
            data['discovery_timestamp'] = data['discovery_timestamp'].isoformat()
        return data


@dataclass
class ScanResult:
    """Represents the result of a symbol discovery scan."""
    scanner_name: str
    scanner_type: str
    symbols_discovered: int
    symbols_filtered: int
    execution_time_seconds: float
    scan_id: Optional[int] = None
    error_message: Optional[str] = None
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)