# SQLAlchemy models for backtesting and optimization metadata (Epic 25)

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


class Backtest(Base):
    """Backtest metadata and results storage"""

    __tablename__ = "backtests"

    id = Column(Integer, primary_key=True, index=True)
    strategy_name = Column(String(255), nullable=False, index=True)
    symbols = Column(JSON, nullable=False)  # List of symbols as JSON array
    parameters = Column(JSON, nullable=False)  # Strategy parameters as JSON
    timeframe = Column(String(50), default="1d")  # Timeframe (1m, 5m, 1h, 1d, etc.)

    # Status and tracking
    status = Column(
        String(50), nullable=False, default="pending"
    )  # pending, running, completed, failed
    mlflow_run_id = Column(String(255), nullable=True, index=True)

    # Metrics (stored as JSON for flexibility)
    metrics = Column(JSON, nullable=True)  # Sharpe ratio, returns, drawdown, etc.

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Backtest(id={self.id}, strategy={self.strategy_name}, status={self.status})>"


class Optimization(Base):
    """Optimization job metadata and results"""

    __tablename__ = "optimizations"

    id = Column(Integer, primary_key=True, index=True)
    strategy_name = Column(String(255), nullable=False, index=True)
    parameter_space = Column(JSON, nullable=False)  # Parameter ranges for optimization
    objective_metric = Column(String(100), nullable=False, default="sharpe_ratio")

    # Results
    status = Column(
        String(50), nullable=False, default="pending"
    )  # pending, running, completed, failed
    best_result_id = Column(Integer, ForeignKey("backtests.id"), nullable=True)
    best_parameters = Column(JSON, nullable=True)
    best_metric_value = Column(Float, nullable=True)

    # MLflow tracking
    mlflow_experiment_id = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Optimization(id={self.id}, strategy={self.strategy_name}, status={self.status})>"


class AnalyticsCache(Base):
    """Cached analytics and portfolio metrics for performance"""

    __tablename__ = "analytics_cache"

    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(
        String(255), nullable=False, unique=True, index=True
    )  # Unique identifier for cache entry
    cache_type = Column(
        String(100), nullable=False, index=True
    )  # portfolio, strategy, symbol, etc.

    # Data
    data = Column(JSON, nullable=False)  # Cached analytics data
    cache_metadata = Column(JSON, nullable=True)  # Additional metadata

    # Cache management
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_updated = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self):
        return f"<AnalyticsCache(id={self.id}, key={self.cache_key}, type={self.cache_type})>"
