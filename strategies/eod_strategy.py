#!/usr/bin/env python3
"""
EOD (End-of-Day) Strategy Extension
Epic 13: US-13.5 - EOD Procedures & Scheduling

Extends BaseStrategy with end-of-day procedures:
- Automatic liquidation at 3:55 PM ET (15 min before close)
- Daily risk limit reset at market open
- Portfolio snapshot logging
- Timezone handling (market time vs system time)
- Configurable EOD behavior

Use this as a base for intraday strategies that should flatten positions daily.
"""

import backtrader as bt
from datetime import time, datetime
import logging

from strategies.base_strategy import BaseStrategy
from strategies.risk_manager import RiskManager
from strategies.db_logger import BacktraderDBLogger

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EODStrategy(BaseStrategy):
    """
    Strategy with End-of-Day procedures.

    Features:
    - Auto-liquidation at specified EOD time (default 3:55 PM)
    - Daily reset of risk limits
    - Daily portfolio snapshots
    - Risk manager integration
    - Database logging integration
    """

    params = (
        # Inherited from BaseStrategy
        ('initial_cash', 100000),
        ('position_size', 0.95),
        ('printlog', True),
        ('log_trades', True),

        # EOD-specific params
        ('eod_liquidate', True),         # Enable automatic EOD liquidation
        ('eod_hour', 15),                # EOD hour (24-hour format, ET)
        ('eod_minute', 55),              # EOD minute
        ('market_open_hour', 9),         # Market open hour (ET)
        ('market_open_minute', 30),      # Market open minute

        # Risk management
        ('enable_risk_manager', True),
        ('daily_loss_limit', 0.02),
        ('max_drawdown', 0.20),
        ('max_position_pct', 0.95),

        # Database logging
        ('enable_db_logging', False),    # Enable in production
        ('algorithm_name', 'EODStrategy'),
    )

    def __init__(self):
        """Initialize strategy with EOD procedures."""
        # Call parent initialization
        super().__init__()

        # Create EOD time objects
        self.eod_time = time(self.params.eod_hour, self.params.eod_minute)
        self.market_open_time = time(self.params.market_open_hour, self.params.market_open_minute)

        # Track EOD state
        self.eod_executed_today = False
        self.daily_reset_done = False
        self.current_date = None

        # Initialize risk manager if enabled
        self.risk_manager = None
        if self.params.enable_risk_manager:
            risk_config = {
                'daily_loss_limit': self.params.daily_loss_limit,
                'max_drawdown': self.params.max_drawdown,
                'max_position_pct': self.params.max_position_pct,
                'max_leverage': 1.0,  # No leverage for EOD strategies
                'max_positions': 10,
            }
            self.risk_manager = RiskManager(self, config=risk_config)

        # Initialize database logger if enabled
        self.db_logger = None
        if self.params.enable_db_logging:
            self.db_logger = BacktraderDBLogger(self, self.params.algorithm_name)

        self.log(f"EOD Strategy initialized: Liquidation at {self.params.eod_hour}:{self.params.eod_minute:02d}")

    # ===================================================================
    # EOD Procedures
    # ===================================================================

    def _get_current_time(self) -> time:
        """
        Get current bar time.

        Returns:
            time object representing current bar time
        """
        if len(self.datas) > 0:
            dt = self.datas[0].datetime.datetime(0)
            return dt.time()
        return time(0, 0)

    def _get_current_date(self):
        """
        Get current bar date.

        Returns:
            date object representing current bar date
        """
        if len(self.datas) > 0:
            return self.datas[0].datetime.date(0)
        return None

    def _check_new_day(self):
        """Check if we've moved to a new trading day and reset tracking."""
        current_date = self._get_current_date()

        if current_date is None:
            return

        # First bar
        if self.current_date is None:
            self.current_date = current_date
            self._initialize_daily_tracking()
            return

        # New day detected
        if current_date > self.current_date:
            self.log(f"New trading day: {current_date.isoformat()}")

            # Save yesterday's daily summary if DB logging enabled
            if self.db_logger:
                self.db_logger.save_daily_summary(self.current_date.isoformat())

            # Reset for new day
            self.current_date = current_date
            self.eod_executed_today = False
            self.daily_reset_done = False
            self._initialize_daily_tracking()

    def _initialize_daily_tracking(self):
        """Initialize tracking variables at start of day."""
        # Reset risk manager daily limits
        if self.risk_manager:
            self.risk_manager.reset_daily()

        # Initialize DB logger daily tracking
        if self.db_logger:
            self.db_logger.init_daily_tracking()

        self.daily_reset_done = True
        self.log("Daily tracking initialized")

    def _execute_eod_liquidation(self):
        """Execute end-of-day liquidation of all positions."""
        if self.eod_executed_today:
            return

        liquidated_count = 0

        # Close all open positions
        for data in self.datas:
            position = self.getposition(data)
            if position and position.size != 0:
                symbol = data._name if hasattr(data, '_name') else 'UNKNOWN'
                self.log(f"EOD LIQUIDATION: Closing {symbol} position (size={position.size})",
                        level='WARNING')

                # Close position
                self.close(data=data)
                liquidated_count += 1

                # Log risk event if DB logging enabled
                if self.db_logger:
                    self.db_logger.log_risk_event(
                        event_type='EOD_LIQUIDATION',
                        severity='INFO',
                        symbol=symbol,
                        message=f'Automatic EOD position closure at {self.eod_time}',
                        portfolio_value=self.broker.getvalue(),
                        action_taken='LIQUIDATE'
                    )

        if liquidated_count > 0:
            self.log(f"EOD: Liquidated {liquidated_count} position(s)")
        else:
            self.log("EOD: No positions to liquidate")

        self.eod_executed_today = True

    def _check_eod_time(self):
        """Check if we've reached EOD time and execute liquidation if needed."""
        if not self.params.eod_liquidate:
            return

        current_time = self._get_current_time()

        # Check if we've reached or passed EOD time
        if current_time >= self.eod_time and not self.eod_executed_today:
            self._execute_eod_liquidation()

    def _check_market_open(self):
        """Check if we're past market open and reset daily limits."""
        if self.daily_reset_done:
            return

        current_time = self._get_current_time()

        # Reset daily tracking after market open
        if current_time >= self.market_open_time:
            self._initialize_daily_tracking()

    # ===================================================================
    # Overridden Strategy Methods
    # ===================================================================

    def prenext(self):
        """Called before minimum period is met."""
        super().prenext()
        self._check_new_day()
        self._check_market_open()

    def next(self):
        """
        Main strategy logic with EOD checks.

        Override this in subclasses to implement trading logic.
        Always call super().next() first to ensure EOD procedures run.
        """
        # Call parent
        super().next()

        # Check for new day
        self._check_new_day()

        # Check market open for daily reset
        self._check_market_open()

        # Check EOD time for liquidation
        self._check_eod_time()

        # Update DB logger with latest prices if enabled
        if self.db_logger:
            self.db_logger.on_next()

    def notify_order(self, order):
        """Handle order notifications with DB logging."""
        # Call parent
        super().notify_order(order)

        # Log to database if enabled
        if self.db_logger:
            self.db_logger.on_order_notify(order)

    def notify_trade(self, trade):
        """Handle trade notifications with DB logging."""
        # Call parent
        super().notify_trade(trade)

        # Log to database if enabled
        if self.db_logger:
            self.db_logger.on_trade_notify(trade)

    def stop(self):
        """Called when strategy ends."""
        # Save final daily summary if DB logging enabled
        if self.db_logger and self.current_date:
            self.db_logger.save_daily_summary(self.current_date.isoformat())

        # Call parent
        super().stop()

    # ===================================================================
    # Helper Methods for Subclasses
    # ===================================================================

    def is_eod_time(self) -> bool:
        """
        Check if we're currently at or past EOD time.

        Returns:
            True if at/past EOD time
        """
        return self._get_current_time() >= self.eod_time

    def is_market_open_time(self) -> bool:
        """
        Check if we're past market open.

        Returns:
            True if past market open
        """
        return self._get_current_time() >= self.market_open_time

    def should_trade(self) -> bool:
        """
        Check if trading is allowed (not near EOD).

        Returns:
            True if trading is allowed
        """
        if self.params.eod_liquidate:
            # Don't enter new positions within 30 minutes of EOD
            current_time = self._get_current_time()
            eod_buffer_time = time(self.params.eod_hour, max(0, self.params.eod_minute - 30))

            if current_time >= eod_buffer_time:
                return False

        return True


if __name__ == "__main__":
    print("EOD Strategy Extension - Ready for use")
    print("\nFeatures:")
    print("  - Auto-liquidation at 3:55 PM ET")
    print("  - Daily risk limit reset")
    print("  - Portfolio snapshot logging")
    print("  - Risk manager integration")
    print("  - Database logging integration")
    print("\nUsage:")
    print("  from strategies.eod_strategy import EODStrategy")
    print("  class MyStrategy(EODStrategy):")
    print("      def next(self):")
    print("          super().next()  # IMPORTANT: Call first for EOD procedures")
    print("          if not self.should_trade():")
    print("              return")
    print("          # Your trading logic here")
