# region imports
from AlgorithmImports import *
# endregion

class BollingerBandMeanReversionETFs(QCAlgorithm):
    """
    Strategy #2: Bollinger Band Mean Reversion - ETFs

    Entry: Price touches lower Bollinger Band (oversold)
    Exit: Price crosses middle band OR profit target (2%)
    Stop Loss: 1% from entry
    Universe: High-liquidity ETFs (SPY, QQQ, IWM, sectors)
    Resolution: Daily
    Target: 100+ trades, 50%+ win rate, 1%+ avg win, Sharpe >1.0
    """

    def initialize(self):
        # Backtest period
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(1000)

        # ETF universe - high liquidity
        self.etf_symbols = [
            "SPY",   # S&P 500
            "QQQ",   # Nasdaq 100
            "IWM",   # Russell 2000
            "XLF",   # Financials
            "XLE",   # Energy
            "XLK",   # Technology
            "XLV",   # Healthcare
            "XLI"    # Industrials
        ]

        # Add securities and create indicators
        self.bollinger_bands = {}
        self.symbols = {}

        for ticker in self.etf_symbols:
            symbol = self.add_equity(ticker, Resolution.DAILY).symbol
            self.symbols[ticker] = symbol

            # Bollinger Bands: 20-period, 2 std devs, simple MA
            self.bollinger_bands[ticker] = self.bb(symbol, 20, 2, MovingAverageType.SIMPLE, Resolution.DAILY)

        # Risk management
        self.profit_target_pct = 0.02  # 2% profit target
        self.stop_loss_pct = 0.01      # 1% stop loss
        self.max_risk_per_trade = 10   # $10 max risk (1% of capital)

        # Track entry prices
        self.entry_prices = {}

        self.debug("Strategy #2: Bollinger Band Mean Reversion - ETFs Initialized")
        self.debug(f"Universe: {len(self.etf_symbols)} ETFs")

    def on_data(self, data: Slice):
        # Check each ETF for signals
        for ticker in self.etf_symbols:
            symbol = self.symbols[ticker]
            bb = self.bollinger_bands[ticker]

            # Skip if indicator not ready or no data
            if not bb.is_ready:
                continue

            if not data.bars.contains_key(symbol):
                continue

            price = data.bars[symbol].close
            lower_band = bb.lower_band.current.value
            middle_band = bb.middle_band.current.value

            # Entry logic: Price touches lower band (oversold)
            if not self.portfolio[symbol].invested:
                if price <= lower_band * 1.01:  # Within 1% of lower band
                    # Calculate position size based on risk
                    stop_price = price * (1 - self.stop_loss_pct)
                    risk_per_share = price - stop_price

                    if risk_per_share > 0:
                        shares = int(self.max_risk_per_trade / risk_per_share)

                        if shares > 0:
                            # Limit position size to available cash
                            max_shares = int(self.portfolio.cash / price)
                            shares = min(shares, max_shares)

                            if shares > 0:
                                self.market_order(symbol, shares)
                                self.entry_prices[ticker] = price
                                self.debug(f"BUY {ticker} @ ${price:.2f} | Lower: ${lower_band:.2f} | Shares: {shares}")

            # Exit logic: Mean reversion to middle band OR profit target OR stop loss
            elif self.portfolio[symbol].invested:
                entry_price = self.entry_prices.get(ticker, price)
                profit_pct = (price - entry_price) / entry_price

                # Exit conditions
                should_exit = False
                exit_reason = ""

                # 1. Price crosses middle band (mean reversion)
                if price >= middle_band:
                    should_exit = True
                    exit_reason = "Mean Reversion"

                # 2. Profit target reached
                elif profit_pct >= self.profit_target_pct:
                    should_exit = True
                    exit_reason = f"Profit Target (+{profit_pct*100:.1f}%)"

                # 3. Stop loss hit
                elif profit_pct <= -self.stop_loss_pct:
                    should_exit = True
                    exit_reason = f"Stop Loss ({profit_pct*100:.1f}%)"

                if should_exit:
                    self.liquidate(symbol)
                    self.debug(f"SELL {ticker} @ ${price:.2f} | {exit_reason} | P&L: {profit_pct*100:.1f}%")
                    if ticker in self.entry_prices:
                        del self.entry_prices[ticker]

    def on_end_of_algorithm(self):
        self.debug("=" * 60)
        self.debug(f"Strategy #2 Complete | Final Equity: ${self.portfolio.total_portfolio_value:.2f}")
        self.debug(f"Net P&L: ${self.portfolio.total_portfolio_value - 1000:.2f}")
        self.debug("=" * 60)
