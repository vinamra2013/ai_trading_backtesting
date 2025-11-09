# Unit tests for database schema and operations (Epic 25)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.models.backtest import Base, Backtest, Optimization, AnalyticsCache
from backend.utils.database import DatabaseManager


@pytest.fixture
def test_engine():
    """Create in-memory SQLite engine for testing"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create test database session"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def db_manager(test_engine):
    """Create test database manager"""
    manager = DatabaseManager()
    manager.engine = test_engine
    manager.SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    return manager


class TestBacktestModel:
    """Test Backtest model operations"""

    def test_create_backtest(self, test_session):
        """Test creating a backtest record"""
        backtest = Backtest(
            strategy_name="sma_crossover",
            symbols=["AAPL", "MSFT"],
            parameters={"short_period": 10, "long_period": 20},
            status="pending",
        )
        test_session.add(backtest)
        test_session.commit()
        test_session.refresh(backtest)

        assert backtest.id is not None
        assert backtest.strategy_name == "sma_crossover"
        assert backtest.symbols == ["AAPL", "MSFT"]
        assert backtest.parameters == {"short_period": 10, "long_period": 20}
        assert backtest.status == "pending"
        assert backtest.timeframe == "1d"  # default value

    def test_backtest_status_update(self, test_session):
        """Test updating backtest status"""
        backtest = Backtest(
            strategy_name="rsi_strategy",
            symbols=["SPY"],
            parameters={"period": 14, "overbought": 70, "oversold": 30},
            status="pending",
        )
        test_session.add(backtest)
        test_session.commit()

        # Update status
        backtest.status = "running"
        test_session.commit()
        test_session.refresh(backtest)

        assert backtest.status == "running"


class TestOptimizationModel:
    """Test Optimization model operations"""

    def test_create_optimization(self, test_session):
        """Test creating an optimization record"""
        optimization = Optimization(
            strategy_name="sma_crossover",
            parameter_space={
                "short_period": {"min": 5, "max": 20},
                "long_period": {"min": 20, "max": 50},
            },
            objective_metric="sharpe_ratio",
            status="pending",
        )
        test_session.add(optimization)
        test_session.commit()
        test_session.refresh(optimization)

        assert optimization.id is not None
        assert optimization.strategy_name == "sma_crossover"
        assert optimization.objective_metric == "sharpe_ratio"
        assert optimization.status == "pending"

    def test_optimization_with_best_result(self, test_session):
        """Test optimization with best result reference"""
        # Create a backtest first
        backtest = Backtest(
            strategy_name="sma_crossover",
            symbols=["AAPL"],
            parameters={"short_period": 10, "long_period": 30},
            status="completed",
            metrics={"sharpe_ratio": 1.5, "returns": 0.12},
        )
        test_session.add(backtest)
        test_session.commit()

        # Create optimization referencing the backtest
        optimization = Optimization(
            strategy_name="sma_crossover",
            parameter_space={"short_period": [5, 10, 15], "long_period": [20, 30, 40]},
            objective_metric="sharpe_ratio",
            status="completed",
            best_result_id=backtest.id,
            best_parameters={"short_period": 10, "long_period": 30},
            best_metric_value=1.5,
        )
        test_session.add(optimization)
        test_session.commit()
        test_session.refresh(optimization)

        assert optimization.best_result_id == backtest.id
        assert optimization.best_metric_value == 1.5


class TestAnalyticsCacheModel:
    """Test AnalyticsCache model operations"""

    def test_create_cache_entry(self, test_session):
        """Test creating a cache entry"""
        cache_entry = AnalyticsCache(
            cache_key="portfolio_metrics_2024",
            cache_type="portfolio",
            data={"total_return": 0.15, "sharpe_ratio": 1.2, "volatility": 0.08},
            metadata={"symbols": ["AAPL", "MSFT", "GOOGL"], "period": "1Y"},
        )
        test_session.add(cache_entry)
        test_session.commit()
        test_session.refresh(cache_entry)

        assert cache_entry.id is not None
        assert cache_entry.cache_key == "portfolio_metrics_2024"
        assert cache_entry.cache_type == "portfolio"
        assert cache_entry.data["total_return"] == 0.15

    def test_unique_cache_key_constraint(self, test_session):
        """Test that cache keys must be unique"""
        # Create first entry
        cache_entry1 = AnalyticsCache(
            cache_key="unique_key", cache_type="test", data={"value": 1}
        )
        test_session.add(cache_entry1)
        test_session.commit()

        # Try to create duplicate key
        cache_entry2 = AnalyticsCache(
            cache_key="unique_key",  # Same key
            cache_type="test2",
            data={"value": 2},
        )
        test_session.add(cache_entry2)

        with pytest.raises(Exception):  # Should raise IntegrityError
            test_session.commit()


class TestDatabaseManager:
    """Test DatabaseManager operations"""

    def test_create_and_retrieve_backtest(self, db_manager, test_session):
        """Test creating and retrieving backtest via DatabaseManager"""
        # Create backtest
        backtest = db_manager.create_backtest(
            test_session,
            strategy_name="test_strategy",
            symbols=["TEST"],
            parameters={"param1": "value1"},
            status="pending",
        )

        assert backtest.id is not None

        # Retrieve backtest
        retrieved = db_manager.get_backtest(test_session, backtest.id)
        assert retrieved is not None
        assert retrieved.strategy_name == "test_strategy"
        assert retrieved.symbols == ["TEST"]

    def test_update_backtest_status(self, db_manager, test_session):
        """Test updating backtest status via DatabaseManager"""
        # Create backtest
        backtest = db_manager.create_backtest(
            test_session,
            strategy_name="update_test",
            symbols=["UPDATE"],
            parameters={"test": True},
            status="pending",
        )

        # Update status
        success = db_manager.update_backtest_status(
            test_session, backtest.id, "completed", metrics={"sharpe_ratio": 2.1}
        )

        assert success is True

        # Verify update
        updated = db_manager.get_backtest(test_session, backtest.id)
        assert updated.status == "completed"
        assert updated.metrics["sharpe_ratio"] == 2.1

    def test_cached_analytics_operations(self, db_manager, test_session):
        """Test analytics cache operations"""
        cache_key = "test_cache_key"
        cache_data = {"metric1": 1.0, "metric2": 2.0}

        # Set cache
        cache_entry = db_manager.set_cached_analytics(
            test_session,
            cache_key=cache_key,
            cache_type="test",
            data=cache_data,
            metadata={"source": "test"},
        )

        assert cache_entry.cache_key == cache_key
        assert cache_entry.data == cache_data

        # Get cache
        retrieved = db_manager.get_cached_analytics(test_session, cache_key)
        assert retrieved is not None
        assert retrieved.data == cache_data

        # Update cache
        updated_data = {"metric1": 1.5, "metric2": 2.5}
        db_manager.set_cached_analytics(
            test_session, cache_key=cache_key, cache_type="test", data=updated_data
        )

        updated = db_manager.get_cached_analytics(test_session, cache_key)
        assert updated.data == updated_data
