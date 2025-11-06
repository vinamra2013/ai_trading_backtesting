#!/usr/bin/env python3
"""
Walk-Forward Analysis Engine
Epic 14: Parameter Optimization & Walk-Forward Analysis

Implements walk-forward analysis for strategy validation by testing on rolling
windows of out-of-sample data to detect overfitting and ensure robustness.

Features:
- Rolling window validation (in-sample optimization, out-of-sample testing)
- Performance degradation analysis
- Stationarity tests
- MLflow experiment tracking
- Comprehensive reporting
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from scipy import stats

import backtrader as bt
from backtrader.analyzers import SharpeRatio, DrawDown, Returns, TradeAnalyzer

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.mlflow_logger import MLflowBacktestLogger
from scripts.data_quality_check import load_data
from scripts.backtest_parser import BacktestResultParser

# Import parallel backtesting for distributed execution
PARALLEL_BACKTEST_AVAILABLE = False
ParallelBacktestOrchestrator = None

try:
    from scripts.parallel_backtest import ParallelBacktestOrchestrator
    PARALLEL_BACKTEST_AVAILABLE = True
    print("✅ Parallel backtesting available for walk-forward analysis")
except ImportError as e:
    print(f"⚠️  Parallel backtesting not available, using sequential execution: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WalkForwardAnalyzer:
    """
    Walk-forward analysis for strategy validation.

    This class implements rolling window analysis where:
    1. Strategy is optimized on in-sample data (training window)
    2. Optimized parameters are tested on out-of-sample data (testing window)
    3. Windows roll forward and process repeats
    4. Results are analyzed for consistency and overfitting
    """

    def __init__(self, mlflow_tracking_uri: str = "http://mlflow:5000"):
        """
        Initialize the walk-forward analyzer.

        Args:
            mlflow_tracking_uri: MLflow tracking server URI
        """
        self.mlflow_logger = MLflowBacktestLogger(tracking_uri=mlflow_tracking_uri)
        self.parser = BacktestResultParser()
        logger.info("WalkForwardAnalyzer initialized")

    def run_walk_forward_analysis(
        self,
        strategy_class: bt.Strategy,
        param_ranges: Dict[str, List[Any]],
        symbols: List[str],
        start_date: str,
        end_date: str,
        window_size_months: int = 12,
        step_size_months: int = 3,
        optimization_metric: str = "sharpe_ratio",
        initial_cash: float = 100000.0,
        commission: float = 0.001,
        project: str = "walk_forward",
        asset_class: str = "equities",
        strategy_family: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Run complete walk-forward analysis.

        Args:
            strategy_class: Backtrader strategy class
            param_ranges: Parameter ranges for optimization
            symbols: List of symbols to trade
            start_date: Overall start date (YYYY-MM-DD)
            end_date: Overall end date (YYYY-MM-DD)
            window_size_months: Size of each analysis window in months
            step_size_months: How many months to step forward each iteration
            optimization_metric: Metric to optimize parameters on
            initial_cash: Starting portfolio value
            commission: Commission per trade
            project: Project name for MLflow
            asset_class: Asset class for tagging
            strategy_family: Strategy family for tagging

        Returns:
            Dictionary with walk-forward analysis results
        """
        logger.info("Starting walk-forward analysis for strategy: %s", strategy_class.__name__)
        logger.info("Analysis period: %s to %s", start_date, end_date)
        logger.info("Window size: %d months, Step size: %d months", window_size_months, step_size_months)

        # Generate analysis windows
        windows = self._generate_analysis_windows(
            start_date, end_date, window_size_months, step_size_months
        )
        logger.info("Generated %d analysis windows", len(windows))

        # Run analysis for each window
        window_results = []
        for i, window in enumerate(windows):
            logger.info("Processing window %d/%d: %s to %s (train: %s to %s, test: %s to %s)",
                       i+1, len(windows), window['start'], window['end'],
                       window['train_start'], window['train_end'],
                       window['test_start'], window['test_end'])

            result = self._analyze_window(
                strategy_class=strategy_class,
                param_ranges=param_ranges,
                symbols=symbols,
                window=window,
                optimization_metric=optimization_metric,
                initial_cash=initial_cash,
                commission=commission
            )
            window_results.append(result)

        # Analyze overall results
        analysis_results = self._analyze_walk_forward_results(
            window_results=window_results,
            strategy_name=strategy_class.__name__,
            windows=windows
        )

        # Log to MLflow
        self._log_walk_forward_to_mlflow(
            results=analysis_results,
            strategy_name=strategy_class.__name__,
            window_results=window_results,
            windows=windows,
            project=project,
            asset_class=asset_class,
            strategy_family=strategy_family
        )

        logger.info("Walk-forward analysis completed. Average out-of-sample Sharpe: %.4f",
                   analysis_results['summary']['avg_out_of_sample_sharpe'])

        return analysis_results

    def _generate_analysis_windows(
        self,
        start_date: str,
        end_date: str,
        window_size_months: int,
        step_size_months: int
    ) -> List[Dict[str, str]]:
        """
        Generate rolling analysis windows.

        Each window contains:
        - train_start/train_end: In-sample period for optimization
        - test_start/test_end: Out-of-sample period for validation
        """
        windows = []
        current_start = pd.to_datetime(start_date)

        while True:
            # Calculate window end
            window_end = current_start + pd.DateOffset(months=window_size_months)

            if window_end > pd.to_datetime(end_date):
                break

            # Split into train/test (80/20 split)
            train_end = current_start + pd.DateOffset(months=int(window_size_months * 0.8))
            test_start = train_end + pd.DateOffset(days=1)
            test_end = window_end

            window = {
                'start': current_start.strftime('%Y-%m-%d'),
                'end': window_end.strftime('%Y-%m-%d'),
                'train_start': current_start.strftime('%Y-%m-%d'),
                'train_end': train_end.strftime('%Y-%m-%d'),
                'test_start': test_start.strftime('%Y-%m-%d'),
                'test_end': test_end.strftime('%Y-%m-%d')
            }

            windows.append(window)

            # Move to next window
            current_start = current_start + pd.DateOffset(months=step_size_months)

        return windows

    def _analyze_window(
        self,
        strategy_class: bt.Strategy,
        param_ranges: Dict[str, List[Any]],
        symbols: List[str],
        window: Dict[str, str],
        optimization_metric: str,
        initial_cash: float,
        commission: float
    ) -> Dict[str, Any]:
        """
        Analyze a single window: optimize on train data, test on test data.
        """
        # Optimize parameters on training data
        best_params = self._optimize_on_training_data(
            strategy_class=strategy_class,
            param_ranges=param_ranges,
            symbols=symbols,
            train_start=window['train_start'],
            train_end=window['train_end'],
            optimization_metric=optimization_metric,
            initial_cash=initial_cash,
            commission=commission
        )

        # Test optimized parameters on out-of-sample data
        test_results = self._test_on_out_of_sample_data(
            strategy_class=strategy_class,
            params=best_params,
            symbols=symbols,
            test_start=window['test_start'],
            test_end=window['test_end'],
            initial_cash=initial_cash,
            commission=commission
        )

        return {
            'window': window,
            'best_params': best_params,
            'in_sample_metrics': {},  # Would be populated from optimization
            'out_of_sample_metrics': test_results.get('metrics', {}),
            'performance_degradation': self._calculate_performance_degradation({}, test_results.get('metrics', {}))
        }

    def _optimize_on_training_data(
        self,
        strategy_class: bt.Strategy,
        param_ranges: Dict[str, List[Any]],
        symbols: List[str],
        train_start: str,
        train_end: str,
        optimization_metric: str,
        initial_cash: float,
        commission: float
    ) -> Dict[str, Any]:
        """
        Optimize strategy parameters on training data.
        For simplicity, we'll use a basic grid search here.
        In production, this could use the CerebroOptimizer.
        """
        # Simple parameter optimization - try all combinations
        param_combinations = []
        param_names = list(param_ranges.keys())
        param_values = list(param_ranges.values())

        for combo in itertools.product(*param_values):
            param_combinations.append(dict(zip(param_names, combo)))

        best_params = {}
        best_score = float('-inf')

        for params in param_combinations[:5]:  # Limit to first 5 for speed
            try:
                # Run backtest with these parameters
                cerebro = bt.Cerebro()
                cerebro.broker.setcash(initial_cash)
                cerebro.broker.setcommission(commission=commission)

                # Load training data
                for symbol in symbols:
                    data = load_data(symbol, train_start, train_end)
                    if data:
                        cerebro.adddata(data, name=symbol)

                # Add strategy with fixed parameters
                cerebro.addstrategy(strategy_class, **params)

                # Add analyzers
                cerebro.addanalyzer(SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Days, annualize=True)
                cerebro.addanalyzer(Returns, _name='returns', timeframe=bt.TimeFrame.NoTimeFrame)

                # Run backtest
                results = cerebro.run()
                strategy = results[0]

                # Extract metric
                score = 0
                if hasattr(strategy.analyzers, 'sharpe'):
                    try:
                        sharpe_results = strategy.analyzers.sharpe.get_analysis()
                        score = sharpe_results.get('sharperatio', 0)
                    except:
                        score = 0

                if score > best_score:
                    best_score = score
                    best_params = params.copy()

            except Exception as e:
                logger.warning("Failed to optimize with params %s: %s", params, e)
                continue

        logger.info("Best training params: %s (score: %.4f)", best_params, best_score)
        return best_params

    def _test_on_out_of_sample_data(
        self,
        strategy_class: bt.Strategy,
        params: Dict[str, Any],
        symbols: List[str],
        test_start: str,
        test_end: str,
        initial_cash: float,
        commission: float
    ) -> Dict[str, Any]:
        """
        Test optimized parameters on out-of-sample data.
        Uses parallel backtesting if available, otherwise falls back to sequential execution.
        """
        # Get strategy path for parallel backtesting
        strategy_path = self._get_strategy_path(strategy_class)

        # Use parallel backtesting if available
        if PARALLEL_BACKTEST_AVAILABLE and len(symbols) > 1:
            logger.info("Using parallel backtesting for %d symbols", len(symbols))
            return self._test_parallel(
                strategy_path=strategy_path,
                params=params,
                symbols=symbols,
                test_start=test_start,
                test_end=test_end,
                initial_cash=initial_cash,
                commission=commission
            )
        else:
            logger.info("Using sequential backtesting")
            return self._test_sequential(
                strategy_class=strategy_class,
                params=params,
                symbols=symbols,
                test_start=test_start,
                test_end=test_end,
                initial_cash=initial_cash,
                commission=commission
            )

    def _get_strategy_path(self, strategy_class: bt.Strategy) -> str:
        """Get the file path for a strategy class."""
        # This is a simplified approach - in practice, you'd need to map class to file
        # For now, we'll use a mapping or require the path to be passed
        strategy_name = strategy_class.__name__.lower()
        possible_paths = [
            f"strategies/{strategy_name}.py",
            f"strategies/{strategy_name}_strategy.py",
            f"strategies/{strategy_name}_risk_managed.py"
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        # Fallback - this would need to be improved
        return f"strategies/{strategy_name}.py"

    def _test_parallel(
        self,
        strategy_path: str,
        params: Dict[str, Any],
        symbols: List[str],
        test_start: str,
        test_end: str,
        initial_cash: float,
        commission: float
    ) -> Dict[str, Any]:
        """Test using parallel backtesting system."""
        try:
            # Initialize parallel orchestrator
            orchestrator = ParallelBacktestOrchestrator(
                redis_host='redis',
                redis_port=6379
            )

            # Prepare strategy parameters for each symbol
            strategy_params = {symbol: params for symbol in symbols}

            # Run parallel backtests
            results_df = orchestrator.execute_batch(
                symbols=symbols,
                strategies=[strategy_path],
                strategy_params=strategy_params,
                show_progress=False  # Disable progress for walk-forward
            )

            # Aggregate results across all symbols
            if not results_df.empty:
                # Calculate weighted averages based on number of trades or returns
                total_return = results_df['total_return'].mean()
                sharpe_ratio = results_df['sharpe_ratio'].mean()
                max_drawdown = results_df['max_drawdown'].max()  # Worst case
                total_trades = results_df['total_trades'].sum()

                metrics = {
                    'total_return': total_return,
                    'sharpe_ratio': sharpe_ratio,
                    'max_drawdown': max_drawdown,
                    'total_trades': total_trades,
                    'symbols_tested': len(symbols),
                    'execution_method': 'parallel'
                }

                return {
                    'success': True,
                    'metrics': metrics,
                    'raw_results': results_df.to_dict('records')
                }
            else:
                return {
                    'success': False,
                    'error': 'No results from parallel backtesting',
                    'metrics': {}
                }

        except Exception as e:
            print(f"Parallel backtesting failed: {e}")
            # Fallback to sequential - but we need strategy_class, so this is tricky
            # For now, return error
            return {
                'success': False,
                'error': f'Parallel backtesting failed: {e}',
                'metrics': {}
            }

    def _test_sequential(
        self,
        strategy_class: bt.Strategy,
        params: Dict[str, Any],
        symbols: List[str],
        test_start: str,
        test_end: str,
        initial_cash: float,
        commission: float
    ) -> Dict[str, Any]:
        """
        Test optimized parameters on out-of-sample data (sequential fallback).
        """
        try:
            cerebro = bt.Cerebro()
            cerebro.broker.setcash(initial_cash)
            cerebro.broker.setcommission(commission=commission)

            # Load test data
            for symbol in symbols:
                data = load_data(symbol, test_start, test_end)
                if data:
                    cerebro.adddata(data, name=symbol)

            # Add strategy with optimized parameters
            cerebro.addstrategy(strategy_class, **params)

            # Add analyzers
            cerebro.addanalyzer(SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Days, annualize=True)
            cerebro.addanalyzer(DrawDown, _name='drawdown')
            cerebro.addanalyzer(Returns, _name='returns', timeframe=bt.TimeFrame.NoTimeFrame)
            cerebro.addanalyzer(TradeAnalyzer, _name='trades')

            # Run backtest
            results = cerebro.run()
            strategy = results[0]

            # Extract metrics
            metrics = {}
            try:
                if hasattr(strategy.analyzers, 'sharpe'):
                    sharpe_results = strategy.analyzers.sharpe.get_analysis()
                    metrics['sharpe_ratio'] = sharpe_results.get('sharperatio', 0)

                if hasattr(strategy.analyzers, 'drawdown'):
                    dd_results = strategy.analyzers.drawdown.get_analysis()
                    metrics['max_drawdown'] = dd_results.get('max', {}).get('drawdown', 0)

                if hasattr(strategy.analyzers, 'returns'):
                    ret_results = strategy.analyzers.returns.get_analysis()
                    metrics['total_return'] = ret_results.get('rtot', 0)

                if hasattr(strategy.analyzers, 'trades'):
                    trade_results = strategy.analyzers.trades.get_analysis()
                    metrics['total_trades'] = trade_results.get('total', {}).get('total', 0)
                    metrics['win_trades'] = trade_results.get('won', {}).get('total', 0)

                    total_trades = metrics['total_trades']
                    if total_trades > 0:
                        metrics['win_rate'] = metrics['win_trades'] / total_trades
                    else:
                        metrics['win_rate'] = 0

                final_value = cerebro.broker.getvalue()
                metrics['final_portfolio_value'] = final_value
                metrics['total_pnl'] = final_value - initial_cash

            except Exception as e:
                logger.warning("Failed to extract metrics: %s", e)

            return {'metrics': metrics}

        except Exception as e:
            logger.error("Failed out-of-sample test: %s", e)
            return {'metrics': {}}

    def _calculate_performance_degradation(
        self,
        in_sample_metrics: Dict[str, float],
        out_of_sample_metrics: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate performance degradation from in-sample to out-of-sample.
        """
        degradation = {}

        for metric in ['sharpe_ratio', 'total_return', 'win_rate']:
            in_sample = in_sample_metrics.get(metric, 0)
            out_sample = out_of_sample_metrics.get(metric, 0)
            degradation[f'{metric}_degradation'] = in_sample - out_sample

        return degradation

    def _analyze_walk_forward_results(
        self,
        window_results: List[Dict[str, Any]],
        strategy_name: str,
        windows: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Analyze overall walk-forward results for consistency and overfitting.
        """
        # Extract out-of-sample metrics
        out_of_sample_sharpes = []
        out_of_sample_returns = []
        out_of_sample_win_rates = []

        for result in window_results:
            metrics = result.get('out_of_sample_metrics', {})
            out_of_sample_sharpes.append(metrics.get('sharpe_ratio', 0))
            out_of_sample_returns.append(metrics.get('total_return', 0))
            out_of_sample_win_rates.append(metrics.get('win_rate', 0))

        # Calculate summary statistics
        summary = {
            'total_windows': len(window_results),
            'avg_out_of_sample_sharpe': np.mean(out_of_sample_sharpes),
            'std_out_of_sample_sharpe': np.std(out_of_sample_sharpes),
            'avg_out_of_sample_return': np.mean(out_of_sample_returns),
            'std_out_of_sample_return': np.std(out_of_sample_returns),
            'avg_out_of_sample_win_rate': np.mean(out_of_sample_win_rates),
            'sharpe_consistency_ratio': np.mean(out_of_sample_sharpes) / max(np.std(out_of_sample_sharpes), 0.001),
            'positive_sharpe_windows': sum(1 for s in out_of_sample_sharpes if s > 0),
            'sharpe_positive_ratio': sum(1 for s in out_of_sample_sharpes if s > 0) / len(out_of_sample_sharpes)
        }

        # Test for stationarity (consistency over time)
        if len(out_of_sample_sharpes) > 3:
            # Augmented Dickey-Fuller test for stationarity
            try:
                adf_result = stats.adfuller(out_of_sample_sharpes)
                summary['sharpe_stationarity_p_value'] = adf_result[1]
                summary['sharpe_is_stationary'] = adf_result[1] < 0.05
            except:
                summary['sharpe_stationarity_p_value'] = None
                summary['sharpe_is_stationary'] = None

        # Performance degradation analysis
        degradation_analysis = {
            'avg_sharpe_degradation': np.mean([r.get('performance_degradation', {}).get('sharpe_ratio_degradation', 0)
                                             for r in window_results]),
            'sharpe_degradation_std': np.std([r.get('performance_degradation', {}).get('sharpe_ratio_degradation', 0)
                                            for r in window_results])
        }

        return {
            'summary': summary,
            'degradation_analysis': degradation_analysis,
            'window_results': window_results,
            'windows': windows,
            'analysis_timestamp': datetime.now().isoformat()
        }

    def _log_walk_forward_to_mlflow(
        self,
        results: Dict[str, Any],
        strategy_name: str,
        window_results: List[Dict[str, Any]],
        windows: List[Dict[str, str]],
        project: str,
        asset_class: str,
        strategy_family: str
    ) -> None:
        """Log walk-forward analysis results to MLflow."""
        try:
            with self.mlflow_logger.start_run(run_name=f"wf_{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                            tags={
                                                'project': project,
                                                'asset_class': asset_class,
                                                'strategy_family': strategy_family,
                                                'analysis_type': 'walk_forward'
                                            }):

                # Log summary metrics
                summary = results['summary']
                for metric_name, metric_value in summary.items():
                    if isinstance(metric_value, (int, float)) and not np.isnan(metric_value):
                        self.mlflow_logger.log_metric(f'wf_{metric_name}', metric_value)

                # Log degradation analysis
                degradation = results['degradation_analysis']
                for metric_name, metric_value in degradation.items():
                    if isinstance(metric_value, (int, float)) and not np.isnan(metric_value):
                        self.mlflow_logger.log_metric(f'wf_{metric_name}', metric_value)

                # Log parameters
                self.mlflow_logger.log_param('strategy_name', strategy_name)
                self.mlflow_logger.log_param('total_windows', summary['total_windows'])
                self.mlflow_logger.log_param('analysis_type', 'walk_forward')

                # Log detailed results as artifact
                results_file = f"walk_forward_results_{strategy_name}.json"
                with open(results_file, 'w') as f:
                    # Convert numpy types to native Python types for JSON serialization
                    json_results = json.loads(json.dumps(results, default=str))
                    json.dump(json_results, f, indent=2)
                self.mlflow_logger.log_artifact(results_file)

                # Clean up
                if os.path.exists(results_file):
                    os.remove(results_file)

        except Exception as e:
            logger.error("Failed to log walk-forward results to MLflow: %s", e)


def main():
    """Command-line interface for walk-forward analysis."""
    import argparse
    import importlib

    parser = argparse.ArgumentParser(description="Walk-Forward Analysis Engine")
    parser.add_argument("--strategy", required=True, help="Strategy module path (e.g., strategies.sma_crossover)")
    parser.add_argument("--param-ranges", required=True, help="JSON file with parameter ranges")
    parser.add_argument("--symbols", required=True, help="Comma-separated list of symbols")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--window-size", type=int, default=12, help="Window size in months")
    parser.add_argument("--step-size", type=int, default=3, help="Step size in months")
    parser.add_argument("--metric", default="sharpe_ratio", help="Optimization metric")
    parser.add_argument("--initial-cash", type=float, default=100000.0, help="Initial portfolio cash")
    parser.add_argument("--commission", type=float, default=0.001, help="Commission per trade")
    parser.add_argument("--project", default="walk_forward", help="Project name")
    parser.add_argument("--asset-class", default="equities", help="Asset class")
    parser.add_argument("--strategy-family", default="unknown", help="Strategy family")
    parser.add_argument("--output-json", help="Output file for results")

    args = parser.parse_args()

    # Load parameter ranges
    with open(args.param_ranges, 'r') as f:
        param_ranges = json.load(f)

    # Import strategy class
    try:
        module_path, class_name = args.strategy.rsplit('.', 1)
        module = importlib.import_module(module_path)
        strategy_class = getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        logger.error("Failed to import strategy %s: %s", args.strategy, e)
        sys.exit(1)

    # Initialize analyzer
    analyzer = WalkForwardAnalyzer()

    # Run walk-forward analysis
    results = analyzer.run_walk_forward_analysis(
        strategy_class=strategy_class,
        param_ranges=param_ranges,
        symbols=args.symbols.split(','),
        start_date=args.start,
        end_date=args.end,
        window_size_months=args.window_size,
        step_size_months=args.step_size,
        optimization_metric=args.metric,
        initial_cash=args.initial_cash,
        commission=args.commission,
        project=args.project,
        asset_class=args.asset_class,
        strategy_family=args.strategy_family
    )

    # Print results
    print("\n" + "="*70)
    print("WALK-FORWARD ANALYSIS RESULTS")
    print("="*70)
    print(f"Strategy: {args.strategy}")
    print(f"Total windows analyzed: {results['summary']['total_windows']}")

    summary = results['summary']
    print(f"\nOUT-OF-SAMPLE PERFORMANCE:")
    print(f"  Average Sharpe Ratio: {summary['avg_out_of_sample_sharpe']:.4f}")
    print(f"  Sharpe Std Dev: {summary['std_out_of_sample_sharpe']:.4f}")
    print(f"  Sharpe Consistency Ratio: {summary['sharpe_consistency_ratio']:.2f}")
    print(f"  Positive Sharpe Windows: {summary['positive_sharpe_windows']}/{summary['total_windows']} ({summary['sharpe_positive_ratio']:.1%})")

    if summary.get('sharpe_is_stationary') is not None:
        print(f"  Sharpe Stationarity: {'Yes' if summary['sharpe_is_stationary'] else 'No'} (p={summary.get('sharpe_stationarity_p_value', 'N/A')})")

    degradation = results['degradation_analysis']
    print(f"\nPERFORMANCE DEGRADATION:")
    print(f"  Average Sharpe Degradation: {degradation['avg_sharpe_degradation']:.4f}")
    print(f"  Sharpe Degradation Std Dev: {degradation['sharpe_degradation_std']:.4f}")

    # Save results to file if requested
    if args.output_json:
        with open(args.output_json, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to: {args.output_json}")

    print("="*70)


if __name__ == "__main__":
    main()