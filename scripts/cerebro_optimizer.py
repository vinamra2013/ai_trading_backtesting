#!/usr/bin/env python3
"""
Cerebro Parameter Optimizer
Epic 14: Parameter Optimization & Walk-Forward Analysis

Implements grid search optimization using Backtrader's built-in Cerebro.optstrategy()
for efficient parameter optimization with parallel execution.

Features:
- Grid search using Cerebro.optstrategy()
- Parallel optimization across CPU cores
- MLflow integration for experiment tracking
- Results ranking and export
- Support for multiple metrics
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import itertools
import multiprocessing as mp

import backtrader as bt
from backtrader.analyzers import SharpeRatio, DrawDown, Returns, TradeAnalyzer

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.mlflow_logger import MLflowBacktestLogger
from scripts.data_quality_check import load_data
from scripts.backtest_parser import BacktestResultParser

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CerebroOptimizer:
    """
    Parameter optimizer using Backtrader's Cerebro.optstrategy() for grid search.

    This approach is more efficient than running separate backtests for each parameter
    combination, as Cerebro handles the optimization internally with proper parallelization.
    """

    def __init__(self, mlflow_tracking_uri: str = "http://mlflow:5000"):
        """
        Initialize the Cerebro optimizer.

        Args:
            mlflow_tracking_uri: MLflow tracking server URI
        """
        self.mlflow_logger = MLflowBacktestLogger(tracking_uri=mlflow_tracking_uri)
        self.parser = BacktestResultParser()
        logger.info("CerebroOptimizer initialized")

    def optimize_strategy(
        self,
        strategy_class: bt.Strategy,
        param_ranges: Dict[str, List[Any]],
        symbols: List[str],
        start_date: str,
        end_date: str,
        initial_cash: float = 100000.0,
        commission: float = 0.001,
        maxcpus: Optional[int] = None,
        project: str = "optimization",
        asset_class: str = "equities",
        strategy_family: str = "unknown"
    ) -> Dict[str, Any]:
        # Store param ranges for result collection
        self.last_param_ranges = param_ranges
        """
        Run grid search optimization using Cerebro.optstrategy().

        Args:
            strategy_class: Backtrader strategy class
            param_ranges: Dictionary mapping parameter names to lists of values to test
            symbols: List of symbols to trade
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            initial_cash: Starting portfolio value
            commission: Commission per trade
            maxcpus: Maximum CPU cores to use (None = auto)
            project: Project name for MLflow
            asset_class: Asset class for tagging
            strategy_family: Strategy family for tagging

        Returns:
            Dictionary with optimization results
        """
        logger.info("Starting Cerebro optimization for strategy: %s", strategy_class.__name__)
        logger.info("Parameter ranges: %s", param_ranges)
        logger.info("Symbols: %s, Date range: %s to %s", symbols, start_date, end_date)

        # Create Cerebro engine for optimization
        cerebro = bt.Cerebro(optreturn=False)  # Don't return optimized strategy

        # Set broker parameters
        cerebro.broker.setcash(initial_cash)
        cerebro.broker.setcommission(commission=commission)

        # Load data for all symbols
        for symbol in symbols:
            data = load_data(symbol, start_date, end_date)
            if data is not None:
                cerebro.adddata(data, name=symbol)
                logger.info("Loaded data for %s: %d bars", symbol, len(data))
            else:
                logger.warning("Failed to load data for %s", symbol)
                return {}

        # Add analyzers
        cerebro.addanalyzer(SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Days, annualize=True)
        cerebro.addanalyzer(DrawDown, _name='drawdown')
        cerebro.addanalyzer(Returns, _name='returns', timeframe=bt.TimeFrame.NoTimeFrame)
        cerebro.addanalyzer(TradeAnalyzer, _name='trades')

        # Set up optimization
        param_combinations = self._generate_param_combinations(param_ranges)
        logger.info("Generated %d parameter combinations", len(param_combinations))

        # Set CPU cores for parallel optimization
        if maxcpus is None:
            maxcpus = max(1, mp.cpu_count() - 1)  # Leave one core free

        # Use optstrategy for parameter optimization
        cerebro.optstrategy(strategy_class, **param_ranges)

        # Run optimization
        results = cerebro.run(maxcpus=maxcpus, optdatas=True)

        # Collect and rank results
        results = self._collect_optimization_results(cerebro, strategy_class.__name__)

        # Log to MLflow
        self._log_optimization_to_mlflow(
            results=results,
            strategy_name=strategy_class.__name__,
            param_ranges=param_ranges,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            project=project,
            asset_class=asset_class,
            strategy_family=strategy_family
        )

        logger.info("Optimization completed. Best Sharpe: %.4f", results['best_result']['sharpe_ratio'])
        return results

    def _generate_param_combinations(self, param_ranges: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """Generate all combinations of parameters for grid search."""
        param_names = list(param_ranges.keys())
        param_values = list(param_ranges.values())

        combinations = []
        for combo in itertools.product(*param_values):
            combinations.append(dict(zip(param_names, combo)))

        return combinations

    def _collect_optimization_results(self, cerebro: bt.Cerebro, strategy_name: str) -> Dict[str, Any]:
        """Collect and rank optimization results from Cerebro run."""
        results = []

        # Cerebro.run() with optstrategy returns a list of optimization results
        # Each result contains (strategy_instance, parameter_tuple)
        opt_results = cerebro.run()

        for result in opt_results:
            if len(result) == 2:
                strategy, param_values = result
            else:
                # Fallback for different result formats
                strategy = result[0]
                param_values = None

            # Extract parameters - with optstrategy, params are in a special format
            params = {}
            if param_values:
                # param_values is a tuple of parameter values in the same order as param_ranges keys
                param_names = list(self.last_param_ranges.keys())  # Store param order
                for i, param_name in enumerate(param_names):
                    if i < len(param_values):
                        params[param_name] = param_values[i]
            else:
                # Fallback: try to extract from strategy params
                try:
                    for param_name in strategy.params._getkeys():
                        if hasattr(strategy.params, param_name):
                            params[param_name] = getattr(strategy.params, param_name)
                except:
                    params = {}

            # Extract analyzer results
            analyzers = strategy.analyzers

            metrics = {}
            if hasattr(analyzers, 'sharpe') and analyzers.sharpe:
                try:
                    sharpe_results = analyzers.sharpe.get_analysis()
                    metrics['sharpe_ratio'] = sharpe_results.get('sharperatio', 0)
                except:
                    metrics['sharpe_ratio'] = 0

            if hasattr(analyzers, 'drawdown') and analyzers.drawdown:
                try:
                    dd_results = analyzers.drawdown.get_analysis()
                    metrics['max_drawdown'] = dd_results.get('max', {}).get('drawdown', 0)
                    metrics['max_drawdown_pct'] = dd_results.get('max', {}).get('drawdown', 0) / 100.0
                except:
                    metrics['max_drawdown'] = 0
                    metrics['max_drawdown_pct'] = 0

            if hasattr(analyzers, 'returns') and analyzers.returns:
                try:
                    ret_results = analyzers.returns.get_analysis()
                    metrics['total_return'] = ret_results.get('rtot', 0)
                    metrics['annual_return'] = ret_results.get('rnorm', 0)
                except:
                    metrics['total_return'] = 0
                    metrics['annual_return'] = 0

            if hasattr(analyzers, 'trades') and analyzers.trades:
                try:
                    trade_results = analyzers.trades.get_analysis()
                    metrics['total_trades'] = trade_results.get('total', {}).get('total', 0)
                    metrics['win_trades'] = trade_results.get('won', {}).get('total', 0)
                    metrics['loss_trades'] = trade_results.get('lost', {}).get('total', 0)

                    total_trades = metrics['total_trades']
                    if total_trades > 0:
                        metrics['win_rate'] = metrics['win_trades'] / total_trades
                    else:
                        metrics['win_rate'] = 0
                except:
                    metrics['total_trades'] = 0
                    metrics['win_trades'] = 0
                    metrics['loss_trades'] = 0
                    metrics['win_rate'] = 0

            # Calculate additional metrics
            if metrics.get('total_return', 0) != 0 and metrics.get('max_drawdown_pct', 0) != 0:
                metrics['calmar_ratio'] = abs(metrics['total_return']) / metrics['max_drawdown_pct']
            else:
                metrics['calmar_ratio'] = 0

            # Portfolio value - this is tricky with optstrategy, use strategy's final value if available
            try:
                final_value = strategy.broker.getvalue() if hasattr(strategy, 'broker') else 100000.0
            except:
                final_value = 100000.0

            metrics['final_portfolio_value'] = final_value
            metrics['total_pnl'] = final_value - 100000.0  # Assuming 100k starting cash

            result_dict = {
                'parameters': params,
                'metrics': metrics,
                'strategy_name': strategy_name
            }

            results.append(result_dict)

        # Rank results by Sharpe ratio (descending), with fallback to total_return
        def sort_key(x):
            sharpe = x['metrics'].get('sharpe_ratio', 0)
            if sharpe != 0:
                return sharpe
            return x['metrics'].get('total_return', 0)

        ranked_results = sorted(results, key=sort_key, reverse=True)

        return {
            'all_results': ranked_results,
            'best_result': ranked_results[0] if ranked_results else {},
            'total_combinations': len(ranked_results),
            'optimization_timestamp': datetime.now().isoformat()
        }

    def _log_optimization_to_mlflow(
        self,
        results: Dict[str, Any],
        strategy_name: str,
        param_ranges: Dict[str, List[Any]],
        symbols: List[str],
        start_date: str,
        end_date: str,
        project: str,
        asset_class: str,
        strategy_family: str
    ) -> None:
        """Log optimization results to MLflow."""
        try:
            with self.mlflow_logger.start_run(run_name=f"opt_{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                            tags={
                                                'project': project,
                                                'asset_class': asset_class,
                                                'strategy_family': strategy_family,
                                                'optimization_type': 'grid_search',
                                                'strategy_name': strategy_name
                                            }):

                # Log parameters
                self.mlflow_logger.log_param('strategy_name', strategy_name)
                self.mlflow_logger.log_param('symbols', ','.join(symbols))
                self.mlflow_logger.log_param('start_date', start_date)
                self.mlflow_logger.log_param('end_date', end_date)
                self.mlflow_logger.log_param('total_combinations', results['total_combinations'])

                # Log parameter ranges
                for param_name, param_values in param_ranges.items():
                    self.mlflow_logger.log_param(f'param_range_{param_name}', str(param_values))

                # Log best result metrics
                if results['best_result']:
                    best_metrics = results['best_result']['metrics']
                    for metric_name, metric_value in best_metrics.items():
                        if isinstance(metric_value, (int, float)):
                            self.mlflow_logger.log_metric(f'best_{metric_name}', metric_value)

                    # Log best parameters
                    best_params = results['best_result']['parameters']
                    for param_name, param_value in best_params.items():
                        self.mlflow_logger.log_param(f'best_{param_name}', param_value)

                # Log all results as artifact
                results_file = f"optimization_results_{strategy_name}.json"
                with open(results_file, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                self.mlflow_logger.log_artifact(results_file)

                # Clean up
                if os.path.exists(results_file):
                    os.remove(results_file)

        except Exception as e:
            logger.error("Failed to log optimization results to MLflow: %s", e)


def main():
    """Command-line interface for Cerebro optimization."""
    import argparse
    import importlib

    parser = argparse.ArgumentParser(description="Cerebro Parameter Optimizer")
    parser.add_argument("--strategy", required=True, help="Strategy module path (e.g., strategies.sma_crossover)")
    parser.add_argument("--param-ranges", required=True, help="JSON file with parameter ranges")
    parser.add_argument("--symbols", required=True, help="Comma-separated list of symbols")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--initial-cash", type=float, default=100000.0, help="Initial portfolio cash")
    parser.add_argument("--commission", type=float, default=0.001, help="Commission per trade")
    parser.add_argument("--maxcpus", type=int, help="Maximum CPU cores to use")
    parser.add_argument("--project", default="optimization", help="Project name")
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

    # Initialize optimizer
    optimizer = CerebroOptimizer()

    # Run optimization
    results = optimizer.optimize_strategy(
        strategy_class=strategy_class,
        param_ranges=param_ranges,
        symbols=args.symbols.split(','),
        start_date=args.start,
        end_date=args.end,
        initial_cash=args.initial_cash,
        commission=args.commission,
        maxcpus=args.maxcpus,
        project=args.project,
        asset_class=args.asset_class,
        strategy_family=args.strategy_family
    )

    # Print results
    print("\n" + "="*60)
    print("CEREBRO OPTIMIZATION RESULTS")
    print("="*60)
    print(f"Strategy: {args.strategy}")
    print(f"Total combinations tested: {results['total_combinations']}")

    if results['best_result']:
        best = results['best_result']
        print(f"\nBEST PARAMETERS:")
        for param, value in best['parameters'].items():
            print(f"  {param}: {value}")

        print(f"\nBEST METRICS:")
        for metric, value in best['metrics'].items():
            if isinstance(value, float):
                print(f"  {metric}: {value:.4f}")
            else:
                print(f"  {metric}: {value}")

    # Save results to file if requested
    if args.output_json:
        with open(args.output_json, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to: {args.output_json}")

    print("="*60)


if __name__ == "__main__":
    main()
<parameter name="filePath">scripts/cerebro_optimizer.py