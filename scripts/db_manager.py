#!/usr/bin/env python3
"""
Database Schema Manager for Live Trading Platform

Epic 5: Live Trading Engine
US-5.3: Position Management
US-5.4: Risk Management & Safety

Manages SQLite database schema and provides utilities for:
- Order tracking and execution history
- Position management and P&L calculations
- Daily performance summaries
- Risk events and metrics monitoring
- Emergency stop procedures
- Trading state management
"""

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DBManager:
    """
    SQLite database manager for live trading platform.

    Features:
    - WAL (Write-Ahead Logging) mode for concurrent access
    - Complete schema management
    - Helper methods for common queries
    - Proper constraints and indexes
    - Transaction support via context managers
    """

    def __init__(self, db_path: str = "data/sqlite/trading.db"):
        """
        Initialize database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"DBManager initialized with database: {self.db_path}")

        # Set WAL mode for concurrent access
        self._enable_wal_mode()

    def _enable_wal_mode(self) -> None:
        """Enable Write-Ahead Logging for better concurrency."""
        try:
            with self.get_connection() as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA foreign_keys=ON")
                logger.info("✓ WAL mode enabled, foreign keys enabled")
        except Exception as e:
            logger.error(f"Failed to enable WAL mode: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Yields:
            sqlite3.Connection: Database connection with row factory

        Example:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM orders")
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_schema(self) -> None:
        """
        Create complete database schema with all tables, constraints, and indexes.

        Tables created:
        - orders: Order execution tracking
        - positions: Current position inventory
        - position_history: Historical position changes
        - daily_summaries: Daily performance metrics
        - risk_events: Risk monitoring and alerts
        - risk_metrics: Real-time risk calculations
        - emergency_stops: Emergency liquidation records
        - trading_state: Key-value state management
        """
        logger.info("Creating database schema...")

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Orders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    algorithm TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL CHECK(side IN ('BUY', 'SELL')),
                    quantity INTEGER NOT NULL CHECK(quantity > 0),
                    order_type TEXT NOT NULL CHECK(order_type IN ('MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT')),
                    limit_price REAL,
                    stop_price REAL,
                    status TEXT NOT NULL CHECK(status IN ('PENDING', 'SUBMITTED', 'PARTIAL', 'FILLED', 'CANCELLED', 'REJECTED', 'EXPIRED')) DEFAULT 'PENDING',
                    filled_quantity INTEGER DEFAULT 0 CHECK(filled_quantity >= 0),
                    average_fill_price REAL,
                    commission REAL DEFAULT 0.0,
                    sec_fee REAL DEFAULT 0.0,
                    total_cost REAL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    submitted_at TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    ib_order_id INTEGER,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    notes TEXT,
                    CHECK(filled_quantity <= quantity),
                    CHECK(limit_price IS NULL OR limit_price > 0),
                    CHECK(stop_price IS NULL OR stop_price > 0)
                )
            """)

            # Positions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    symbol TEXT PRIMARY KEY,
                    algorithm TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    cost_basis REAL NOT NULL,
                    average_price REAL NOT NULL CHECK(average_price > 0),
                    current_price REAL,
                    unrealized_pnl REAL DEFAULT 0.0,
                    realized_pnl REAL DEFAULT 0.0,
                    entry_date TEXT NOT NULL,
                    last_updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Position history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS position_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    algorithm TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL CHECK(price > 0),
                    pnl REAL,
                    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT NOT NULL CHECK(event_type IN ('ENTRY', 'ADD', 'REDUCE', 'EXIT', 'UPDATE')),
                    order_id TEXT,
                    FOREIGN KEY (order_id) REFERENCES orders(order_id)
                )
            """)

            # Daily summaries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_summaries (
                    date TEXT PRIMARY KEY,
                    algorithm TEXT NOT NULL,
                    starting_equity REAL NOT NULL,
                    ending_equity REAL NOT NULL,
                    realized_pnl REAL DEFAULT 0.0,
                    unrealized_pnl REAL DEFAULT 0.0,
                    total_pnl REAL DEFAULT 0.0,
                    total_pnl_pct REAL DEFAULT 0.0,
                    trades_count INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0.0,
                    total_commission REAL DEFAULT 0.0,
                    total_sec_fees REAL DEFAULT 0.0,
                    gross_profit REAL DEFAULT 0.0,
                    gross_loss REAL DEFAULT 0.0,
                    profit_factor REAL,
                    max_position_size INTEGER DEFAULT 0,
                    positions_count INTEGER DEFAULT 0,
                    turnover REAL DEFAULT 0.0,
                    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Risk events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS risk_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL CHECK(event_type IN (
                        'POSITION_LIMIT', 'PORTFOLIO_LIMIT', 'DRAWDOWN', 'VOLATILITY',
                        'CORRELATION', 'MARGIN_CALL', 'LEVERAGE', 'CONCENTRATION',
                        'ORDER_REJECTION', 'CONNECTION_LOSS', 'OTHER'
                    )),
                    severity TEXT NOT NULL CHECK(severity IN ('INFO', 'WARNING', 'CRITICAL', 'EMERGENCY')),
                    symbol TEXT,
                    algorithm TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    portfolio_value REAL,
                    position_value REAL,
                    limit_value REAL,
                    breach_pct REAL,
                    action_taken TEXT,
                    resolved INTEGER DEFAULT 0 CHECK(resolved IN (0, 1)),
                    resolved_at TEXT
                )
            """)

            # Risk metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS risk_metrics (
                    timestamp TEXT PRIMARY KEY,
                    algorithm TEXT NOT NULL,
                    portfolio_value REAL NOT NULL,
                    portfolio_heat REAL DEFAULT 0.0,
                    var_95 REAL,
                    var_99 REAL,
                    correlation_avg REAL,
                    correlation_max REAL,
                    leverage_ratio REAL DEFAULT 0.0,
                    margin_used REAL DEFAULT 0.0,
                    margin_available REAL,
                    buying_power REAL,
                    position_count INTEGER DEFAULT 0,
                    largest_position_pct REAL DEFAULT 0.0,
                    top5_concentration REAL DEFAULT 0.0
                )
            """)

            # Emergency stops table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS emergency_stops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    algorithm TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    positions_liquidated INTEGER DEFAULT 0,
                    orders_cancelled INTEGER DEFAULT 0,
                    total_pnl REAL,
                    initiated_by TEXT NOT NULL CHECK(initiated_by IN ('SYSTEM', 'USER', 'RISK_MANAGER')),
                    manual INTEGER DEFAULT 0 CHECK(manual IN (0, 1)),
                    notes TEXT
                )
            """)

            # Trading state table (key-value store)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trading_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Performance metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    metric_type TEXT NOT NULL CHECK(metric_type IN (
                        'ORDER_LATENCY', 'DATA_FEED_LATENCY', 'BACKTEST_TIME',
                        'MEMORY_USAGE', 'CPU_USAGE', 'DISK_USAGE', 'DATABASE_LATENCY'
                    )),
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    algorithm TEXT,
                    additional_data TEXT
                )
            """)

            # Create indexes for performance
            logger.info("Creating indexes...")

            # Orders indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_algorithm ON orders(algorithm)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_ib_order_id ON orders(ib_order_id)")

            # Positions indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_algorithm ON positions(algorithm)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_last_updated ON positions(last_updated)")

            # Position history indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_position_history_symbol ON position_history(symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_position_history_timestamp ON position_history(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_position_history_event_type ON position_history(event_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_position_history_order_id ON position_history(order_id)")

            # Daily summaries indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_summaries_algorithm ON daily_summaries(algorithm)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_summaries_date ON daily_summaries(date)")

            # Risk events indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_risk_events_severity ON risk_events(severity)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_risk_events_timestamp ON risk_events(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_risk_events_resolved ON risk_events(resolved)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_risk_events_symbol ON risk_events(symbol)")

            # Risk metrics indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_risk_metrics_algorithm ON risk_metrics(algorithm)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_risk_metrics_timestamp ON risk_metrics(timestamp)")

            # Emergency stops indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_emergency_stops_algorithm ON emergency_stops(algorithm)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_emergency_stops_timestamp ON emergency_stops(timestamp)")

            # Performance metrics indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_timestamp ON performance_metrics(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_type ON performance_metrics(metric_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_algorithm ON performance_metrics(algorithm)")

            # Initialize default trading state values
            cursor.execute("""
                INSERT OR IGNORE INTO trading_state (key, value) VALUES
                    ('trading_enabled', 'true'),
                    ('emergency_stop_active', 'false'),
                    ('last_health_check', CURRENT_TIMESTAMP),
                    ('system_status', 'READY')
            """)

            conn.commit()
            logger.info("✓ Database schema created successfully")

    # Helper methods for common queries

    def get_orders(
        self,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        algorithm: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve orders with optional filters.

        Args:
            symbol: Filter by symbol
            status: Filter by status
            algorithm: Filter by algorithm
            limit: Maximum number of records

        Returns:
            List of order dictionaries
        """
        query = "SELECT * FROM orders WHERE 1=1"
        params = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        if status:
            query += " AND status = ?"
            params.append(status)
        if algorithm:
            query += " AND algorithm = ?"
            params.append(algorithm)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_positions(
        self,
        algorithm: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve current positions.

        Args:
            algorithm: Filter by algorithm

        Returns:
            List of position dictionaries
        """
        query = "SELECT * FROM positions WHERE 1=1"
        params = []

        if algorithm:
            query += " AND algorithm = ?"
            params.append(algorithm)

        query += " ORDER BY symbol"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_position_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get position for a specific symbol.

        Args:
            symbol: Ticker symbol

        Returns:
            Position dictionary or None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM positions WHERE symbol = ?", (symbol,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_daily_summary(self, target_date: date) -> Optional[Dict[str, Any]]:
        """
        Get daily summary for a specific date.

        Args:
            target_date: Date to retrieve

        Returns:
            Daily summary dictionary or None
        """
        date_str = target_date.isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM daily_summaries WHERE date = ?",
                (date_str,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_risk_events(
        self,
        severity: Optional[str] = None,
        resolved: Optional[bool] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve risk events with optional filters.

        Args:
            severity: Filter by severity level
            resolved: Filter by resolution status
            limit: Maximum number of records

        Returns:
            List of risk event dictionaries
        """
        query = "SELECT * FROM risk_events WHERE 1=1"
        params = []

        if severity:
            query += " AND severity = ?"
            params.append(severity)
        if resolved is not None:
            query += " AND resolved = ?"
            params.append(1 if resolved else 0)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_latest_risk_metrics(self, algorithm: str) -> Optional[Dict[str, Any]]:
        """
        Get latest risk metrics for an algorithm.

        Args:
            algorithm: Algorithm name

        Returns:
            Risk metrics dictionary or None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM risk_metrics
                WHERE algorithm = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (algorithm,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_emergency_stops(
        self,
        algorithm: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retrieve emergency stop records.

        Args:
            algorithm: Filter by algorithm
            limit: Maximum number of records

        Returns:
            List of emergency stop dictionaries
        """
        query = "SELECT * FROM emergency_stops WHERE 1=1"
        params = []

        if algorithm:
            query += " AND algorithm = ?"
            params.append(algorithm)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_trading_state(self, key: str) -> Optional[str]:
        """
        Get trading state value by key.

        Args:
            key: State key

        Returns:
            State value or None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM trading_state WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            return row['value'] if row else None

    def set_trading_state(self, key: str, value: str) -> None:
        """
        Set trading state value.

        Args:
            key: State key
            value: State value
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO trading_state (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, value)
            )
            conn.commit()
            logger.info(f"Trading state updated: {key} = {value}")

    def get_portfolio_summary(self, algorithm: str) -> Dict[str, Any]:
        """
        Get comprehensive portfolio summary for an algorithm.

        Args:
            algorithm: Algorithm name

        Returns:
            Dictionary with portfolio metrics
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get position count and total value
            cursor.execute(
                """
                SELECT
                    COUNT(*) as position_count,
                    SUM(quantity * current_price) as total_position_value,
                    SUM(unrealized_pnl) as total_unrealized_pnl,
                    SUM(realized_pnl) as total_realized_pnl
                FROM positions
                WHERE algorithm = ?
                """,
                (algorithm,)
            )
            positions_summary = dict(cursor.fetchone())

            # Get order statistics
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_orders,
                    SUM(CASE WHEN status = 'FILLED' THEN 1 ELSE 0 END) as filled_orders,
                    SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) as rejected_orders,
                    SUM(CASE WHEN status IN ('PENDING', 'SUBMITTED', 'PARTIAL') THEN 1 ELSE 0 END) as active_orders
                FROM orders
                WHERE algorithm = ? AND date(created_at) = date('now')
                """,
                (algorithm,)
            )
            orders_summary = dict(cursor.fetchone())

            return {
                **positions_summary,
                **orders_summary,
                'algorithm': algorithm,
                'timestamp': datetime.now().isoformat()
            }

    def record_performance_metric(
        self,
        metric_type: str,
        metric_name: str,
        metric_value: float,
        unit: str,
        algorithm: Optional[str] = None,
        additional_data: Optional[Dict] = None
    ) -> bool:
        """
        Record a performance metric.

        Args:
            metric_type: Type of metric (ORDER_LATENCY, DATA_FEED_LATENCY, etc.)
            metric_name: Name of the metric
            metric_value: Value of the metric
            unit: Unit of measurement (ms, seconds, %, MB, etc.)
            algorithm: Algorithm name (optional)
            additional_data: Additional context data (optional)

        Returns:
            True if successful
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO performance_metrics
                    (metric_type, metric_name, metric_value, unit, algorithm, additional_data)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    metric_type,
                    metric_name,
                    metric_value,
                    unit,
                    algorithm,
                    str(additional_data) if additional_data else None
                ))
                return True
        except Exception as e:
            logger.error(f"Failed to record performance metric: {e}")
            return False

    def get_performance_metrics(
        self,
        metric_type: Optional[str] = None,
        metric_name: Optional[str] = None,
        algorithm: Optional[str] = None,
        hours_back: int = 24,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Retrieve performance metrics with optional filters.

        Args:
            metric_type: Filter by metric type
            metric_name: Filter by metric name
            algorithm: Filter by algorithm
            hours_back: How many hours back to look
            limit: Maximum number of records

        Returns:
            List of performance metric dictionaries
        """
        query = """
            SELECT * FROM performance_metrics
            WHERE timestamp >= datetime('now', '-{} hours')
        """.format(hours_back)
        params = []

        if metric_type:
            query += " AND metric_type = ?"
            params.append(metric_type)
        if metric_name:
            query += " AND metric_name = ?"
            params.append(metric_name)
        if algorithm:
            query += " AND algorithm = ?"
            params.append(algorithm)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_latest_performance_metrics(
        self,
        metric_type: Optional[str] = None,
        algorithm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get latest performance metrics for each metric type/name combination.

        Args:
            metric_type: Filter by metric type
            algorithm: Filter by algorithm

        Returns:
            Dictionary mapping metric keys to latest values
        """
        query = """
            SELECT metric_type, metric_name, metric_value, unit, algorithm, timestamp
            FROM performance_metrics
            WHERE timestamp >= datetime('now', '-24 hours')
        """
        params = []

        if metric_type:
            query += " AND metric_type = ?"
            params.append(metric_type)
        if algorithm:
            query += " AND algorithm = ?"
            params.append(algorithm)

        query += """
            AND timestamp = (
                SELECT MAX(timestamp)
                FROM performance_metrics p2
                WHERE p2.metric_type = performance_metrics.metric_type
                AND p2.metric_name = performance_metrics.metric_name
                AND p2.algorithm = performance_metrics.algorithm
            )
            ORDER BY metric_type, metric_name
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            result = {}
            for row in rows:
                key = f"{row['metric_type']}_{row['metric_name']}"
                if row['algorithm']:
                    key += f"_{row['algorithm']}"
                result[key] = {
                    'value': row['metric_value'],
                    'unit': row['unit'],
                    'timestamp': row['timestamp']
                }
            
            return result

    def vacuum(self) -> None:
        """
        Optimize database by running VACUUM command.
        Should be run periodically during maintenance windows.
        """
        logger.info("Running VACUUM to optimize database...")
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
            logger.info("✓ Database optimized successfully")
        except Exception as e:
            logger.error(f"Failed to vacuum database: {e}")
            raise


# Example usage and testing
if __name__ == "__main__":
    # Initialize database manager
    db_manager = DBManager("data/sqlite/trading.db")

    # Create schema
    db_manager.create_schema()

    # Test state management
    db_manager.set_trading_state("test_key", "test_value")
    value = db_manager.get_trading_state("test_key")
    print(f"Trading state test: {value}")

    # Test connection
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as table_count FROM sqlite_master WHERE type='table'")
        result = cursor.fetchone()
        print(f"Total tables created: {result['table_count']}")

    # Get trading state values
    print("\nDefault trading state:")
    for key in ['trading_enabled', 'emergency_stop_active', 'system_status']:
        value = db_manager.get_trading_state(key)
        print(f"  {key}: {value}")

    logger.info("✓ Database manager ready for use")
