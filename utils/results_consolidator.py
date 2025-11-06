#!/usr/bin/env python3
"""
Results Consolidator for Parallel Backtesting and Strategy Ranking
Epic 20: US-20.3 - Results Consolidation System
Epic 21: Strategy Ranking & Portfolio Optimizer

Consolidates results from parallel backtest executions into a unified DataFrame.
Extended for strategy ranking and portfolio optimization workflows.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class ResultsConsolidator:
    """Consolidates parallel backtest results into unified DataFrame"""

    # Expected result columns from backtest execution
    EXPECTED_METRICS = [
        'sharpe_ratio', 'sortino_ratio', 'max_drawdown', 'win_rate',
        'profit_factor', 'trade_count', 'avg_trade_return', 'total_return',
        'annual_return', 'volatility', 'calmar_ratio', 'alpha', 'beta'
    ]

    def __init__(self):
        """Initialize consolidator"""
        self.consolidated_data = []
        logger.info("Results consolidator initialized")

    def consolidate(self, results: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Consolidate list of backtest results into DataFrame

        Args:
            results: List of individual backtest result dictionaries

        Returns:
            Consolidated DataFrame with all results
        """
        if not results:
            logger.warning("No results to consolidate")
            return pd.DataFrame()

        logger.info(f"Consolidating {len(results)} backtest results")

        # Extract successful results
        successful_results = [r for r in results if r.get('status') == 'success']
        failed_results = [r for r in results if r.get('status') != 'success']

        if failed_results:
            logger.warning(f"{len(failed_results)} backtests failed - excluding from consolidation")

        if not successful_results:
            logger.error("No successful results to consolidate")
            return pd.DataFrame()

        # Process successful results
        processed_results = []
        for result in successful_results:
            try:
                processed_result = self._process_single_result(result)
                if processed_result:
                    processed_results.append(processed_result)
            except Exception as e:
                logger.error(f"Failed to process result for {result.get('symbol', 'unknown')}: {e}")

        if not processed_results:
            logger.error("No valid results after processing")
            return pd.DataFrame()

        # Create consolidated DataFrame
        df = pd.DataFrame(processed_results)

        # Ensure consistent column ordering
        base_columns = ['symbol', 'strategy', 'batch_id', 'job_id', 'execution_timestamp']
        metric_columns = [col for col in self.EXPECTED_METRICS if col in df.columns]
        other_columns = [col for col in df.columns if col not in base_columns + metric_columns]

        ordered_columns = base_columns + metric_columns + other_columns
        df = df[ordered_columns]

        # Sort by Sharpe ratio descending for easy analysis
        if 'sharpe_ratio' in df.columns:
            df = df.sort_values('sharpe_ratio', ascending=False, na_position='last')

        logger.info(f"Consolidated {len(df)} successful backtest results")
        return df

    def _process_single_result(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single backtest result into standardized format"""
        try:
            # Extract basic information
            symbol = result.get('symbol', 'unknown')
            strategy_path = result.get('strategy_path', '')
            strategy_name = Path(strategy_path).stem if strategy_path else 'unknown'

            # Extract performance metrics (handle both old and new formats)
            metrics = result.get('performance_metrics', result.get('performance', {}))
            analyzer_results = result.get('analyzer_results', {})

            # Build consolidated result
            consolidated = {
                'symbol': symbol,
                'strategy': strategy_name,
                'strategy_path': strategy_path,
                'batch_id': result.get('batch_id'),
                'job_id': result.get('job_id'),
                'execution_timestamp': result.get('execution_timestamp'),
                'worker_process_id': result.get('worker_process_id'),
            }

            # Extract metrics from various sources
            self._extract_performance_metrics(consolidated, metrics, analyzer_results)

            # Add trade statistics
            self._extract_trade_statistics(consolidated, result)

            # Add risk metrics (skip if regime_analysis causes issues)
            try:
                self._extract_risk_metrics(consolidated, result)
            except Exception as e:
                logger.warning(f"Failed to extract risk metrics: {e}")
                # Use performance metrics as fallback
                if 'max_drawdown' not in consolidated and 'max_drawdown' in metrics:
                    consolidated['max_drawdown'] = metrics['max_drawdown']
                if 'volatility' not in consolidated:
                    consolidated['volatility'] = 0.0

            return consolidated

        except Exception as e:
            logger.error(f"Error processing result: {e}")
            logger.error(f"Result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def _extract_performance_metrics(self, consolidated: Dict[str, Any],
                                   metrics: Dict[str, Any],
                                   analyzer_results: Dict[str, Any]) -> None:
        """Extract performance metrics from result data"""
        # Direct metrics from result
        for metric in self.EXPECTED_METRICS:
            if metric in metrics:
                consolidated[metric] = metrics[metric]

        # Extract from analyzer results (Backtrader analyzers)
        if 'sharpe' in analyzer_results:
            sharpe_data = analyzer_results['sharpe']
            if isinstance(sharpe_data, dict) and 'sharperatio' in sharpe_data:
                consolidated['sharpe_ratio'] = sharpe_data['sharperatio']

        if 'drawdown' in analyzer_results:
            dd_data = analyzer_results['drawdown']
            if isinstance(dd_data, dict) and 'max' in dd_data:
                consolidated['max_drawdown'] = dd_data['max']['drawdown']

        if 'returns' in analyzer_results:
            ret_data = analyzer_results['returns']
            if isinstance(ret_data, dict):
                if 'rnorm100' in ret_data:
                    consolidated['total_return'] = ret_data['rnorm100']
                if 'ravg' in ret_data:
                    consolidated['avg_annual_return'] = ret_data['ravg']

        # Handle QuantStats metrics if available
        quantstats_metrics = analyzer_results.get('quantstats', {})
        for metric in ['sharpe_ratio', 'sortino_ratio', 'calmar_ratio', 'alpha', 'beta']:
            if metric in quantstats_metrics:
                consolidated[metric] = quantstats_metrics[metric]

    def _extract_trade_statistics(self, consolidated: Dict[str, Any],
                                result: Dict[str, Any]) -> None:
        """Extract trade-related statistics"""
        # Handle both old format (trades list) and new format (trading dict)
        trading_data = result.get('trading', {})
        trades = result.get('trades', [])

        if trading_data:
            # Use trading data from BacktestRunner
            consolidated['trade_count'] = trading_data.get('total_trades', 0)
            consolidated['win_rate'] = trading_data.get('win_rate', 0.0)
            consolidated['avg_trade_return'] = trading_data.get('avg_win', 0.0) if trading_data.get('avg_win', 0) != 0 else 0.0
            consolidated['profit_factor'] = trading_data.get('profit_factor', 0.0)
        elif trades:
            # Fallback to old format
            consolidated['trade_count'] = len(trades)
            winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
            consolidated['win_rate'] = len(winning_trades) / len(trades) if trades else 0.0
            trade_returns = [t.get('pnl', 0) for t in trades if t.get('pnl', 0) != 0]
            consolidated['avg_trade_return'] = np.mean(trade_returns) if trade_returns else 0.0
            gross_profit = sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0)
            gross_loss = abs(sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0))
            consolidated['profit_factor'] = gross_profit / gross_loss if gross_loss > 0 else 0.0
        else:
            # No trading data available
            consolidated['trade_count'] = 0
            consolidated['win_rate'] = 0.0
            consolidated['avg_trade_return'] = 0.0
            consolidated['profit_factor'] = 0.0
            consolidated['profit_factor'] = float('inf') if gross_profit > 0 else 0.0

    def _extract_risk_metrics(self, consolidated: Dict[str, Any],
                            result: Dict[str, Any]) -> None:
        """Extract risk-related metrics"""
        # Volatility (annualized)
        returns = result.get('returns', [])
        if returns and len(returns) > 1:
            returns_series = pd.Series(returns)
            consolidated['volatility'] = returns_series.std() * np.sqrt(252)  # Annualized

        # Maximum drawdown from equity curve
        equity_curve = result.get('equity_curve', [])
        if equity_curve and len(equity_curve) > 1:
            equity_series = pd.Series(equity_curve)
            peak = equity_series.expanding().max()
            drawdown = (equity_series - peak) / peak
            consolidated['max_drawdown'] = abs(drawdown.min())

    def save_to_csv(self, df: pd.DataFrame, output_path: str) -> None:
        """Save consolidated results to CSV"""
        try:
            df.to_csv(output_path, index=False)
            logger.info(f"Results saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save results to {output_path}: {e}")

    def generate_summary_report(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate summary statistics report"""
        if df.empty:
            return {'error': 'No data to summarize'}

        summary = {
            'total_backtests': len(df),
            'unique_symbols': df['symbol'].nunique(),
            'unique_strategies': df['strategy'].nunique(),
            'symbol_strategy_combinations': len(df),
            'execution_time_seconds': df.get('execution_time_seconds', pd.Series()).max(),
        }

        # Performance summary
        if 'sharpe_ratio' in df.columns:
            summary.update({
                'best_sharpe_ratio': df['sharpe_ratio'].max(),
                'worst_sharpe_ratio': df['sharpe_ratio'].min(),
                'avg_sharpe_ratio': df['sharpe_ratio'].mean(),
                'sharpe_ratio_std': df['sharpe_ratio'].std(),
            })

        if 'total_return' in df.columns:
            summary.update({
                'best_total_return': df['total_return'].max(),
                'avg_total_return': df['total_return'].mean(),
            })

        if 'max_drawdown' in df.columns:
            summary.update({
                'best_max_drawdown': df['max_drawdown'].min(),  # Lower is better
                'avg_max_drawdown': df['max_drawdown'].mean(),
            })

        # Top performers
        if 'sharpe_ratio' in df.columns and not df.empty:
            top_performers = df.nlargest(5, 'sharpe_ratio')[['symbol', 'strategy', 'sharpe_ratio']]
            summary['top_5_by_sharpe'] = top_performers.to_dict('records')

        return summary

    def filter_results(self, df: pd.DataFrame,
                      min_sharpe: Optional[float] = None,
                      max_drawdown: Optional[float] = None,
                      min_trades: Optional[int] = None) -> pd.DataFrame:
        """Filter results based on criteria"""
        filtered_df = df.copy()

        if min_sharpe is not None and 'sharpe_ratio' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['sharpe_ratio'] >= min_sharpe]

        if max_drawdown is not None and 'max_drawdown' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['max_drawdown'] <= max_drawdown]

        if min_trades is not None and 'trade_count' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['trade_count'] >= min_trades]

        logger.info(f"Filtered results: {len(filtered_df)} of {len(df)} backtests remain")
        return filtered_df


class RankingResultsConsolidator:
    """
    Consolidates backtest results for strategy ranking and portfolio optimization.

    Epic 21: Strategy Ranking & Portfolio Optimizer
    Handles loading, validation, and aggregation of backtest results for ranking workflows.
    """

    def __init__(self, results_dir: str = "results/backtests"):
        """
        Initialize consolidator.

        Args:
            results_dir: Directory containing backtest result JSON files
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"RankingResultsConsolidator initialized with directory: {results_dir}")

    def load_all_results(self, pattern: str = "*.json") -> List[Dict[str, Any]]:
        """
        Load all backtest results matching the pattern.

        Args:
            pattern: Glob pattern for result files (default: *.json)

        Returns:
            List of backtest result dictionaries
        """
        results = []

        for result_file in self.results_dir.glob(pattern):
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    data['_source_file'] = str(result_file.name)
                    results.append(data)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Skipping invalid file {result_file}: {e}")
                continue

        logger.info(f"Loaded {len(results)} backtest results")
        return results

    def consolidate_to_dataframe(self, results: Optional[List[Dict]] = None) -> pd.DataFrame:
        """
        Consolidate results into a pandas DataFrame for ranking analysis.

        Args:
            results: List of backtest results (if None, loads all)

        Returns:
            DataFrame with consolidated results optimized for ranking
        """
        if results is None:
            results = self.load_all_results()

        if not results:
            logger.warning("No results to consolidate")
            return pd.DataFrame()

        # Extract key fields for ranking
        consolidated_data = []

        for result in results:
            try:
                # Extract basic info
                row = {
                    'backtest_id': result.get('backtest_id', 'unknown'),
                    'strategy': result.get('algorithm', 'unknown'),
                    'symbol': result.get('symbol', 'unknown'),
                    'start_date': result.get('period', {}).get('start'),
                    'end_date': result.get('period', {}).get('end'),
                    'status': result.get('status', 'unknown'),
                    'source_file': result.get('_source_file', 'unknown')
                }

                # Extract metrics
                metrics = result.get('metrics', {})

                # Basic performance metrics
                row.update({
                    'total_return': metrics.get('total_return', 0),
                    'annualized_return': metrics.get('annualized_return', 0),
                    'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                    'sortino_ratio': metrics.get('sortino_ratio', 0),
                    'max_drawdown': metrics.get('max_drawdown', 0),
                    'win_rate': metrics.get('win_rate', 0),
                    'profit_factor': metrics.get('profit_factor', 0),
                    'total_trades': result.get('trade_count', 0),
                    'avg_win': metrics.get('avg_win', 0),
                    'avg_loss': metrics.get('avg_loss', 0),
                })

                # Risk metrics
                row.update({
                    'var_95': metrics.get('var_95', 0),
                    'cvar_95': metrics.get('cvar_95', 0),
                    'annual_volatility': metrics.get('annual_volatility', 0),
                    'tail_ratio': metrics.get('tail_ratio', 0),
                    'omega_ratio': metrics.get('omega_ratio', 0),
                })

                # Distribution metrics
                row.update({
                    'skewness': metrics.get('skewness', 0),
                    'kurtosis': metrics.get('kurtosis', 0),
                    'avg_rolling_volatility': metrics.get('avg_rolling_volatility', 0),
                })

                # Benchmark metrics (if available)
                row.update({
                    'beta': metrics.get('beta'),
                    'alpha': metrics.get('alpha'),
                    'information_ratio': metrics.get('information_ratio'),
                    'r_squared': metrics.get('r_squared'),
                    'tracking_error': metrics.get('tracking_error'),
                })

                consolidated_data.append(row)

            except Exception as e:
                logger.warning(f"Error processing result {result.get('backtest_id', 'unknown')}: {e}")
                continue

        df = pd.DataFrame(consolidated_data)

        # Convert percentage fields to decimals if needed
        pct_fields = ['total_return', 'annualized_return', 'max_drawdown', 'win_rate', 'avg_win', 'avg_loss']
        for field in pct_fields:
            if field in df.columns:
                # Check if values are already in decimal form (assume < 10 means decimal)
                df[field] = df[field].apply(lambda x: x if abs(x) < 10 else x / 100)

        logger.info(f"Consolidated {len(df)} results into DataFrame with {len(df.columns)} columns")
        return df

    def get_returns_series(self, results: Optional[List[Dict]] = None) -> pd.DataFrame:
        """
        Extract returns series from results for correlation analysis.

        Args:
            results: List of backtest results

        Returns:
            DataFrame with returns series (dates as index, strategies as columns)
        """
        if results is None:
            results = self.load_all_results()

        returns_data = {}

        for result in results:
            try:
                strategy_name = f"{result.get('algorithm', 'unknown')}_{result.get('symbol', 'unknown')}"
                equity_curve = result.get('equity_curve', [])

                if equity_curve:
                    # Convert equity curve to returns
                    equity_df = pd.DataFrame(equity_curve)
                    if 'date' in equity_df.columns and 'value' in equity_df.columns:
                        equity_df['date'] = pd.to_datetime(equity_df['date'])
                        equity_df = equity_df.set_index('date').sort_index()

                        # Calculate daily returns
                        returns = equity_df['value'].pct_change().dropna()
                        returns_data[strategy_name] = returns

            except Exception as e:
                logger.warning(f"Error extracting returns for {result.get('backtest_id', 'unknown')}: {e}")
                continue

        if returns_data:
            returns_df = pd.DataFrame(returns_data)
            logger.info(f"Extracted returns series for {len(returns_df.columns)} strategies")
            return returns_df
        else:
            logger.warning("No returns series could be extracted")
            return pd.DataFrame()

    def filter_by_criteria(self, df: pd.DataFrame,
                          min_sharpe: float = 0,
                          max_drawdown: float = 1.0,
                          min_trades: int = 10,
                          status_filter: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Filter results by performance criteria for ranking.

        Args:
            df: Consolidated results DataFrame
            min_sharpe: Minimum Sharpe ratio
            max_drawdown: Maximum drawdown (as decimal)
            min_trades: Minimum number of trades
            status_filter: List of acceptable statuses

        Returns:
            Filtered DataFrame
        """
        if df.empty:
            return df

        # Apply filters
        mask = (
            (df['sharpe_ratio'] >= min_sharpe) &
            (df['max_drawdown'] <= max_drawdown) &
            (df['total_trades'] >= min_trades)
        )

        if status_filter:
            mask &= df['status'].isin(status_filter)

        filtered_df = df[mask].copy()

        logger.info(f"Filtered {len(df)} results to {len(filtered_df)} based on criteria")
        return filtered_df

    def export_consolidated(self, df: pd.DataFrame,
                           output_path: str,
                           format: str = 'csv') -> str:
        """
        Export consolidated results to file.

        Args:
            df: DataFrame to export
            output_path: Output file path
            format: Export format ('csv', 'json', 'parquet')

        Returns:
            Path to exported file
        """
        output_path = Path(output_path)

        if format.lower() == 'csv':
            df.to_csv(output_path, index=False)
        elif format.lower() == 'json':
            df.to_json(output_path, orient='records', indent=2)
        elif format.lower() == 'parquet':
            df.to_parquet(output_path, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info(f"Exported {len(df)} results to {output_path}")
        return str(output_path)

    def get_summary_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate summary statistics for consolidated results.

        Args:
            df: Consolidated results DataFrame

        Returns:
            Dictionary with summary statistics
        """
        if df.empty:
            return {}

        summary = {
            'total_strategies': len(df),
            'unique_strategies': df['strategy'].nunique(),
            'unique_symbols': df['symbol'].nunique(),
            'avg_sharpe_ratio': df['sharpe_ratio'].mean(),
            'avg_max_drawdown': df['max_drawdown'].mean(),
            'avg_win_rate': df['win_rate'].mean(),
            'total_trades': df['total_trades'].sum(),
            'strategies_by_symbol': df.groupby('symbol')['strategy'].count().to_dict(),
            'performance_distribution': {
                'sharpe_ratio': {
                    'mean': df['sharpe_ratio'].mean(),
                    'std': df['sharpe_ratio'].std(),
                    'min': df['sharpe_ratio'].min(),
                    'max': df['sharpe_ratio'].max(),
                    'median': df['sharpe_ratio'].median()
                },
                'max_drawdown': {
                    'mean': df['max_drawdown'].mean(),
                    'std': df['max_drawdown'].std(),
                    'min': df['max_drawdown'].min(),
                    'max': df['max_drawdown'].max(),
                    'median': df['max_drawdown'].median()
                }
            }
        }

        return summary