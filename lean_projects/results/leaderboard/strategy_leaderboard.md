# Strategy Leaderboard - Performance Rankings

**Last Updated**: 2025-01-10
**Capital**: $1000
**Minimum Criteria**: >100 trades, >50% win rate, >1% avg win, Sharpe >1.0, Drawdown <15%

---

## Top Performers (Updated After Each Backtest)

| Rank | Strategy | Asset Class | Sharpe | Annual Return | Max DD | Total Trades | Win Rate | Avg Win | Avg Loss | Deployed |
|------|----------|-------------|--------|---------------|--------|--------------|----------|---------|----------|----------|
| 🥇 | - | - | - | - | - | - | - | - | - | ❌ |
| 🥈 | - | - | - | - | - | - | - | - | - | ❌ |
| 🥉 | - | - | - | - | - | - | - | - | - | ❌ |
| 4 | - | - | - | - | - | - | - | - | - | ❌ |
| 5 | - | - | - | - | - | - | - | - | - | ❌ |

---

## Deployment Portfolio (Top 3 Active Strategies)

| Strategy | Allocation | Capital | Status | Deploy Date | Live P&L |
|----------|------------|---------|--------|-------------|----------|
| - | - | - | Not Deployed | - | - |
| - | - | - | Not Deployed | - | - |
| - | - | - | Not Deployed | - | - |

**Total Allocated**: $0 / $1000
**Cash Buffer**: $1000 (100%)

---

## All Tested Strategies (Chronological)

### Strategy #1: RSI Mean Reversion - Equities (REJECTED)
**Date**: 2025-01-10
**Category**: Mean Reversion
**Asset**: US Equities (NVDA, AVGO, AMZN, MSFT, GOOGL, QCOM, UNH)
**Status**: ❌ REJECTED
**Backtest URL**: https://www.quantconnect.com/project/26136271/d132ee6df2e83b577dbd26eeb2c0fac9

**Metrics**:
- Sharpe Ratio: -1.042 ❌ (need >1.0)
- Annual Return: 0.171% ❌
- Net Profit: $8.59 (+0.86%)
- Max Drawdown: 5.10% ⚠️ (too high for small profit)
- Total Trades: 8 ❌ (need >100)
- Win Rate: 50% ✅
- Average Win: 1.17% ✅ (meets 1%+ target)
- Average Loss: -0.73%
- Profit-Loss Ratio: 1.60
- Fees: $8.00

**Rejection Reasons**:
1. Insufficient trade frequency (8 trades over 5 years)
2. Negative Sharpe ratio indicates poor risk-adjusted returns
3. High drawdown (5.1%) relative to minimal profit
4. Statistically insignificant sample size

**Learnings**:
- RSI < 25 entry threshold too restrictive
- Need more symbols or different universe
- Consider relaxing entry conditions (RSI < 30-35)
- Daily resolution may be too slow for $1K capital

### Strategy #2: Bollinger Band Mean Reversion - ETFs (REJECTED)
**Date**: 2025-01-10
**Category**: Mean Reversion
**Asset**: US ETFs (SPY, QQQ, IWM, XLF, XLE, XLK, XLV, XLI)
**Status**: ❌ REJECTED
**URL**: https://www.quantconnect.com/project/26140687/f73ae2edac053e03cc91ab5575d7cc4c

**Metrics**:
- Sharpe Ratio: -0.207 ❌ (need >1.0)
- Net Profit: -$142.11 (-14.21%) ❌
- Total Trades: 822 ✅ (excellent frequency!)
- Win Rate: 43% ❌ (need >50%)
- Average Win: 1.54% ✅
- Average Loss: -1.21%
- Max Drawdown: 36.9% ❌ (need <15%)
- Total Fees: $674.00 ❌ (67% of capital!)

**Rejection Reasons**:
1. CRITICAL: Fees ($674) destroyed profitability on $1K capital
2. Win rate below 50% threshold (43%)
3. Negative returns (-14.21%)
4. Excessive drawdown (36.9% vs 15% max)
5. Negative Sharpe ratio

**Learnings**:
- ✅ 822 trades proves ETF mean reversion generates signals
- ❌ High frequency kills small accounts with fees
- Need either: (a) bigger capital, (b) lower frequency, or (c) better win rate
- $674 fees on 822 trades = ~$0.82/trade average
- Position sizing may be triggering minimum fees

---

## Strategy Performance Matrix

| Category | Best Strategy | Sharpe | Asset | Status |
|----------|---------------|--------|-------|--------|
| Mean Reversion | - | - | - | Testing |
| Momentum | - | - | - | Planned |
| Volatility | - | - | - | Planned |
| Futures | - | - | - | Testing |
| Hybrid | - | - | - | Planned |
| Event-Based | - | - | - | Planned |

---

## Rejected Strategies (Failed Criteria)

| Strategy | Asset | Reason | Sharpe | Win Rate | Avg Win |
|----------|-------|--------|--------|----------|---------|
| - | - | - | - | - | - |

**Rejection Criteria**:
- ❌ Sharpe < 1.0
- ❌ Win rate < 50%
- ❌ Avg win < 1%
- ❌ Max drawdown > 15%
- ❌ Total trades < 100

---

## Performance Trends

**By Asset Class**:
- Micro Futures: [No data yet]
- ETFs: [No data yet]
- Equities: [No data yet]
- Forex: [No data yet]

**By Strategy Type**:
- Mean Reversion: [No data yet]
- Momentum: [No data yet]
- Volatility: [No data yet]
- Hybrid: [No data yet]

---

## Next Backtest Queue

1. ⚙️ RSI Mean Reversion - Micro Futures (MES/MNQ) - **BUILDING**
2. 🔄 Bollinger Band Mean Reversion - ETFs
3. 🔄 Micro Futures Momentum - MES/MNQ
4. 🔄 RSI Mean Reversion - Equities

---

## Notes

- Update this file after EVERY backtest completion
- Maintain historical record of all tested strategies
- Track performance trends by category/asset class
- Identify patterns in what works vs. what doesn't
- Document lessons learned from each test
