# QuantConnect Cloud Backtest Runner

**Category**: Trading & Backtesting
**Purpose**: Automate QuantConnect cloud backtesting workflow with GitHub integration

## Description

This skill automates the complete workflow for running backtests on QuantConnect cloud:
1. Optional git commit and push to GitHub (git@github.com:vinamra2013/QuantConnectAlgoTradingStratigies.git)
2. Push strategy code to QuantConnect cloud via LEAN CLI
3. Execute backtest on QuantConnect servers
4. Wait for completion and retrieve results
5. Parse and display key performance metrics

## When to Use

**Auto-activate when user requests:**
- "Run backtest on QuantConnect"
- "Test strategy on QC cloud"
- "Upload and backtest on QuantConnect"
- "Run cloud backtest"
- Keywords: "quantconnect", "qc cloud", "lean backtest", "cloud backtest"

**Manual invocation:**
- User explicitly asks to run QuantConnect backtest
- After strategy modifications when validation is needed
- When comparing strategy performance

## Prerequisites

1. **LEAN CLI installed:**
   ```bash
   pip install lean
   lean login
   ```

2. **Environment variables in .env:**
   ```bash
   QC_PROJECT_NAME="Your Project Name"
   ```

3. **GitHub repo configured:**
   - Repo: git@github.com:vinamra2013/QuantConnectAlgoTradingStratigies.git
   - Strategy files in strategies/ directory

## Parameters

### Required
- None (uses defaults from .env)

### Optional
- `--project`: QuantConnect project name (default: from QC_PROJECT_NAME env var)
- `--commit`: Commit and push to GitHub before backtest
- `--commit-message`: Custom git commit message
- `--open`: Open results in browser after starting backtest
- `--wait`: Wait for backtest to complete (polls every 10s)
- `--save`: Download and save results locally to results/qc/
- `--timeout`: Wait timeout in seconds (default: 300)
- `--no-push`: Skip pushing to QC cloud (use existing code)

## Usage Examples

### Quick Backtest (Start Only)
```bash
source venv/bin/activate
python scripts/qc_cloud_backtest.py --open
```

### Full Workflow (Wait for Results)
```bash
source venv/bin/activate
python scripts/qc_cloud_backtest.py --wait --save
```

### With Git Commit
```bash
source venv/bin/activate
python scripts/qc_cloud_backtest.py --commit --wait --save
```

### Custom Project
```bash
source venv/bin/activate
python scripts/qc_cloud_backtest.py --project "My Custom Strategy" --open
```

## Output

### Immediate Feedback
- ✓ LEAN CLI version
- ✓ Project name confirmation
- ✓ Git push status (if --commit)
- ✓ Cloud push status
- ✓ Backtest started confirmation

### When Using --wait --save
```
============================================================
BACKTEST RESULTS
============================================================
Total Return        : 392.23%
Sharpe Ratio        : 0.829
Total Orders        : 2
Win Rate            : 0%
Loss Rate           : 0%
Average Win         : 0%
Average Loss        : 0%
Max Drawdown        : 59.000%
Sortino Ratio       : 0.856
Net Profit          : $3922.28
Annual Return       : 37.501%
============================================================
```

### Result Files
- JSON results saved to: `results/qc/backtest_YYYYMMDD_HHMMSS.json`

## Error Handling

**LEAN CLI not installed:**
```
Error: LEAN CLI not installed
Install with: pip install lean
Then login with: lean login
```

**Missing credentials:**
```
Error: QC_PROJECT_NAME not set in .env
Add to .env file:
QC_PROJECT_NAME="Your Project Name"
```

**Backtest timeout:**
```
⚠ Backtest timed out after 300 seconds
Check status at: https://www.quantconnect.com/terminal
```

## Integration with Claude Code

### Auto-Activation Patterns

Claude Code will automatically suggest this skill when detecting:
- File changes in `strategies/*.py`
- Keywords: "backtest", "quantconnect", "test strategy"
- After strategy modifications
- User requests validation or performance testing

### Workflow Integration

1. **Strategy Development:**
   ```
   User: "I updated the RSI strategy, can you test it on QuantConnect?"
   Claude: [Auto-invokes qc-backtest-runner skill]
   ```

2. **Result Analysis:**
   ```
   User: "Run backtest and show me the results"
   Claude: [Invokes with --wait --save, then analyzes metrics]
   ```

3. **Iterative Testing:**
   ```
   User: "Test with different parameters"
   Claude: [Modifies strategy, commits, runs backtest]
   ```

## Success Criteria

**Backtest Started:** Exit code 0, "Backtest started" message
**Backtest Completed:** Results JSON downloaded, metrics displayed
**Git Integration:** Changes committed and pushed successfully
**Error Handling:** Clear error messages with actionable steps

## Related Skills

- `data-manager`: Download historical data before backtesting
- `backtest-runner`: Run local Backtrader backtests
- `parameter-optimizer`: Optimize strategy parameters before cloud testing

## Notes

- **GitHub Sync:** If GitHub integration is enabled in QuantConnect, changes pushed to git@github.com:vinamra2013/QuantConnectAlgoTradingStratigies.git will auto-sync to QuantConnect within 1-2 minutes
- **Rate Limits:** QuantConnect Research Seat allows unlimited backtests
- **Execution Time:** Typical backtest (5 years daily data) completes in 30-90 seconds
- **Cost:** $27/month Research Seat (unlimited backtests)

## Troubleshooting

### Issue: "Project not found"
**Solution:** Check QC_PROJECT_NAME matches exact project name in QuantConnect terminal

### Issue: "Authentication failed"
**Solution:** Run `lean login` and re-enter credentials from https://www.quantconnect.com/account

### Issue: "Results not found"
**Solution:** Backtest may still be running. Increase --timeout or check web UI manually

### Issue: Git push fails
**Solution:** Ensure SSH key is configured for git@github.com:vinamra2013/QuantConnectAlgoTradingStratigies.git
