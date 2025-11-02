#!/usr/bin/env python3
"""
Parameter Optimization Script - Grid search optimization for LEAN algorithms.

US-4.4: Parameter Optimization
Track C: Optimization Engine
"""

import argparse
import json
import logging
import multiprocessing as mp
import subprocess
import sys
import time
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import uuid

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ParameterOptimizer:
    """
    Grid search optimization system for LEAN algorithm parameters.

    Features:
    - Grid search over parameter combinations
    - Parallel execution using all CPU cores
    - Progress tracking with time estimates
    - Overfitting detection via train/test split
    - Results ranking by optimization metric
    """

    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize optimizer.

        Args:
            max_workers: Number of parallel workers (default: all CPU cores)
        """
        self.max_workers = max_workers or mp.cpu_count()
        logger.info(f"Initialized optimizer with {self.max_workers} workers")

    def optimize(
        self,
        algorithm: str,
        param_ranges: Dict[str, List[Any]],
        metric: str,
        start_date: str,
        end_date: str,
        cost_model: str = "ib_standard",
        train_test_split: Optional[float] = None,
        overfitting_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Run grid search optimization.

        Args:
            algorithm: Path to LEAN algorithm directory
            param_ranges: Parameter ranges dict like {"sma_period": [10, 20, 50]}
            metric: Optimization target (sharpe_ratio, total_return, etc.)
            start_date: Backtest start date YYYY-MM-DD
            end_date: Backtest end date YYYY-MM-DD
            cost_model: Cost model to use (default: ib_standard)
            train_test_split: If set, split data into train/test (e.g., 0.6 = 60% train)
            overfitting_threshold: Flag if test < threshold * train performance

        Returns:
            Optimization results with all combinations ranked
        """
        logger.info(f"Starting optimization for {algorithm}")
        logger.info(f"Parameter ranges: {param_ranges}")
        logger.info(f"Optimizing for: {metric}")

        # Generate all parameter combinations
        combinations = self._generate_combinations(param_ranges)
        total_combinations = len(combinations)
        logger.info(f"Total combinations to test: {total_combinations}")

        # Handle train/test split
        if train_test_split:
            train_start, train_end, test_start, test_end = self._split_dates(
                start_date, end_date, train_test_split
            )
            logger.info(f"Train period: {train_start} to {train_end}")
            logger.info(f"Test period: {test_start} to {test_end}")
            run_mode = "train_test"
        else:
            train_start, train_end = start_date, end_date
            test_start, test_end = None, None
            run_mode = "full"

        # Run backtests in parallel
        start_time = time.time()
        results = []

        # Create work items
        work_items = [
            (algorithm, params, metric, train_start, train_end, cost_model, "train")
            for params in combinations
        ]

        # Add test period work items if applicable
        if run_mode == "train_test":
            work_items.extend([
                (algorithm, params, metric, test_start, test_end, cost_model, "test")
                for params in combinations
            ])

        # Execute with progress tracking
        logger.info("Running backtests in parallel...")
        with mp.Pool(processes=self.max_workers) as pool:
            results_raw = []
            for i, result in enumerate(pool.imap_unordered(self._run_single_backtest, work_items)):
                results_raw.append(result)

                # Progress reporting
                progress_pct = ((i + 1) / len(work_items)) * 100
                elapsed = time.time() - start_time
                if i > 0:
                    eta = (elapsed / (i + 1)) * (len(work_items) - i - 1)
                    logger.info(f"Progress: {progress_pct:.1f}% ({i+1}/{len(work_items)}) - ETA: {eta/60:.1f}m")

        # Organize results
        if run_mode == "train_test":
            results = self._merge_train_test_results(results_raw, combinations)
        else:
            results = [r for r in results_raw if r is not None]

        # Rank by metric
        results.sort(key=lambda x: x.get(f"train_{metric}", 0), reverse=True)

        # Detect overfitting if applicable
        if run_mode == "train_test":
            for result in results:
                train_metric = result.get(f"train_{metric}", 0)
                test_metric = result.get(f"test_{metric}", 0)

                if train_metric > 0:
                    test_ratio = test_metric / train_metric
                    result["overfitting_ratio"] = test_ratio
                    result["overfitting_detected"] = test_ratio < overfitting_threshold
                else:
                    result["overfitting_ratio"] = None
                    result["overfitting_detected"] = None

        # Save optimization results
        optimization_id = str(uuid.uuid4())
        elapsed_time = time.time() - start_time

        output = {
            "optimization_id": optimization_id,
            "algorithm": algorithm,
            "metric": metric,
            "param_ranges": param_ranges,
            "total_combinations": total_combinations,
            "train_period": {"start": train_start, "end": train_end},
            "test_period": {"start": test_start, "end": test_end} if run_mode == "train_test" else None,
            "execution_time_seconds": elapsed_time,
            "parallel_workers": self.max_workers,
            "results": results,
            "top_10": results[:10],
            "timestamp": datetime.now().isoformat()
        }

        # Save to file
        results_dir = Path("results/optimizations")
        results_dir.mkdir(parents=True, exist_ok=True)
        output_file = results_dir / f"{optimization_id}.json"

        output_file.write_text(json.dumps(output, indent=2))
        logger.info(f"✓ Optimization completed in {elapsed_time/60:.1f} minutes")
        logger.info(f"Results saved to: {output_file}")

        # Print top 3 results
        logger.info("\n" + "="*80)
        logger.info("TOP 3 PARAMETER COMBINATIONS:")
        logger.info("="*80)
        for i, result in enumerate(results[:3], 1):
            logger.info(f"\n{i}. Parameters: {result['parameters']}")
            logger.info(f"   Train {metric}: {result.get(f'train_{metric}', 'N/A')}")
            if run_mode == "train_test":
                logger.info(f"   Test {metric}: {result.get(f'test_{metric}', 'N/A')}")
                logger.info(f"   Overfitting ratio: {result.get('overfitting_ratio', 'N/A'):.2f}")

        return output

    def _generate_combinations(self, param_ranges: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """
        Generate all parameter combinations using itertools.product.

        Args:
            param_ranges: Dict of parameter names to value lists

        Returns:
            List of parameter dictionaries
        """
        param_names = list(param_ranges.keys())
        param_values = list(param_ranges.values())

        combinations = []
        for values in product(*param_values):
            combinations.append(dict(zip(param_names, values)))

        return combinations

    def _split_dates(
        self, start_date: str, end_date: str, split_ratio: float
    ) -> Tuple[str, str, str, str]:
        """
        Split date range into train and test periods.

        Args:
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD
            split_ratio: Fraction for training (e.g., 0.6 = 60% train, 40% test)

        Returns:
            (train_start, train_end, test_start, test_end)
        """
        from datetime import datetime, timedelta

        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        total_days = (end - start).days
        train_days = int(total_days * split_ratio)

        train_end = start + timedelta(days=train_days)
        test_start = train_end + timedelta(days=1)

        return (
            start_date,
            train_end.strftime("%Y-%m-%d"),
            test_start.strftime("%Y-%m-%d"),
            end_date
        )

    @staticmethod
    def _run_single_backtest(args: Tuple) -> Optional[Dict[str, Any]]:
        """
        Run a single backtest with given parameters.

        This is a static method to support multiprocessing.

        Args:
            args: (algorithm, parameters, metric, start, end, cost_model, run_type)

        Returns:
            Result dictionary or None if failed
        """
        algorithm, parameters, metric, start, end, cost_model, run_type = args

        # Build LEAN CLI command with parameters
        cmd = ["lean", "backtest", algorithm]

        # Add parameters
        for param_name, param_value in parameters.items():
            cmd.extend(["--parameter", param_name, str(param_value)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=600  # 10 minute timeout per backtest
            )

            # Parse results from stdout
            metrics = ParameterOptimizer._parse_backtest_output(result.stdout, metric)

            return {
                "parameters": parameters,
                f"{run_type}_{metric}": metrics.get(metric),
                f"{run_type}_stdout": result.stdout,
                "run_type": run_type,
                "status": "success"
            }

        except subprocess.CalledProcessError as e:
            logger.warning(f"Backtest failed for params {parameters}: {e}")
            return {
                "parameters": parameters,
                f"{run_type}_{metric}": 0,
                "run_type": run_type,
                "status": "failed",
                "error": str(e)
            }
        except subprocess.TimeoutExpired:
            logger.warning(f"Backtest timeout for params {parameters}")
            return {
                "parameters": parameters,
                f"{run_type}_{metric}": 0,
                "run_type": run_type,
                "status": "timeout"
            }

    @staticmethod
    def _parse_backtest_output(stdout: str, metric: str) -> Dict[str, float]:
        """
        Parse backtest output to extract metrics.

        Args:
            stdout: LEAN backtest stdout
            metric: Primary metric name

        Returns:
            Dictionary of metrics
        """
        metrics = {}

        # Common LEAN output patterns
        patterns = {
            "sharpe_ratio": r"Sharpe Ratio:\s+([-+]?\d*\.?\d+)",
            "total_return": r"Total Return:\s+([-+]?\d*\.?\d+)%?",
            "sortino_ratio": r"Sortino Ratio:\s+([-+]?\d*\.?\d+)",
            "max_drawdown": r"Max Drawdown:\s+([-+]?\d*\.?\d+)%?",
            "profit_factor": r"Profit Factor:\s+([-+]?\d*\.?\d+)",
            "win_rate": r"Win Rate:\s+([-+]?\d*\.?\d+)%?"
        }

        import re
        for metric_name, pattern in patterns.items():
            match = re.search(pattern, stdout, re.IGNORECASE)
            if match:
                try:
                    metrics[metric_name] = float(match.group(1))
                except ValueError:
                    metrics[metric_name] = 0.0

        # If primary metric not found, default to 0
        if metric not in metrics:
            metrics[metric] = 0.0

        return metrics

    def _merge_train_test_results(
        self, results_raw: List[Dict], combinations: List[Dict]
    ) -> List[Dict]:
        """
        Merge train and test results for each parameter combination.

        Args:
            results_raw: Raw results from parallel execution
            combinations: Original parameter combinations

        Returns:
            Merged results with both train and test metrics
        """
        merged = []

        for params in combinations:
            # Find train and test results for this param combination
            train_result = None
            test_result = None

            for result in results_raw:
                if result and result["parameters"] == params:
                    if result["run_type"] == "train":
                        train_result = result
                    elif result["run_type"] == "test":
                        test_result = result

            # Merge
            merged_result = {"parameters": params}

            if train_result:
                for key, value in train_result.items():
                    if key.startswith("train_"):
                        merged_result[key] = value

            if test_result:
                for key, value in test_result.items():
                    if key.startswith("test_"):
                        merged_result[key] = value

            merged.append(merged_result)

        return merged


def main():
    """CLI entry point for parameter optimization."""
    parser = argparse.ArgumentParser(
        description="Parameter optimization for LEAN algorithms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple optimization
  python scripts/optimize_parameters.py \\
    --algorithm algorithms/my_strategy \\
    --params "sma_period:10,20,50" \\
    --metric sharpe_ratio \\
    --start 2020-01-01 --end 2024-12-31

  # With train/test split
  python scripts/optimize_parameters.py \\
    --algorithm algorithms/my_strategy \\
    --params "sma_period:10,20,50;rsi_threshold:30,40,50" \\
    --metric sharpe_ratio \\
    --start 2020-01-01 --end 2024-12-31 \\
    --train-test-split 0.6

  # Multiple parameters
  python scripts/optimize_parameters.py \\
    --algorithm algorithms/my_strategy \\
    --params "period:10,20,50;threshold:0.01,0.02,0.05;stop_loss:0.02,0.05" \\
    --metric total_return \\
    --start 2020-01-01 --end 2024-12-31
        """
    )

    parser.add_argument("--algorithm", required=True, help="Path to LEAN algorithm")
    parser.add_argument(
        "--params",
        required=True,
        help='Parameter ranges as "name:val1,val2,val3;name2:val1,val2"'
    )
    parser.add_argument(
        "--metric",
        default="sharpe_ratio",
        choices=["sharpe_ratio", "total_return", "sortino_ratio", "profit_factor", "max_drawdown"],
        help="Optimization metric (default: sharpe_ratio)"
    )
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--cost-model", default="ib_standard", help="Cost model")
    parser.add_argument(
        "--train-test-split",
        type=float,
        help="Train/test split ratio (e.g., 0.6 = 60%% train, 40%% test)"
    )
    parser.add_argument(
        "--overfitting-threshold",
        type=float,
        default=0.7,
        help="Flag overfitting if test < threshold * train (default: 0.7)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        help="Number of parallel workers (default: all CPU cores)"
    )

    args = parser.parse_args()

    # Parse parameter ranges
    param_ranges = {}
    for param_spec in args.params.split(";"):
        name, values_str = param_spec.split(":")
        values = []
        for v in values_str.split(","):
            # Try to convert to number
            try:
                if "." in v:
                    values.append(float(v))
                else:
                    values.append(int(v))
            except ValueError:
                values.append(v)  # Keep as string
        param_ranges[name] = values

    # Run optimization
    optimizer = ParameterOptimizer(max_workers=args.workers)
    result = optimizer.optimize(
        algorithm=args.algorithm,
        param_ranges=param_ranges,
        metric=args.metric,
        start_date=args.start,
        end_date=args.end,
        cost_model=args.cost_model,
        train_test_split=args.train_test_split,
        overfitting_threshold=args.overfitting_threshold
    )

    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
