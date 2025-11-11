# Data Download Request - High-Frequency Mean Reversion Backtesting
**Date**: 2025-11-09
**Requested by**: Quant Director
**Priority**: HIGH - Blocking backtest execution
**Status**: Ready for download

---

## 📊 Data Requirements Summary

I need historical daily data for **11 volatile symbols** + **4 leveraged ETFs** to backtest my new RSI Mean Reversion strategy across 5 years (2020-2024).

**Current Status**:
- ✅ VIX Daily data exists (2020-2025)
- ✅ 1-minute data exists for 2025-11-08 only (not sufficient for backtesting)
- ❌ NO daily data for discovered symbols (BLOCKER)

---

## 🎯 Required Data Downloads

### **Download #1: Primary Volatile Symbols (Daily Data)**

**Purpose**: Backtest RSI Mean Reversion strategy on high-volatility large-caps

```
Developer Request:
Please download historical market data with the following specifications:

- Symbols: AVGO, NVDA, AMZN, MSFT, GOOGL, QCOM, UNH, AAPL, TXN, PG, JNJ
- Date Range: 2020-01-01 to 2024-12-31
- Resolution: Daily
- Data Type: Trade
- Format: CSV (Backtrader-compatible OHLCV format)
- Output Directory: data/csv/{SYMBOL}/Daily/{SYMBOL}_Daily_20200101_20241231.csv
```

**Justification**: These 11 symbols were discovered via volatility_leaders scanner (ATR 2.5-12.8). They represent the top candidates for mean reversion trading with 2-4% daily volatility.

---

### **Download #2: Leveraged ETFs (Daily Data)**

**Purpose**: Test mean reversion on 3x leveraged instruments for higher profit potential

```
Developer Request:
Please download historical market data with the following specifications:

- Symbols: TQQQ, SQQQ, UPRO, SPXU
- Date Range: 2020-01-01 to 2024-12-31
- Resolution: Daily
- Data Type: Trade
- Format: CSV (Backtrader-compatible OHLCV format)
- Output Directory: data/csv/{SYMBOL}/Daily/{SYMBOL}_Daily_20200101_20241231.csv
```

**Justification**: Leveraged ETFs provide 3x daily moves, making 1%+ profit targets easier to achieve. Critical for portfolio diversification.

---

### **Download #3: Sector ETFs (Daily Data)**

**Purpose**: Add sector rotation capability and reduce tech concentration risk

```
Developer Request:
Please download historical market data with the following specifications:

- Symbols: XLE, XLF, XLK, XLV, XLI, XLU, XLP, XLY
- Date Range: 2020-01-01 to 2024-12-31
- Resolution: Daily
- Data Type: Trade
- Format: CSV (Backtrader-compatible OHLCV format)
- Output Directory: data/csv/{SYMBOL}/Daily/{SYMBOL}_Daily_20200101_20241231.csv
```

**Justification**: Sector ETFs enable mean reversion trades across different sectors, reducing correlation and improving portfolio stability.

---

### **Download #4: Benchmark & Broad Market (Daily Data)**

**Purpose**: Performance comparison and market regime analysis

```
Developer Request:
Please download historical market data with the following specifications:

- Symbols: SPY, QQQ, IWM, DIA
- Date Range: 2020-01-01 to 2024-12-31
- Resolution: Daily
- Data Type: Trade
- Format: CSV (Backtrader-compatible OHLCV format)
- Output Directory: data/csv/{SYMBOL}/Daily/{SYMBOL}_Daily_20200101_20241231.csv
```

**Justification**: Need benchmarks for performance comparison and to validate mean reversion works better than buy-and-hold.

---

## 📋 Data Download Summary Table

| Category | Symbols | Count | Date Range | Resolution | Priority |
|----------|---------|-------|------------|------------|----------|
| Volatile Large-Caps | AVGO, NVDA, AMZN, MSFT, GOOGL, QCOM, UNH, AAPL, TXN, PG, JNJ | 11 | 2020-2024 | Daily | **CRITICAL** |
| Leveraged ETFs | TQQQ, SQQQ, UPRO, SPXU | 4 | 2020-2024 | Daily | **HIGH** |
| Sector ETFs | XLE, XLF, XLK, XLV, XLI, XLU, XLP, XLY | 8 | 2020-2024 | Daily | **MEDIUM** |
| Benchmarks | SPY, QQQ, IWM, DIA | 4 | 2020-2024 | Daily | **MEDIUM** |
| **TOTAL** | | **27 symbols** | **5 years** | **Daily** | |

---

## 🔧 Technical Requirements

### Data Format Specification

**CSV Column Structure** (Backtrader-compatible):
```csv
Date,Open,High,Low,Close,Volume
2020-01-02,100.50,101.25,100.00,101.00,1000000
2020-01-03,101.00,102.00,100.75,101.75,1200000
...
```

**Requirements**:
- Date format: YYYY-MM-DD
- Prices: Float with 2 decimal places
- Volume: Integer
- No header row conflicts (first row should be column names)
- No missing data (weekends/holidays excluded automatically)
- Timezone: US Eastern (market hours)

### Data Source Preference

**Priority 1**: Yahoo Finance (yfinance)
- Free, reliable, good data quality
- You mentioned VIX data came from yfinance, so infrastructure exists

**Priority 2**: Interactive Brokers API
- Higher quality, but requires IB Gateway connection
- More complex, only use if yfinance fails

**Priority 3**: Alternative (Databento, Alpha Vantage)
- Only if above options fail

---

## ✅ Acceptance Criteria

**For each symbol, verify**:
1. ✅ File exists at expected path: `data/csv/{SYMBOL}/Daily/{SYMBOL}_Daily_20200101_20241231.csv`
2. ✅ Date range: 2020-01-01 to 2024-12-31 (approximately 1,260 trading days)
3. ✅ No missing dates (except weekends/holidays)
4. ✅ Volume > 0 for all rows
5. ✅ High >= Low, High >= Close, High >= Open
6. ✅ Prices are reasonable (no $0 or $999,999 outliers)

**Validation Command**:
```bash
# For each symbol, run:
python -c "
import pandas as pd
df = pd.read_csv('data/csv/NVDA/Daily/NVDA_Daily_20200101_20241231.csv')
print(f'Rows: {len(df)}')
print(f'Date range: {df.Date.min()} to {df.Date.max()}')
print(f'Missing values: {df.isnull().sum().sum()}')
print(f'Volume check: {(df.Volume > 0).all()}')
"
```

---

## 🚨 Blockers if Data Not Available

**Without this data, I CANNOT**:
1. ❌ Run backtests on my new RSI Mean Reversion strategy
2. ❌ Validate the 1%+ per trade profit thesis
3. ❌ Rank strategies by performance
4. ❌ Build optimized portfolio
5. ❌ Deploy to paper/live trading

**Current Workaround**: NONE - This is a hard blocker. I can write strategies but cannot validate them without historical data.

---

## ⏱️ Timeline

**Requested Completion**: Within 24-48 hours
**Estimated Download Time**: 1-2 hours (27 symbols × 5 years via yfinance)
**Director Availability**: Standing by to validate data quality immediately after download

---

## 📞 Questions for Developer

Before starting download, please confirm:

1. **Data Source**: Will you use yfinance (preferred) or IB API?
2. **Storage Format**: Is the CSV structure above correct, or should I adjust?
3. **Batch Download**: Do you have a script to download all 27 symbols automatically, or should I provide one?
4. **Existing Data**: I see 1-minute data for 2025-11-08 exists. Should we preserve it or can it be overwritten?
5. **ETA**: When can you complete this download (target: 24-48 hours)?

---

## 🔄 After Data Download

**Immediate Next Steps** (Director will execute):
1. Validate data quality using acceptance criteria above
2. Run initial backtest on NVDA using new API endpoints
3. Batch backtest all 27 symbols if initial test passes
4. Rank strategies and build portfolio
5. Update session notes with backtest results

**Commands I'll Use** (New API approach):
```bash
# Test single backtest via API
curl -X POST "${FASTAPI_BACKEND_URL:-http://localhost:8230}/api/backtests/run" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "rsi_mean_reversion_basic",
    "symbols": ["NVDA"],
    "start_date": "2020-01-01",
    "end_date": "2024-12-31"
  }'

# Batch backtest via API (if test passes)
for symbol in AVGO NVDA AMZN MSFT GOOGL QCOM UNH TQQQ SQQQ UPRO SPXU; do
  curl -X POST "${FASTAPI_BACKEND_URL:-http://localhost:8230}/api/backtests/run" \
    -H "Content-Type: application/json" \
    -d "{\"strategy\": \"rsi_mean_reversion_basic\", \"symbols\": [\"$symbol\"], \"start_date\": \"2020-01-01\", \"end_date\": \"2024-12-31\"}"
done
```

---

## ✅ Developer Sign-Off

**Developer Acknowledgment**: [Pending]
**Confirmed Data Source**: [To be specified]
**Estimated Completion Date**: [To be confirmed]
**Blockers/Concerns**: [List any issues]

---

**END OF DATA DOWNLOAD REQUEST**

*Prepared by: Quant Director*
*Date: 2025-11-09*
*Status: Awaiting developer response*
