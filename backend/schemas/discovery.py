# Pydantic schemas for symbol discovery API (Epic 26 Story 1)

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime


class DiscoveryRequest(BaseModel):
    """Request model for triggering a symbol discovery scan"""

    scanner_name: str = Field(
        ...,
        description="Scanner type to run",
        examples=["high_volume", "volatility_leaders", "top_gainers"],
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Scanner-specific parameters",
        examples=[{"number_of_rows": 50, "above_volume": 1000000}],
    )
    filters: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Filtering criteria to apply",
        examples=[
            {
                "liquidity": {"min_avg_volume": 1000000},
                "price_range": {"min_price": 5.0, "max_price": 500.0},
                "volatility": {"min_atr": 0.5, "max_atr": 20.0},
            }
        ],
    )

    @validator("scanner_name")
    def validate_scanner_name(cls, v):
        valid_scanners = [
            "high_volume",
            "most_active_stocks",
            "top_gainers",
            "top_losers",
            "most_active_etfs",
            "volatility_leaders",
        ]
        if v not in valid_scanners:
            raise ValueError(f"Scanner must be one of: {', '.join(valid_scanners)}")
        return v


class DiscoveryResponse(BaseModel):
    """Response model for discovery job submission"""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Current job status")
    message: str = Field(..., description="Status message")
    created_at: datetime = Field(..., description="Job creation timestamp")
    estimated_completion: Optional[datetime] = Field(
        None, description="Estimated completion time"
    )


class DiscoveryStatus(BaseModel):
    """Discovery job status information"""

    job_id: str
    scanner_name: str
    scanner_type: str
    status: str
    progress: float = Field(..., ge=0.0, le=100.0)
    symbols_discovered: int = 0
    symbols_filtered: int = 0
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class DiscoveredSymbol(BaseModel):
    """Individual discovered symbol information"""

    symbol: str
    exchange: str
    sector: Optional[str] = None
    avg_volume: Optional[int] = None
    atr: Optional[float] = None
    price: Optional[float] = None
    pct_change: Optional[float] = None
    market_cap: Optional[int] = None
    volume: Optional[int] = None
    discovery_timestamp: datetime
    scanner_type: str
    metadata: Optional[Dict[str, Any]] = None


class DiscoveryResult(BaseModel):
    """Discovery results with pagination"""

    job_id: str
    scanner_name: str
    scanner_type: str
    symbols: List[DiscoveredSymbol]
    total_count: int
    filtered_count: int
    completed_at: datetime
    execution_time_seconds: float


class DiscoveryListResponse(BaseModel):
    """Paginated response for discovery job list"""

    jobs: List[DiscoveryStatus]
    total: int
    page: int
    page_size: int
    total_pages: int


class DiscoveryFilter(BaseModel):
    """Filter parameters for discovery job queries"""

    scanner_name: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
