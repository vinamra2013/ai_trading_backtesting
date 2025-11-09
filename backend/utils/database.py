# Database connectivity and utility functions for FastAPI backend

import os
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from backend.models.backtest import Base, Backtest, Optimization, AnalyticsCache


class DatabaseManager:
    """Database connection manager for the FastAPI backend"""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql://mlflow:mlflow_secure_password@postgres:5432/mlflow",
        )
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()

    def _initialize_engine(self):
        """Initialize SQLAlchemy engine and session factory"""
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600,
            echo=False,  # Set to True for debugging
        )

        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def get_session(self):
        """Get a database session"""
        if self.SessionLocal is None:
            raise RuntimeError("Database not initialized")
        return self.SessionLocal()

    def create_tables(self):
        """Create all tables defined in the models"""
        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self):
        """Drop all tables (use with caution)"""
        Base.metadata.drop_all(bind=self.engine)

    # Backtest CRUD operations
    def create_backtest(self, session, **kwargs):
        """Create a new backtest record"""
        backtest = Backtest(**kwargs)
        session.add(backtest)
        session.commit()
        session.refresh(backtest)
        return backtest

    def get_backtest(self, session, backtest_id: int):
        """Get a backtest by ID"""
        return session.query(Backtest).filter(Backtest.id == backtest_id).first()

    def get_backtests_by_strategy(self, session, strategy_name: str):
        """Get all backtests for a specific strategy"""
        return (
            session.query(Backtest)
            .filter(Backtest.strategy_name == strategy_name)
            .all()
        )

    def update_backtest_status(self, session, backtest_id: int, status: str, **kwargs):
        """Update backtest status and optional fields"""
        backtest = session.query(Backtest).filter(Backtest.id == backtest_id).first()
        if backtest:
            setattr(backtest, "status", status)
            for key, value in kwargs.items():
                if hasattr(backtest, key):
                    setattr(backtest, key, value)
            session.commit()
            return True
        return False

    # Optimization CRUD operations
    def create_optimization(self, session: Session, **kwargs) -> Optimization:
        """Create a new optimization record"""
        optimization = Optimization(**kwargs)
        session.add(optimization)
        session.commit()
        session.refresh(optimization)
        return optimization

    def get_optimization(
        self, session: Session, optimization_id: int
    ) -> Optional[Optimization]:
        """Get an optimization by ID"""
        return (
            session.query(Optimization)
            .filter(Optimization.id == optimization_id)
            .first()
        )

    # Analytics Cache operations
    def get_cached_analytics(
        self, session: Session, cache_key: str
    ) -> Optional[AnalyticsCache]:
        """Get cached analytics by key"""
        return (
            session.query(AnalyticsCache)
            .filter(AnalyticsCache.cache_key == cache_key)
            .first()
        )

    def set_cached_analytics(
        self,
        session: Session,
        cache_key: str,
        cache_type: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[Any] = None,
    ) -> AnalyticsCache:
        """Set or update cached analytics"""
        cache_entry = (
            session.query(AnalyticsCache)
            .filter(AnalyticsCache.cache_key == cache_key)
            .first()
        )

        if cache_entry:
            setattr(cache_entry, "data", data)
            setattr(cache_entry, "cache_metadata", metadata)
            setattr(cache_entry, "expires_at", expires_at)
        else:
            cache_entry = AnalyticsCache(
                cache_key=cache_key,
                cache_type=cache_type,
                data=data,
                cache_metadata=metadata,
                expires_at=expires_at,
            )
            session.add(cache_entry)

        session.commit()
        session.refresh(cache_entry)
        return cache_entry

    def clear_expired_cache(self, session: Session) -> int:
        """Clear expired cache entries. Returns number of entries cleared."""
        from sqlalchemy import func

        result = (
            session.query(AnalyticsCache)
            .filter(
                AnalyticsCache.expires_at.isnot(None),
                AnalyticsCache.expires_at < func.now(),
            )
            .delete()
        )
        session.commit()
        return result


# Global database manager instance
db_manager = DatabaseManager()


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance"""
    return db_manager
