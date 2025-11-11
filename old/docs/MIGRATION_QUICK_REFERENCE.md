# LEAN to Backtrader Migration - Quick Reference

**One-page guide for the migration effort**

---

## At a Glance

| Aspect | Details |
|--------|---------|
| **Reason** | LEAN requires paid API key, Backtrader is 100% free |
| **Effort** | 4-6 weeks (200-240 hours) |
| **Epics** | 6 epics, 44 user stories |
| **Risk** | Moderate - proven technology, well-documented |
| **Outcome** | Zero vendor lock-in, full feature parity |

---

## Epic Checklist

- [ ] **Epic 11:** Foundation & Docker (1 week)
- [ ] **Epic 12:** Backtesting Engine (1.5 weeks)
- [ ] **Epic 13:** Algorithm Migration (1.5 weeks)
- [ ] **Epic 14:** Advanced Features (1 week)
- [ ] **Epic 15:** Testing & Validation (1 week + monitoring)
- [ ] **Epic 16:** Documentation & Cutover (3-5 days)

---

## Key Code Changes

### LEAN Algorithm → Backtrader Strategy

```python
# LEAN (OLD)
class MyAlgo(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.AddEquity("SPY", Resolution.Daily)
        self.sma = self.SMA("SPY", 20)

    def OnData(self, data):
        if not self.Portfolio.Invested:
            if self.Securities["SPY"].Price > self.sma.Current.Value:
                self.SetHoldings("SPY", 1.0)

# Backtrader (NEW)
class MyStrategy(bt.Strategy):
    params = (('sma_period', 20),)

    def __init__(self):
        self.sma = bt.indicators.SMA(self.data.close, period=self.p.sma_period)

    def next(self):
        if not self.position:
            if self.data.close[0] > self.sma[0]:
                size = int(self.broker.getcash() / self.data.close[0])
                self.buy(size=size)
```

### Data Download

```bash
# LEAN (OLD)
lean data download --data-provider-historical "Interactive Brokers" \
  --symbols SPY --start 20200101 --end 20241231

# Backtrader (NEW)
python scripts/download_data.py \
  --symbols SPY --start 2020-01-01 --end 2024-12-31 \
  --resolution Daily --data-type Trade
```

### Running Backtests

```bash
# LEAN (OLD)
lean backtest algorithms/my_algo

# Backtrader (NEW)
python scripts/run_backtest.py \
  --strategy strategies.my_strategy.MyStrategy \
  --symbols SPY --start 2020-01-01 --end 2024-12-31 \
  --commission ib_standard
```

---

## What Stays the Same?

✅ **IB Gateway container** - No changes
✅ **SQLite database** - Same schema
✅ **Monitoring dashboard** - Streamlit (parser updates only)
✅ **Project structure** - Algorithms, data, results, config
✅ **Risk management logic** - Ported to Backtrader
✅ **Commission models** - IB Standard & Pro (reimplemented)

---

## What Changes?

❌ **LEAN CLI** → Python scripts
❌ **QCAlgorithm** → bt.Strategy
❌ **Initialize()** → __init__()
❌ **OnData()** → next()
❌ **self.Portfolio** → self.broker, self.position
❌ **lean backtest** → python run_backtest.py
❌ **Docker service name** - lean → backtrader

---

## Critical Milestones

### Week 1: Foundation Working
- [ ] Backtrader Docker image builds
- [ ] IB Gateway connection established
- [ ] Sample data downloaded

### Week 2-3: First Backtest
- [ ] Cerebro engine functional
- [ ] Commission models validated
- [ ] Simple strategy backtested successfully

### Week 4: Algorithm Migrated
- [ ] At least one LEAN algorithm → Backtrader
- [ ] Risk management integrated
- [ ] Database logging working

### Week 5: Advanced Features
- [ ] Parameter optimization working
- [ ] Walk-forward analysis functional
- [ ] Live deployment scripts ready

### Week 6: Validated
- [ ] LEAN comparison within ±5%
- [ ] All tests passing (>80% coverage)
- [ ] Paper trading successful (1 week)

### Week 7: Production
- [ ] Documentation complete
- [ ] LEAN dependencies removed
- [ ] Production cutover successful

---

## Validation Checklist

Before considering migration complete:

**Technical Validation:**
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] LEAN comparison within tolerance (±5% return, ±0.3 Sharpe)
- [ ] Performance benchmarks met
- [ ] Commission calculations validated

**Operational Validation:**
- [ ] Paper trading matches expectations
- [ ] Monitoring dashboard functional
- [ ] Database logging working
- [ ] Emergency stop procedure tested
- [ ] Alerts working

**Documentation Validation:**
- [ ] README.md updated (no LEAN references)
- [ ] CLAUDE.md updated
- [ ] Migration guide created
- [ ] All code commented
- [ ] Troubleshooting guide complete

**Production Readiness:**
- [ ] Zero LEAN dependencies
- [ ] Code passes linting
- [ ] Rollback plan documented
- [ ] 24-hour monitoring successful
- [ ] Stakeholder sign-off

---

## Common Pitfalls & Solutions

### Pitfall 1: Algorithm Logic Differs
**Problem:** LEAN event-driven vs Backtrader iterator pattern
**Solution:** Focus on strategy intent, not exact translation. Validate with backtests.

### Pitfall 2: Commission Calculation Errors
**Problem:** Small differences compound over many trades
**Solution:** Extensive unit tests, validate against IB documentation

### Pitfall 3: Data Pipeline Complexity
**Problem:** No LEAN CLI automation for downloads
**Solution:** Use ib_insync, implement caching, handle rate limits

### Pitfall 4: Performance Slower Than Expected
**Problem:** Python vs C# performance difference
**Solution:** Use optimization techniques, consider parallelization

### Pitfall 5: Overfitting in Optimization
**Problem:** Parameters work in-sample but fail out-of-sample
**Solution:** Walk-forward validation mandatory

---

## Emergency Contacts & Resources

### Documentation
- Epic files: `stories/epic-11-stories.md` through `epic-16-stories.md`
- Migration summary: `docs/EPIC_MIGRATION_SUMMARY.md`
- This guide: `docs/MIGRATION_QUICK_REFERENCE.md`

### External Resources
- Backtrader docs: https://www.backtrader.com/docu/
- ib_insync docs: https://ib-insync.readthedocs.io/
- Backtrader community: https://community.backtrader.com/

### Rollback Plan
If migration fails, LEAN system can be restored:
1. `git checkout lean-baseline`
2. `docker compose up -d lean`
3. Restore .env file
4. Verify LEAN operational

---

## Daily Standup Template

**What did I complete yesterday?**
- [Epic X, Story Y] - Brief description

**What am I working on today?**
- [Epic X, Story Z] - Brief description

**Any blockers?**
- None / [Describe blocker]

**Progress:**
- Epics complete: X/6
- Stories complete: Y/44
- Estimated completion: [Date]

---

## Success Criteria

### Technical Success
✅ All automated tests pass
✅ Results within ±5% of LEAN
✅ Performance acceptable
✅ Production stable for 1 week

### Business Success
✅ Zero ongoing API costs
✅ No operational disruption
✅ Team confident in new system
✅ Knowledge transfer complete

### Quality Success
✅ Code quality high (passes linting)
✅ Documentation complete
✅ Maintainability improved
✅ Rollback plan tested

---

## Final Checklist Before Production

- [ ] All 6 epics complete
- [ ] All 44 user stories complete
- [ ] All tests passing (unit, integration, regression)
- [ ] LEAN comparison within tolerance
- [ ] 1 week paper trading successful
- [ ] Performance benchmarks met
- [ ] Documentation 100% complete
- [ ] LEAN dependencies removed
- [ ] Code cleanup complete
- [ ] Rollback plan documented and tested
- [ ] Team trained on new system
- [ ] Stakeholder approval received
- [ ] Production cutover plan reviewed
- [ ] 24-hour monitoring scheduled

---

**When all checkboxes are complete: MIGRATION SUCCESSFUL! 🎉**

---

## Quick Commands Reference

```bash
# Start services
./scripts/start.sh

# Stop services
./scripts/stop.sh

# Download data
python scripts/download_data.py --symbols SPY --start 2020-01-01 --end 2024-12-31

# Run backtest
python scripts/run_backtest.py --strategy strategies.my_strategy.MyStrategy --symbols SPY

# Start live trading (paper)
./scripts/start_live_trading.sh

# Emergency stop
./scripts/emergency_stop.sh

# View logs
docker compose logs backtrader
tail -f logs/live_trading.log

# Run tests
pytest tests/

# Check coverage
pytest --cov=scripts --cov=strategies tests/
```

---

**Keep this document handy throughout the migration!** 📌
