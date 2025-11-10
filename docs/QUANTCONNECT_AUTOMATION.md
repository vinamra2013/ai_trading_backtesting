# QuantConnect Cloud Automation

Automated workflow for backtesting strategies on QuantConnect cloud with GitHub integration.

## Quick Start

### 1. Setup (One-Time)

```bash
# Activate virtual environment
source venv/bin/activate

# Run setup script
chmod +x scripts/setup_qc_automation.sh
./scripts/setup_qc_automation.sh
```

This will:
- Install LEAN CLI
- Configure .env file
- Prompt you to login to QuantConnect
- Create necessary directories

### 2. Configure Project Name

Edit `.env` and set your QuantConnect project name:

```bash
nano .env
```

Add/update:
```bash
QC_PROJECT_NAME="RSI Mean Reversion Basic"
```

**Important:** Project name must match EXACTLY with your QuantConnect project name.

### 3. Run Your First Backtest

```bash
# Quick test (start backtest and open browser)
python scripts/qc_cloud_backtest.py --open

# Full workflow (wait for results and save locally)
python scripts/qc_cloud_backtest.py --wait --save

# With git commit
python scripts/qc_cloud_backtest.py --commit --wait --save
```

## Usage Examples

### Basic Usage

**Start backtest only:**
```bash
python scripts/qc_cloud_backtest.py
```

**Open results in browser:**
```bash
python scripts/qc_cloud_backtest.py --open
```

### Wait for Completion

**Wait and display results:**
```bash
python scripts/qc_cloud_backtest.py --wait --save
```

Output:
```
============================================================
BACKTEST RESULTS
============================================================
Total Return        : 392.23%
Sharpe Ratio        : 0.829
Total Orders        : 2
Win Rate            : 0%
Max Drawdown        : 59.000%
============================================================
```

### Git Integration

**Commit and push before backtest:**
```bash
python scripts/qc_cloud_backtest.py --commit --wait --save
```

**Custom commit message:**
```bash
python scripts/qc_cloud_backtest.py \
  --commit \
  --commit-message "Fix RSI exit logic" \
  --wait --save
```

### Advanced Options

**Custom project:**
```bash
python scripts/qc_cloud_backtest.py --project "My Custom Strategy" --open
```

**Skip cloud push (test existing code):**
```bash
python scripts/qc_cloud_backtest.py --no-push --wait --save
```

**Custom timeout:**
```bash
python scripts/qc_cloud_backtest.py --wait --timeout 600 --save
```

## Complete Workflow

### Typical Development Cycle

1. **Edit strategy locally:**
   ```bash
   nano strategies/rsi_mean_reversion_lean.py
   ```

2. **Test on QuantConnect:**
   ```bash
   python scripts/qc_cloud_backtest.py --commit --wait --save
   ```

3. **Analyze results:**
   ```bash
   cat results/qc/backtest_*.json | jq '.Statistics'
   ```

4. **Iterate based on results**

### One-Line Full Workflow

```bash
python scripts/qc_cloud_backtest.py --commit --wait --save --open
```

This will:
1. ✓ Commit and push changes to GitHub
2. ✓ Push to QuantConnect cloud
3. ✓ Start backtest
4. ✓ Open browser to view progress
5. ✓ Wait for completion
6. ✓ Download and display results

## Claude Code Skill

The automation is available as a Claude Code skill that auto-activates when you:

- Modify strategy files in `strategies/`
- Ask: "Run backtest on QuantConnect"
- Use keywords: "qc cloud", "quantconnect", "cloud backtest"

### Invoke Manually

You can also invoke the skill directly:

```
User: Run QuantConnect backtest with full results
Claude: [Auto-invokes qc-backtest-runner skill]
```

## GitHub Integration

### GitHub Repository

- **URL:** git@github.com:vinamra2013/QuantConnectAlgoTradingStratigies.git
- **Strategies:** Stored in `strategies/` directory
- **Auto-sync:** Enable in QuantConnect settings for automatic syncing

### Enable GitHub Auto-Sync (Optional)

1. Go to https://www.quantconnect.com/terminal
2. Open your project
3. Settings → Version Control
4. Link to GitHub
5. Select repository: `QuantConnectAlgoTradingStratigies`
6. Set path: `strategies/`

Now commits pushed to GitHub will auto-sync to QuantConnect within 1-2 minutes.

## File Structure

```
.
├── scripts/
│   ├── qc_cloud_backtest.py      # Main automation script
│   └── setup_qc_automation.sh    # Setup script
├── .claude/
│   └── skills/
│       └── qc-backtest-runner.md # Claude Code skill
├── strategies/
│   └── rsi_mean_reversion_lean.py # Your strategy
├── results/
│   └── qc/
│       └── backtest_*.json        # Saved results
└── .env                           # Configuration (gitignored)
```

## Command Reference

### All Options

```bash
python scripts/qc_cloud_backtest.py [OPTIONS]

Options:
  --project NAME          Project name (default: from .env)
  --commit                Commit and push to GitHub first
  --commit-message MSG    Custom commit message
  --open                  Open results in browser
  --wait                  Wait for backtest to complete
  --save                  Download and save results locally
  --timeout SECONDS       Wait timeout (default: 300)
  --no-push               Skip pushing to QC cloud
  -h, --help              Show help message
```

### Common Combinations

```bash
# Quick test
--open

# Full results
--wait --save

# Development workflow
--commit --wait --save

# Complete workflow
--commit --wait --save --open

# Test without pushing
--no-push --open

# Background job
--wait --save > backtest.log 2>&1 &
```

## Troubleshooting

### Error: "LEAN CLI not installed"

```bash
source venv/bin/activate
pip install lean
lean login
```

### Error: "Project not found"

Check that `QC_PROJECT_NAME` in `.env` matches exactly with your QuantConnect project name (case-sensitive).

### Error: "Authentication failed"

Re-login to QuantConnect:
```bash
lean login
```

Get credentials from: https://www.quantconnect.com/account

### Backtest Timeout

If backtest takes longer than 5 minutes:
```bash
python scripts/qc_cloud_backtest.py --timeout 600 --wait --save
```

### Git Push Fails

Ensure SSH key is configured:
```bash
ssh -T git@github.com
# Should show: "Hi vinamra2013! You've successfully authenticated"
```

## Performance

- **Typical backtest time:** 30-90 seconds (5 years daily data)
- **Wait polling interval:** 10 seconds
- **Default timeout:** 300 seconds (5 minutes)
- **Cost:** $27/month Research Seat (unlimited backtests)

## Best Practices

1. **Always test with `--wait --save`** to capture results
2. **Use `--commit`** to maintain version history
3. **Review logs** before deploying to live trading
4. **Set reasonable timeouts** based on backtest complexity
5. **Save results** for comparison and analysis

## Related Documentation

- [QuantConnect Documentation](https://www.quantconnect.com/docs)
- [LEAN CLI Documentation](https://www.quantconnect.com/docs/v2/lean-cli)
- [GitHub Integration](https://www.quantconnect.com/docs/v2/cloud-platform/projects/git)

## Support

- QuantConnect Forums: https://www.quantconnect.com/forum
- GitHub Issues: https://github.com/vinamra2013/QuantConnectAlgoTradingStratigies/issues
- Claude Code Skills: `.claude/skills/qc-backtest-runner.md`

## Next Steps

After successful backtesting:

1. **Parameter Optimization:** Run multiple backtests with different parameters
2. **Walk-Forward Analysis:** Validate out-of-sample performance
3. **Paper Trading:** Deploy to QuantConnect paper trading
4. **Live Trading:** Deploy to live account (after thorough validation)

---

**GitHub:** git@github.com:vinamra2013/QuantConnectAlgoTradingStratigies.git
**QuantConnect:** https://www.quantconnect.com/terminal
**Subscription:** $27/month Research Seat
