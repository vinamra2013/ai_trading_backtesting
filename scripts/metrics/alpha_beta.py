#!/usr/bin/env python3
"""
Alpha/Beta Analyzer - Epic 17: US-17.8
Alpha/beta calculation for benchmark comparison in trading strategies.

This module provides comprehensive benchmark comparison metrics:
- Alpha calculation (excess return vs benchmark)
- Beta calculation (sensitivity to benchmark movements)
- R-squared calculation (correlation strength)
- Information Ratio calculation
- Tracking error calculation
- Jenson Alpha calculation
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlphaBetaAnalyzer:
    """
    Alpha/Beta analyzer for benchmark comparison in trading strategies.
    
    Provides comprehensive benchmark comparison metrics for strategy evaluation:
    - Alpha: Excess return vs benchmark (risk-adjusted)
    - Beta: Sensitivity to benchmark movements
    - R-squared: Correlation strength between strategy and benchmark
    - Information Ratio: Excess return per unit of tracking error
    - Tracking Error: Standard deviation of excess returns
    - Jenson Alpha: Risk-adjusted alpha using CAPM
    
    Example usage:
        analyzer = AlphaBetaAnalyzer(benchmark_returns)
        alpha_beta_metrics = analyzer.calculate_alpha_beta(strategy_returns)
        info_ratio = analyzer.calculate_information_ratio(strategy_returns, benchmark_returns)
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize Alpha/Beta analyzer.
        
        Args:
            risk_free_rate: Annual risk-free rate for calculations (default 2%)
        """
        self.risk_free_rate = risk_free_rate
        
        logger.info(f"AlphaBetaAnalyzer initialized with risk-free rate: {risk_free_rate}")
    
    def calculate_alpha_beta(self, strategy_returns: pd.Series, 
                           benchmark_returns: pd.Series) -> Dict:
        """
        Calculate comprehensive alpha/beta metrics.
        
        Args:
            strategy_returns: Strategy returns series
            benchmark_returns: Benchmark returns series
            
        Returns:
            Dictionary with alpha/beta metrics
        """
        try:
            # Align dates between strategy and benchmark
            aligned_data = self._align_returns(strategy_returns, benchmark_returns)
            
            if len(aligned_data) < 30:  # Need sufficient data
                logger.warning("Insufficient aligned data for alpha/beta calculations")
                return {}
                
            strategy_aligned = aligned_data['strategy']
            benchmark_aligned = aligned_data['benchmark']
            
            # Convert annual risk-free rate to daily
            daily_rf = (1 + self.risk_free_rate) ** (1/252) - 1
            
            # Remove risk-free rate from both series
            strategy_excess = strategy_aligned - daily_rf
            benchmark_excess = benchmark_aligned - daily_rf
            
            metrics = {}
            
            # Calculate beta using linear regression
            metrics['beta'] = self._calculate_beta(strategy_excess, benchmark_excess)
            
            # Calculate alpha (Jenson Alpha)
            metrics['alpha'] = self._calculate_alpha(strategy_excess, benchmark_excess, metrics['beta'])
            
            # Calculate correlation and R-squared
            correlation = strategy_excess.corr(benchmark_excess)
            metrics['r_squared'] = correlation ** 2
            
            # Information Ratio
            metrics['information_ratio'] = self._calculate_information_ratio(strategy_excess, benchmark_excess)
            
            # Tracking Error
            metrics['tracking_error'] = self._calculate_tracking_error(strategy_excess, benchmark_excess)
            
            # Additional metrics
            metrics['correlation'] = correlation
            metrics['strategy_volatility'] = strategy_aligned.std() * np.sqrt(252)
            metrics['benchmark_volatility'] = benchmark_aligned.std() * np.sqrt(252)
            metrics['data_points'] = len(aligned_data)
            
            # Excess return metrics
            strategy_annual_return = strategy_aligned.mean() * 252
            benchmark_annual_return = benchmark_aligned.mean() * 252
            excess_return = strategy_annual_return - benchmark_annual_return
            
            metrics['excess_return'] = excess_return
            metrics['strategy_annual_return'] = strategy_annual_return
            metrics['benchmark_annual_return'] = benchmark_annual_return
            
            # Alpha and Beta interpretation
            metrics['alpha_interpretation'] = self._interpret_alpha(metrics['alpha'])
            metrics['beta_interpretation'] = self._interpret_beta(metrics['beta'])
            
            logger.info(f"Calculated alpha/beta metrics with {len(aligned_data)} data points")
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating alpha/beta metrics: {e}")
            return {}
    
    def _align_returns(self, strategy_returns: pd.Series, 
                      benchmark_returns: pd.Series) -> pd.DataFrame:
        """Align strategy and benchmark returns by date."""
        # Ensure proper datetime index
        strategy_returns = pd.to_datetime(strategy_returns.index)
        benchmark_returns = pd.to_datetime(benchmark_returns.index)
        
        # Combine and drop NaN values
        aligned_data = pd.DataFrame({
            'strategy': strategy_returns,
            'benchmark': benchmark_returns
        }).dropna()
        
        return aligned_data
    
    def _calculate_beta(self, strategy_excess: pd.Series, 
                       benchmark_excess: pd.Series) -> float:
        """Calculate beta using linear regression."""
        try:
            # Linear regression: strategy = alpha + beta * benchmark + error
            slope, _ = np.polyfit(benchmark_excess, strategy_excess, 1)
            return slope
        except Exception as e:
            logger.error(f"Error calculating beta: {e}")
            return 0.0
    
    def _calculate_alpha(self, strategy_excess: pd.Series, 
                        benchmark_excess: pd.Series, beta: float) -> float:
        """Calculate alpha using CAPM formula."""
        try:
            # Convert annual risk-free rate to daily
            daily_rf = (1 + self.risk_free_rate) ** (1/252) - 1
            
            # Alpha = Strategy return - Risk-free rate - Beta * (Benchmark return - Risk-free rate)
            strategy_mean_return = strategy_excess.mean()
            benchmark_mean_return = benchmark_excess.mean()
            
            alpha_daily = strategy_mean_return - (beta * benchmark_mean_return)
            alpha_annual = alpha_daily * 252  # Convert to annual percentage
            
            return alpha_annual
            
        except Exception as e:
            logger.error(f"Error calculating alpha: {e}")
            return 0.0
    
    def _calculate_information_ratio(self, strategy_excess: pd.Series, 
                                   benchmark_excess: pd.Series) -> float:
        """Calculate information ratio."""
        try:
            # Excess returns of strategy over benchmark
            excess_returns = strategy_excess - benchmark_excess
            
            # Information ratio = Mean excess return / Standard deviation of excess returns
            if excess_returns.std() == 0:
                return 0.0
                
            return excess_returns.mean() / excess_returns.std() * np.sqrt(252)
            
        except Exception as e:
            logger.error(f"Error calculating information ratio: {e}")
            return 0.0
    
    def _calculate_tracking_error(self, strategy_excess: pd.Series, 
                                benchmark_excess: pd.Series) -> float:
        """Calculate tracking error."""
        try:
            # Excess returns of strategy over benchmark
            excess_returns = strategy_excess - benchmark_excess
            
            # Tracking error = Standard deviation of excess returns (annualized)
            return excess_returns.std() * np.sqrt(252)
            
        except Exception as e:
            logger.error(f"Error calculating tracking error: {e}")
            return 0.0
    
    def _interpret_alpha(self, alpha: float) -> str:
        """Provide interpretation of alpha value."""
        if alpha > 0.05:  # > 5% annual alpha
            return "Excellent alpha generation"
        elif alpha > 0.02:  # > 2% annual alpha
            return "Good alpha generation"
        elif alpha > 0:  # > 0% annual alpha
            return "Positive alpha"
        elif alpha > -0.02:  # > -2% annual alpha
            return "Minimal negative alpha"
        else:  # < -2% annual alpha
            return "Significant negative alpha"
    
    def _interpret_beta(self, beta: float) -> str:
        """Provide interpretation of beta value."""
        if beta > 1.5:
            return "Highly volatile vs market"
        elif beta > 1.2:
            return "More volatile than market"
        elif beta > 0.8:
            return "Similar volatility to market"
        elif beta > 0.2:
            return "Less volatile than market"
        else:
            return "Very low volatility (defensive)"
    
    def calculate_rolling_metrics(self, strategy_returns: pd.Series, 
                                benchmark_returns: pd.Series, 
                                window: int = 252) -> Dict:
        """
        Calculate rolling alpha/beta metrics over time.
        
        Args:
            strategy_returns: Strategy returns series
            benchmark_returns: Benchmark returns series
            window: Rolling window size (default 252 for 1 year)
            
        Returns:
            Dictionary with rolling metrics time series
        """
        try:
            aligned_data = self._align_returns(strategy_returns, benchmark_returns)
            
            if len(aligned_data) < window:
                logger.warning("Insufficient data for rolling calculations")
                return {}
            
            strategy_aligned = aligned_data['strategy']
            benchmark_aligned = aligned_data['benchmark']
            
            # Convert to excess returns
            daily_rf = (1 + self.risk_free_rate) ** (1/252) - 1
            strategy_excess = strategy_aligned - daily_rf
            benchmark_excess = benchmark_aligned - daily_rf
            
            # Rolling calculations
            rolling_metrics = {}
            
            # Rolling beta
            rolling_beta = []
            rolling_alpha = []
            rolling_ir = []
            
            for i in range(window, len(strategy_excess)):
                window_strategy = strategy_excess.iloc[i-window:i]
                window_benchmark = benchmark_excess.iloc[i-window:i]
                
                beta = self._calculate_beta(window_strategy, window_benchmark)
                alpha = self._calculate_alpha(window_strategy, window_benchmark, beta)
                ir = self._calculate_information_ratio(window_strategy, window_benchmark)
                
                rolling_beta.append(beta)
                rolling_alpha.append(alpha)
                rolling_ir.append(ir)
            
            # Create time series
            dates = strategy_excess.index[window:]
            
            rolling_metrics['rolling_beta'] = pd.Series(rolling_beta, index=dates)
            rolling_metrics['rolling_alpha'] = pd.Series(rolling_alpha, index=dates)
            rolling_metrics['rolling_information_ratio'] = pd.Series(rolling_ir, index=dates)
            
            # Summary statistics
            rolling_metrics['beta_mean'] = np.mean(rolling_beta)
            rolling_metrics['beta_std'] = np.std(rolling_beta)
            rolling_metrics['alpha_mean'] = np.mean(rolling_alpha)
            rolling_metrics['alpha_std'] = np.std(rolling_alpha)
            rolling_metrics['ir_mean'] = np.mean(rolling_ir)
            
            logger.info(f"Calculated rolling metrics with {window}-day window")
            return rolling_metrics
            
        except Exception as e:
            logger.error(f"Error calculating rolling metrics: {e}")
            return {}
    
    def create_comparison_chart_data(self, strategy_returns: pd.Series, 
                                   benchmark_returns: pd.Series) -> Dict:
        """
        Create data for comparison charts.
        
        Args:
            strategy_returns: Strategy returns series
            benchmark_returns: Benchmark returns series
            
        Returns:
            Dictionary with chart data
        """
        try:
            aligned_data = self._align_returns(strategy_returns, benchmark_returns)
            
            strategy_aligned = aligned_data['strategy']
            benchmark_aligned = aligned_data['benchmark']
            
            # Calculate cumulative returns
            strategy_cumulative = (1 + strategy_aligned).cumprod()
            benchmark_cumulative = (1 + benchmark_aligned).cumprod()
            
            # Calculate rolling correlation (30-day)
            rolling_corr = strategy_aligned.rolling(30).corr(benchmark_aligned)
            
            # Calculate rolling beta (60-day)
            rolling_beta_series = strategy_aligned.rolling(60).apply(
                lambda x: np.polyfit(
                    benchmark_aligned.iloc[x.index - strategy_aligned.index[0]],
                    x, 1
                )[0] if len(x) == 60 else np.nan
            )
            
            chart_data = {
                'dates': aligned_data.index,
                'strategy_cumulative': strategy_cumulative,
                'benchmark_cumulative': benchmark_cumulative,
                'rolling_correlation': rolling_corr,
                'rolling_beta': rolling_beta_series
            }
            
            logger.info("Created comparison chart data")
            return chart_data
            
        except Exception as e:
            logger.error(f"Error creating comparison chart data: {e}")
            return {}
    
    def get_metric_summary(self, metrics: Dict) -> str:
        """Get a human-readable summary of alpha/beta metrics."""
        if not metrics:
            return "No metrics available"
            
        summary = f"""
Alpha/Beta Analysis Summary:
- Alpha (Annual): {metrics.get('alpha', 0):.2%} ({metrics.get('alpha_interpretation', 'N/A')})
- Beta: {metrics.get('beta', 0):.2f} ({metrics.get('beta_interpretation', 'N/A')})
- R-squared: {metrics.get('r_squared', 0):.2f}
- Information Ratio: {metrics.get('information_ratio', 0):.2f}
- Tracking Error: {metrics.get('tracking_error', 0):.2%}
- Correlation: {metrics.get('correlation', 0):.2f}

Returns (Annual):
- Strategy: {metrics.get('strategy_annual_return', 0):.2%}
- Benchmark: {metrics.get('benchmark_annual_return', 0):.2%}
- Excess: {metrics.get('excess_return', 0):.2%}
        """
        
        return summary.strip()
