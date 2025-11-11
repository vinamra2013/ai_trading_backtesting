#!/usr/bin/env python3
"""
QuantStats Integration - Epic 17: US-17.6
Advanced metrics calculation using QuantStats library for 30+ performance metrics.

This module provides comprehensive quantstats integration for trading backtests:
- Risk metrics: Sortino, Calmar, Omega, Tail Ratio, VaR, CVaR
- Return metrics: CAGR, total return, average returns
- Benchmark metrics: Alpha, Beta, R², Information Ratio
- Distribution metrics: Skew, Kurtosis, Win Rate, Payoff Ratio
- HTML tearsheets for comprehensive analysis
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
import warnings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress quantstats warnings for cleaner output
warnings.filterwarnings('ignore', category=FutureWarning)

try:
    import quantstats as qs
    QUANTSTATS_AVAILABLE = True
    logger.info("QuantStats library loaded successfully")
except ImportError:
    QUANTSTATS_AVAILABLE = False
    logger.warning("QuantStats library not available. Install with: pip install quantstats")

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("Plotly not available for advanced visualizations")


class QuantStatsAnalyzer:
    """
    Advanced metrics analyzer using QuantStats for comprehensive backtest analysis.
    
    Provides 30+ advanced metrics beyond basic Backtrader analyzers:
    - Risk-adjusted performance metrics
    - Return distribution analysis
    - Benchmark comparison metrics
    - HTML tearsheet generation
    
    Example usage:
        analyzer = QuantStatsAnalyzer(benchmark='SPY')
        metrics = analyzer.calculate_metrics(returns_series)
        tearsheet_path = analyzer.generate_tearsheet(returns_series, 'strategy_name')
    """
    
    def __init__(self, benchmark: str = 'SPY', risk_free_rate: float = 0.02):
        """
        Initialize QuantStats analyzer.
        
        Args:
            benchmark: Benchmark ticker for alpha/beta calculations
            risk_free_rate: Annual risk-free rate for calculations
        """
        self.benchmark = benchmark
        self.risk_free_rate = risk_free_rate
        
        if not QUANTSTATS_AVAILABLE:
            raise ImportError("QuantStats library required. Install with: pip install quantstats")
            
        # Set quantstats options for cleaner output (if available)
        try:
            qs.utils.silent_mode(silent=True)
        except AttributeError:
            # silent_mode not available in this version, skip
            pass
        
        logger.info(f"QuantStatsAnalyzer initialized with benchmark: {benchmark}")
    
    def calculate_metrics(self, returns: pd.Series, benchmark_returns: Optional[pd.Series] = None) -> Dict:
        """
        Calculate comprehensive metrics using quantstats.
        
        Args:
            returns: Strategy returns series (daily returns)
            benchmark_returns: Optional benchmark returns series
            
        Returns:
            Dictionary with comprehensive metrics
        """
        if not QUANTSTATS_AVAILABLE:
            return self._calculate_fallback_metrics(returns)
            
        try:
            # Ensure returns are properly formatted
            returns = self._format_returns(returns)
            
            metrics = {}
            
            # Basic performance metrics
            metrics.update(self._calculate_basic_metrics(returns))
            
            # Risk metrics
            metrics.update(self._calculate_risk_metrics(returns))
            
            # Return metrics
            metrics.update(self._calculate_return_metrics(returns))
            
            # Distribution metrics
            metrics.update(self._calculate_distribution_metrics(returns))
            
            # Benchmark metrics (if benchmark provided)
            if benchmark_returns is not None:
                metrics.update(self._calculate_benchmark_metrics(returns, benchmark_returns))
            elif self.benchmark:
                # Try to fetch benchmark data
                benchmark_returns = self._get_benchmark_data(returns.index)
                if benchmark_returns is not None:
                    metrics.update(self._calculate_benchmark_metrics(returns, benchmark_returns))
            
            logger.info(f"Calculated {len(metrics)} advanced metrics")
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return self._calculate_fallback_metrics(returns)
    
    def _format_returns(self, returns: pd.Series) -> pd.Series:
        """Format returns series for quantstats calculations."""
        # Remove any infinite or NaN values
        returns = returns.replace([np.inf, -np.inf], np.nan).dropna()
        
        # Ensure daily frequency
        if len(returns) > 0:
            returns.index = pd.to_datetime(returns.index)
            returns = returns.sort_index()
        
        return returns
    
    def _calculate_basic_metrics(self, returns: pd.Series) -> Dict:
        """Calculate basic performance metrics."""
        metrics = {}
        
        try:
            # Total return
            metrics['total_return'] = qs.stats.comp(returns)
            
            # Compound Annual Growth Rate (CAGR)
            metrics['cagr'] = qs.stats.cagr(returns)
            
            # Volatility
            metrics['annual_volatility'] = qs.stats.volatility(returns)
            
            # Sharpe ratio
            metrics['sharpe_ratio'] = qs.stats.sharpe(returns, rf=self.risk_free_rate)
            
            # Sortino ratio
            metrics['sortino_ratio'] = qs.stats.sortino(returns, rf=self.risk_free_rate)
            
            # Calmar ratio
            metrics['calmar_ratio'] = qs.stats.calmar(returns)
            
        except Exception as e:
            logger.warning(f"Error calculating basic metrics: {e}")
            
        return metrics
    
    def _calculate_risk_metrics(self, returns: pd.Series) -> Dict:
        """Calculate risk-related metrics."""
        metrics = {}
        
        try:
            # Maximum drawdown
            metrics['max_drawdown'] = qs.stats.max_drawdown(returns)
            
            # Value at Risk (95%)
            metrics['var_95'] = qs.stats.var(returns, confidence=0.95)
            
            # Conditional Value at Risk (95%)
            metrics['cvar_95'] = qs.stats.cvar(returns, confidence=0.95)
            
            # Tail ratio
            metrics['tail_ratio'] = qs.stats.tail_ratio(returns)
            
            # Omega ratio
            metrics['omega_ratio'] = qs.stats.omega(returns, rf=self.risk_free_rate)
            
        except Exception as e:
            logger.warning(f"Error calculating risk metrics: {e}")
            
        return metrics
    
    def _calculate_return_metrics(self, returns: pd.Series) -> Dict:
        """Calculate return-related metrics."""
        metrics = {}
        
        try:
            # Best and worst days
            metrics['best_day'] = returns.max()
            metrics['worst_day'] = returns.min()
            
            # Best and worst months
            monthly_returns = qs.stats.monthly_returns(returns)
            metrics['best_month'] = monthly_returns.max().max()
            metrics['worst_month'] = monthly_returns.min().min()
            
            # Win rate
            metrics['win_rate'] = (returns > 0).mean()
            
            # Profit factor
            gross_profit = returns[returns > 0].sum()
            gross_loss = abs(returns[returns < 0].sum())
            metrics['profit_factor'] = gross_profit / gross_loss if gross_loss != 0 else np.inf
            
            # Average win/loss
            winning_trades = returns[returns > 0]
            losing_trades = returns[returns < 0]
            metrics['avg_win'] = winning_trades.mean() if len(winning_trades) > 0 else 0
            metrics['avg_loss'] = losing_trades.mean() if len(losing_trades) > 0 else 0
            
        except Exception as e:
            logger.warning(f"Error calculating return metrics: {e}")
            
        return metrics
    
    def _calculate_distribution_metrics(self, returns: pd.Series) -> Dict:
        """Calculate distribution-related metrics."""
        metrics = {}
        
        try:
            # Skewness
            metrics['skewness'] = returns.skew()
            
            # Kurtosis
            metrics['kurtosis'] = returns.kurtosis()
            
            # Jarque-Bera test (normality test) - Not available in current QuantStats version
            # jb_stat, jb_pvalue = qs.stats.jarque_bera(returns)
            # metrics['jarque_bera_stat'] = jb_stat
            # metrics['jarque_bera_pvalue'] = jb_pvalue
            
            # Rolling volatility (30-day)
            rolling_vol = returns.rolling(30).std() * np.sqrt(252)
            metrics['avg_rolling_volatility'] = rolling_vol.mean()
            
        except Exception as e:
            logger.warning(f"Error calculating distribution metrics: {e}")
            
        return metrics
    
    def _calculate_benchmark_metrics(self, returns: pd.Series, benchmark_returns: pd.Series) -> Dict:
        """Calculate benchmark comparison metrics."""
        metrics = {}
        
        try:
            # Align dates between strategy and benchmark
            aligned_data = pd.DataFrame({
                'strategy': returns,
                'benchmark': benchmark_returns
            }).dropna()
            
            if len(aligned_data) < 30:  # Need sufficient data
                logger.warning("Insufficient aligned data for benchmark calculations")
                return metrics
                
            strategy_aligned = aligned_data['strategy']
            benchmark_aligned = aligned_data['benchmark']
            
            # Calculate Alpha and Beta manually using standard formulas
            # Beta = Covariance(strategy, benchmark) / Variance(benchmark)
            cov_matrix = np.cov(strategy_aligned, benchmark_aligned)
            beta = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] != 0 else 0
            metrics['beta'] = beta

            # Alpha = (Strategy Return - RF) - Beta * (Benchmark Return - RF)
            # Simplified: assuming RF = 0 for now
            avg_strategy_return = strategy_aligned.mean()
            avg_benchmark_return = benchmark_aligned.mean()
            alpha = avg_strategy_return - beta * avg_benchmark_return
            metrics['alpha'] = alpha

            # Information ratio
            metrics['information_ratio'] = qs.stats.information_ratio(strategy_aligned, benchmark_aligned)

            # R-squared
            metrics['r_squared'] = qs.stats.r_squared(strategy_aligned, benchmark_aligned)

            # Tracking error = StdDev(Strategy Return - Benchmark Return)
            tracking_error = (strategy_aligned - benchmark_aligned).std()
            metrics['tracking_error'] = tracking_error
            
        except Exception as e:
            logger.warning(f"Error calculating benchmark metrics: {e}")
            
        return metrics
    
    def _get_benchmark_data(self, date_index: pd.DatetimeIndex) -> Optional[pd.Series]:
        """Fetch benchmark data for the given date range."""
        try:
            # For now, return None - in production this would fetch real data
            # Example: import yfinance as yf; data = yf.download(self.benchmark, start=date_index[0], end=date_index[-1])
            logger.info(f"Benchmark data fetch not implemented for {self.benchmark}")
            return None
        except Exception as e:
            logger.warning(f"Could not fetch benchmark data: {e}")
            return None
    
    def _calculate_fallback_metrics(self, returns: pd.Series) -> Dict:
        """Calculate basic metrics when quantstats is not available."""
        metrics = {}
        
        try:
            # Basic statistics
            metrics['total_return'] = returns.sum()
            metrics['annual_return'] = returns.mean() * 252
            metrics['annual_volatility'] = returns.std() * np.sqrt(252)
            metrics['sharpe_ratio'] = metrics['annual_return'] / metrics['annual_volatility'] if metrics['annual_volatility'] != 0 else 0
            metrics['max_drawdown'] = self._calculate_max_drawdown(returns)
            metrics['win_rate'] = (returns > 0).mean()
            
        except Exception as e:
            logger.error(f"Error calculating fallback metrics: {e}")
            
        return metrics
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown from returns."""
        try:
            # Calculate cumulative returns
            cumulative = (1 + returns).cumprod()
            
            # Calculate running maximum
            running_max = cumulative.expanding().max()
            
            # Calculate drawdown
            drawdown = (cumulative - running_max) / running_max
            
            # Return maximum drawdown (as positive number)
            return abs(drawdown.min())
            
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return 0.0
    
    def generate_tearsheet(self, returns: pd.Series, strategy_name: str, 
                          output_path: Optional[str] = None) -> str:
        """
        Generate HTML tearsheet with comprehensive analysis.
        
        Args:
            returns: Strategy returns series
            strategy_name: Name for the strategy
            output_path: Optional output file path
            
        Returns:
            Path to generated tearsheet HTML file
        """
        if not QUANTSTATS_AVAILABLE:
            logger.warning("Cannot generate tearsheet: QuantStats not available")
            return ""
            
        try:
            # Format returns
            returns = self._format_returns(returns)
            
            # Generate default output path if not provided
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"results/tearsheets/{strategy_name}_{timestamp}.html"
                
                # Ensure directory exists
                import os
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Generate tearsheet
            qs.reports.full(returns, output=output_path, title=f"{strategy_name} - Performance Report")
            
            logger.info(f"Tearsheet generated: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating tearsheet: {e}")
            return ""
    
    def create_performance_charts(self, returns: pd.Series, strategy_name: str) -> Dict[str, str]:
        """
        Create performance charts using Plotly.
        
        Args:
            returns: Strategy returns series
            strategy_name: Name for the strategy
            
        Returns:
            Dictionary mapping chart names to file paths
        """
        if not PLOTLY_AVAILABLE:
            logger.warning("Cannot create charts: Plotly not available")
            return {}
            
        try:
            returns = self._format_returns(returns)
            chart_paths = {}
            
            # Create results directory
            import os
            os.makedirs("results/charts", exist_ok=True)
            
            # 1. Equity Curve
            cumulative_returns = (1 + returns).cumprod()
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=cumulative_returns.index,
                y=cumulative_returns.values,
                mode='lines',
                name='Equity Curve',
                line=dict(color='blue', width=2)
            ))
            fig.update_layout(
                title=f'{strategy_name} - Equity Curve',
                xaxis_title='Date',
                yaxis_title='Cumulative Return',
                hovermode='x unified'
            )
            chart_path = f"results/charts/{strategy_name}_equity_curve.html"
            fig.write_html(chart_path)
            chart_paths['equity_curve'] = chart_path
            
            # 2. Drawdown Chart
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=drawdown.index,
                y=drawdown.values * 100,  # Convert to percentage
                mode='lines',
                name='Drawdown',
                fill='tonexty',
                line=dict(color='red', width=1)
            ))
            fig.update_layout(
                title=f'{strategy_name} - Drawdown Analysis',
                xaxis_title='Date',
                yaxis_title='Drawdown (%)',
                hovermode='x unified'
            )
            chart_path = f"results/charts/{strategy_name}_drawdown.html"
            fig.write_html(chart_path)
            chart_paths['drawdown'] = chart_path
            
            # 3. Monthly Returns Heatmap
            monthly_returns = returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
            monthly_returns_matrix = monthly_returns.groupby([
                monthly_returns.index.year, 
                monthly_returns.index.month
            ]).first().unstack()
            
            fig = px.imshow(
                monthly_returns_matrix.values * 100,  # Convert to percentage
                x=monthly_returns_matrix.columns,
                y=monthly_returns_matrix.index,
                color_continuous_scale='RdYlGn',
                title=f'{strategy_name} - Monthly Returns Heatmap (%)'
            )
            fig.update_layout(
                xaxis_title='Month',
                yaxis_title='Year'
            )
            chart_path = f"results/charts/{strategy_name}_monthly_heatmap.html"
            fig.write_html(chart_path)
            chart_paths['monthly_heatmap'] = chart_path
            
            logger.info(f"Generated {len(chart_paths)} performance charts")
            return chart_paths
            
        except Exception as e:
            logger.error(f"Error creating performance charts: {e}")
            return {}
    
    def get_metric_categories(self) -> Dict[str, List[str]]:
        """Get categorized list of available metrics."""
        return {
            'performance': [
                'total_return', 'annual_return', 'sharpe_ratio', 'sortino_ratio', 'calmar_ratio'
            ],
            'risk': [
                'max_drawdown', 'var_95', 'cvar_95', 'tail_ratio', 'omega_ratio', 'annual_volatility'
            ],
            'returns': [
                'best_day', 'worst_day', 'best_month', 'worst_month', 
                'win_rate', 'profit_factor', 'avg_win', 'avg_loss'
            ],
            'distribution': [
                'skewness', 'kurtosis', 'avg_rolling_volatility'
            ],
            'benchmark': [
                'information_ratio', 'r_squared'
            ]
        }
