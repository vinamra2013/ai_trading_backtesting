#!/usr/bin/env python3
"""
PostgreSQL Database Manager for Symbol Discovery Engine
Epic 18: Symbol Discovery Engine - US-18.4 Data Output and Storage

Handles storage and retrieval of discovered symbols and scan history.
"""

import os
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import asdict

import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool

from scripts.symbol_discovery_models import DiscoveredSymbol


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SymbolDiscoveryDB:
    """
    PostgreSQL database manager for symbol discovery data.

    Handles:
    - Discovered symbols storage and retrieval
    - Scan history and performance tracking
    - Symbol metadata and filtering criteria
    """

    def __init__(self, db_config: Dict[str, Any]):
        """
        Initialize database connection pool.

        Args:
            db_config: Database configuration from YAML
        """
        self.db_config = db_config
        self.pool = None
        self._create_connection_pool()

        logger.info("SymbolDiscoveryDB initialized")

    def _create_connection_pool(self):
        """Create PostgreSQL connection pool."""
        try:
            pool_config = self.db_config.get('pool', {})
            self.pool = SimpleConnectionPool(
                minconn=pool_config.get('min_connections', 1),
                maxconn=pool_config.get('max_connections', 10),
                host=self.db_config['host'],
                port=self.db_config['port'],
                database=self.db_config['database'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                connect_timeout=pool_config.get('connection_timeout', 30)
            )
            logger.info("✅ Database connection pool created")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Yields:
            psycopg2 connection with DictCursor
        """
        conn = None
        try:
            conn = self.pool.getconn()
            conn.cursor_factory = psycopg2.extras.RealDictCursor
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                self.pool.putconn(conn)

    def create_schema(self) -> None:
        """
        Create database schema for symbol discovery.

        Tables:
        - discovered_symbols: Symbol metadata and discovery info
        - scan_history: Scan execution logs and performance
        - symbol_performance: Historical price/volume data
        """
        logger.info("Creating symbol discovery database schema...")

        schema_sql = """
        -- Symbol Discovery Database Schema
        -- Epic 18: Symbol Discovery Engine

        -- Discovered symbols table
        CREATE TABLE IF NOT EXISTS discovered_symbols (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            exchange VARCHAR(20) NOT NULL,
            sector VARCHAR(100),
            avg_volume BIGINT,
            atr DECIMAL(10,4),
            price DECIMAL(10,2),
            pct_change DECIMAL(8,4),
            market_cap BIGINT,
            volume BIGINT,
            discovery_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            scanner_type VARCHAR(50) NOT NULL,
            scan_id INTEGER REFERENCES scan_history(id),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(symbol, exchange, scanner_type, discovery_timestamp::date)
        );

        -- Scan history table
        CREATE TABLE IF NOT EXISTS scan_history (
            id SERIAL PRIMARY KEY,
            scanner_name VARCHAR(50) NOT NULL,
            scanner_type VARCHAR(50) NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            symbols_discovered INTEGER DEFAULT 0,
            symbols_filtered INTEGER DEFAULT 0,
            status VARCHAR(20) DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
            error_message TEXT,
            execution_time_seconds DECIMAL(10,2),
            filters_applied JSONB,
            performance_metrics JSONB,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        -- Symbol performance tracking
        CREATE TABLE IF NOT EXISTS symbol_performance (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            exchange VARCHAR(20) NOT NULL,
            date DATE NOT NULL,
            open_price DECIMAL(10,2),
            high_price DECIMAL(10,2),
            low_price DECIMAL(10,2),
            close_price DECIMAL(10,2),
            volume BIGINT,
            atr_14 DECIMAL(10,4),
            avg_volume_30d BIGINT,
            pct_change DECIMAL(8,4),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(symbol, exchange, date)
        );

        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_discovered_symbols_symbol ON discovered_symbols(symbol);
        CREATE INDEX IF NOT EXISTS idx_discovered_symbols_exchange ON discovered_symbols(exchange);
        CREATE INDEX IF NOT EXISTS idx_discovered_symbols_scanner ON discovered_symbols(scanner_type);
        CREATE INDEX IF NOT EXISTS idx_discovered_symbols_timestamp ON discovered_symbols(discovery_timestamp);
        CREATE INDEX IF NOT EXISTS idx_discovered_symbols_scan_id ON discovered_symbols(scan_id);

        CREATE INDEX IF NOT EXISTS idx_scan_history_name ON scan_history(scanner_name);
        CREATE INDEX IF NOT EXISTS idx_scan_history_status ON scan_history(status);
        CREATE INDEX IF NOT EXISTS idx_scan_history_start_time ON scan_history(start_time);

        CREATE INDEX IF NOT EXISTS idx_symbol_performance_symbol ON symbol_performance(symbol);
        CREATE INDEX IF NOT EXISTS idx_symbol_performance_date ON symbol_performance(date);

        -- Update trigger for updated_at
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';

        DROP TRIGGER IF EXISTS update_discovered_symbols_updated_at ON discovered_symbols;
        CREATE TRIGGER update_discovered_symbols_updated_at
            BEFORE UPDATE ON discovered_symbols
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(schema_sql)
            conn.commit()

        logger.info("✅ Symbol discovery database schema created")

    def start_scan(self, scanner_name: str, scanner_type: str, filters: Dict[str, Any]) -> int:
        """
        Record the start of a symbol discovery scan.

        Args:
            scanner_name: Name of the scanner
            scanner_type: Type of scanner
            filters: Applied filters

        Returns:
            Scan ID for tracking
        """
        sql = """
        INSERT INTO scan_history (scanner_name, scanner_type, start_time, filters_applied)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (scanner_name, scanner_type, datetime.now(), psycopg2.extras.Json(filters)))
            scan_id = cursor.fetchone()['id']
            conn.commit()

        logger.info(f"Started scan {scan_id}: {scanner_name}")
        return scan_id

    def complete_scan(self, scan_id: int, symbols_discovered: int, symbols_filtered: int,
                     execution_time: float, performance_metrics: Optional[Dict] = None):
        """
        Record the completion of a symbol discovery scan.

        Args:
            scan_id: Scan identifier
            symbols_discovered: Number of symbols initially discovered
            symbols_filtered: Number of symbols after filtering
            execution_time: Total execution time in seconds
            performance_metrics: Optional performance metrics
        """
        sql = """
        UPDATE scan_history
        SET end_time = %s,
            symbols_discovered = %s,
            symbols_filtered = %s,
            status = 'completed',
            execution_time_seconds = %s,
            performance_metrics = %s
        WHERE id = %s
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (
                datetime.now(),
                symbols_discovered,
                symbols_filtered,
                execution_time,
                psycopg2.extras.Json(performance_metrics) if performance_metrics else None,
                scan_id
            ))
            conn.commit()

        logger.info(f"Completed scan {scan_id}: {symbols_filtered} symbols filtered from {symbols_discovered}")

    def fail_scan(self, scan_id: int, error_message: str):
        """
        Record a failed symbol discovery scan.

        Args:
            scan_id: Scan identifier
            error_message: Error description
        """
        sql = """
        UPDATE scan_history
        SET end_time = %s,
            status = 'failed',
            error_message = %s
        WHERE id = %s
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (datetime.now(), error_message, scan_id))
            conn.commit()

        logger.error(f"Failed scan {scan_id}: {error_message}")

    def save_discovered_symbols(self, symbols: List[DiscoveredSymbol], scanner_type: str, scan_id: Optional[int] = None):
        """
        Save discovered symbols to database.

        Args:
            symbols: List of discovered symbols
            scanner_type: Type of scanner used
            scan_id: Optional scan identifier
        """
        if not symbols:
            logger.warning("No symbols to save")
            return

        sql = """
        INSERT INTO discovered_symbols (
            symbol, exchange, sector, avg_volume, atr, price, pct_change,
            market_cap, volume, scanner_type, scan_id
        ) VALUES %s
        ON CONFLICT (symbol, exchange, scanner_type, discovery_timestamp::date)
        DO UPDATE SET
            sector = EXCLUDED.sector,
            avg_volume = EXCLUDED.avg_volume,
            atr = EXCLUDED.atr,
            price = EXCLUDED.price,
            pct_change = EXCLUDED.pct_change,
            market_cap = EXCLUDED.market_cap,
            volume = EXCLUDED.volume,
            updated_at = CURRENT_TIMESTAMP
        """

        # Prepare data for bulk insert
        values = []
        for symbol in symbols:
            data = (
                symbol.symbol,
                symbol.exchange,
                symbol.sector,
                symbol.avg_volume,
                symbol.atr,
                symbol.price,
                symbol.pct_change,
                symbol.market_cap,
                symbol.volume,
                scanner_type,
                scan_id
            )
            values.append(data)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            psycopg2.extras.execute_values(cursor, sql, values)
            conn.commit()

        logger.info(f"Saved {len(symbols)} symbols to database")

    def get_recent_discovered_symbols(self, scanner_type: Optional[str] = None,
                                    days_back: int = 7, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Retrieve recently discovered symbols.

        Args:
            scanner_type: Filter by scanner type
            days_back: How many days back to look
            limit: Maximum number of records

        Returns:
            List of symbol dictionaries
        """
        sql = """
        SELECT * FROM discovered_symbols
        WHERE discovery_timestamp >= CURRENT_TIMESTAMP - INTERVAL '%s days'
        """
        params = [days_back]

        if scanner_type:
            sql += " AND scanner_type = %s"
            params.append(scanner_type)

        sql += " ORDER BY discovery_timestamp DESC LIMIT %s"
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_scan_history(self, scanner_name: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve scan execution history.

        Args:
            scanner_name: Filter by scanner name
            limit: Maximum number of records

        Returns:
            List of scan history records
        """
        sql = "SELECT * FROM scan_history WHERE 1=1"
        params = []

        if scanner_name:
            sql += " AND scanner_name = %s"
            params.append(scanner_name)

        sql += " ORDER BY start_time DESC LIMIT %s"
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_symbol_performance(self, symbol: str, exchange: str, days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Get historical performance data for a symbol.

        Args:
            symbol: Stock symbol
            exchange: Exchange
            days_back: Days of history to retrieve

        Returns:
            List of performance records
        """
        sql = """
        SELECT * FROM symbol_performance
        WHERE symbol = %s AND exchange = %s
        AND date >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY date DESC
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (symbol, exchange, days_back))
            return [dict(row) for row in cursor.fetchall()]

    def update_symbol_performance(self, symbol: str, exchange: str, performance_data: Dict[str, Any]):
        """
        Update or insert symbol performance data.

        Args:
            symbol: Stock symbol
            exchange: Exchange
            performance_data: Performance metrics
        """
        sql = """
        INSERT INTO symbol_performance (
            symbol, exchange, date, open_price, high_price, low_price,
            close_price, volume, atr_14, avg_volume_30d, pct_change
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (symbol, exchange, date)
        DO UPDATE SET
            open_price = EXCLUDED.open_price,
            high_price = EXCLUDED.high_price,
            low_price = EXCLUDED.low_price,
            close_price = EXCLUDED.close_price,
            volume = EXCLUDED.volume,
            atr_14 = EXCLUDED.atr_14,
            avg_volume_30d = EXCLUDED.avg_volume_30d,
            pct_change = EXCLUDED.pct_change
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (
                symbol,
                exchange,
                performance_data.get('date'),
                performance_data.get('open_price'),
                performance_data.get('high_price'),
                performance_data.get('low_price'),
                performance_data.get('close_price'),
                performance_data.get('volume'),
                performance_data.get('atr_14'),
                performance_data.get('avg_volume_30d'),
                performance_data.get('pct_change')
            ))
            conn.commit()

    def get_discovery_stats(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Get discovery statistics and analytics.

        Args:
            days_back: Analysis period in days

        Returns:
            Dictionary with discovery statistics
        """
        sql = """
        SELECT
            COUNT(DISTINCT symbol) as unique_symbols,
            COUNT(*) as total_discoveries,
            COUNT(DISTINCT scanner_type) as scanner_types_used,
            AVG(symbols_filtered::float / NULLIF(symbols_discovered, 0)) as avg_filter_rate,
            SUM(symbols_discovered) as total_scanned,
            SUM(symbols_filtered) as total_filtered
        FROM discovered_symbols d
        JOIN scan_history s ON d.scan_id = s.id
        WHERE d.discovery_timestamp >= CURRENT_TIMESTAMP - INTERVAL '%s days'
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (days_back,))
            result = dict(cursor.fetchone())

        # Get scanner type breakdown
        scanner_sql = """
        SELECT scanner_type, COUNT(*) as count
        FROM discovered_symbols
        WHERE discovery_timestamp >= CURRENT_TIMESTAMP - INTERVAL '%s days'
        GROUP BY scanner_type
        ORDER BY count DESC
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(scanner_sql, (days_back,))
            scanner_breakdown = {row['scanner_type']: row['count'] for row in cursor.fetchall()}

        result['scanner_breakdown'] = scanner_breakdown
        return result

    def cleanup_old_data(self, days_to_keep: int = 90):
        """
        Clean up old discovery data to manage database size.

        Args:
            days_to_keep: Number of days of data to retain
        """
        logger.info(f"Cleaning up data older than {days_to_keep} days...")

        # Delete old discovered symbols
        sql1 = """
        DELETE FROM discovered_symbols
        WHERE discovery_timestamp < CURRENT_TIMESTAMP - INTERVAL '%s days'
        """

        # Delete old scan history
        sql2 = """
        DELETE FROM scan_history
        WHERE start_time < CURRENT_TIMESTAMP - INTERVAL '%s days'
        """

        # Delete old performance data
        sql3 = """
        DELETE FROM symbol_performance
        WHERE date < CURRENT_DATE - INTERVAL '%s days'
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql1, (days_to_keep,))
            deleted_symbols = cursor.rowcount

            cursor.execute(sql2, (days_to_keep,))
            deleted_scans = cursor.rowcount

            cursor.execute(sql3, (days_to_keep,))
            deleted_performance = cursor.rowcount

            conn.commit()

        logger.info(f"Cleanup complete: {deleted_symbols} symbols, {deleted_scans} scans, {deleted_performance} performance records deleted")

    def close(self):
        """Close database connection pool."""
        if self.pool:
            self.pool.closeall()
            logger.info("Database connection pool closed")


# Convenience functions
def create_symbol_discovery_db(config_path: str = "config/symbol_discovery_config.yaml") -> SymbolDiscoveryDB:
    """
    Create and initialize symbol discovery database.

    Args:
        config_path: Path to configuration file

    Returns:
        Initialized SymbolDiscoveryDB instance
    """
    import yaml

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    db = SymbolDiscoveryDB(config['database'])
    db.create_schema()
    return db


if __name__ == '__main__':
    # Test database functionality
    print("Testing Symbol Discovery Database...")

    try:
        db = create_symbol_discovery_db()

        # Test scan tracking
        scan_id = db.start_scan("test_scanner", "high_volume", {"min_volume": 1000000})
        print(f"Started test scan with ID: {scan_id}")

        # Test symbol saving
        test_symbols = [
            DiscoveredSymbol("AAPL", "NASDAQ", avg_volume=50000000, price=150.0),
            DiscoveredSymbol("GOOGL", "NASDAQ", avg_volume=3000000, price=2800.0)
        ]
        db.save_discovered_symbols(test_symbols, "test_scanner", scan_id)

        # Complete scan
        db.complete_scan(scan_id, 100, 50, 30.5)

        # Get stats
        stats = db.get_discovery_stats()
        print(f"Discovery stats: {stats}")

        print("✅ Database tests completed successfully")

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        raise
    finally:
        if 'db' in locals():
            db.close()