# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Algorithmic trading platform built on **QuantConnect LEAN** for backtesting and live trading with Interactive Brokers integration. This is a Python-based system using QuantConnect Cloud infrastructure for execution.

**Platform**: QuantConnect LEAN (C#/Python)
**Backtesting**: QuantConnect Cloud
**Live Trading**: QuantConnect Cloud with Interactive Brokers
**Development**: Local LEAN CLI + Cloud deployment

## Environment Management

**CRITICAL**: This project uses a Python virtual environment. ALWAYS activate it before running Python commands:

```bash
source venv/bin/activate.fish
```

All Python commands (pip, python scripts) MUST run within the virtual environment.

## QuantConnect Cloud Backtesting

**Status**: ✅ Primary Platform - LEAN projects with cloud automation

**Project Structure**:
```
lean_projects/
├── RSIMeanReversion/     # LEAN strategy project
│   └── main.py          # Strategy code
├── data/                # Sample data
└── lean.json            # LEAN configuration
```

### Run Cloud Backtest

**Via Automation Script** (Recommended):
```bash
source venv/bin/activate

# Quick backtest (open browser)
python scripts/qc_cloud_backtest.py --open

# Full workflow (commit, push, wait, save results)
python scripts/qc_cloud_backtest.py --commit --wait --save --open

# Without push (test existing code)
python scripts/qc_cloud_backtest.py --no-push --open
```

**Via LEAN CLI Directly**:
```bash
cd lean_projects

# Push to cloud
lean cloud push --project RSIMeanReversion

# Run backtest
lean cloud backtest RSIMeanReversion --open

# Download results
lean cloud results <backtest-id>
```

**Script Options**:
- `--commit` - Commit and push to GitHub first
- `--open` - Open results in browser
- `--wait` - Wait for backtest to complete
- `--save` - Download and save results locally
- `--no-push` - Skip pushing to QC cloud

**Output**: Results in terminal + URL to https://www.quantconnect.com/project/...

### Strategy Development

**LEAN Strategy Structure** (`lean_projects/RSIMeanReversion/main.py`):

```python
from AlgorithmImports import *

class MyStrategy(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2024, 12, 31)
        self.SetCash(1000)

        # Add securities
        self.symbol = self.AddEquity("SPY", Resolution.Daily).Symbol

        # Add indicators
        self.rsi = self.RSI(self.symbol, 14, Resolution.Daily)

    def OnData(self, data):
        # Trading logic
        if not self.Portfolio.Invested:
            if self.rsi.Current.Value < 30:
                self.SetHoldings(self.symbol, 1.0)
        elif self.rsi.Current.Value > 70:
            self.Liquidate(self.symbol)
```

**Key LEAN Concepts**:
- `QCAlgorithm` base class for all strategies
- `Initialize()` - Setup method called once
- `OnData()` - Called on each data point
- `self.SetHoldings()` - Position sizing
- `self.Liquidate()` - Close positions
- `self.Portfolio` - Portfolio state
- Built-in indicators: RSI, SMA, EMA, MACD, etc.

### Live Trading Deployment

**Deploy to QuantConnect Cloud Live Trading**:

```bash
# Deploy live trading via QuantConnect Cloud
lean cloud live "RSIMeanReversion" \
  --brokerage InteractiveBrokers \
  --environment live \
  --ib-user-name "your-username" \
  --ib-account "your-account-id"

# Monitor live trading on QuantConnect web interface
# URL: https://www.quantconnect.com/live
```

**Pre-Deployment Checklist**:
- [ ] Strategy has 100+ backtest trades for statistical significance
- [ ] Sharpe ratio > 1.0
- [ ] Max drawdown < 15%
- [ ] Win rate > 50%
- [ ] Average win > 1% per trade
- [ ] IB account credentials configured
- [ ] Capital allocation documented and approved
- [ ] Risk management parameters set correctly

## Data Management

### QuantConnect Cloud Data

QuantConnect Cloud provides:
- **US Equities**: Minute/Daily data from 1998
- **Options**: Minute data from 2000
- **Futures**: Minute/Daily data
- **Forex**: Minute/Daily data
- **Crypto**: Minute/Daily data from 2015

**No manual data download required** - QuantConnect Cloud handles all data automatically.

### Local Development Data

For local backtesting (optional):
```bash
cd lean_projects

# Download data for local backtesting
lean data download --dataset "US Equities" \
  --start 20200101 \
  --end 20241231 \
  --resolution Daily
```

## Strategy Development Workflow

### 1. Create New Strategy

```bash
cd lean_projects
lean project-create "MyNewStrategy" --language python
```

### 2. Edit Strategy

```bash
nano lean_projects/MyNewStrategy/main.py
```

### 3. Test Locally (Optional)

```bash
cd lean_projects
lean backtest "MyNewStrategy"
```

### 4. Test on Cloud

```bash
python scripts/qc_cloud_backtest.py --open
```

### 5. Iterate

Repeat steps 2-4 until performance meets targets.

### 6. Deploy Live

```bash
lean cloud live "MyNewStrategy" \
  --brokerage InteractiveBrokers \
  --environment live
```

## Key Metrics to Monitor

**Performance Targets**:
- **Total Orders**: 100+ trades for statistical significance
- **Win Rate**: 50%+
- **Average Win**: 1%+ per trade
- **Sharpe Ratio**: >1.0
- **Max Drawdown**: <15%
- **Trade Frequency**: 5-15 trades per week

**Risk Metrics**:
- **Risk per trade**: ≤1% of capital
- **Max portfolio drawdown**: ≤2%
- **Max open positions**: 3
- **Leverage**: ≤2x

## QuantConnect Resources

**Documentation**: https://www.quantconnect.com/docs
**Community Forum**: https://www.quantconnect.com/forum
**API Reference**: https://www.quantconnect.com/docs/v2/our-platform/api-reference
**Example Algorithms**: https://www.quantconnect.com/project/examples

**Current Project**: https://www.quantconnect.com/project/26136271

## Troubleshooting

### Common Issues

**"lean: command not found"**
- Install LEAN CLI: `pip install lean`
- Activate virtual environment: `source venv/bin/activate.fish`

**"No API credentials found"**
- Login to QuantConnect: `lean cloud login`
- Follow authentication prompts

**"Project not found on cloud"**
- Push project first: `lean cloud push --project YourProject`
- Verify project exists at https://www.quantconnect.com/project

**"Insufficient data"**
- Check date range in `Initialize()`
- Ensure QuantConnect has data for your symbols/period
- Try different securities or date ranges

**"Backtest fails immediately"**
- Check strategy syntax errors
- Verify `Initialize()` and `OnData()` methods exist
- Check logs in terminal or QuantConnect web UI

### Debug Mode

Enable verbose logging:
```bash
# Local backtest with verbose output
lean backtest "MyStrategy" --verbose

# Cloud backtest (check web UI for logs)
python scripts/qc_cloud_backtest.py --open
# Then click "Logs" tab in QuantConnect web interface
```

## Project Rules

**Environment**: Always use `source venv/bin/activate.fish` before Python commands

**LEAN CLI**: Primary tool for all QuantConnect operations

**Git**: Never commit API keys or credentials

**Trading Mode**: Always test in paper mode before live deployment

**Results**: All backtest results available in QuantConnect Cloud web interface

## Quick Reference Card

**Essential Commands**:
```bash
# Login to QuantConnect
lean cloud login

# Create new strategy
lean project-create "StrategyName" --language python

# Push to cloud
cd lean_projects
lean cloud push --project StrategyName

# Run cloud backtest
python scripts/qc_cloud_backtest.py --open

# Deploy live trading
lean cloud live "StrategyName" --brokerage InteractiveBrokers

# View live deployments
lean cloud live list
```

**File Locations**:
- Strategy code: `lean_projects/RSIMeanReversion/main.py`
- LEAN config: `lean_projects/lean.json`
- Automation script: `scripts/qc_cloud_backtest.py`
- Session notes: `data/notes/`

**Web Interfaces**:
- QuantConnect Dashboard: https://www.quantconnect.com
- Current Project: https://www.quantconnect.com/project/26136271
- Live Trading: https://www.quantconnect.com/live
- Documentation: https://www.quantconnect.com/docs

---

**For The Director Persona**: Use `/quant_director` command for autonomous trading operations workflow and session continuity guidelines.
