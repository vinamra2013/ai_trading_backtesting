# LEAN Developer Guide - QuantConnect Python API Reference

**Version**: 2.5.0
**Python**: 3.11
**Last Updated**: 2025-01-10

**Complete Official Documentation**: https://www.quantconnect.com/docs/v2/writing-algorithms/indicators/supported-indicators

---

## Table of Contents

1. [Parameter System for Optimization](#parameter-system)
2. [Common Indicators (Most Used)](#common-indicators)
3. [Data Access Patterns](#data-access-patterns)
4. [Position Sizing & Risk Management](#position-sizing)
5. [Resolution & Time Periods](#resolutions)
6. [Common Errors & Solutions](#common-errors)
7. [Complete Indicator Reference](#complete-indicator-list)

---

## Parameter System for Optimization {#parameter-system}

### Using GetParameter()

**CRITICAL**: All optimizable values MUST use `get_parameter()`. Constants cannot be optimized.

```python
# ✅ CORRECT - Can be optimized
rsi_period = int(self.get_parameter("rsi_period", "14"))
entry_threshold = int(self.get_parameter("entry_threshold", "30"))
stop_loss_pct = float(self.get_parameter("stop_loss", "0.01"))

# ❌ WRONG - Cannot be optimized
rsi_period = 14
```

### Data Type Conversion

```python
# Integer parameters
period = int(self.get_parameter("period", "20"))

# Float parameters
threshold = float(self.get_parameter("threshold", "0.5"))

# String parameters (rare)
symbol_filter = self.get_parameter("filter", "SPY")
```

### Default Values

Always provide sensible defaults as strings:

```python
rsi_period = int(self.get_parameter("rsi_period", "14"))  # Default: 14
# NOT: int(self.get_parameter("rsi_period"))  # Error if not provided
```

### Config.json Format

Parameters defined in project's `config.json`:

```json
{
  "parameters": {
    "rsi_period": "14",
    "entry_threshold": "30",
    "stop_loss": "0.01"
  }
}
```

---

## Common Indicators (Most Used) {#common-indicators}

### RSI (Relative Strength Index)

**Signature**: `self.rsi(symbol, period, moving_average_type, resolution)`

**Parameters**:
- `symbol`: Symbol object (from `add_equity()`)
- `period`: int - Lookback period (typical: 14)
- `moving_average_type`: `MovingAverageType.WILDERS` (recommended for RSI)
- `resolution`: `Resolution.DAILY`, `Resolution.HOUR`, etc.

**Example**:
```python
def initialize(self):
    symbol = self.add_equity("SPY", Resolution.DAILY).symbol
    rsi_period = int(self.get_parameter("rsi_period", "14"))

    # Create RSI indicator
    self.rsi_indicator = self.rsi(symbol, rsi_period, MovingAverageType.WILDERS, Resolution.DAILY)

def on_data(self, data):
    # Check if ready
    if not self.rsi_indicator.is_ready:
        return

    # Get current value
    current_rsi = self.rsi_indicator.current.value

    # Use in logic
    if current_rsi < 30:  # Oversold
        self.market_order(symbol, 100)
```

**Common Error**:
```python
# ❌ WRONG - Missing MovingAverageType parameter
self.rsi_indicator = self.rsi(symbol, 14, Resolution.DAILY)

# ✅ CORRECT
self.rsi_indicator = self.rsi(symbol, 14, MovingAverageType.WILDERS, Resolution.DAILY)
```

---

### Bollinger Bands

**Signature**: `self.bb(symbol, period, std_dev, moving_average_type, resolution)`

**Parameters**:
- `symbol`: Symbol object
- `period`: int - Lookback period (typical: 20)
- `std_dev`: int - Standard deviations (typical: 2)
- `moving_average_type`: `MovingAverageType.SIMPLE` or `.EXPONENTIAL`
- `resolution`: Resolution enum

**Example**:
```python
def initialize(self):
    symbol = self.add_equity("SPY", Resolution.DAILY).symbol
    bb_period = int(self.get_parameter("bb_period", "20"))
    bb_std_dev = int(self.get_parameter("bb_std_dev", "2"))

    # Create Bollinger Bands
    self.bb = self.bb(symbol, bb_period, bb_std_dev, MovingAverageType.SIMPLE, Resolution.DAILY)

def on_data(self, data):
    if not self.bb.is_ready:
        return

    # Access bands
    upper_band = self.bb.upper_band.current.value
    middle_band = self.bb.middle_band.current.value
    lower_band = self.bb.lower_band.current.value

    price = data.bars[symbol].close

    # Mean reversion logic
    if price <= lower_band:  # Oversold
        self.market_order(symbol, 100)
```

---

### SMA (Simple Moving Average)

**Signature**: `self.sma(symbol, period, resolution)`

**Example**:
```python
def initialize(self):
    symbol = self.add_equity("SPY", Resolution.DAILY).symbol
    fast_period = int(self.get_parameter("fast_sma", "50"))
    slow_period = int(self.get_parameter("slow_sma", "200"))

    self.fast_sma = self.sma(symbol, fast_period, Resolution.DAILY)
    self.slow_sma = self.sma(symbol, slow_period, Resolution.DAILY)

def on_data(self, data):
    if not self.fast_sma.is_ready or not self.slow_sma.is_ready:
        return

    # Golden cross
    if self.fast_sma.current.value > self.slow_sma.current.value:
        self.set_holdings(symbol, 1.0)
```

---

### EMA (Exponential Moving Average)

**Signature**: `self.ema(symbol, period, resolution)`

**Example**:
```python
self.ema_indicator = self.ema(symbol, 20, Resolution.DAILY)
```

---

### MACD (Moving Average Convergence Divergence)

**Signature**: `self.macd(symbol, fast_period, slow_period, signal_period, moving_average_type, resolution)`

**Example**:
```python
def initialize(self):
    symbol = self.add_equity("SPY", Resolution.DAILY).symbol

    # Standard MACD (12, 26, 9)
    self.macd = self.macd(symbol, 12, 26, 9, MovingAverageType.EXPONENTIAL, Resolution.DAILY)

def on_data(self, data):
    if not self.macd.is_ready:
        return

    macd_value = self.macd.current.value
    signal_value = self.macd.signal.current.value
    histogram = macd_value - signal_value

    # Bullish crossover
    if macd_value > signal_value:
        self.set_holdings(symbol, 1.0)
```

---

### ATR (Average True Range)

**Signature**: `self.atr(symbol, period, moving_average_type, resolution)`

**Example**:
```python
self.atr_indicator = self.atr(symbol, 14, MovingAverageType.SIMPLE, Resolution.DAILY)

# Use for position sizing
atr_value = self.atr_indicator.current.value
stop_distance = 2 * atr_value  # 2 ATR stop loss
```

---

### ADX (Average Directional Index)

**Signature**: `self.adx(symbol, period, resolution)`

**Example**:
```python
self.adx = self.adx(symbol, 14, Resolution.DAILY)

# Trend strength
adx_value = self.adx.current.value
if adx_value > 25:  # Strong trend
    # Trade momentum strategies
```

---

### Stochastic

**Signature**: `self.sto(symbol, period, k_period, d_period, resolution)`

**Example**:
```python
self.stoch = self.sto(symbol, 14, 3, 3, Resolution.DAILY)

k_value = self.stoch.stoch_k.current.value
d_value = self.stoch.stoch_d.current.value

if k_value < 20:  # Oversold
    self.market_order(symbol, 100)
```

---

## Data Access Patterns {#data-access-patterns}

### Checking Data Availability

**CRITICAL**: Always check if data exists before accessing.

```python
def on_data(self, data):
    # ✅ CORRECT - Check first
    if data.bars.contains_key(symbol):
        price = data.bars[symbol].close

    # ❌ WRONG - NoneType error
    price = data[symbol].close
```

### Accessing Bar Data

```python
# Trade bars (OHLCV)
if data.bars.contains_key(symbol):
    bar = data.bars[symbol]
    open_price = bar.open
    high_price = bar.high
    low_price = bar.low
    close_price = bar.close
    volume = bar.volume
```

### Accessing Quote Bars

```python
# Quote bars (bid/ask)
if data.quote_bars.contains_key(symbol):
    quote = data.quote_bars[symbol]
    bid_price = quote.bid.close
    ask_price = quote.ask.close
```

---

## Position Sizing & Risk Management {#position-sizing}

### Risk-Based Position Sizing

```python
def calculate_position_size(self, symbol, entry_price, stop_loss_price):
    # Maximum risk per trade (1% of capital)
    max_risk_dollars = self.portfolio.total_portfolio_value * 0.01

    # Risk per share
    risk_per_share = abs(entry_price - stop_loss_price)

    if risk_per_share == 0:
        return 0

    # Calculate shares
    shares = int(max_risk_dollars / risk_per_share)

    # Respect cash limits
    max_shares_by_cash = int(self.portfolio.cash / entry_price)
    shares = min(shares, max_shares_by_cash)

    return shares
```

### Using in Strategy

```python
def on_data(self, data):
    if data.bars.contains_key(symbol):
        entry_price = data.bars[symbol].close
        stop_price = entry_price * 0.99  # 1% stop loss

        shares = self.calculate_position_size(symbol, entry_price, stop_price)

        if shares > 0:
            self.market_order(symbol, shares)
```

---

## Resolutions & Time Periods {#resolutions}

### Available Resolutions

```python
Resolution.TICK      # Tick-by-tick data
Resolution.SECOND    # Second bars
Resolution.MINUTE    # Minute bars
Resolution.HOUR      # Hourly bars
Resolution.DAILY     # Daily bars
```

### Choosing Resolution

**Daily** - Recommended for:
- Swing trading (2-10 day holds)
- Small capital accounts ($1K-$10K)
- Lower fees
- ~5-50 trades/year per symbol

**Hour** - Good for:
- Intraday trading
- Medium capital ($10K+)
- More frequent signals
- Higher fees

**Minute** - Use with caution:
- High-frequency strategies
- Large capital ($50K+)
- Very high fees (can destroy small accounts)

### Fee Impact by Resolution

| Resolution | Typical Trades/Year | Fees on $1K Capital | Impact |
|------------|-------------------|---------------------|--------|
| Daily | 50-200 | $50-$200 | 5-20% |
| Hour | 500-2000 | $500-$2000 | 50-200% ❌ |
| Minute | 5000+ | $5000+ | 500%+ ❌❌ |

**Rule**: For $1K capital, stick with Daily resolution unless proven profitable.

---

## Common Errors & Solutions {#common-errors}

### Error 1: "Trying to dynamically access a method that does not exist"

**Cause**: Missing or incorrect parameters in indicator creation.

**Example**:
```python
# ❌ WRONG
self.bb = self.bb(symbol, 20, 2, Resolution.DAILY)

# ✅ CORRECT
self.bb = self.bb(symbol, 20, 2, MovingAverageType.SIMPLE, Resolution.DAILY)
```

**Solution**: Check indicator signature in this guide.

---

### Error 2: "'NoneType' object has no attribute 'close'"

**Cause**: Accessing data without checking if it exists.

**Example**:
```python
# ❌ WRONG
price = data[symbol].close

# ✅ CORRECT
if data.bars.contains_key(symbol):
    price = data.bars[symbol].close
```

---

### Error 3: Variable naming conflicts

**Cause**: Using `self.rsi` when LEAN has `self.rsi()` method.

**Example**:
```python
# ❌ WRONG
self.rsi = None  # Overwrites LEAN's self.rsi() method
self.rsi = self.rsi(symbol, 14, MovingAverageType.WILDERS, Resolution.DAILY)

# ✅ CORRECT
self.rsi_indicator = self.rsi(symbol, 14, MovingAverageType.WILDERS, Resolution.DAILY)
```

**Reserved names to avoid**:
- `self.rsi` → Use `self.rsi_indicator`
- `self.sma` → Use `self.sma_indicator`
- `self.ema` → Use `self.ema_indicator`
- `self.bb` → Use `self.bollinger_bands`

---

### Error 4: Casing issues

**Cause**: Wrong enum casing.

**Example**:
```python
# ❌ WRONG
Resolution.Daily  # Python style
MovingAverageType.Wilders  # Python style

# ✅ CORRECT
Resolution.DAILY  # C# style (LEAN is C#)
MovingAverageType.WILDERS  # C# style
```

---

## Complete Indicator List {#complete-indicator-list}

### Trend Indicators

| Indicator | Method | Use Case |
|-----------|--------|----------|
| Simple Moving Average | `self.sma(symbol, period, resolution)` | Trend direction, crossovers |
| Exponential Moving Average | `self.ema(symbol, period, resolution)` | Faster trend response |
| Bollinger Bands | `self.bb(symbol, period, std, ma_type, resolution)` | Volatility, mean reversion |
| MACD | `self.macd(symbol, fast, slow, signal, ma_type, resolution)` | Trend changes, momentum |
| ADX | `self.adx(symbol, period, resolution)` | Trend strength |
| Aroon | `self.aroon(symbol, period, resolution)` | Trend changes |
| Parabolic SAR | `self.psar(symbol, af_start, af_increment, af_max, resolution)` | Trailing stops |

### Momentum Indicators

| Indicator | Method | Use Case |
|-----------|--------|----------|
| RSI | `self.rsi(symbol, period, ma_type, resolution)` | Overbought/oversold |
| Stochastic | `self.sto(symbol, period, k, d, resolution)` | Overbought/oversold |
| CCI | `self.cci(symbol, period, ma_type, resolution)` | Cyclical trends |
| Momentum | `self.mom(symbol, period, resolution)` | Price momentum |
| ROC | `self.roc(symbol, period, resolution)` | Rate of change |
| Williams %R | `self.wilr(symbol, period, resolution)` | Overbought/oversold |

### Volatility Indicators

| Indicator | Method | Use Case |
|-----------|--------|----------|
| ATR | `self.atr(symbol, period, ma_type, resolution)` | Position sizing, stops |
| Standard Deviation | `self.std(symbol, period, resolution)` | Volatility measurement |
| Keltner Channels | `self.kch(symbol, period, atr_mult, ma_type, resolution)` | Trend + volatility |
| Donchian Channel | `self.dch(symbol, period, resolution)` | Breakout trading |

### Volume Indicators

| Indicator | Method | Use Case |
|-----------|--------|----------|
| OBV | `self.obv(symbol, resolution)` | Volume confirmation |
| VWAP | `self.vwap(symbol, resolution)` | Intraday price levels |
| AD | `self.ad(symbol, resolution)` | Accumulation/distribution |
| Money Flow Index | `self.mfi(symbol, period, resolution)` | Volume-weighted RSI |

### Candlestick Patterns

40+ patterns available via pattern recognizer. See official docs.

---

## Best Practices

### 1. Always Use GetParameter for Optimization

```python
# ✅ CORRECT - Optimizable
rsi_period = int(self.get_parameter("rsi_period", "14"))

# ❌ WRONG - Not optimizable
rsi_period = 14
```

### 2. Check Data Before Access

```python
# ✅ CORRECT
if data.bars.contains_key(symbol):
    price = data.bars[symbol].close
```

### 3. Check Indicator Readiness

```python
# ✅ CORRECT
if not self.rsi_indicator.is_ready:
    return

current_rsi = self.rsi_indicator.current.value
```

### 4. Use Descriptive Variable Names

```python
# ✅ CORRECT
self.rsi_indicator = self.rsi(...)
self.fast_ema = self.ema(...)

# ❌ WRONG (conflicts with LEAN methods)
self.rsi = self.rsi(...)
self.ema = self.ema(...)
```

### 5. Implement Risk Management

```python
# ✅ CORRECT - Always use stops
max_risk = self.portfolio.total_portfolio_value * 0.01
stop_price = entry_price * 0.99
shares = int(max_risk / (entry_price - stop_price))
```

---

## Quick Reference Card

```python
# Template for any indicator-based strategy
from AlgorithmImports import *

class MyStrategy(QCAlgorithm):
    def initialize(self):
        # Backtest period
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(1000)

        # Get parameters (optimizable)
        rsi_period = int(self.get_parameter("rsi_period", "14"))
        entry_threshold = int(self.get_parameter("entry_threshold", "30"))

        # Add securities
        self.symbol = self.add_equity("SPY", Resolution.DAILY).symbol

        # Create indicators
        self.rsi_indicator = self.rsi(self.symbol, rsi_period, MovingAverageType.WILDERS, Resolution.DAILY)

        # Store parameters
        self.entry_threshold = entry_threshold

    def on_data(self, data):
        # Check data availability
        if not data.bars.contains_key(self.symbol):
            return

        # Check indicator readiness
        if not self.rsi_indicator.is_ready:
            return

        # Get current values
        price = data.bars[self.symbol].close
        rsi = self.rsi_indicator.current.value

        # Trading logic
        if not self.portfolio.invested:
            if rsi < self.entry_threshold:
                # Calculate position size
                shares = self.calculate_position_size(price)
                self.market_order(self.symbol, shares)

        elif rsi > 70:
            self.liquidate(self.symbol)

    def calculate_position_size(self, entry_price):
        max_risk = self.portfolio.total_portfolio_value * 0.01
        stop_price = entry_price * 0.99
        risk_per_share = entry_price - stop_price
        shares = int(max_risk / risk_per_share)
        max_by_cash = int(self.portfolio.cash / entry_price)
        return min(shares, max_by_cash)
```

---

**Official Documentation**: https://www.quantconnect.com/docs/v2/writing-algorithms/indicators/supported-indicators
**API Reference**: https://www.lean.io/docs/v2/lean-engine/class-reference/py/QuantConnect/
