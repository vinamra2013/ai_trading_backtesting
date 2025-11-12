# region imports
from AlgorithmImports import *
# endregion

class VIXMarketTiming(QCAlgorithm):
    """
    VIX-based market timing strategy.

    Entry: Buy SPY when VIX spikes above threshold (fear = opportunity)
    Exit: Sell SPY when VIX normalizes below threshold (fear subsides)

    Uses VIX as signal source and SPY as trading vehicle.
    """

    def initialize(self):
        """Initialize algorithm parameters and securities."""
        # Optimization parameters - ALL use get_parameter()
        self.vix_entry_threshold = float(self.get_parameter("vix_entry_threshold", "25"))
        self.vix_exit_threshold = float(self.get_parameter("vix_exit_threshold", "18"))
        self.position_size_pct = float(self.get_parameter("position_size_pct", "0.75"))
        self.profit_target_pct = float(self.get_parameter("profit_target_pct", "0.02"))
        self.stop_loss_pct = float(self.get_parameter("stop_loss_pct", "0.015"))

        # Date range
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(1000)

        # Brokerage model
        self.set_brokerage_model(BrokerageName.INTERACTIVE_BROKERS_BROKERAGE, AccountType.MARGIN)

        # Add securities - SPY (trading) and VIX (signal)
        self.spy_symbol = self.add_equity("SPY", Resolution.DAILY).symbol
        self.vix_symbol = self.add_equity("VIX", Resolution.DAILY).symbol

        # Track entry price for profit/loss targets
        self.entry_price = None

        # Log parameters
        self.debug(f"VIX Market Timing Strategy Initialized")
        self.debug(f"Entry Threshold: {self.vix_entry_threshold}")
        self.debug(f"Exit Threshold: {self.vix_exit_threshold}")
        self.debug(f"Position Size: {self.position_size_pct * 100}%")
        self.debug(f"Profit Target: {self.profit_target_pct * 100}%")
        self.debug(f"Stop Loss: {self.stop_loss_pct * 100}%")

    def on_data(self, data: Slice):
        """
        Process incoming data and execute trading logic.

        Args:
            data: Market data slice containing price bars
        """
        # Data availability checks
        if not data.bars.contains_key(self.spy_symbol):
            return
        if not data.bars.contains_key(self.vix_symbol):
            return

        # Get current prices
        spy_price = data.bars[self.spy_symbol].close
        vix_value = data.bars[self.vix_symbol].close

        # Current position status
        is_invested = self.portfolio[self.spy_symbol].invested

        # Entry logic: VIX spike above threshold (fear = opportunity)
        if not is_invested:
            if vix_value > self.vix_entry_threshold:
                self.set_holdings(self.spy_symbol, self.position_size_pct)
                self.entry_price = spy_price
                self.debug(f"ENTRY: VIX spike {vix_value:.2f} > {self.vix_entry_threshold} | SPY @ ${spy_price:.2f} | Position: {self.position_size_pct * 100}%")

        # Exit logic: Multiple exit conditions
        else:
            exit_signal = False
            exit_reason = ""

            # Exit 1: VIX normalized (fear subsided)
            if vix_value < self.vix_exit_threshold:
                exit_signal = True
                exit_reason = f"VIX normalized {vix_value:.2f} < {self.vix_exit_threshold}"

            # Exit 2: Profit target hit
            elif self.entry_price is not None:
                pnl_pct = (spy_price - self.entry_price) / self.entry_price

                if pnl_pct >= self.profit_target_pct:
                    exit_signal = True
                    exit_reason = f"Profit target hit +{pnl_pct * 100:.2f}% >= {self.profit_target_pct * 100}%"

                # Exit 3: Stop loss hit
                elif pnl_pct <= -self.stop_loss_pct:
                    exit_signal = True
                    exit_reason = f"Stop loss hit {pnl_pct * 100:.2f}% <= -{self.stop_loss_pct * 100}%"

            # Execute exit
            if exit_signal:
                self.liquidate(self.spy_symbol)
                pnl = spy_price - self.entry_price if self.entry_price else 0
                self.debug(f"EXIT: {exit_reason} | SPY @ ${spy_price:.2f} | P&L: ${pnl:.2f}")
                self.entry_price = None

    def on_order_event(self, order_event: OrderEvent):
        """
        Log order execution events.

        Args:
            order_event: Order status update event
        """
        if order_event.status == OrderStatus.FILLED:
            order = self.transactions.get_order_by_id(order_event.order_id)
            self.debug(f"Order Filled: {order.symbol} | {order.direction} | Qty: {order.quantity} | Price: ${order_event.fill_price:.2f}")
