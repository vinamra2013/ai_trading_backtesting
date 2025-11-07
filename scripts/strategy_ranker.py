#!/usr/bin/env python3
"""
Strategy Ranker - Epic 21: US-21.1 - Multi-Criteria Ranking System
Multi-criteria strategy ranking system with configurable scoring weights.

This module implements systematic strategy evaluation using multiple performance metrics
with configurable weights and normalization for consistent ranking.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
import argparse
import logging
import yaml

from utils.results_consolidator import RankingResultsConsolidator

logger = logging.getLogger(__name__)


class StrategyRanker:
    """
    Multi-criteria strategy ranking system.

    Evaluates strategies based on multiple performance metrics with configurable weights,
    providing consistent, reproducible rankings for portfolio construction.
    """

    def __init__(self, config_path: str = 'config/ranking_config.yaml'):
        """
        Initialize strategy ranker with configuration.

        Args:
            config_path: Path to ranking configuration file
        """
        self.config = self._load_config(config_path)
        self.consolidator = RankingResultsConsolidator()

        # Extract scoring configuration
        self.scoring_weights = self.config['scoring']['weights']
        self.scoring_params = self.config['scoring']

        # Validate weights sum to 100
        total_weight = sum(self.scoring_weights.values())
        if abs(total_weight - 100) > 0.1:  # Allow small floating point errors
            logger.warning(f"Scoring weights sum to {total_weight}, not 100. Normalizing...")
            self.scoring_weights = {k: v/total_weight * 100 for k, v in self.scoring_weights.items()}

        logger.info(f"StrategyRanker initialized with {len(self.scoring_weights)} scoring criteria")
        logger.info(f"Scoring weights: {self.scoring_weights}")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load ranking configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded ranking configuration from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            # Return default configuration
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default ranking configuration."""
        return {
            'scoring': {
                'weights': {
                    'sharpe_ratio': 40,
                    'consistency': 20,
                    'drawdown_control': 20,
                    'trade_frequency': 10,
                    'capital_efficiency': 10
                },
                'consistency': {
                    'window_days': 30,
                    'min_periods': 10
                },
                'drawdown_control': {
                    'max_drawdown_weight': 1.0
                },
                'trade_frequency': {
                    'optimal_trades_per_month': 20,
                    'frequency_weight': 1.0
                },
                'capital_efficiency': {
                    'efficiency_weight': 1.0
                }
            }
        }

    def rank_strategies(self, results_dir: Optional[str] = None,
                        results_df: Optional[pd.DataFrame] = None,
                        csv_input: Optional[str] = None) -> pd.DataFrame:
        """
        Rank strategies based on multi-criteria scoring.

        Args:
            results_dir: Directory containing backtest results (if results_df not provided)
            results_df: Pre-consolidated results DataFrame
            csv_input: Path to consolidated CSV file (alternative to results_dir)

        Returns:
            DataFrame with ranked strategies and composite scores
        """
        # Get consolidated results
        if results_df is None:
            if csv_input is not None:
                # Load directly from CSV
                results_df = self._load_from_csv(csv_input)
            elif results_dir is not None:
                # Load from JSON files in directory
                self.consolidator = RankingResultsConsolidator(results_dir)
                results_df = self.consolidator.consolidate_to_dataframe()
            else:
                # Use default directory
                results_df = self.consolidator.consolidate_to_dataframe()

        if results_df is None or results_df.empty:
            logger.warning("No results to rank")
            return pd.DataFrame()

        logger.info(f"Ranking {len(results_df)} strategies using {len(self.scoring_weights)} criteria")

        # Calculate individual scores for each criterion
        scored_df = results_df.copy()

        # Calculate each scoring component
        scored_df['sharpe_score'] = self._calculate_sharpe_score(scored_df)
        scored_df['consistency_score'] = self._calculate_consistency_score(scored_df)
        scored_df['drawdown_score'] = self._calculate_drawdown_score(scored_df)
        scored_df['frequency_score'] = self._calculate_frequency_score(scored_df)
        scored_df['efficiency_score'] = self._calculate_efficiency_score(scored_df)

        # Calculate composite score
        scored_df['composite_score'] = self._calculate_composite_score(scored_df)

        # Rank strategies by composite score
        scored_df['rank'] = scored_df['composite_score'].rank(ascending=False, method='dense').astype(int)

        # Sort by rank
        ranked_df = scored_df.sort_values('composite_score', ascending=False).reset_index(drop=True)

        logger.info(f"Strategy ranking complete. Top strategy: {ranked_df.iloc[0]['strategy']} "
                   f"(score: {ranked_df.iloc[0]['composite_score']:.2f})")

        return ranked_df

    def _calculate_sharpe_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate Sharpe ratio score (0-100 scale)."""
        sharpe_values = df['sharpe_ratio'].fillna(0)

        # Normalize Sharpe ratios to 0-100 scale
        # Assume Sharpe > 3 is excellent (100), Sharpe < 0 is poor (0)
        min_sharpe, max_sharpe = -1, 3
        normalized = (sharpe_values - min_sharpe) / (max_sharpe - min_sharpe)
        normalized = np.clip(normalized, 0, 1)  # Ensure 0-1 range

        return (normalized * 100).round(2)

    def _calculate_consistency_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate consistency score based on rolling return stability."""
        # For now, use win rate as a proxy for consistency
        # TODO: Implement rolling 30-day return standard deviation when equity curves available
        win_rates = df['win_rate'].fillna(0.5)

        # Normalize win rate to 0-100 (50% = 0, 70%+ = 100)
        min_win, max_win = 0.5, 0.8
        normalized = (win_rates - min_win) / (max_win - min_win)
        normalized = np.clip(normalized, 0, 1)

        return (normalized * 100).round(2)

    def _calculate_drawdown_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate drawdown control score (lower drawdown = higher score)."""
        drawdowns = df['max_drawdown'].fillna(0.5).abs()  # Ensure positive

        # Normalize drawdown to 0-100 scale
        # 0% drawdown = 100, 50%+ drawdown = 0
        max_dd, min_dd = 0.5, 0.0
        normalized = 1 - (drawdowns - min_dd) / (max_dd - min_dd)
        normalized = np.clip(normalized, 0, 1)

        return (normalized * 100).round(2)

    def _calculate_frequency_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate trade frequency score."""
        # Calculate trades per month (assuming 1 year = 12 months)
        total_trades = df['total_trades'].fillna(0)

        # Assume backtests are ~1 year, so trades_per_month = total_trades / 12
        trades_per_month = total_trades / 12

        optimal_trades = self.scoring_params['trade_frequency']['optimal_trades_per_month']

        # Score based on distance from optimal frequency
        # Use Gaussian-like scoring centered on optimal
        distance = abs(trades_per_month - optimal_trades)
        max_distance = optimal_trades  # Allow up to 2x optimal as still good

        normalized = 1 - (distance / max_distance)
        normalized = np.clip(normalized, 0, 1)

        return (normalized * 100).round(2)

    def _calculate_efficiency_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate capital efficiency score."""
        # Use profit factor as proxy for capital efficiency
        profit_factors = df['profit_factor'].fillna(1.0)

        # Normalize profit factor to 0-100
        # PF = 1.0 = 0, PF = 2.0+ = 100
        min_pf, max_pf = 1.0, 3.0
        normalized = (profit_factors - min_pf) / (max_pf - min_pf)
        normalized = np.clip(normalized, 0, 1)

        return (normalized * 100).round(2)

    def _calculate_composite_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate weighted composite score from individual criteria."""
        composite = (
            df['sharpe_score'] * (self.scoring_weights['sharpe_ratio'] / 100) +
            df['consistency_score'] * (self.scoring_weights['consistency'] / 100) +
            df['drawdown_score'] * (self.scoring_weights['drawdown_control'] / 100) +
            df['frequency_score'] * (self.scoring_weights['trade_frequency'] / 100) +
            df['efficiency_score'] * (self.scoring_weights['capital_efficiency'] / 100)
        )

        return composite.round(2)

    def _load_from_csv(self, csv_path: str) -> pd.DataFrame:
        """
        Load backtest results directly from CSV file.

        Args:
            csv_path: Path to CSV file with consolidated results

        Returns:
            DataFrame with results ready for ranking
        """
        try:
            df = pd.read_csv(csv_path)
            logger.info(f"Loaded {len(df)} results from CSV: {csv_path}")

            # Map CSV columns to expected DataFrame format
            # The CSV has columns like: symbol, strategy, sharpe_ratio, max_drawdown, etc.
            # We need to ensure the column names match what the ranking functions expect

            # Rename columns if needed
            column_mapping = {
                'trade_count': 'total_trades',  # CSV uses trade_count, ranking expects total_trades
            }

            df = df.rename(columns=column_mapping)

            # Ensure required columns exist with defaults
            required_columns = ['strategy', 'symbol', 'sharpe_ratio', 'max_drawdown', 'win_rate', 'total_trades', 'profit_factor']
            for col in required_columns:
                if col not in df.columns:
                    if col in ['sharpe_ratio', 'max_drawdown', 'win_rate', 'profit_factor']:
                        df[col] = 0.0
                    elif col == 'total_trades':
                        df[col] = 0
                    else:
                        df[col] = 'unknown'

            # Convert data types
            df['total_trades'] = df['total_trades'].fillna(0).astype(int)
            df['sharpe_ratio'] = df['sharpe_ratio'].fillna(0.0).astype(float)
            df['max_drawdown'] = df['max_drawdown'].fillna(0.0).astype(float)
            df['win_rate'] = df['win_rate'].fillna(0.0).astype(float)
            df['profit_factor'] = df['profit_factor'].fillna(1.0).astype(float)

            logger.info(f"Prepared DataFrame with {len(df)} rows and columns: {list(df.columns)}")
            return df

        except Exception as e:
            logger.error(f"Failed to load CSV from {csv_path}: {e}")
            return pd.DataFrame()

    def get_top_strategies(self, ranked_df: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
        """
        Get top N strategies from ranked results.

        Args:
            ranked_df: Ranked strategies DataFrame
            top_n: Number of top strategies to return

        Returns:
            DataFrame with top N strategies
        """
        if ranked_df.empty:
            return pd.DataFrame()

        top_strategies = ranked_df.head(top_n).copy()
        logger.info(f"Selected top {len(top_strategies)} strategies for portfolio construction")

        return top_strategies

    def export_rankings(self, ranked_df: pd.DataFrame,
                        output_path: Union[str, Path],
                        format: str = 'csv') -> str:
        """
        Export ranked strategies to file.

        Args:
            ranked_df: Ranked strategies DataFrame
            output_path: Output file path
            format: Export format ('csv', 'json', 'parquet')

        Returns:
            Path to exported file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Select columns for export
        export_columns = [
            'rank', 'strategy', 'symbol', 'composite_score',
            'sharpe_ratio', 'max_drawdown', 'win_rate', 'total_trades',
            'sharpe_score', 'consistency_score', 'drawdown_score',
            'frequency_score', 'efficiency_score'
        ]

        export_df = ranked_df[export_columns].copy()

        if format.lower() == 'csv':
            export_df.to_csv(output_path, index=False)
        elif format.lower() == 'json':
            export_df.to_json(output_path, orient='records', indent=2)
        elif format.lower() == 'parquet':
            export_df.to_parquet(output_path, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info(f"Exported rankings to {output_path}")
        return str(output_path)

    def get_ranking_summary(self, ranked_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate ranking summary statistics.

        Args:
            ranked_df: Ranked strategies DataFrame

        Returns:
            Dictionary with ranking summary
        """
        if ranked_df.empty:
            return {}

        summary = {
            'total_strategies_ranked': len(ranked_df),
            'unique_strategies': ranked_df['strategy'].nunique(),
            'unique_symbols': ranked_df['symbol'].nunique(),
            'top_strategy': {
                'name': ranked_df.iloc[0]['strategy'],
                'symbol': ranked_df.iloc[0]['symbol'],
                'score': ranked_df.iloc[0]['composite_score'],
                'sharpe': ranked_df.iloc[0]['sharpe_ratio']
            },
            'score_distribution': {
                'mean': ranked_df['composite_score'].mean(),
                'std': ranked_df['composite_score'].std(),
                'min': ranked_df['composite_score'].min(),
                'max': ranked_df['composite_score'].max(),
                'median': ranked_df['composite_score'].median()
            },
            'scoring_weights': self.scoring_weights
        }

        return summary


def main():
    """Command-line interface for strategy ranking."""
    parser = argparse.ArgumentParser(
        description="Rank trading strategies using multi-criteria scoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Rank strategies from backtest results
  python scripts/strategy_ranker.py --results-dir results/backtests/ --output rankings.csv

  # Rank with custom config
  python scripts/strategy_ranker.py --results-dir results/backtests/ --config config/custom_ranking.yaml --top-n 20

  # Export in JSON format
  python scripts/strategy_ranker.py --results-dir results/backtests/ --output rankings.json --format json
        """
    )

    # Make results-dir and csv-input mutually exclusive
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--results-dir',
        type=str,
        help='Directory containing backtest result files'
    )

    group.add_argument(
        '--csv-input',
        type=str,
        help='Path to consolidated backtest results CSV file'
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config/ranking_config.yaml',
        help='Path to ranking configuration file'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Output file path for rankings (optional)'
    )

    parser.add_argument(
        '--format',
        type=str,
        choices=['csv', 'json', 'parquet'],
        default='csv',
        help='Output format (default: csv)'
    )

    parser.add_argument(
        '--top-n',
        type=int,
        default=15,
        help='Number of top strategies to display/export (default: 15)'
    )

    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Only show summary statistics, no detailed rankings'
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
        # Initialize ranker
        ranker = StrategyRanker(args.config)

        # Rank strategies
        if args.csv_input:
            print(f"Loading backtest results from CSV: {args.csv_input}")
            rankings = ranker.rank_strategies(csv_input=args.csv_input)
        else:
            print(f"Loading backtest results from directory: {args.results_dir}")
            rankings = ranker.rank_strategies(args.results_dir)

        if rankings.empty:
            print("No strategies found to rank")
            return 1

        # Get top strategies
        top_strategies = ranker.get_top_strategies(rankings, args.top_n)

        # Show summary
        summary = ranker.get_ranking_summary(rankings)
        print(f"\n{'='*60}")
        print("STRATEGY RANKING SUMMARY")
        print(f"{'='*60}")
        print(f"Total strategies ranked: {summary['total_strategies_ranked']}")
        print(f"Unique strategies: {summary['unique_strategies']}")
        print(f"Unique symbols: {summary['unique_symbols']}")
        print(f"Top strategy: {summary['top_strategy']['name']} ({summary['top_strategy']['symbol']})")
        print(".2f")
        print(".2f")
        print(f"\nScoring weights: {summary['scoring_weights']}")

        if not args.summary_only:
            print(f"\n{'='*100}")
            print("TOP STRATEGIES")
            print(f"{'='*100}")
            print(top_strategies.to_string(index=False))

        # Export if requested
        if args.output:
            output_path = ranker.export_rankings(top_strategies, args.output, args.format)
            print(f"\nRankings exported to: {output_path}")

        return 0

    except Exception as e:
        logger.error(f"Error during strategy ranking: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())