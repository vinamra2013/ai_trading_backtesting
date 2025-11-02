#!/usr/bin/env python3
"""
Database Logger for LEAN Algorithms

Provides thread-safe database logging for live trading algorithms with:
- Order execution tracking
- Position change monitoring
- Daily performance summaries
- Risk event logging
- Graceful error handling

Epic 5: Live Trading Engine
US-5.3: Position Management
US-5.4: Risk Management & Safety
"""

import logging
from datetime import datetime
from typing import Optional

# Import DBManager from scripts directory
# Note: In Docker container, this will be at /app/scripts/db_manager.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.db_manager import DBManager


# Setup logging
logger = logging.getLogger(__name__)


class DatabaseLogger:
    """
    Database logger for LEAN algorithms with graceful error handling.

    Features:
    - Integrates with DBManager for all database operations
    - Safe for LEAN's event-driven single-threaded model
    - Graceful degradation on database errors
    - Console fallback logging
    - Type-safe interfaces

    Example:
        db_logger = DatabaseLogger(
            db_path="/app/data/sqlite/trading.db",
            algorithm="MeanReversionStrategy"
        )

        # Log order fill
        db_logger.log_order_fill(
            order_id="ORD-123",
            symbol="SPY",
            side="BUY",
            quantity=100,
            fill_price=450.25,
            commission=0.50,
            timestamp=datetime.now()
        )

        # Close connection when done
        db_logger.close()
    """

    def __init__(self, db_path: str, algorithm: str):
        """
        Initialize database logger.

        Args:
            db_path: Path to SQLite database file (e.g., "/app/data/sqlite/trading.db")
            algorithm: Name of the algorithm (e.g., "MeanReversionStrategy")
        """
        self.algorithm = algorithm
        self.db_path = db_path
        self._db_manager: Optional[DBManager] = None
        self._connection_failed = False

        # Initialize database connection
        try:
            self._db_manager = DBManager(db_path)
            logger.info(f"DatabaseLogger initialized for algorithm: {algorithm}")
            logger.debug(f"Database path: {db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            logger.warning("Database logging disabled - using console fallback")
            self._connection_failed = True

    def _execute_with_fallback(self, operation: str, func, *args, **kwargs) -> bool:
        """
        Execute database operation with error handling and console fallback.

        Args:
            operation: Description of operation (for logging)
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            True if operation succeeded, False otherwise
        """
        if self._connection_failed or not self._db_manager:
            logger.debug(f"DB operation skipped (connection unavailable): {operation}")
            return False

        try:
            logger.debug(f"Executing DB operation: {operation}")
            func(*args, **kwargs)
            return True
        except Exception as e:
            logger.error(f"Database operation failed ({operation}): {e}")
            logger.debug(f"Operation details - Args: {args}, Kwargs: {kwargs}")
            # Don't set _connection_failed here - allow retry on next operation
            return False

    def log_order_fill(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: int,
        fill_price: float,
        commission: float,
        timestamp: datetime
    ) -> bool:
        """
        Log a filled order to the database.

        Args:
            order_id: Unique order identifier
            symbol: Ticker symbol (e.g., "SPY")
            side: "BUY" or "SELL"
            quantity: Number of shares filled
            fill_price: Average fill price
            commission: Commission paid
            timestamp: Order fill timestamp

        Returns:
            True if logged successfully, False otherwise
        """
        def _insert_order():
            with self._db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO orders (
                        order_id, algorithm, symbol, side, quantity, order_type,
                        status, filled_quantity, average_fill_price, commission,
                        total_cost, created_at, submitted_at, updated_at, completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(order_id) DO UPDATE SET
                        status = excluded.status,
                        filled_quantity = excluded.filled_quantity,
                        average_fill_price = excluded.average_fill_price,
                        commission = excluded.commission,
                        total_cost = excluded.total_cost,
                        updated_at = excluded.updated_at,
                        completed_at = excluded.completed_at
                    """,
                    (
                        order_id,
                        self.algorithm,
                        symbol,
                        side.upper(),
                        quantity,
                        "MARKET",  # Default to MARKET for filled orders
                        "FILLED",
                        quantity,
                        fill_price,
                        commission,
                        (quantity * fill_price) + commission,
                        timestamp.isoformat(),
                        timestamp.isoformat(),
                        timestamp.isoformat(),
                        timestamp.isoformat()
                    )
                )
                conn.commit()

        success = self._execute_with_fallback(
            f"log_order_fill({order_id}, {symbol}, {side}, {quantity}@{fill_price})",
            _insert_order
        )

        # Console fallback
        if not success:
            logger.info(
                f"ORDER_FILL: {order_id} | {symbol} | {side} | "
                f"{quantity}@${fill_price:.2f} | comm=${commission:.2f}"
            )

        return success

    def log_position_change(
        self,
        symbol: str,
        quantity: int,
        price: float,
        event_type: str
    ) -> bool:
        """
        Log a position change to the position_history table.

        Args:
            symbol: Ticker symbol
            quantity: New position quantity (positive for long, negative for short)
            price: Current price
            event_type: One of: "ENTRY", "ADD", "REDUCE", "EXIT", "UPDATE"

        Returns:
            True if logged successfully, False otherwise
        """
        def _insert_position_history():
            with self._db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO position_history (
                        symbol, algorithm, quantity, price, timestamp, event_type
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        symbol,
                        self.algorithm,
                        quantity,
                        price,
                        datetime.now().isoformat(),
                        event_type.upper()
                    )
                )
                conn.commit()

        success = self._execute_with_fallback(
            f"log_position_change({symbol}, {quantity}, {event_type})",
            _insert_position_history
        )

        # Console fallback
        if not success:
            logger.info(
                f"POSITION_CHANGE: {symbol} | {event_type} | "
                f"qty={quantity} | price=${price:.2f}"
            )

        return success

    def log_daily_summary(
        self,
        date: str,
        starting_equity: float,
        ending_equity: float,
        realized_pnl: float,
        unrealized_pnl: float,
        num_trades: int
    ) -> bool:
        """
        Log daily performance summary.

        Args:
            date: Date in YYYY-MM-DD format
            starting_equity: Starting equity for the day
            ending_equity: Ending equity for the day
            realized_pnl: Realized P&L for the day
            unrealized_pnl: Unrealized P&L for the day
            num_trades: Number of trades executed

        Returns:
            True if logged successfully, False otherwise
        """
        def _insert_daily_summary():
            total_pnl = realized_pnl + unrealized_pnl
            total_pnl_pct = (total_pnl / starting_equity * 100.0) if starting_equity > 0 else 0.0

            with self._db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO daily_summaries (
                        date, algorithm, starting_equity, ending_equity,
                        realized_pnl, unrealized_pnl, total_pnl, total_pnl_pct,
                        trades_count, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(date) DO UPDATE SET
                        ending_equity = excluded.ending_equity,
                        realized_pnl = excluded.realized_pnl,
                        unrealized_pnl = excluded.unrealized_pnl,
                        total_pnl = excluded.total_pnl,
                        total_pnl_pct = excluded.total_pnl_pct,
                        trades_count = excluded.trades_count,
                        timestamp = excluded.timestamp
                    """,
                    (
                        date,
                        self.algorithm,
                        starting_equity,
                        ending_equity,
                        realized_pnl,
                        unrealized_pnl,
                        total_pnl,
                        total_pnl_pct,
                        num_trades,
                        datetime.now().isoformat()
                    )
                )
                conn.commit()

        success = self._execute_with_fallback(
            f"log_daily_summary({date}, pnl={realized_pnl + unrealized_pnl})",
            _insert_daily_summary
        )

        # Console fallback
        if not success:
            logger.info(
                f"DAILY_SUMMARY: {date} | "
                f"start=${starting_equity:.2f} | end=${ending_equity:.2f} | "
                f"realized_pnl=${realized_pnl:.2f} | unrealized_pnl=${unrealized_pnl:.2f} | "
                f"trades={num_trades}"
            )

        return success

    def log_risk_event(
        self,
        event_type: str,
        severity: str,
        message: str,
        symbol: Optional[str] = None,
        portfolio_value: Optional[float] = None
    ) -> bool:
        """
        Log a risk management event.

        Args:
            event_type: One of: "POSITION_LIMIT", "PORTFOLIO_LIMIT", "DRAWDOWN",
                       "VOLATILITY", "CORRELATION", "MARGIN_CALL", "LEVERAGE",
                       "CONCENTRATION", "ORDER_REJECTION", "CONNECTION_LOSS", "OTHER"
            severity: One of: "INFO", "WARNING", "CRITICAL", "EMERGENCY"
            message: Human-readable description of the event
            symbol: Optional ticker symbol related to event
            portfolio_value: Optional portfolio value at time of event

        Returns:
            True if logged successfully, False otherwise
        """
        def _insert_risk_event():
            with self._db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO risk_events (
                        event_type, severity, symbol, algorithm, message,
                        timestamp, portfolio_value
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_type.upper(),
                        severity.upper(),
                        symbol,
                        self.algorithm,
                        message,
                        datetime.now().isoformat(),
                        portfolio_value
                    )
                )
                conn.commit()

        success = self._execute_with_fallback(
            f"log_risk_event({event_type}, {severity})",
            _insert_risk_event
        )

        # Console fallback - always log risk events to console for visibility
        log_func = logger.info if severity == "INFO" else logger.warning
        if severity in ["CRITICAL", "EMERGENCY"]:
            log_func = logger.error

        log_func(
            f"RISK_EVENT: [{severity}] {event_type} | {message}" +
            (f" | symbol={symbol}" if symbol else "") +
            (f" | portfolio=${portfolio_value:.2f}" if portfolio_value else "")
        )

        return success

    def close(self) -> None:
        """
        Close database connection and cleanup resources.

        Note: DBManager uses context managers for connections,
        so this is primarily for cleanup and logging.
        """
        if self._db_manager and not self._connection_failed:
            logger.info(f"Closing DatabaseLogger for algorithm: {self.algorithm}")
            self._db_manager = None
        else:
            logger.debug("DatabaseLogger close called (no active connection)")


# Example usage
if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize logger
    db_logger = DatabaseLogger(
        db_path="data/sqlite/trading.db",
        algorithm="TestStrategy"
    )

    # Test order fill logging
    db_logger.log_order_fill(
        order_id="TEST-001",
        symbol="SPY",
        side="BUY",
        quantity=100,
        fill_price=450.25,
        commission=0.50,
        timestamp=datetime.now()
    )

    # Test position change logging
    db_logger.log_position_change(
        symbol="SPY",
        quantity=100,
        price=450.25,
        event_type="ENTRY"
    )

    # Test daily summary logging
    db_logger.log_daily_summary(
        date="2025-11-01",
        starting_equity=100000.0,
        ending_equity=100500.0,
        realized_pnl=250.0,
        unrealized_pnl=250.0,
        num_trades=2
    )

    # Test risk event logging
    db_logger.log_risk_event(
        event_type="POSITION_LIMIT",
        severity="WARNING",
        message="Position size approaching limit",
        symbol="SPY",
        portfolio_value=100500.0
    )

    # Close logger
    db_logger.close()

    print("\n✓ DatabaseLogger test completed successfully")
