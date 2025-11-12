#!/bin/bash
# Complete Run Script for All 14 Strategies
# Execute this script to run all optimizations in sequence

set -e  # Exit on error

cd /home/vbhatnagar/code/ai_trading_backtesting

# Activate virtual environment
source venv/bin/activate.fish

echo "=========================================="
echo "STRATEGY OPTIMIZATION - COMPLETE SUITE"
echo "=========================================="
echo ""

# ==================================================
# PRIORITY 1: HIGH - Mean Reversion Strategies
# ==================================================

echo "START: HIGH Priority Strategies"
echo "================================"

echo "STR-001: RSI_MeanReversion_ETF"
python scripts/optimize_runner.py --config configs/optimizations/rsi_etf_lowfreq.yaml --estimate
python scripts/optimize_runner.py --config configs/optimizations/rsi_etf_lowfreq.yaml
echo "✓ STR-001 COMPLETE"
echo ""

echo "STR-002: BollingerBand_ETF_LowFreq"
python scripts/optimize_runner.py --config configs/optimizations/bollinger_etf_lowfreq.yaml --estimate
python scripts/optimize_runner.py --config configs/optimizations/bollinger_etf_lowfreq.yaml
echo "✓ STR-002 COMPLETE"
echo ""

echo "STR-009: MeanReversion_TrendFilter_ETF (A/B Test)"
python scripts/optimize_runner.py --config configs/optimizations/meanreversion_trendfilter_etf.yaml --estimate
python scripts/optimize_runner.py --config configs/optimizations/meanreversion_trendfilter_etf.yaml
echo "✓ STR-009 COMPLETE"
echo ""

# ==================================================
# PRIORITY 2: MEDIUM - Momentum & Timing Strategies
# ==================================================

echo "START: MEDIUM Priority Strategies"
echo "=================================="

echo "STR-003: SMA_Crossover_ETF"
python scripts/optimize_runner.py --config configs/optimizations/sma_crossover_etf.yaml --estimate
python scripts/optimize_runner.py --config configs/optimizations/sma_crossover_etf.yaml
echo "✓ STR-003 COMPLETE"
echo ""

echo "STR-004: Breakout_Momentum_Equity"
python scripts/optimize_runner.py --config configs/optimizations/breakout_momentum_equity.yaml --estimate
python scripts/optimize_runner.py --config configs/optimizations/breakout_momentum_equity.yaml
echo "✓ STR-004 COMPLETE"
echo ""

echo "STR-006: VIX_Market_Timing"
python scripts/optimize_runner.py --config configs/optimizations/vix_market_timing.yaml --estimate
python scripts/optimize_runner.py --config configs/optimizations/vix_market_timing.yaml
echo "✓ STR-006 COMPLETE"
echo ""

echo "STR-008: RSI_MACD_Combo_ETF"
python scripts/optimize_runner.py --config configs/optimizations/rsi_macd_combo_etf.yaml --estimate
python scripts/optimize_runner.py --config configs/optimizations/rsi_macd_combo_etf.yaml
echo "✓ STR-008 COMPLETE"
echo ""

echo "STR-013: Gap_Trading_Overnight"
python scripts/optimize_runner.py --config configs/optimizations/gap_trading_overnight.yaml --estimate
python scripts/optimize_runner.py --config configs/optimizations/gap_trading_overnight.yaml
echo "✓ STR-013 COMPLETE"
echo ""

# ==================================================
# PRIORITY 3: LOW - Specialized Strategies
# ==================================================

echo "START: LOW Priority Strategies"
echo "=============================="

echo "STR-005: ATR_Breakout_ETF"
python scripts/optimize_runner.py --config configs/optimizations/atr_breakout_etf.yaml --estimate
python scripts/optimize_runner.py --config configs/optimizations/atr_breakout_etf.yaml
echo "✓ STR-005 COMPLETE"
echo ""

echo "STR-010: Earnings_Momentum"
python scripts/optimize_runner.py --config configs/optimizations/earnings_momentum.yaml --estimate
python scripts/optimize_runner.py --config configs/optimizations/earnings_momentum.yaml
echo "✓ STR-010 COMPLETE"
echo ""

echo "STR-011: Statistical_Pairs_Trading"
python scripts/optimize_runner.py --config configs/optimizations/statistical_pairs_trading.yaml --estimate
python scripts/optimize_runner.py --config configs/optimizations/statistical_pairs_trading.yaml
echo "✓ STR-011 COMPLETE"
echo ""

echo "STR-012: Relative_Strength_Leaders"
python scripts/optimize_runner.py --config configs/optimizations/relative_strength_leaders.yaml --estimate
python scripts/optimize_runner.py --config configs/optimizations/relative_strength_leaders.yaml
echo "✓ STR-012 COMPLETE"
echo ""

echo "STR-014: Donchian_Breakout_ETF"
python scripts/optimize_runner.py --config configs/optimizations/donchian_breakout_etf.yaml --estimate
python scripts/optimize_runner.py --config configs/optimizations/donchian_breakout_etf.yaml
echo "✓ STR-014 COMPLETE"
echo ""

echo "STR-015: Quality_Factor_Momentum"
python scripts/optimize_runner.py --config configs/optimizations/quality_factor_momentum.yaml --estimate
python scripts/optimize_runner.py --config configs/optimizations/quality_factor_momentum.yaml
echo "✓ STR-015 COMPLETE"
echo ""

echo "=========================================="
echo "ALL 14 STRATEGIES OPTIMIZATION COMPLETE!"
echo "=========================================="
echo ""
echo "Next: Query PostgreSQL for results:"
echo "  docker exec mlflow-postgres psql -U mlflow -d trading -c \"SELECT * FROM strategy_leaderboard LIMIT 20;\""
