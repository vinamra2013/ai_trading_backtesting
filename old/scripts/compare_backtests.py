#!/usr/bin/env python3
"""
Backtest Comparison Tool - Compare performance of multiple backtests.

Usage:
    python compare_backtests.py backtest_id1 backtest_id2 --metric sharpe_ratio
    python compare_backtests.py --list  # List all available backtests

Track A: Parser & Core Infrastructure
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from tabulate import tabulate

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BacktestComparator:
    """
    Compare multiple backtest results side-by-side.

    Features:
    - Load multiple backtest JSON files
    - Create comparison tables
    - Highlight winners by metric
    - Export comparison data
    """

    def __init__(self, results_dir: str = "results/backtests"):
        """
        Initialize comparator.

        Args:
            results_dir: Directory containing backtest result JSON files
        """
        self.results_dir = Path(results_dir)
        if not self.results_dir.exists():
            raise ValueError(f"Results directory not found: {results_dir}")

    def load_backtest(self, backtest_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a single backtest result.

        Args:
            backtest_id: UUID or partial UUID of backtest

        Returns:
            Backtest result dictionary or None if not found
        """
        # Try exact match first
        result_file = self.results_dir / f"{backtest_id}.json"

        if not result_file.exists():
            # Try partial match (for convenience)
            matches = list(self.results_dir.glob(f"{backtest_id}*.json"))
            if len(matches) == 1:
                result_file = matches[0]
            elif len(matches) > 1:
                logger.error(f"Ambiguous backtest ID '{backtest_id}': {len(matches)} matches")
                return None
            else:
                logger.error(f"Backtest not found: {backtest_id}")
                return None

        try:
            with open(result_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse {result_file}: {e}")
            return None

    def list_backtests(self) -> List[Dict[str, Any]]:
        """
        List all available backtests.

        Returns:
            List of backtest metadata (ID, algorithm, date, etc.)
        """
        backtests = []

        for result_file in self.results_dir.glob("*.json"):
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    backtests.append({
                        'backtest_id': data.get('backtest_id', result_file.stem),
                        'algorithm': data.get('algorithm', 'Unknown'),
                        'timestamp': data.get('timestamp', 'Unknown'),
                        'period': data.get('period', {}),
                        'trade_count': data.get('trade_count', 0),
                        'status': data.get('status', 'Unknown')
                    })
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Skipping invalid file {result_file}: {e}")
                continue

        # Sort by timestamp (newest first)
        backtests.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return backtests

    def compare(self, backtest_ids: List[str], metric: str = "sharpe_ratio") -> Dict[str, Any]:
        """
        Compare multiple backtests.

        Args:
            backtest_ids: List of backtest IDs to compare
            metric: Primary metric to highlight winner (default: sharpe_ratio)

        Returns:
            Comparison dictionary with results, table, and winner
        """
        logger.info(f"Comparing {len(backtest_ids)} backtests by {metric}")

        # Load all backtests
        results = []
        for bid in backtest_ids:
            result = self.load_backtest(bid)
            if result:
                results.append(result)
            else:
                logger.warning(f"Skipping {bid} - could not load")

        if len(results) < 2:
            logger.error("Need at least 2 valid backtests to compare")
            return None

        # Build comparison table
        comparison_data = self._build_comparison_table(results, metric)

        # Determine winner
        winner = self._find_winner(results, metric)

        # Print results
        self._print_comparison(comparison_data, metric, winner)

        return {
            "backtests": results,
            "comparison_table": comparison_data,
            "metric": metric,
            "winner": winner,
            "num_compared": len(results)
        }

    def _build_comparison_table(self, results: List[Dict], highlight_metric: str) -> List[List]:
        """
        Build side-by-side comparison table.

        Returns:
            Table data for tabulate (list of rows)
        """
        # Define metrics to compare
        metrics_to_show = [
            ('Total Return (%)', lambda x: f"{x.get('metrics', {}).get('total_return', 0)*100:.2f}"),
            ('Annualized Return (%)', lambda x: f"{x.get('metrics', {}).get('annualized_return', 0)*100:.2f}"),
            ('Sharpe Ratio', lambda x: f"{x.get('metrics', {}).get('sharpe_ratio', 0):.2f}"),
            ('Sortino Ratio', lambda x: f"{x.get('metrics', {}).get('sortino_ratio', 0):.2f}"),
            ('Max Drawdown (%)', lambda x: f"{x.get('metrics', {}).get('max_drawdown', 0)*100:.2f}"),
            ('Win Rate (%)', lambda x: f"{x.get('metrics', {}).get('win_rate', 0)*100:.2f}"),
            ('Profit Factor', lambda x: f"{x.get('metrics', {}).get('profit_factor', 0):.2f}"),
            ('Total Trades', lambda x: f"{x.get('trade_count', 0)}"),
            ('Avg Win (%)', lambda x: f"{x.get('metrics', {}).get('avg_win', 0)*100:.2f}"),
            ('Avg Loss (%)', lambda x: f"{x.get('metrics', {}).get('avg_loss', 0)*100:.2f}"),
        ]

        # Build table
        table = []

        # Header row (backtest IDs)
        header = ['Metric'] + [r.get('backtest_id', 'Unknown')[:8] for r in results]
        table.append(header)

        # Metric rows
        for metric_name, extractor in metrics_to_show:
            row = [metric_name]
            for result in results:
                row.append(extractor(result))
            table.append(row)

        return table

    def _find_winner(self, results: List[Dict], metric: str) -> Optional[Dict]:
        """
        Find the best backtest by specified metric.

        Args:
            results: List of backtest results
            metric: Metric to optimize (higher is better, except drawdown)

        Returns:
            Winner backtest result
        """
        if not results:
            return None

        # Handle special cases (lower is better)
        reverse = metric in ['max_drawdown', 'avg_loss']

        best = max(
            results,
            key=lambda x: x.get('metrics', {}).get(metric, -float('inf') if not reverse else float('inf'))
        )

        return best

    def _print_comparison(self, table_data: List[List], metric: str, winner: Dict):
        """
        Pretty print comparison results.

        Args:
            table_data: Table rows for tabulate
            metric: Highlighted metric
            winner: Winner backtest
        """
        print("\n" + "="*80)
        print("BACKTEST COMPARISON")
        print("="*80)

        # Print table
        headers = table_data[0]
        rows = table_data[1:]
        print(tabulate(rows, headers=headers, tablefmt='grid'))

        # Highlight winner
        if winner:
            winner_id = winner.get('backtest_id', 'Unknown')
            winner_value = winner.get('metrics', {}).get(metric, 'N/A')

            print("\n" + "-"*80)
            print(f"🏆 WINNER (by {metric}): {winner_id}")
            print(f"   Value: {winner_value}")
            print(f"   Algorithm: {winner.get('algorithm', 'Unknown')}")
            print(f"   Period: {winner.get('period', {}).get('start')} to {winner.get('period', {}).get('end')}")
            print("-"*80 + "\n")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Compare multiple backtest results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare two backtests
  python compare_backtests.py abc123 def456 --metric sharpe_ratio

  # Compare by total return
  python compare_backtests.py abc123 def456 xyz789 --metric total_return

  # List all available backtests
  python compare_backtests.py --list
        """
    )

    parser.add_argument(
        'backtest_ids',
        nargs='*',
        help='Backtest IDs to compare (UUID or partial UUID)'
    )

    parser.add_argument(
        '--metric',
        default='sharpe_ratio',
        choices=[
            'total_return', 'annualized_return', 'sharpe_ratio', 'sortino_ratio',
            'max_drawdown', 'win_rate', 'profit_factor', 'avg_win', 'avg_loss'
        ],
        help='Metric to optimize for winner selection (default: sharpe_ratio)'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available backtests'
    )

    parser.add_argument(
        '--results-dir',
        default='results/backtests',
        help='Directory containing backtest results (default: results/backtests)'
    )

    parser.add_argument(
        '--export',
        help='Export comparison to JSON file'
    )

    args = parser.parse_args()

    # Initialize comparator
    try:
        comparator = BacktestComparator(results_dir=args.results_dir)
    except ValueError as e:
        logger.error(f"Failed to initialize comparator: {e}")
        sys.exit(1)

    # Handle --list
    if args.list:
        backtests = comparator.list_backtests()

        if not backtests:
            print("No backtests found.")
            sys.exit(0)

        # Print list
        print(f"\nFound {len(backtests)} backtest(s):\n")

        headers = ['ID (short)', 'Algorithm', 'Timestamp', 'Period', 'Trades', 'Status']
        rows = []

        for bt in backtests:
            period = bt.get('period', {})
            period_str = f"{period.get('start', 'N/A')} to {period.get('end', 'N/A')}"

            rows.append([
                bt['backtest_id'][:8],
                bt['algorithm'],
                bt['timestamp'][:19] if bt['timestamp'] != 'Unknown' else 'Unknown',
                period_str,
                bt['trade_count'],
                bt['status']
            ])

        print(tabulate(rows, headers=headers, tablefmt='grid'))
        print(f"\nUse the ID (short) to reference backtests in comparisons.\n")
        sys.exit(0)

    # Handle comparison
    if len(args.backtest_ids) < 2:
        logger.error("Need at least 2 backtest IDs to compare")
        parser.print_help()
        sys.exit(1)

    # Run comparison
    result = comparator.compare(args.backtest_ids, args.metric)

    if not result:
        logger.error("Comparison failed")
        sys.exit(1)

    # Export if requested
    if args.export:
        export_path = Path(args.export)
        export_path.write_text(json.dumps(result, indent=2, default=str))
        logger.info(f"✓ Comparison exported to {export_path}")

    sys.exit(0)


if __name__ == "__main__":
    main()
