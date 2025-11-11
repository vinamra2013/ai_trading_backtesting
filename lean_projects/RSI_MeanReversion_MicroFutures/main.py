# region imports
from AlgorithmImports import *
# endregion

class RSIMeanReversionMicroFutures(QCAlgorithm):
    """
    SIMPLIFIED TEST VERSION - Verify futures data availability

    This version just tries to access ES futures data and log what happens.
    If this works, we can add RSI logic back.
    """

    def initialize(self):
        # Shorter test period first
        self.set_start_date(2023, 1, 1)
        self.set_end_date(2024, 1, 1)
        self.set_cash(1000)

        # Try regular E-mini S&P 500 (not Micro - might not be available)
        self.debug("=" * 60)
        self.debug("SIMPLIFIED TEST - Checking ES Futures Data Availability")
        self.debug("=" * 60)

        # Use continuous contract (not front month filter)
        self.es = self.add_future(Futures.Indices.SP_500_E_MINI, Resolution.Daily)
        self.es.set_filter(0, 180)  # Contracts expiring within 180 days

        self.current_contract = None
        self.trade_count = 0

    def on_securities_changed(self, changes):
        """Log when contracts are added/removed"""
        self.debug(f"Securities Changed Event | Added: {len(changes.added_securities)} | Removed: {len(changes.removed_securities)}")

        for security in changes.added_securities:
            self.debug(f"  -> Added: {security.symbol} | Type: {security.symbol.security_type}")

            if security.symbol.security_type == SecurityType.FUTURE:
                self.current_contract = security.symbol
                self.debug(f"  -> Selected contract: {self.current_contract}")

        for security in changes.removed_securities:
            self.debug(f"  -> Removed: {security.symbol}")

    def on_data(self, data: Slice):
        """Simple test: just try to access data and make one trade"""

        if self.current_contract is None:
            return

        if not data.contains_key(self.current_contract):
            return

        if not data.bars.contains_key(self.current_contract):
            return

        # Log data access once
        if self.trade_count == 0:
            bar = data.bars[self.current_contract]
            self.debug(f"SUCCESS! Got futures data: {self.current_contract} | Price: {bar.close:.2f} | Time: {self.time}")

            # Try to make a simple trade
            self.debug("Attempting to place market order for 1 contract...")
            self.market_order(self.current_contract, 1)
            self.trade_count += 1

    def on_order_event(self, order_event):
        """Log order results"""
        self.debug(f"Order Event | Symbol: {order_event.symbol} | Status: {order_event.status} | Filled: {order_event.fill_quantity} @ {order_event.fill_price:.2f}")

    def on_end_of_algorithm(self):
        self.debug("=" * 60)
        self.debug(f"Test Complete | Total trades attempted: {self.trade_count}")
        self.debug(f"Final equity: ${self.portfolio.total_portfolio_value:.2f}")
        self.debug("=" * 60)
