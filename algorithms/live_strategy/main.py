# region imports
from AlgorithmImports import *
import sys
import os

# Add project root to path for imports
sys.path.append('/app')

from scripts.db_manager import DBManager
from algorithms.live_strategy.risk_manager import RiskManager
from algorithms.live_strategy.db_logger import DatabaseLogger
# endregion


class LiveTradingStrategy(QCAlgorithm):
    """
    Production-ready live trading strategy with risk management.

    Epic 5: Live Trading Engine (LEAN-Native Implementation)
    Epic 6: Risk Management System (Library Integration)

    Features:
    - Real-time risk checks before every order
    - Position size, loss limit, and concentration limit enforcement
    - Automated end-of-day liquidation at 3:55 PM ET
    - Comprehensive database logging for monitoring
    - Emergency stop capability via external script
    """

    def Initialize(self):
        """
        Initialize the algorithm with securities, risk management, and logging.

        US-5.1: Live Algorithm Execution
        """
        # ============================================================
        # Basic Setup
        # ============================================================
        self.SetStartDate(2024, 1, 1)
        self.SetCash(100000)  # Starting capital

        # Set brokerage model for realistic simulation
        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, AccountType.Margin)

        # ============================================================
        # Initialize Risk Manager (Epic 6)
        # ============================================================
        try:
            self.risk = RiskManager(
                algorithm=self,
                config_path="/app/config/risk_config.yaml"
            )
            self.Log("✓ Risk Manager initialized")
        except Exception as e:
            self.Error(f"Failed to initialize Risk Manager: {e}")
            self.Quit(f"Cannot proceed without risk management: {e}")
            return

        # ============================================================
        # Initialize Database Logger
        # ============================================================
        try:
            self.db = DatabaseLogger(
                db_path="/app/data/sqlite/trades.db",
                algorithm="LiveTradingStrategy"
            )
            self.Log("✓ Database Logger initialized")
        except Exception as e:
            self.Error(f"Failed to initialize Database Logger: {e}")
            # Continue without DB logging (log to LEAN logs instead)
            self.db = None

        # ============================================================
        # Add Securities
        # ============================================================
        # TODO: Add your securities here
        # Example: self.spy = self.AddEquity("SPY", Resolution.Minute)
        self.spy = self.AddEquity("SPY", Resolution.Minute)
        self.spy.SetDataNormalizationMode(DataNormalizationMode.Raw)

        # ============================================================
        # Schedule End-of-Day Procedures (US-5.4)
        # ============================================================
        # Liquidate all positions at 3:55 PM ET (5 minutes before close)
        self.Schedule.On(
            self.DateRules.EveryDay(self.spy.Symbol),
            self.TimeRules.At(15, 55),  # 3:55 PM Eastern
            self.LiquidateBeforeClose
        )

        # Log daily summary at market close
        self.Schedule.On(
            self.DateRules.EveryDay(self.spy.Symbol),
            self.TimeRules.BeforeMarketClose(self.spy.Symbol, 0),
            self.LogDailySummary
        )

        # ============================================================
        # Trading State
        # ============================================================
        self.trading_enabled = True  # Can be disabled by risk manager
        self.daily_starting_equity = self.Portfolio.TotalPortfolioValue

        self.Log(f"✓ Algorithm initialized. Starting equity: ${self.daily_starting_equity:,.2f}")

    def OnData(self, data: Slice):
        """
        Process incoming market data and execute trading logic.

        US-5.2: Order Management (via LEAN)
        US-5.3: Position Tracking (via LEAN Portfolio)
        US-6.2: Loss Limit Monitoring

        Args:
            data: Market data slice containing prices, trades, quotes, etc.
        """
        # ============================================================
        # Pre-Flight Checks
        # ============================================================

        # Check if trading is halted (by risk manager or emergency)
        if not self.trading_enabled:
            return

        # Track starting equity for daily loss calculations
        if self.Time.hour == 9 and self.Time.minute == 30:
            self.daily_starting_equity = self.Portfolio.TotalPortfolioValue

        # ============================================================
        # Risk Check: Daily Loss Limit (US-6.2)
        # ============================================================
        if self.risk.check_loss_limit_breached():
            self.Log("⚠️ DAILY LOSS LIMIT BREACHED - Initiating emergency liquidation")
            self.Liquidate()  # Close all positions immediately
            self.trading_enabled = False

            if self.db:
                self.db.log_risk_event(
                    event_type="LOSS_LIMIT_BREACH",
                    severity="CRITICAL",
                    message=f"Daily loss limit exceeded. Liquidated all positions.",
                    portfolio_value=self.Portfolio.TotalPortfolioValue
                )
            return

        # ============================================================
        # Trading Logic (TODO: Implement your strategy)
        # ============================================================

        # Example: Simple momentum strategy (replace with your logic)
        if not self.Portfolio.Invested:
            # Check if we have data
            if not data.ContainsKey(self.spy.Symbol):
                return

            # Risk Check: Can we open this position? (US-6.1, US-6.3)
            quantity = 100  # TODO: Calculate optimal position size
            price = data[self.spy.Symbol].Close

            if self.risk.can_open_position(self.spy.Symbol, quantity, price):
                # US-5.2: Place order via LEAN
                ticket = self.MarketOrder(self.spy.Symbol, quantity)
                self.Log(f"→ BUY {quantity} shares of {self.spy.Symbol} @ ${price:.2f}")
            else:
                self.Debug(f"Risk check failed for {self.spy.Symbol} position")

        else:
            # TODO: Implement exit logic
            # Example: Exit on simple condition
            if data.ContainsKey(self.spy.Symbol):
                price = data[self.spy.Symbol].Close
                holdings = self.Portfolio[self.spy.Symbol]

                # Simple profit target or stop loss
                pnl_pct = (price - holdings.AveragePrice) / holdings.AveragePrice

                if pnl_pct > 0.02:  # 2% profit target
                    self.Liquidate(self.spy.Symbol)
                    self.Log(f"← SELL {holdings.Quantity} shares (Profit Target)")
                elif pnl_pct < -0.01:  # 1% stop loss
                    self.Liquidate(self.spy.Symbol)
                    self.Log(f"← SELL {holdings.Quantity} shares (Stop Loss)")

    def OnOrderEvent(self, orderEvent: OrderEvent):
        """
        Handle order events (fills, cancellations, rejections).

        US-5.2: Order Management - Track order status

        Args:
            orderEvent: Event containing order status and fill information
        """
        order = self.Transactions.GetOrderById(orderEvent.OrderId)

        # Log order status changes
        if orderEvent.Status == OrderStatus.Filled:
            self.Log(f"✓ Order {orderEvent.OrderId} FILLED: {orderEvent.FillQuantity} @ ${orderEvent.FillPrice:.2f}")

            # Log to database
            if self.db:
                self.db.log_order_fill(
                    order_id=str(orderEvent.OrderId),
                    symbol=orderEvent.Symbol.Value,
                    side="BUY" if orderEvent.FillQuantity > 0 else "SELL",
                    quantity=abs(orderEvent.FillQuantity),
                    fill_price=orderEvent.FillPrice,
                    commission=orderEvent.OrderFee.Value.Amount,
                    timestamp=self.Time
                )

        elif orderEvent.Status == OrderStatus.PartiallyFilled:
            self.Log(f"⊙ Order {orderEvent.OrderId} PARTIAL: {orderEvent.FillQuantity} @ ${orderEvent.FillPrice:.2f}")

        elif orderEvent.Status == OrderStatus.Canceled:
            self.Log(f"✗ Order {orderEvent.OrderId} CANCELED")

        elif orderEvent.Status == OrderStatus.Invalid:
            self.Error(f"✗ Order {orderEvent.OrderId} INVALID: {order.Tag}")

            if self.db:
                self.db.log_risk_event(
                    event_type="ORDER_REJECTED",
                    severity="WARNING",
                    symbol=orderEvent.Symbol.Value,
                    message=f"Order {orderEvent.OrderId} rejected: {order.Tag}"
                )

    def OnEndOfDay(self, symbol: Symbol):
        """
        Called at the end of each trading day.

        US-5.4: Log daily summary

        Args:
            symbol: The symbol that triggered the end-of-day event
        """
        # Only process once per day (for SPY)
        if symbol != self.spy.Symbol:
            return

        # Calculate daily P&L
        ending_equity = self.Portfolio.TotalPortfolioValue
        daily_pnl = ending_equity - self.daily_starting_equity
        daily_pnl_pct = (daily_pnl / self.daily_starting_equity) * 100 if self.daily_starting_equity > 0 else 0

        self.Log(f"═══ End of Day Summary ═══")
        self.Log(f"Starting Equity: ${self.daily_starting_equity:,.2f}")
        self.Log(f"Ending Equity: ${ending_equity:,.2f}")
        self.Log(f"Daily P&L: ${daily_pnl:,.2f} ({daily_pnl_pct:+.2f}%)")
        self.Log(f"Open Positions: {len([x for x in self.Portfolio.Values if x.Invested])}")

        # Log to database
        if self.db:
            self.db.log_daily_summary(
                date=self.Time.date(),
                starting_equity=self.daily_starting_equity,
                ending_equity=ending_equity,
                realized_pnl=self.Portfolio.TotalProfit,
                unrealized_pnl=self.Portfolio.TotalUnrealizedProfit,
                num_trades=self.Transactions.GetOrders().Count
            )

    def LiquidateBeforeClose(self):
        """
        End-of-day liquidation procedure.

        US-5.4: End-of-Day Procedures - Liquidate at 3:55 PM ET

        Closes all positions 5 minutes before market close to ensure
        all orders are filled before 4:00 PM.
        """
        if self.Portfolio.Invested:
            num_positions = len([x for x in self.Portfolio.Values if x.Invested])
            self.Log(f"⏰ EOD Liquidation: Closing {num_positions} position(s)")

            # Liquidate all positions with market orders
            self.Liquidate()

            if self.db:
                self.db.log_risk_event(
                    event_type="EOD_LIQUIDATION",
                    severity="INFO",
                    message=f"End-of-day liquidation: {num_positions} positions closed",
                    portfolio_value=self.Portfolio.TotalPortfolioValue
                )
        else:
            self.Debug("EOD: No positions to liquidate")

    def LogDailySummary(self):
        """
        Log comprehensive daily summary at market close.

        Called via scheduled event at market close.
        """
        # This is called by OnEndOfDay, but we keep the schedule
        # for explicit timing control
        pass

    def OnEndOfAlgorithm(self):
        """
        Called when algorithm terminates (end of backtest or live trading stop).

        Final cleanup and logging.
        """
        self.Log("═══ Algorithm Terminating ═══")
        self.Log(f"Final Portfolio Value: ${self.Portfolio.TotalPortfolioValue:,.2f}")
        self.Log(f"Total Profit: ${self.Portfolio.TotalProfit:,.2f}")
        self.Log(f"Total Unrealized: ${self.Portfolio.TotalUnrealizedProfit:,.2f}")

        # Close database connection
        if self.db:
            self.db.close()
