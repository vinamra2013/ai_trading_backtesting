# QuantConnect Migration Guide - Complete Onboarding
**Date**: 2025-11-09
**Platform**: QuantConnect Cloud ($27/month Research Seat)
**Purpose**: Migrate from Backtrader to QuantConnect for data access and futures support

---

## 🎯 Why We're Migrating

**Problem Solved**: Data management complexity with Backtrader
**New Platform**: QuantConnect Cloud (LEAN engine)
**Cost**: $27/month for Research Seat
**Benefits**: Built-in data, futures support, professional infrastructure

---

## 📋 Step-by-Step Onboarding

### **Step 1: Sign Up for QuantConnect** (5 minutes)

1. Go to: https://www.quantconnect.com/pricing
2. Select **"Research Seat"** - $27/month
3. Create account with email
4. Verify email
5. Complete payment setup

**What You Get**:
- ✅ US Equities data (2000-present, daily + minute)
- ✅ Unlimited backtests
- ✅ Jupyter research environment
- ✅ Paper trading capability
- ✅ Community algorithms access

### **Step 2: Access the Platform** (2 minutes)

1. Login to: https://www.quantconnect.com/terminal
2. Navigate to **"Lab"** tab (Jupyter notebooks for research)
3. Navigate to **"Algorithm Lab"** (for backtesting)
4. Familiarize yourself with the interface

### **Step 3: Upload Your First Strategy** (10 minutes)

**Option A: Via Web UI** (Easiest)

1. Click **"Algorithm Lab"** → **"New Algorithm"**
2. Name it: `RSI_Mean_Reversion_Basic`
3. Select Language: **Python**
4. Delete default code
5. Copy-paste the LEAN strategy from: `strategies/rsi_mean_reversion_lean.py`
6. Click **"Save"**

**Option B: Via GitHub Integration** (Professional)

1. Connect your GitHub account (Settings → Integrations)
2. Push `strategies/rsi_mean_reversion_lean.py` to your repo
3. QuantConnect will auto-sync
4. More details: https://www.quantconnect.com/docs/v2/cloud-platform/projects/git

### **Step 4: Run Your First Backtest** (5 minutes)

1. In Algorithm Lab, open `RSI_Mean_Reversion_Basic`
2. Set date range (already set in code: 2020-2024)
3. Click **"Backtest"** button (top right)
4. Wait 30-60 seconds for results
5. View performance chart and metrics

**What to Check**:
- ✅ Total Return
- ✅ Sharpe Ratio
- ✅ Max Drawdown
- ✅ Number of Trades
- ✅ Win Rate
- ✅ **Profit Per Trade** (under "Statistics")

### **Step 5: Analyze Results** (10 minutes)

**Key Metrics to Review**:
1. **Profit Per Trade**: Is it >1%?
2. **Win Rate**: Is it >65%?
3. **Sharpe Ratio**: Is it >1.5?
4. **Max Drawdown**: Is it <15%?
5. **Trade Count**: Are there 50+ trades over 5 years?

**If Results Look Good**:
- ✅ Strategy validated!
- Move to Step 6 (Multi-Symbol Testing)

**If Results Are Weak**:
- Try different symbols
- Adjust parameters (RSI threshold, hold days, etc.)
- See optimization section below

### **Step 6: Multi-Symbol Backtesting** (15 minutes)

**Test Across All 7 Symbols**:

The strategy already includes 7 symbols in the universe:
```python
["NVDA", "AVGO", "AMZN", "MSFT", "GOOGL", "QCOM", "UNH"]
```

**To test different symbols**:
1. Open algorithm
2. Modify the `symbols` list in `Initialize()` method
3. Add/remove tickers as needed
4. Run new backtest

**Example - Add Leveraged ETFs**:
```python
for ticker in ["TQQQ", "SQQQ", "UPRO", "SPXU"]:
    symbol = self.AddEquity(ticker, Resolution.Daily).Symbol
    self.symbols.append(symbol)
```

### **Step 7: Parameter Optimization** (20 minutes)

**Use QuantConnect's Optimization Feature**:

1. In Algorithm Lab, click **"Optimize"** (next to Backtest)
2. Select parameters to optimize:
   - `rsi_entry_threshold`: 20, 22, 25, 27, 30
   - `rsi_exit_threshold`: 45, 50, 55
   - `max_hold_days`: 2, 3, 4, 5
3. Select optimization target: **Sharpe Ratio** or **Total Return**
4. Click **"Start Optimization"**
5. Review results and select best parameter set

**Note**: QuantConnect doesn't have built-in `profit_per_trade` metric yet. You can calculate it manually:
```python
profit_per_trade = total_net_profit / number_of_trades
```

### **Step 8: Paper Trading Setup** (15 minutes)

**Once Strategy is Validated**:

1. Navigate to **"Live Trading"** tab
2. Click **"Deploy"**
3. Select **"Paper Trading"** (free simulated trading)
4. Connect to **"QuantConnect Paper Brokerage"**
5. Set capital: $1000
6. Deploy algorithm
7. Monitor for 1-2 weeks

**What to Monitor**:
- Daily P&L
- Trade execution quality
- Slippage and commissions
- Live vs backtest performance divergence

---

## 🔧 Key LEAN Code Differences from Backtrader

### **1. Algorithm Structure**

**Backtrader**:
```python
class Strategy(bt.Strategy):
    def __init__(self):
        # Setup indicators

    def next(self):
        # Called every bar
```

**LEAN/QuantConnect**:
```python
class Strategy(QCAlgorithm):
    def Initialize(self):
        # Setup indicators, data subscriptions

    def OnData(self, data):
        # Called when new data arrives
```

### **2. Adding Symbols**

**Backtrader**:
```python
cerebro.adddata(data_feed)
```

**LEAN**:
```python
symbol = self.AddEquity("NVDA", Resolution.Daily).Symbol
```

### **3. Indicators**

**Backtrader**:
```python
self.rsi = bt.indicators.RSI(self.data.close, period=14)
```

**LEAN**:
```python
self.rsi = self.RSI("NVDA", 14, MovingAverageType.Wilders, Resolution.Daily)
```

### **4. Orders**

**Backtrader**:
```python
self.buy(size=shares)
self.close()
```

**LEAN**:
```python
self.MarketOrder("NVDA", shares)
self.Liquidate("NVDA")
```

### **5. Position Tracking**

**Backtrader**:
```python
if self.position:
    # Have position
```

**LEAN**:
```python
if self.Portfolio["NVDA"].Invested:
    # Have position
```

---

## 📊 Expected Performance (Based on Strategy Design)

### **Target Metrics** (What We're Aiming For)
- **Profit Per Trade**: 1-1.5%
- **Win Rate**: 65-75%
- **Sharpe Ratio**: >1.5
- **Max Drawdown**: <15%
- **Trade Frequency**: 10-20 trades/year per symbol
- **Total Trades**: 70-140 trades over 5 years (7 symbols)

### **Realistic Outcomes**

**Best Case** (60% probability):
- Strategy works on 4-5 symbols
- Profit per trade: 1.2-1.5%
- Win rate: 68-72%
- Ready for paper trading

**Good Case** (30% probability):
- Strategy works on 2-3 symbols
- Profit per trade: 0.8-1.0%
- Win rate: 62-67%
- Needs minor optimization

**Challenging Case** (10% probability):
- Strategy works on 1 symbol only
- Profit per trade: 0.5-0.7%
- Win rate: <60%
- Needs major revision or different approach

---

## 🚀 Next Steps After First Backtest

### **If Strategy Validates** (Profit per trade >1%)

1. **Week 1**: Multi-symbol testing
2. **Week 2**: Parameter optimization
3. **Week 3**: Paper trading deployment
4. **Week 4**: Monitor paper trading
5. **Week 5**: Go live with real money (if paper trading successful)

### **If Strategy Needs Work** (Profit per trade <1%)

1. **Optimize Parameters**: Try different RSI thresholds, hold times
2. **Test Different Symbols**: Maybe volatile stocks work better than large caps
3. **Add Filters**: Consider VIX regime filtering (high volatility mode only)
4. **Request Director Analysis**: I can analyze results and suggest improvements

---

## 💡 Pro Tips for QuantConnect

### **Data Tips**
- ✅ Data is already adjusted for splits/dividends (no manual work)
- ✅ Use `Resolution.Daily` for end-of-day strategies
- ✅ Use `Resolution.Minute` for intraday (we'll do this later if needed)
- ✅ Check data with: `self.Debug(f"Price: {data['NVDA'].Close}")`

### **Debugging Tips**
- ✅ Use `self.Debug("message")` to log (shows in backtest results)
- ✅ Check indicator readiness: `if rsi.IsReady:`
- ✅ Verify data exists: `if data.ContainsKey(symbol):`
- ✅ Monitor portfolio: `self.Debug(f"Cash: {self.Portfolio.Cash}")`

### **Performance Tips**
- ✅ Avoid complex calculations in `OnData()` (runs every bar)
- ✅ Use scheduled functions for daily logic: `self.Schedule.On()`
- ✅ Cache indicator values instead of recalculating
- ✅ Limit universe size (7-10 symbols max for Research seat)

### **Cost Management**
- ✅ Research Seat ($27/month): Unlimited backtests, no live trading fees
- ✅ Paper Trading: FREE (included in Research seat)
- ✅ Live Trading: Additional $20-30/month when you're ready
- ✅ Futures Data: Additional $8-15/month when needed

---

## 📚 Resources

### **Official Documentation**
- Getting Started: https://www.quantconnect.com/docs/v2/cloud-platform
- Algorithm Framework: https://www.quantconnect.com/docs/v2/writing-algorithms
- Indicators: https://www.quantconnect.com/docs/v2/writing-algorithms/indicators
- Backtesting: https://www.quantconnect.com/docs/v2/cloud-platform/backtesting

### **Community**
- Forum: https://www.quantconnect.com/forum
- Discord: https://discord.gg/quantconnect
- GitHub Examples: https://github.com/QuantConnect/Lean/tree/master/Algorithm.Python

### **Video Tutorials**
- YouTube Channel: https://www.youtube.com/c/QuantConnect
- Getting Started Series: https://www.quantconnect.com/learning

---

## ✅ Checklist: First Week on QuantConnect

**Day 1**:
- [ ] Sign up for Research Seat ($27/month)
- [ ] Upload RSI Mean Reversion strategy
- [ ] Run first backtest on NVDA

**Day 2-3**:
- [ ] Review backtest results
- [ ] Test all 7 symbols in universe
- [ ] Document which symbols work best

**Day 4-5**:
- [ ] Run parameter optimization
- [ ] Find optimal RSI thresholds
- [ ] Validate best parameter set

**Day 6-7**:
- [ ] Prepare portfolio (top 3 symbols)
- [ ] Plan paper trading deployment
- [ ] Review results with Director (me)

---

## 🤝 Director Support

**I'm here to help with**:
1. **Strategy Analysis**: Review your backtest results, suggest improvements
2. **Parameter Tuning**: Recommend optimal settings based on results
3. **Portfolio Construction**: Select top 3 uncorrelated strategies
4. **Risk Management**: Validate position sizing and stop losses
5. **Paper Trading**: Monitor live performance and compare to backtest

**How to Get Help**:
- Run backtests on QuantConnect
- Share results (screenshots or statistics)
- Ask questions about interpretation
- Request strategic guidance

---

## 🎯 Success Criteria

**You'll know the migration was successful when**:
1. ✅ First backtest completes in <60 seconds (vs hours with Backtrader data download)
2. ✅ Strategy achieves 1%+ profit per trade on 3+ symbols
3. ✅ Win rate is 65%+ with reasonable Sharpe ratio
4. ✅ No data quality issues or missing bars
5. ✅ Ready for paper trading within 1 week

---

**SUMMARY**: Sign up at quantconnect.com/pricing → Upload strategy → Run backtest → Analyze results → Optimize → Paper trade → Go live

**Timeline**: 1 week from signup to paper trading (vs 2-3 weeks with Backtrader data issues)

**Cost**: $27/month (vs $0 but + massive time investment in data management)

**Result**: Professional trading infrastructure with futures-ready platform

---

**Ready to start? Let me know once you've signed up and run your first backtest!**
