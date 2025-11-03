#!/usr/bin/env python3
"""
Database Logger for Backtrader Strategies
Epic 13: US-13.4 - Database Logging Integration

Provides database logging capabilities for Backtrader strategies:
- Order tracking (submissions, fills, cancellations)
- Position management (entries, exits, updates)
- Trade P&L logging
- Risk event logging
- Daily summaries

Integrates with:
- scripts/db_manager.py (database schema)
- strategies/base_strategy.py (base class)
- strategies/risk_manager.py (risk events)
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
import backtrader as bt

from scripts.db_manager import DBManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BacktraderDBLogger:
    """
    Database logger for Backtrader strategies.

    Logs all trading activity to SQLite database for:
    - Historical analysis
    - Performance monitoring
    - Risk tracking
    - Compliance/audit trail
    """

    def __init__(self, strategy, algorithm_name: str, db_path: str = 'data/sqlite/trading.db'):
        """
        Initialize database logger.

        Args:
            strategy: Backtrader strategy instance
            algorithm_name: Name/identifier for this strategy
            db_path: Path to SQLite database
        """
        self.strategy = strategy
        self.algorithm_name = algorithm_name
        self.db_manager = DBManager(db_path)

        # Ensure schema exists
        self.db_manager.create_schema()

        # Track logged orders to avoid duplicates
        self.logged_orders = set()

        # Daily tracking
        self.daily_start_value = None
        self.daily_trade_count = 0
        self.daily_winning_trades = 0
        self.daily_losing_trades = 0
        self.daily_commission = 0.0

        logger.info(f"BacktraderDBLogger initialized for {algorithm_name}")

    # ===================================================================
    # Order Logging
    # ===================================================================

    def log_order(self, order: bt.Order):
        """
        Log order to database.

        Args:
            order: Backtrader Order object
        """
        # Skip if already logged this order
        order_id = f"{self.algorithm_name}_{order.ref}"
        if order_id in self.logged_orders:
            return

        try:
            # Determine order status
            status_map = {
                bt.Order.Created: 'PENDING',
                bt.Order.Submitted: 'SUBMITTED',
                bt.Order.Accepted: 'SUBMITTED',
                bt.Order.Partial: 'PARTIAL',
                bt.Order.Completed: 'FILLED',
                bt.Order.Canceled: 'CANCELLED',
                bt.Order.Expired: 'EXPIRED',
                bt.Order.Margin: 'REJECTED',
                bt.Order.Rejected: 'REJECTED',
            }

            status = status_map.get(order.status, 'PENDING')

            # Get data feed info
            symbol = order.data._name if hasattr(order.data, '_name') else 'UNKNOWN'

            # Determine side
            side = 'BUY' if order.isbuy() else 'SELL'

            # Get order type
            order_type_map = {
                bt.Order.Market: 'MARKET',
                bt.Order.Limit: 'LIMIT',
                bt.Order.Stop: 'STOP',
                bt.Order.StopLimit: 'STOP_LIMIT',
            }
            order_type = order_type_map.get(order.exectype, 'MARKET')

            # Build order record
            order_data = {
                'order_id': order_id,
                'algorithm': self.algorithm_name,
                'symbol': symbol,
                'side': side,
                'quantity': int(abs(order.created.size)),
                'order_type': order_type,
                'status': status,
            }

            # Add execution details if order is filled
            if order.status == bt.Order.Completed:
                order_data['filled_quantity'] = int(abs(order.executed.size))
                order_data['average_fill_price'] = float(order.executed.price)
                order_data['commission'] = float(order.executed.comm)
                order_data['total_cost'] = float(order.executed.value + order.executed.comm)
                order_data['completed_at'] = datetime.now().isoformat()

            # Add timestamps
            if order.status == bt.Order.Submitted:
                order_data['submitted_at'] = datetime.now().isoformat()

            # Insert or update order
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Check if order exists
                cursor.execute("SELECT order_id FROM orders WHERE order_id = ?", (order_id,))
                exists = cursor.fetchone()

                if exists:
                    # Update existing order
                    update_fields = []
                    update_values = []

                    for key, value in order_data.items():
                        if key != 'order_id':
                            update_fields.append(f"{key} = ?")
                            update_values.append(value)

                    update_values.append(order_id)
                    update_query = f"UPDATE orders SET {', '.join(update_fields)} WHERE order_id = ?"

                    cursor.execute(update_query, update_values)
                else:
                    # Insert new order
                    columns = ', '.join(order_data.keys())
                    placeholders = ', '.join(['?' for _ in order_data])
                    insert_query = f"INSERT INTO orders ({columns}) VALUES ({placeholders})"

                    cursor.execute(insert_query, list(order_data.values()))

                conn.commit()

            # Mark as logged
            self.logged_orders.add(order_id)

            logger.debug(f"Order logged: {order_id} - {status}")

        except Exception as e:
            logger.error(f"Failed to log order: {e}", exc_info=True)

    # ===================================================================
    # Position Logging
    # ===================================================================

    def log_position_change(self, data, event_type: str, quantity: int,
                           price: float, pnl: Optional[float] = None,
                           order_id: Optional[str] = None):
        """
        Log position change to position_history table.

        Args:
            data: Backtrader data feed
            event_type: ENTRY, ADD, REDUCE, EXIT, UPDATE
            quantity: Position size change
            price: Price of transaction
            pnl: Realized P&L (for exits/reductions)
            order_id: Associated order ID
        """
        try:
            symbol = data._name if hasattr(data, '_name') else 'UNKNOWN'

            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO position_history
                    (symbol, algorithm, quantity, price, pnl, event_type, order_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol,
                    self.algorithm_name,
                    quantity,
                    price,
                    pnl,
                    event_type,
                    order_id
                ))
                conn.commit()

            logger.debug(f"Position change logged: {symbol} {event_type} {quantity} @ ${price:.2f}")

        except Exception as e:
            logger.error(f"Failed to log position change: {e}", exc_info=True)

    def update_position(self, data):
        """
        Update current position in positions table.

        Args:
            data: Backtrader data feed
        """
        try:
            symbol = data._name if hasattr(data, '_name') else 'UNKNOWN'
            position = self.strategy.getposition(data)

            if not position or position.size == 0:
                # Remove position from table if closed
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "DELETE FROM positions WHERE symbol = ? AND algorithm = ?",
                        (symbol, self.algorithm_name)
                    )
                    conn.commit()
                return

            # Calculate metrics
            current_price = data.close[0]
            cost_basis = abs(position.size * position.price)
            average_price = position.price
            current_value = abs(position.size * current_price)
            unrealized_pnl = (current_price - position.price) * position.size

            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Upsert position
                cursor.execute("""
                    INSERT INTO positions
                    (symbol, algorithm, quantity, cost_basis, average_price,
                     current_price, unrealized_pnl, entry_date, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol) DO UPDATE SET
                        quantity = excluded.quantity,
                        cost_basis = excluded.cost_basis,
                        average_price = excluded.average_price,
                        current_price = excluded.current_price,
                        unrealized_pnl = excluded.unrealized_pnl,
                        last_updated = excluded.last_updated
                """, (
                    symbol,
                    self.algorithm_name,
                    position.size,
                    cost_basis,
                    average_price,
                    current_price,
                    unrealized_pnl,
                    datetime.now().isoformat(),  # Would ideally track actual entry date
                    datetime.now().isoformat()
                ))
                conn.commit()

            logger.debug(f"Position updated: {symbol} size={position.size}")

        except Exception as e:
            logger.error(f"Failed to update position: {e}", exc_info=True)

    # ===================================================================
    # Trade Logging
    # ===================================================================

    def log_trade(self, trade: bt.Trade):
        """
        Log completed trade (called when position closes).

        Args:
            trade: Backtrader Trade object
        """
        if not trade.isclosed:
            return

        try:
            symbol = trade.data._name if hasattr(trade.data, '_name') else 'UNKNOWN'

            # Update daily counters
            self.daily_trade_count += 1
            if trade.pnlcomm > 0:
                self.daily_winning_trades += 1
            elif trade.pnlcomm < 0:
                self.daily_losing_trades += 1

            self.daily_commission += trade.commission

            # Log to position history as EXIT
            self.log_position_change(
                trade.data,
                'EXIT',
                trade.size,
                trade.price,
                pnl=trade.pnlcomm
            )

            logger.info(f"Trade logged: {symbol} P&L=${trade.pnlcomm:.2f} (Gross: ${trade.pnl:.2f})")

        except Exception as e:
            logger.error(f"Failed to log trade: {e}", exc_info=True)

    # ===================================================================
    # Risk Event Logging
    # ===================================================================

    def log_risk_event(self, event_type: str, severity: str, message: str,
                      symbol: Optional[str] = None, portfolio_value: Optional[float] = None,
                      position_value: Optional[float] = None, limit_value: Optional[float] = None,
                      breach_pct: Optional[float] = None, action_taken: Optional[str] = None):
        """
        Log risk management event.

        Args:
            event_type: Type of risk event (POSITION_LIMIT, DRAWDOWN, etc.)
            severity: INFO, WARNING, CRITICAL, EMERGENCY
            message: Event description
            symbol: Associated symbol (optional)
            portfolio_value: Portfolio value at time of event
            position_value: Position value (if applicable)
            limit_value: Limit that was breached
            breach_pct: Percentage of breach
            action_taken: Action taken in response
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO risk_events
                    (event_type, severity, symbol, algorithm, message,
                     portfolio_value, position_value, limit_value, breach_pct, action_taken)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_type,
                    severity,
                    symbol,
                    self.algorithm_name,
                    message,
                    portfolio_value,
                    position_value,
                    limit_value,
                    breach_pct,
                    action_taken
                ))
                conn.commit()

            logger.info(f"Risk event logged: [{severity}] {event_type} - {message}")

        except Exception as e:
            logger.error(f"Failed to log risk event: {e}", exc_info=True)

    # ===================================================================
    # Daily Summary
    # ===================================================================

    def init_daily_tracking(self):
        """Initialize daily tracking variables. Call at start of day."""
        self.daily_start_value = self.strategy.broker.getvalue()
        self.daily_trade_count = 0
        self.daily_winning_trades = 0
        self.daily_losing_trades = 0
        self.daily_commission = 0.0

        logger.info(f"Daily tracking initialized: ${self.daily_start_value:,.2f}")

    def save_daily_summary(self, target_date: Optional[str] = None):
        """
        Save daily summary to database.

        Args:
            target_date: Date string YYYY-MM-DD (uses today if None)
        """
        try:
            if target_date is None:
                target_date = datetime.now().date().isoformat()

            if self.daily_start_value is None:
                logger.warning("Daily tracking not initialized, skipping summary")
                return

            ending_equity = self.strategy.broker.getvalue()
            total_pnl = ending_equity - self.daily_start_value
            total_pnl_pct = (total_pnl / self.daily_start_value * 100) if self.daily_start_value > 0 else 0

            win_rate = (self.daily_winning_trades / self.daily_trade_count * 100) if self.daily_trade_count > 0 else 0

            # Get position count
            position_count = sum(1 for data in self.strategy.datas
                                if self.strategy.getposition(data).size != 0)

            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO daily_summaries
                    (date, algorithm, starting_equity, ending_equity, total_pnl, total_pnl_pct,
                     trades_count, winning_trades, losing_trades, win_rate,
                     total_commission, positions_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(date) DO UPDATE SET
                        ending_equity = excluded.ending_equity,
                        total_pnl = excluded.total_pnl,
                        total_pnl_pct = excluded.total_pnl_pct,
                        trades_count = excluded.trades_count,
                        winning_trades = excluded.winning_trades,
                        losing_trades = excluded.losing_trades,
                        win_rate = excluded.win_rate,
                        total_commission = excluded.total_commission,
                        positions_count = excluded.positions_count,
                        timestamp = CURRENT_TIMESTAMP
                """, (
                    target_date,
                    self.algorithm_name,
                    self.daily_start_value,
                    ending_equity,
                    total_pnl,
                    total_pnl_pct,
                    self.daily_trade_count,
                    self.daily_winning_trades,
                    self.daily_losing_trades,
                    win_rate,
                    self.daily_commission,
                    position_count
                ))
                conn.commit()

            logger.info(f"Daily summary saved: {target_date} P&L=${total_pnl:.2f} ({total_pnl_pct:+.2f}%)")

        except Exception as e:
            logger.error(f"Failed to save daily summary: {e}", exc_info=True)

    # ===================================================================
    # Integration Helpers
    # ===================================================================

    def on_order_notify(self, order):
        """
        Call this from strategy's notify_order() method.

        Args:
            order: Backtrader Order object
        """
        self.log_order(order)

        # Log position changes on fills
        if order.status == bt.Order.Completed:
            # Determine event type
            if order.isbuy():
                event_type = 'ENTRY' if self.strategy.get_position_size(order.data) == order.executed.size else 'ADD'
            else:
                event_type = 'EXIT' if self.strategy.get_position_size(order.data) == 0 else 'REDUCE'

            self.log_position_change(
                order.data,
                event_type,
                int(abs(order.executed.size)),
                order.executed.price,
                order_id=f"{self.algorithm_name}_{order.ref}"
            )

            # Update position record
            self.update_position(order.data)

    def on_trade_notify(self, trade):
        """
        Call this from strategy's notify_trade() method.

        Args:
            trade: Backtrader Trade object
        """
        self.log_trade(trade)

    def on_next(self):
        """
        Call this from strategy's next() method.

        Updates position values with latest prices.
        """
        # Update all positions with current prices
        for data in self.strategy.datas:
            position = self.strategy.getposition(data)
            if position and position.size != 0:
                self.update_position(data)


if __name__ == "__main__":
    print("BacktraderDBLogger - Ready for use")
    print("\nUsage:")
    print("  from strategies.db_logger import BacktraderDBLogger")
    print("  class MyStrategy(BaseStrategy):")
    print("      def __init__(self):")
    print("          super().__init__()")
    print("          self.db_logger = BacktraderDBLogger(self, 'MyStrategy')")
    print("      def notify_order(self, order):")
    print("          super().notify_order(order)")
    print("          self.db_logger.on_order_notify(order)")
    print("      def notify_trade(self, trade):")
    print("          super().notify_trade(trade)")
    print("          self.db_logger.on_trade_notify(trade)")
    print("      def next(self):")
    print("          super().next()")
    print("          self.db_logger.on_next()")
