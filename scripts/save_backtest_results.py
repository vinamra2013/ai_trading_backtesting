#!/usr/bin/env python3
"""
Save Backtest Results for Ranking - Epic 21: Strategy Ranking & Portfolio Optimizer
Post-processes parallel backtest results and saves them in JSON format for ranking consumption.

This script bridges the gap between parallel backtest execution and strategy ranking workflows
by converting consolidated results into individual JSON files that the ranking system expects.
"""

import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import argparse
import sys
from datetime import datetime

logger = logging.getLogger(__name__)


class BacktestResultsSaver:
    """
    Saves consolidated backtest results to individual JSON files for ranking consumption.

    Epic 21: Strategy Ranking & Portfolio Optimizer
    Converts parallel backtest output to ranking-compatible format.
    """

    def __init__(self, output_dir: str = "results/backtests"):
        """
        Initialize results saver.

        Args:
            output_dir: Directory to save individual result JSON files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"BacktestResultsSaver initialized with output directory: {output_dir}")

    def load_consolidated_results(self, input_file: str) -> pd.DataFrame:
        """
        Load consolidated backtest results from CSV file.

        Args:
            input_file: Path to consolidated results CSV file

        Returns:
            DataFrame with consolidated results
        """
        try:
            df = pd.read_csv(input_file)
            logger.info(f"Loaded {len(df)} consolidated results from {input_file}")
            return df
        except Exception as e:
            logger.error(f"Failed to load consolidated results: {e}")
            raise

    def convert_to_ranking_format(self, row: pd.Series) -> Dict[str, Any]:
        """
        Convert a consolidated result row to ranking-compatible JSON format.

        Args:
            row: Single row from consolidated results DataFrame

        Returns:
            Dictionary in ranking system expected format
        """
        # Extract strategy name from path or use fallback
        strategy_path = row.get('strategy_path', '')
        if strategy_path and not pd.isna(strategy_path):
            strategy_name = Path(strategy_path).stem
        else:
            # Try to extract from job_id or use fallback
            job_id = str(row.get('job_id', ''))
            if 'sma_crossover' in job_id:
                strategy_name = 'sma_crossover'
            elif 'rsi_momentum' in job_id:
                strategy_name = 'rsi_momentum'
            else:
                strategy_name = 'unknown_strategy'

        # Build ranking-compatible result structure
        result = {
            # Core identifiers
            'strategy': strategy_name,
            'symbol': row.get('symbol', 'UNKNOWN'),
            'strategy_path': strategy_path,

                # Performance metrics (required for ranking)
                'sharpe_ratio': float(row.get('sharpe_ratio', 0) or 0),
                'max_drawdown': float(row.get('max_drawdown', 0) or 0),
                'win_rate': float(row.get('win_rate', 0) or 0),
                'total_trades': int(row.get('total_trades', row.get('trade_count', 0)) or 0),
            'profit_factor': float(row.get('profit_factor', 1.0) or 1.0),
            'total_return': float(row.get('total_return', 0) or 0),
            'volatility': float(row.get('volatility', 0) or 0),
            'avg_trade': float(row.get('avg_trade_return', 0) or 0),

            # Additional metrics (optional but useful)
            'sortino_ratio': float(row.get('sortino_ratio', 0) or 0),
            'annual_return': float(row.get('annual_return', 0) or 0),
            'calmar_ratio': float(row.get('calmar_ratio', 0) or 0),
            'alpha': float(row.get('alpha', 0) or 0),
            'beta': float(row.get('beta', 1.0) or 1.0),

            # Execution metadata
            'execution_time_seconds': float(row.get('execution_time_seconds', 0) or 0),
            'job_id': str(row.get('job_id', '')),
            'batch_id': str(row.get('batch_id', '')),
            'status': 'success',

            # Timestamp
            'timestamp': datetime.now().isoformat(),
            'processed_by': 'backtest_results_saver'
        }

        return result

    def save_individual_results(self, results_df: pd.DataFrame,
                              filename_template: str = "{strategy}_{symbol}_{timestamp}.json") -> List[str]:
        """
        Save each result as an individual JSON file.

        Args:
            results_df: DataFrame with consolidated results
            filename_template: Template for individual result filenames

        Returns:
            List of saved file paths
        """
        saved_files = []

        for idx, row in results_df.iterrows():
            try:
                # Convert row to ranking format
                result_dict = self.convert_to_ranking_format(row)

                # Generate filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                strategy = result_dict['strategy']
                symbol = result_dict['symbol']

                filename = filename_template.format(
                    strategy=strategy,
                    symbol=symbol,
                    timestamp=timestamp,
                    index=idx
                )

                filepath = self.output_dir / filename

                # Save as JSON
                with open(filepath, 'w') as f:
                    json.dump(result_dict, f, indent=2, default=str)

                saved_files.append(str(filepath))
                logger.debug(f"Saved result for {strategy} ({symbol}) to {filepath}")

            except Exception as e:
                logger.error(f"Failed to save result for row {idx}: {e}")
                continue

        logger.info(f"Successfully saved {len(saved_files)} individual result files")
        return saved_files

    def validate_results_for_ranking(self, results_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate that results contain required fields for ranking.

        Args:
            results_df: DataFrame with consolidated results

        Returns:
            Validation report dictionary
        """
        # Handle field name mapping (trade_count -> total_trades)
        required_fields = ['sharpe_ratio', 'max_drawdown', 'win_rate']
        required_fields_mapped = ['total_trades']  # Fields that may have alternative names

        # Check if we have the required fields or their alternatives
        missing_required = []
        for field in required_fields:
            if field not in results_df.columns:
                missing_required.append(field)

        # Check for total_trades or trade_count
        has_total_trades = 'total_trades' in results_df.columns or 'trade_count' in results_df.columns
        if not has_total_trades:
            missing_required.append('total_trades')

        optional_fields = ['profit_factor', 'total_return', 'volatility']

        validation = {
            'total_results': len(results_df),
            'required_fields_present': len(missing_required) == 0,
            'missing_required_fields': missing_required,
            'optional_fields_present': [f for f in optional_fields if f in results_df.columns],
            'results_with_valid_sharpe': len(results_df[results_df['sharpe_ratio'].notna()]),
            'results_with_valid_drawdown': len(results_df[results_df['max_drawdown'].notna()]),
            'unique_strategies': results_df['strategy'].nunique() if 'strategy' in results_df.columns else 0,
            'unique_symbols': results_df['symbol'].nunique() if 'symbol' in results_df.columns else 0
        }

        # Check for data quality issues
        if validation['required_fields_present']:
            # Include total_trades field for NaN checking
            check_fields = required_fields + ['total_trades']
            nan_counts = {}
            for field in check_fields:
                if field == 'total_trades':
                    # Check both possible field names
                    trade_field = 'total_trades' if 'total_trades' in results_df.columns else 'trade_count'
                    nan_counts[field] = results_df[trade_field].isna().sum()
                else:
                    nan_counts[field] = results_df[field].isna().sum()
            validation['nan_counts'] = nan_counts

        return validation

    def generate_summary_report(self, results_df: pd.DataFrame,
                              saved_files: List[str]) -> Dict[str, Any]:
        """
        Generate summary report of the conversion process.

        Args:
            results_df: Original consolidated results
            saved_files: List of saved file paths

        Returns:
            Summary report dictionary
        """
        summary = {
            'conversion_timestamp': datetime.now().isoformat(),
            'input_results_count': len(results_df),
            'output_files_count': len(saved_files),
            'output_directory': str(self.output_dir),
            'validation': self.validate_results_for_ranking(results_df)
        }

        # Add performance summary if available
        if not results_df.empty:
            perf_summary = {}
            if 'sharpe_ratio' in results_df.columns:
                perf_summary['avg_sharpe'] = results_df['sharpe_ratio'].mean()
                perf_summary['max_sharpe'] = results_df['sharpe_ratio'].max()
                perf_summary['min_sharpe'] = results_df['sharpe_ratio'].min()

            if 'max_drawdown' in results_df.columns:
                perf_summary['avg_drawdown'] = results_df['max_drawdown'].mean()
                perf_summary['max_drawdown'] = results_df['max_drawdown'].max()

            summary['performance_summary'] = perf_summary

        return summary


def main():
    """Command-line interface for saving backtest results."""
    parser = argparse.ArgumentParser(
        description="Convert consolidated backtest results to individual JSON files for ranking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert parallel backtest results for ranking
  python scripts/save_backtest_results.py --input results/parallel_backtests.csv --output results/backtests/

  # Custom filename template
  python scripts/save_backtest_results.py --input results.csv --template "{strategy}_{symbol}.json"

  # Validate results without saving
  python scripts/save_backtest_results.py --input results.csv --validate-only
        """
    )

    parser.add_argument(
        '--input', '-i',
        type=str,
        required=True,
        help='Path to consolidated backtest results CSV file'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        default='results/backtests',
        help='Output directory for individual JSON files (default: results/backtests)'
    )

    parser.add_argument(
        '--template',
        type=str,
        default='{strategy}_{symbol}_{timestamp}.json',
        help='Filename template for individual results (default: {strategy}_{symbol}_{timestamp}.json)'
    )

    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate results, do not save files'
    )

    parser.add_argument(
        '--summary-report',
        type=str,
        help='Save summary report to specified JSON file'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        # Initialize saver
        saver = BacktestResultsSaver(args.output)

        # Load consolidated results
        print(f"Loading consolidated results from: {args.input}")
        results_df = saver.load_consolidated_results(args.input)

        if results_df.empty:
            print("No results found in input file")
            return 1

        # Validate results
        print("Validating results for ranking compatibility...")
        validation = saver.validate_results_for_ranking(results_df)

        print(f"Validation Results:")
        print(f"  Total results: {validation['total_results']}")
        print(f"  Required fields present: {validation['required_fields_present']}")
        if not validation['required_fields_present']:
            print(f"  Missing required fields: {validation['missing_required_fields']}")
        print(f"  Valid Sharpe ratios: {validation['results_with_valid_sharpe']}")
        print(f"  Valid drawdowns: {validation['results_with_valid_drawdown']}")
        print(f"  Unique strategies: {validation['unique_strategies']}")
        print(f"  Unique symbols: {validation['unique_symbols']}")

        if not validation['required_fields_present']:
            print("ERROR: Missing required fields for ranking. Cannot proceed.")
            return 1

        if not args.validate_only:
            # Save individual results
            print(f"\nSaving individual result files to: {args.output}")
            saved_files = saver.save_individual_results(results_df, args.template)

            print(f"Successfully saved {len(saved_files)} result files")

            # Generate summary report
            summary = saver.generate_summary_report(results_df, saved_files)

            if args.summary_report:
                with open(args.summary_report, 'w') as f:
                    json.dump(summary, f, indent=2, default=str)
                print(f"Summary report saved to: {args.summary_report}")

            print("\nReady for ranking! Use the following commands:")
            print(f"  python scripts/strategy_ranker.py --results-dir {args.output}")
            print(f"  python scripts/correlation_analyzer.py --rankings rankings.csv")
            print(f"  python scripts/portfolio_optimizer.py --strategies filtered_strategies.csv")

        return 0

    except Exception as e:
        logger.error(f"Error during result conversion: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())