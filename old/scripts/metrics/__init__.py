#!/usr/bin/env python3
"""
Advanced Metrics Library - Epic 17: US-17.5
Advanced metrics calculation for backtrader backtests including quantstats integration.

This module provides comprehensive metrics analysis beyond the basic Backtrader analyzers:
- Risk-adjusted metrics (Sortino, Calmar, Omega)
- Return distribution analysis (Skew, Kurtosis, VaR, CVaR)
- Benchmark comparison (Alpha, Beta, R², Information Ratio)
- Regime-aware analysis (bull/bear, high/low volatility periods)
- HTML tearsheets with quantstats integration
"""

from .quantstats_metrics import QuantStatsAnalyzer
from .alpha_beta import AlphaBetaAnalyzer
from .regime_metrics import RegimeAnalyzer

__all__ = [
    'QuantStatsAnalyzer',
    'AlphaBetaAnalyzer', 
    'RegimeAnalyzer'
]

__version__ = '1.0.0'
