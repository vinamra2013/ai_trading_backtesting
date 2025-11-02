# Dashboard Screenshots & Visual Guide

**Note**: This document describes the visual appearance and layout of the new Backtests and Optimization tabs. Actual screenshots would be captured after running the dashboard.

---

## Tab Structure

The dashboard now has **8 tabs** in the main navigation:

```
📊 Dashboard | 💼 Live Trading | 📜 Trade Log | 📈 Performance | 🔬 Backtests | ⚙️ Optimization | 🏥 Health | ⚙️ Settings
```

---

## 🔬 Backtests Tab

### Main Layout

When you click the "🔬 Backtests" tab, you see 4 sub-tabs:

```
📋 List View | 📊 Detail View | 📝 Trade Log | ⚖️ Comparison
```

---

### 📋 List View

**Header**: "All Backtests (2)"

**Table**: Full-width sortable DataFrame

| ID (short) | Algorithm | Start Date | End Date | Sharpe | Return % | Max DD % | Win Rate % | Trades | Status |
|------------|-----------|------------|----------|--------|----------|----------|------------|--------|---------|
| sample_b... | algorithms/live_strategy | 2023-01-01 | 2023-12-31 | 1.85 | 15.42% | -8.23% | 62.50% | 48 | COMPLETED |
| sample_b... | algorithms/live_strategy | 2023-01-01 | 2023-12-31 | 2.15 | 22.80% | -6.15% | 68.20% | 52 | COMPLETED |

**Filter Controls** (2 columns):
- Left: "Filter by Algorithm" (multiselect dropdown)
- Right: "Filter by Status" (multiselect dropdown)

**Empty State** (when no backtests):
```
ℹ️ No backtest results found. Run a backtest to see results here.

Run a backtest:
source venv/bin/activate
python scripts/run_backtest.py --algorithm algorithms/my_strategy
```

---

### 📊 Detail View

**Backtest Selector**: Dropdown at top
- Format: "sample_b - algorithms/live_strategy"

**Section 1: Key Metrics** (6 metric cards in a row)

```
┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│ Sharpe Ratio │ Total Return │ Max Drawdown │  Win Rate    │  Trade Count │ Profit Factor│
│    1.85      │   15.42%     │    -8.23%    │   62.50%     │      48      │     1.92     │
└──────────────┴──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

**Section 2: Equity Curve** (line chart)

```
Portfolio Equity Over Time

    $120,000 ┤                                               ╭─
    $115,000 ┤                                         ╭────╯
    $110,000 ┤                               ╭────────╯
    $105,000 ┤                     ╭────────╯
    $100,000 ┼────────────────────╯
             └─────────────────────────────────────────────────>
             Jan '23      Apr '23      Jul '23      Oct '23
```

**Section 3: Drawdown Chart** (area chart, red fill)

```
Underwater Plot (Drawdown %)

       0% ┼────╮                    ╭──────╮
      -2% ┤    │                    │      │
      -4% ┤    ╰──╮            ╭───╯      │              ╭────
      -6% ┤       │      ╭─────╯          │         ╭────╯
      -8% ┤       ╰──────╯                ╰─────────╯
         └────────────────────────────────────────────────────>
         Jan '23     Apr '23     Jul '23     Oct '23
```

**Section 4: Monthly Returns** (heatmap)

```
Monthly Returns Heatmap

Year │ Jan  Feb  Mar  Apr  May  Jun  Jul  Aug  Sep  Oct  Nov  Dec
─────┼─────────────────────────────────────────────────────────────
2023 │ 2.5  1.7  2.0  2.5  1.6  1.6 -0.4  1.5  1.5 -0.4  1.5  0.8

Color scale: Red (negative) ← Yellow (0%) → Green (positive)
```

---

### 📝 Trade Log

**Backtest Selector**: Dropdown at top

**Trade Count**: "Total Trades: 3"

**Table**: Full-width DataFrame

| Symbol | Entry Date | Entry Price | Exit Date | Exit Price | P&L | Return % | Duration |
|--------|------------|-------------|-----------|------------|-----|----------|----------|
| SPY | 2023-01-05 | $385.50 | 2023-01-20 | $392.80 | $730.00 | 1.89% | 15 days |
| AAPL | 2023-02-10 | $150.25 | 2023-02-28 | $155.80 | $1110.00 | 3.69% | 18 days |
| MSFT | 2023-03-15 | $275.60 | 2023-03-30 | $268.20 | -$370.00 | -2.68% | 15 days |

**Export Button**: "📥 Export to CSV"
- Downloads: `trades_{backtest_id}_{timestamp}.csv`

---

### ⚖️ Comparison

**Multi-Select**: "Select Backtests to Compare (2-5)"
- Shows: "sample_b - algorithms/live_strategy"
- Max 5 selections

**Metrics Comparison Table** (when 2+ selected):

| ID | Algorithm | Sharpe | Return % | Max DD % | Win Rate % | Trades | Profit Factor |
|----|-----------|--------|----------|----------|------------|--------|---------------|
| sample_b | algorithms/live_strategy | **2.15** | **22.80%** | **-6.15%** | **68.20%** | **52** | **2.18** |
| sample_b | algorithms/live_strategy | 1.85 | 15.42% | -8.23% | 62.50% | 48 | 1.92 |

*Best values highlighted in green*

**Equity Curve Comparison** (overlay chart):

```
Equity Curve Comparison

    $125,000 ┤                                               ╭─ sample_b (blue)
    $120,000 ┤                                         ╭────╯
    $115,000 ┤                                   ╭────╯     ╭─ sample_b (red)
    $110,000 ┤                         ╭────────╯      ╭───╯
    $105,000 ┤               ╭────────╯          ╭────╯
    $100,000 ┼──────────────╯──────────╯────────╯
             └─────────────────────────────────────────────────>
             Jan '23    Apr '23    Jul '23    Oct '23
```

**Info Messages**:
- "Please select at least 2 backtests to compare" (when <2 selected)
- "Select 2 or more backtests above to compare their performance" (when 0 selected)

---

## ⚙️ Optimization Tab

### Main Layout

When you click the "⚙️ Optimization" tab, you see 3 sub-tabs:

```
🚀 Run Optimization | 📊 Results | 📜 History
```

---

### 🚀 Run Optimization

**Section 1: Algorithm Selection**

```
Select Algorithm
┌───────────────────────────────────────┐
│ algorithms/live_strategy              │ ▼
└───────────────────────────────────────┘
```

**Section 2: Parameter Configuration**

```
Parameter Configuration
ℹ️ Add parameters to optimize. Each parameter needs a name, min value, max value, and step size.

Current Parameters:                              ┌─────────────────┐
1. fast_period: [5, 20] step 5                   │ ➕ Add Parameter │
2. slow_period: [20, 50] step 10                 └─────────────────┘
```

**Parameter Form** (when "Add Parameter" clicked):

```
New Parameter

Parameter Name
┌─────────────────────────────────────┐
│ e.g., fast_period                   │
└─────────────────────────────────────┘

Min Value          Max Value          Step Size
┌────────────┐    ┌────────────┐    ┌────────────┐
│    1.0     │    │   100.0    │    │    1.0     │
└────────────┘    └────────────┘    └────────────┘

              ┌─────────────────┐
              │  Add Parameter  │
              └─────────────────┘
```

**Clear Button**: "🗑️ Clear All Parameters" (shown when parameters exist)

**Section 3: Optimization Settings**

```
Optimization Metric              Max Iterations
┌─────────────────────────┐     ┌──────────┐
│ Sharpe Ratio            │ ▼   │   100    │
└─────────────────────────┘     └──────────┘
```

**Start Button**:
```
┌────────────────────────────┐
│  🚀 Start Optimization     │  (Primary button, blue)
└────────────────────────────┘
```

*Disabled when no parameters configured*

**Progress** (when running):
```
Running optimization... This may take several minutes.
[████████████████████████████────────] 70%
```

---

### 📊 Results

**Optimization Selector**: Dropdown at top
- Format: "sample_o - algorithms/live_strategy"

**Metadata**:
```
Algorithm: algorithms/live_strategy
Optimization Metric: Sharpe Ratio
Created: 2024-10-18T16:45:00
```

**Parameter Combinations Table**:

| fast_period | slow_period | sharpe_ratio | total_return | max_drawdown | trade_count |
|-------------|-------------|--------------|--------------|--------------|-------------|
| 10 | 40 | **2.15** | **22.3** | **-5.2** | 36 |
| 15 | 40 | 2.05 | 20.9 | -5.6 | 38 |
| 10 | 30 | 1.95 | 19.5 | -5.8 | 40 |
| ... | ... | ... | ... | ... | ... |

*Top performers highlighted in green*
*Showing top 20 results*

**Export Button**: "📥 Export Results to CSV"

**Parameter Heatmap** (for 2-parameter optimizations):

```
Parameter Heatmap

Select Metric for Heatmap: [Sharpe Ratio ▼]

slow_period
    50 │ 1.55  1.88  1.78  1.52
    40 │ 1.82  2.15  2.05  1.68
    30 │ 1.68  1.95  1.72  1.45
    20 │ 1.45  1.22  0.95  --
       └──────────────────────
          5    10    15    20  fast_period

Color scale: Dark (low Sharpe) → Bright (high Sharpe)
```

**Info** (when >2 parameters): "Heatmap visualization is available for 2-parameter optimizations only"

---

### 📜 History

**Header**: "Total Optimization Runs: 1"

**Table**: Full-width DataFrame

| ID (short) | Algorithm | Metric | Param Count | Result Count | Created | Status |
|------------|-----------|--------|-------------|--------------|---------|---------|
| sample_o... | algorithms/live_strategy | Sharpe Ratio | 2 | 15 | 2024-10-18T16:45:00 | COMPLETED |

**Empty State** (when no optimizations):
```
ℹ️ No optimization history available
```

---

## Color Schemes

### Backtests
- **Equity Curves**: Blue (default), multi-color for comparison
- **Drawdowns**: Red fill with gradient (rgba(255,0,0,0.3))
- **Monthly Returns**: RdYlGn (Red-Yellow-Green)
- **Best Metrics**: Light green highlight

### Optimization
- **Heatmap**: Viridis (purple to yellow)
- **Best Results**: Light green highlight
- **Start Button**: Streamlit primary (blue)

### General
- **Info Messages**: Blue info boxes
- **Warnings**: Yellow/orange
- **Errors**: Red
- **Success**: Green

---

## Responsive Behavior

All tables and charts use `use_container_width=True` for responsive design:
- Tables expand to fill available space
- Charts maintain aspect ratio
- Multi-column layouts stack on mobile
- Buttons and inputs scale appropriately

---

## Interactive Features

### Plotly Charts
- Hover tooltips with exact values
- Zoom and pan controls
- Download as PNG button
- Legend toggle (click to show/hide series)
- Unified hover mode (comparison charts)

### Streamlit Components
- Sortable DataFrames (click headers)
- Expandable sections (expanders)
- Multi-select with search
- Form validation
- Session state persistence
- Auto-refresh on data changes

---

## Error Handling

### Missing Data
```
ℹ️ Equity curve data not available
ℹ️ Drawdown data not available
ℹ️ Monthly returns data not available
ℹ️ No trade data available for this backtest
```

### Empty States
```
ℹ️ No backtest results found. Run a backtest to see results here.
ℹ️ No optimization results found. Run an optimization to see results here.
ℹ️ No optimization history available
```

### Errors
```
❌ Error loading backtests: [error message]
ℹ️ Make sure backtest results are available in /app/results/backtests/

❌ Error loading optimizations: [error message]
ℹ️ Make sure optimization results are available in /app/results/optimizations/
```

---

## File Locations

**Dashboard**: `/home/vbhatnagar/code/ai_trading_backtesting/monitoring/app.py`
**Loaders**: `/home/vbhatnagar/code/ai_trading_backtesting/monitoring/utils/`
**Backtests Data**: `/home/vbhatnagar/code/ai_trading_backtesting/results/backtests/`
**Optimizations Data**: `/home/vbhatnagar/code/ai_trading_backtesting/results/optimizations/`

---

## Testing the Dashboard

1. Start the dashboard:
   ```bash
   cd /home/vbhatnagar/code/ai_trading_backtesting
   docker compose up -d monitoring
   ```

2. Access: `http://localhost:8501`

3. Navigate to "🔬 Backtests" or "⚙️ Optimization" tabs

4. Sample data is pre-loaded for immediate testing

---

## Next Steps (Track C Integration)

When Track C completes the optimization runner:

1. Replace placeholder in "Run Optimization" tab
2. Update progress bar to show real-time progress
3. Call actual optimization runner with parameters
4. Save results to `/app/results/optimizations/`
5. Auto-refresh results view when complete

**Integration Point**: Line 954 in `monitoring/app.py`
```python
# TODO: Integrate with actual optimization runner from Track C
st.info("Optimization feature will be integrated with Track C optimizer")
```
