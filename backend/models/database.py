"""
V2 Parallel Optimization System - Database Models
SQLAlchemy models for the V2 optimization schema with proper relationships and constraints.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    Float,
    JSON,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Dict, List, Any, Optional

Base = declarative_base()


class Strategy(Base):
    """Master list of trading strategies."""

    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(
        String(50), nullable=False
    )  # mean_reversion, momentum, volatility, futures, hybrid, event_based
    asset_class = Column(
        String(50), nullable=False
    )  # etf, equity, futures, forex, crypto
    lean_project_path = Column(
        String(255), nullable=False
    )  # Must match actual directory names
    description = Column(Text)
    status = Column(
        String(20), nullable=False, default="planned"
    )  # planned, testing, rejected, passed, deployed
    priority = Column(Integer, default=0)  # Higher = more important
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships - commented out due to missing foreign keys
    # success_criteria = relationship(
    #     "SuccessCriteria", back_populates="strategy_rel", uselist=False
    # )

    def __repr__(self):
        return f"<Strategy(name='{self.name}', category='{self.category}', status='{self.status}')>"


class BacktestJob(Base):
    """Individual backtest jobs with container tracking (V2 core)."""

    __tablename__ = "backtest_jobs"

    id = Column(Integer, primary_key=True)
    batch_id = Column(
        String(100), index=True
    )  # Groups related jobs (opt_20241112_143052_abc123)
    strategy_name = Column(String(255), nullable=False, index=True)
    lean_project_path = Column(String(255), nullable=False)
    parameters = Column(
        JSONB, nullable=False
    )  # Individual parameter set {"rsi_period": 14, "entry_threshold": 30}
    symbols = Column(JSONB, default='["SPY"]')  # List of symbols as JSON array
    status = Column(
        String(50), default="queued", index=True
    )  # queued, running, completed, failed
    container_id = Column(String(100))  # Docker container tracking
    result_path = Column(String(500))  # LEAN output directory path
    error_message = Column(Text)  # Failure details
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Relationships
    results = relationship(
        "BacktestResult", back_populates="job", cascade="all, delete-orphan"
    )
    batch = relationship("OptimizationBatch", back_populates="jobs")

    def __repr__(self):
        return f"<BacktestJob(id={self.id}, strategy='{self.strategy_name}', status='{self.status}')>"


class OptimizationBatch(Base):
    """Batch management for grouped optimizations (V2)."""

    __tablename__ = "optimization_batches"

    id = Column(
        String(100), primary_key=True
    )  # Unique batch ID (opt_20241112_143052_abc123)
    strategy_name = Column(String(255), nullable=False)
    config_file = Column(String(500))  # Source config file path
    total_jobs = Column(Integer, nullable=False)  # Total number of jobs in batch
    completed_jobs = Column(Integer, default=0)  # Jobs completed so far
    status = Column(
        String(50), default="running", index=True
    )  # running, completed, failed
    best_result_id = Column(
        Integer, ForeignKey("backtest_jobs.id")
    )  # Best performing job
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    # Relationships
    jobs = relationship("BacktestJob", back_populates="batch")
    best_result = relationship("BacktestJob", foreign_keys=[best_result_id])

    def __repr__(self):
        return f"<OptimizationBatch(id='{self.id}', strategy='{self.strategy_name}', status='{self.status}', completed={self.completed_jobs}/{self.total_jobs})>"


class BacktestResult(Base):
    """Extended results with JSON metrics (V2)."""

    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True)
    job_id = Column(
        Integer,
        ForeignKey("backtest_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    batch_id = Column(String(100), ForeignKey("optimization_batches.id"), index=True)
    parameters = Column(JSONB)  # Duplicate for querying (denormalized)
    metrics = Column(
        JSONB, nullable=False
    )  # All metrics as JSON {"sharpe_ratio": 1.45, "total_return": 0.234, ...}
    meets_criteria = Column(
        Boolean, default=False, index=True
    )  # Whether result passes success criteria
    rejection_reasons = Column(
        JSON
    )  # Array of reasons as JSON ["insufficient_trades", "high_drawdown"]
    qc_backtest_id = Column(String(100), unique=True)  # QuantConnect backtest ID
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    job = relationship("BacktestJob", back_populates="results")

    def __repr__(self):
        return f"<BacktestResult(job_id={self.job_id}, meets_criteria={self.meets_criteria})>"


class SuccessCriteria(Base):
    """Success criteria for each strategy (V2)."""

    __tablename__ = "success_criteria"

    id = Column(Integer, primary_key=True)
    strategy_name = Column(
        String(255), nullable=False, unique=True
    )  # Links to strategies.name
    min_trades = Column(
        Integer, default=100
    )  # Minimum trades for statistical significance
    min_sharpe = Column(Float, default=1.0)  # Minimum Sharpe ratio
    max_drawdown = Column(Float, default=0.15)  # Maximum drawdown (15%)
    min_win_rate = Column(Float, default=0.45)  # Minimum win rate (45%)
    max_fee_pct = Column(Float, default=0.30)  # Maximum fees as % of capital (30%)
    min_avg_win = Column(Float, default=0.01)  # Minimum average winning trade (1%)
    max_fee_per_trade = Column(Float)  # Maximum fee per trade
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships - commented out due to missing foreign keys
    # strategy_rel = relationship("Strategy", back_populates="success_criteria")

    def __repr__(self):
        return f"<SuccessCriteria(strategy='{self.strategy_name}', min_sharpe={self.min_sharpe})>"


# Note: Indexes are defined in the database schema SQL file
# These are created when the schema is applied to the database</content>
