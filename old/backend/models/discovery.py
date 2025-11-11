# SQLAlchemy models for symbol discovery operations (Epic 26 Story 1)

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    Boolean,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from typing import Optional

Base = declarative_base()


class DiscoveryJob(Base):
    """Discovery job metadata and status tracking"""

    __tablename__ = "discovery_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(255), nullable=False, unique=True, index=True)
    scanner_name = Column(String(100), nullable=False, index=True)
    scanner_type = Column(String(100), nullable=False)

    # Configuration
    parameters = Column(JSON, nullable=True)  # Scanner parameters
    filters = Column(JSON, nullable=True)  # Applied filters

    # Status and tracking
    status = Column(
        String(50), nullable=False, default="pending"
    )  # pending, running, completed, failed
    progress = Column(Float, default=0.0)  # Progress percentage 0-100

    # Results
    symbols_discovered = Column(Integer, default=0)
    symbols_filtered = Column(Integer, default=0)
    result_data = Column(JSON, nullable=True)  # Discovery results

    # Error handling
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self):
        return f"<DiscoveryJob(id={self.id}, job_id={self.job_id}, scanner={self.scanner_name}, status={self.status})>"


class DiscoveryResult(Base):
    """Individual discovery results storage"""

    __tablename__ = "discovery_results"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(
        String(255), ForeignKey("discovery_jobs.job_id"), nullable=False, index=True
    )

    # Symbol information
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(20), nullable=False, index=True)
    sector = Column(String(100), nullable=True)

    # Financial metrics
    avg_volume = Column(Integer, nullable=True)
    atr = Column(Float, nullable=True)
    price = Column(Float, nullable=True)
    pct_change = Column(Float, nullable=True)
    market_cap = Column(Integer, nullable=True)
    volume = Column(Integer, nullable=True)

    # Discovery metadata
    scanner_type = Column(String(100), nullable=False)
    discovery_timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Additional data
    symbol_metadata = Column(JSON, nullable=True)  # Additional symbol metadata

    def __repr__(self):
        return f"<DiscoveryResult(id={self.id}, symbol={self.symbol}, exchange={self.exchange})>"


class RankingJob(Base):
    """Ranking job metadata and status tracking"""

    __tablename__ = "ranking_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(255), nullable=False, unique=True, index=True)

    # Input configuration
    input_type = Column(String(50), nullable=False)  # 'csv', 'database', 'results_dir'
    input_source = Column(String(500), nullable=True)  # File path or query parameters

    # Ranking configuration
    criteria_weights = Column(JSON, nullable=False)  # Scoring weights
    ranking_config = Column(JSON, nullable=True)  # Additional ranking parameters

    # Status and tracking
    status = Column(
        String(50), nullable=False, default="pending"
    )  # pending, running, completed, failed
    progress = Column(Float, default=0.0)  # Progress percentage 0-100

    # Results summary
    total_strategies = Column(Integer, default=0)
    ranked_strategies = Column(Integer, default=0)
    result_summary = Column(JSON, nullable=True)  # Summary statistics

    # Error handling
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self):
        return f"<RankingJob(id={self.id}, job_id={self.job_id}, status={self.status})>"


class RankingResult(Base):
    """Individual ranking results storage"""

    __tablename__ = "ranking_results"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(
        String(255), ForeignKey("ranking_jobs.job_id"), nullable=False, index=True
    )

    # Strategy information
    strategy_name = Column(String(255), nullable=False, index=True)
    symbol = Column(String(20), nullable=True, index=True)

    # Performance metrics
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    total_trades = Column(Integer, nullable=True)
    profit_factor = Column(Float, nullable=True)

    # Individual scores (0-100 scale)
    sharpe_score = Column(Float, nullable=True)
    consistency_score = Column(Float, nullable=True)
    drawdown_score = Column(Float, nullable=True)
    frequency_score = Column(Float, nullable=True)
    efficiency_score = Column(Float, nullable=True)

    # Composite score and ranking
    composite_score = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False, index=True)

    # Additional data
    strategy_metadata = Column(JSON, nullable=True)  # Additional strategy metadata

    def __repr__(self):
        return f"<RankingResult(id={self.id}, strategy={self.strategy_name}, rank={self.rank}, score={self.composite_score})>"
