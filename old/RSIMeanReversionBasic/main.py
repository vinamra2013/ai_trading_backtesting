# region imports
from AlgorithmImports import *
# endregion

class RSIMeanReversionBasic(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(1000)

        self.rsi_period = 14
        self.rsi_entry_threshold = 25
        self.rsi_exit_threshold = 50
        self.volume_period = 20
        self.volume_multiplier = 1.5
        self.profit_target_pct = 0.02
        self.stop_loss_pct = 0.01
        self.max_hold_days = 3
        self.risk_per_trade_pct = 0.01
        self.max_positions = 3

        self.rsi_indicators = {}
        self.volume_sma = {}
        self.entry_prices = {}
        self.entry_times = {}
        self.entry_bars = {}

        self.symbols = ["NVDA", "AVGO", "AMZN", "MSFT", "GOOGL", "QCOM", "UNH"]

        for ticker in self.symbols:
            symbol = self.add_equity(ticker, Resolution.Daily).symbol
            self.rsi_indicators[symbol] = self.rsi(symbol, self.rsi_period, MovingAverageType.Wilders, Resolution.Daily)
            self.volume_sma[symbol] = self.sma(symbol, self.volume_period, Resolution.Daily, Field.Volume)

        self.set_brokerage_model(BrokerageName.InteractiveBrokersBrokerage, AccountType.Margin)

        self.debug("=" * 60)
        self.debug("RSI Mean Reversion Strategy Initialized")
        self.debug(f"Symbols: {', '.join(self.symbols)}")
        self.debug(f"Entry: RSI < {self.rsi_entry_threshold}, Volume > {self.volume_multiplier}x avg")
        self.debug(f"Exit: RSI > {self.rsi_exit_threshold} OR +{self.profit_target_pct*100}% OR -{self.stop_loss_pct*100}% OR {self.max_hold_days} days")
        self.debug("=" * 60)

    def on_data(self, data):
        self.check_exits_inline(data)

        for symbol in self.rsi_indicators.keys():
            if symbol not in data or data[symbol] is None:
                continue
            if self.portfolio[symbol].invested:
                continue
            if self.get_open_position_count() >= self.max_positions:
                continue
            if self.check_entry_conditions(symbol, data):
                self.enter_position(symbol, data)

    def check_entry_conditions(self, symbol, data):
        rsi = self.rsi_indicators[symbol]
        if not rsi.is_ready or rsi.current.value >= self.rsi_entry_threshold:
            return False
        vol_sma = self.volume_sma[symbol]
        if not vol_sma.is_ready:
            return False
        current_volume = data[symbol].volume
        return current_volume >= (vol_sma.current.value * self.volume_multiplier)

    def enter_position(self, symbol, data):
        price = data[symbol].close
        portfolio_value = self.portfolio.total_portfolio_value
        risk_amount = portfolio_value * self.risk_per_trade_pct
        position_value = risk_amount / self.stop_loss_pct
        position_value = min(position_value, self.portfolio.cash * 0.95)
        shares = int(position_value / price)
        if shares < 1:
            return
        self.market_order(symbol, shares)
        self.entry_prices[symbol] = price
        self.entry_times[symbol] = self.time
        self.entry_bars[symbol] = 0
        rsi_value = self.rsi_indicators[symbol].current.value
        self.debug(f">>> BUY {symbol.value}: {shares} shares @ ${price:.2f}, RSI={rsi_value:.2f}")

    def check_exits_inline(self, data):
        for symbol in list(self.entry_prices.keys()):
            if not self.portfolio[symbol].invested:
                self.cleanup_position_tracking(symbol)
                continue
            if symbol not in data or data[symbol] is None:
                continue

            self.entry_bars[symbol] += 1
            entry_price = self.entry_prices[symbol]
            entry_time = self.entry_times[symbol]
            current_price = data[symbol].close
            bars_held = self.entry_bars[symbol]
            pnl_pct = (current_price - entry_price) / entry_price
            rsi = self.rsi_indicators[symbol]
            rsi_value = rsi.current.value if rsi.is_ready else 0

            if rsi.is_ready and rsi_value > self.rsi_exit_threshold:
                self.liquidate(symbol)
                self.debug(f"<<< EXIT {symbol.value}: RSI>{self.rsi_exit_threshold} (RSI={rsi_value:.2f}), P&L={pnl_pct*100:+.2f}%, Bars={bars_held}")
                self.cleanup_position_tracking(symbol)
                continue
            if pnl_pct >= self.profit_target_pct:
                self.liquidate(symbol)
                self.debug(f"<<< EXIT {symbol.value}: PROFIT TARGET (+{self.profit_target_pct*100}%), P&L={pnl_pct*100:+.2f}%, Bars={bars_held}")
                self.cleanup_position_tracking(symbol)
                continue
            if pnl_pct <= -self.stop_loss_pct:
                self.liquidate(symbol)
                self.debug(f"<<< EXIT {symbol.value}: STOP LOSS (-{self.stop_loss_pct*100}%), P&L={pnl_pct*100:+.2f}%, Bars={bars_held}")
                self.cleanup_position_tracking(symbol)
                continue
            days_held = (self.time - entry_time).days
            if days_held >= self.max_hold_days:
                self.liquidate(symbol)
                self.debug(f"<<< EXIT {symbol.value}: TIME STOP ({days_held} days), P&L={pnl_pct*100:+.2f}%, Bars={bars_held}")
                self.cleanup_position_tracking(symbol)
                continue

            if bars_held % 5 == 0:
                self.debug(f"--- HOLD {symbol.value}: P&L={pnl_pct*100:+.2f}%, RSI={rsi_value:.2f}, Bars={bars_held}, Days={days_held}")

    def cleanup_position_tracking(self, symbol):
        if symbol in self.entry_prices:
            del self.entry_prices[symbol]
        if symbol in self.entry_times:
            del self.entry_times[symbol]
        if symbol in self.entry_bars:
            del self.entry_bars[symbol]

    def get_open_position_count(self):
        count = 0
        for kvp in self.portfolio:
            if kvp.value.invested:
                count += 1
        return count

    def on_order_event(self, order_event):
        if order_event.status != OrderStatus.Filled:
            return
        order = self.transactions.get_order_by_id(order_event.order_id)
        if order.direction == OrderDirection.Buy:
            self.debug(f"*** ORDER FILLED: BUY {order.symbol.value} {order_event.fill_quantity} @ ${order_event.fill_price:.2f}")
        else:
            self.debug(f"*** ORDER FILLED: SELL {order.symbol.value} {order_event.fill_quantity} @ ${order_event.fill_price:.2f}")

    def on_end_of_algorithm(self):
        self.debug("=" * 60)
        self.debug("BACKTEST COMPLETE")
        self.debug(f"Final Portfolio Value: ${self.portfolio.total_portfolio_value:.2f}")
        self.debug(f"Net Profit: ${self.portfolio.total_portfolio_value - 1000:.2f}")
        self.debug(f"Open Positions at End: {self.get_open_position_count()}")
        self.debug("=" * 60)
