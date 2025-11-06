#!/usr/bin/env python3
"""
Correlation Analyzer - Epic 21: US-21.2 - Correlation Analysis Engine
Analyzes strategy correlations and implements diversity selection algorithms.

This module provides correlation matrix calculation, filtering algorithms,
and visualization for strategy diversification in portfolio construction.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
import seaborn as sns
import matplotlib.pyplot as plt
from scipy import stats
import argparse

from utils.results_consolidator import RankingResultsConsolidator

logger = logging.getLogger(__name__)


class CorrelationAnalyzer:
    """
    Analyzes correlations between trading strategies and implements diversity selection.

    Provides correlation matrix calculation, filtering algorithms, and visualization
    to ensure portfolio diversification by removing highly correlated strategies.
    """

    def __init__(self, threshold: float = 0.7, method: str = 'pearson',
                 min_periods: int = 30):
        """
        Initialize correlation analyzer.

        Args:
            threshold: Correlation coefficient threshold for filtering (0.7 = 70%)
            method: Correlation method ('pearson', 'spearman', 'kendall')
            min_periods: Minimum overlapping periods required for correlation
        """
        self.threshold = threshold
        self.method = method.lower()
        self.min_periods = min_periods

        if self.method not in ['pearson', 'spearman', 'kendall']:
            raise ValueError(f"Unsupported correlation method: {method}")

        logger.info(f"CorrelationAnalyzer initialized with threshold={threshold}, "
                   f"method={method}, min_periods={min_periods}")

    def calculate_correlation_matrix(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate correlation matrix from returns data.

        Args:
            returns_df: DataFrame with returns series (dates as index, strategies as columns)

        Returns:
            Correlation matrix DataFrame
        """
        if returns_df.empty:
            logger.warning("Empty returns data provided")
            return pd.DataFrame()

        # Ensure we have enough data points
        if len(returns_df) < self.min_periods:
            logger.warning(f"Insufficient data points: {len(returns_df)} < {self.min_periods}")
            return pd.DataFrame()

        # Calculate correlation matrix
        try:
            if self.method == 'pearson':
                corr_matrix = returns_df.corr(method='pearson', min_periods=self.min_periods)
            elif self.method == 'spearman':
                corr_matrix = returns_df.corr(method='spearman', min_periods=self.min_periods)
            elif self.method == 'kendall':
                corr_matrix = returns_df.corr(method='kendall', min_periods=self.min_periods)
            else:
                raise ValueError(f"Unsupported method: {self.method}")

            # Fill NaN values with 0 (no correlation data)
            corr_matrix = corr_matrix.fillna(0)

            logger.info(f"Calculated {self.method} correlation matrix for {len(corr_matrix)} strategies")
            return corr_matrix

        except Exception as e:
            logger.error(f"Error calculating correlation matrix: {e}")
            return pd.DataFrame()

    def filter_correlated_strategies(self, rankings_df: pd.DataFrame,
                                   returns_df: Optional[pd.DataFrame] = None,
                                   use_greedy_selection: bool = True) -> pd.DataFrame:
        """
        Filter out highly correlated strategies from rankings.

        Args:
            rankings_df: Ranked strategies DataFrame
            returns_df: Returns data for correlation calculation (optional)
            use_greedy_selection: Whether to use greedy diversity maximization

        Returns:
            Filtered rankings DataFrame with uncorrelated strategies
        """
        if rankings_df.empty:
            return rankings_df

        if returns_df is None or returns_df.empty:
            logger.warning("No returns data available for correlation analysis")
            # Return top strategies without correlation filtering
            return rankings_df.head(15)

        # Calculate correlation matrix
        corr_matrix = self.calculate_correlation_matrix(returns_df)

        if corr_matrix.empty:
            logger.warning("Could not calculate correlation matrix")
            return rankings_df.head(15)

        # Apply filtering algorithm
        if use_greedy_selection:
            selected_strategies = self._greedy_diversity_selection(
                rankings_df, corr_matrix
            )
        else:
            selected_strategies = self._threshold_based_filtering(
                rankings_df, corr_matrix
            )

        # Filter rankings to selected strategies
        filtered_df = rankings_df[rankings_df['strategy'].isin(selected_strategies)].copy()
        filtered_df = filtered_df.sort_values('composite_score', ascending=False).reset_index(drop=True)

        logger.info(f"Filtered {len(rankings_df)} strategies to {len(filtered_df)} uncorrelated strategies")
        return filtered_df

    def _threshold_based_filtering(self, rankings_df: pd.DataFrame,
                                 corr_matrix: pd.DataFrame) -> List[str]:
        """
        Simple threshold-based filtering: remove strategies correlated above threshold.

        Args:
            rankings_df: Ranked strategies DataFrame
            corr_matrix: Correlation matrix

        Returns:
            List of selected strategy names
        """
        selected = []
        strategy_names = rankings_df['strategy'].tolist()

        for strategy in strategy_names:
            if strategy not in corr_matrix.columns:
                # Strategy not in correlation matrix, include it
                selected.append(strategy)
                continue

            # Check correlation with already selected strategies
            correlations = corr_matrix.loc[strategy, selected] if selected else []

            if not correlations.empty and any(abs(corr) > self.threshold for corr in correlations):
                # Too correlated with existing selection, skip
                continue
            else:
                # Not correlated or below threshold, include
                selected.append(strategy)

        return selected

    def _greedy_diversity_selection(self, rankings_df: pd.DataFrame,
                                  corr_matrix: pd.DataFrame) -> List[str]:
        """
        Greedy algorithm to maximize diversity while maintaining ranking priority.

        Args:
            rankings_df: Ranked strategies DataFrame
            corr_matrix: Correlation matrix

        Returns:
            List of selected strategy names
        """
        selected = []
        remaining = rankings_df['strategy'].tolist()

        while remaining:
            # Select highest ranked remaining strategy
            current_strategy = remaining[0]

            # Check if it correlates too highly with selected strategies
            should_include = True

            if current_strategy in corr_matrix.columns and selected:
                max_corr = max(
                    abs(corr_matrix.loc[current_strategy, selected_strategy])
                    for selected_strategy in selected
                    if selected_strategy in corr_matrix.columns
                )
                if max_corr > self.threshold:
                    should_include = False

            if should_include:
                selected.append(current_strategy)

            # Remove from remaining list
            remaining.remove(current_strategy)

            # Limit to reasonable number (top 15-20)
            if len(selected) >= 20:
                break

        return selected

    def get_correlation_summary(self, corr_matrix: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate summary statistics for correlation matrix.

        Args:
            corr_matrix: Correlation matrix DataFrame

        Returns:
            Dictionary with correlation summary statistics
        """
        if corr_matrix.empty:
            return {}

        # Calculate summary statistics
        summary = {
            'num_strategies': len(corr_matrix),
            'correlation_method': self.method,
            'threshold': self.threshold,
            'avg_correlation': corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].mean(),
            'max_correlation': corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].max(),
            'min_correlation': corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].min(),
            'correlation_std': corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].std(),
        }

        # Count highly correlated pairs
        upper_triangle = corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)]
        highly_correlated = np.sum(np.abs(upper_triangle) > self.threshold)
        total_pairs = len(upper_triangle)

        summary.update({
            'highly_correlated_pairs': highly_correlated,
            'total_pairs': total_pairs,
            'correlation_density': highly_correlated / total_pairs if total_pairs > 0 else 0
        })

        return summary

    def plot_correlation_heatmap(self, corr_matrix: pd.DataFrame,
                               title: str = "Strategy Correlation Matrix",
                               save_path: Optional[str] = None) -> Optional[str]:
        """
        Create and optionally save correlation heatmap visualization.

        Args:
            corr_matrix: Correlation matrix DataFrame
            title: Plot title
            save_path: Path to save plot (optional)

        Returns:
            Path to saved plot if save_path provided, None otherwise
        """
        if corr_matrix.empty:
            logger.warning("Empty correlation matrix, cannot create heatmap")
            return None

        try:
            # Set up the plot
            plt.figure(figsize=(12, 10))

            # Create mask for upper triangle
            mask = np.triu(np.ones_like(corr_matrix, dtype=bool))

            # Create heatmap
            sns.heatmap(
                corr_matrix,
                mask=mask,
                annot=len(corr_matrix) <= 10,  # Only annotate if small matrix
                cmap='coolwarm',
                vmin=-1, vmax=1,
                center=0,
                square=True,
                linewidths=0.5,
                cbar_kws={"shrink": 0.8}
            )

            plt.title(f"{title}\n(Method: {self.method}, Threshold: {self.threshold})")
            plt.xticks(rotation=45, ha='right')
            plt.yticks(rotation=0)
            plt.tight_layout()

            if save_path:
                save_path = Path(save_path)
                save_path.parent.mkdir(parents=True, exist_ok=True)
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"Correlation heatmap saved to {save_path}")
                plt.close()
                return str(save_path)
            else:
                plt.show()
                plt.close()
                return None

        except Exception as e:
            logger.error(f"Error creating correlation heatmap: {e}")
            plt.close()
            return None

    def export_correlation_matrix(self, corr_matrix: pd.DataFrame,
                                output_path: str,
                                format: str = 'csv') -> str:
        """
        Export correlation matrix to file.

        Args:
            corr_matrix: Correlation matrix DataFrame
            output_path: Output file path
            format: Export format ('csv', 'json', 'parquet')

        Returns:
            Path to exported file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format.lower() == 'csv':
            corr_matrix.to_csv(output_path)
        elif format.lower() == 'json':
            corr_matrix.to_json(output_path, orient='split', indent=2)
        elif format.lower() == 'parquet':
            corr_matrix.to_parquet(output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info(f"Correlation matrix exported to {output_path}")
        return str(output_path)

    def find_correlation_clusters(self, corr_matrix: pd.DataFrame,
                                cluster_threshold: float = 0.8) -> List[List[str]]:
        """
        Identify clusters of highly correlated strategies.

        Args:
            corr_matrix: Correlation matrix DataFrame
            cluster_threshold: Threshold for cluster identification

        Returns:
            List of strategy clusters (lists of strategy names)
        """
        if corr_matrix.empty:
            return []

        try:
            # Simple clustering based on correlation threshold
            clusters = []
            processed = set()

            for strategy in corr_matrix.columns:
                if strategy in processed:
                    continue

                # Find strategies highly correlated with this one
                correlated_strategies = []
                for other_strategy in corr_matrix.columns:
                    if (other_strategy != strategy and
                        abs(corr_matrix.loc[strategy, other_strategy]) > cluster_threshold):
                        correlated_strategies.append(other_strategy)

                if correlated_strategies:
                    # Form cluster
                    cluster = [strategy] + correlated_strategies
                    clusters.append(sorted(cluster))

                    # Mark as processed
                    processed.update(cluster)
                else:
                    # Singleton cluster
                    clusters.append([strategy])
                    processed.add(strategy)

            logger.info(f"Identified {len(clusters)} correlation clusters")
            return clusters

        except Exception as e:
            logger.error(f"Error finding correlation clusters: {e}")
            return []

    def get_diversification_score(self, selected_strategies: List[str],
                                corr_matrix: pd.DataFrame) -> float:
        """
        Calculate diversification score for selected strategies.

        Args:
            selected_strategies: List of selected strategy names
            corr_matrix: Correlation matrix DataFrame

        Returns:
            Diversification score (0-1, higher is better diversification)
        """
        if not selected_strategies or len(selected_strategies) < 2:
            return 0.0

        try:
            # Filter correlation matrix to selected strategies
            selected_corr = corr_matrix.loc[selected_strategies, selected_strategies]

            # Calculate average absolute correlation (excluding diagonal)
            upper_triangle = selected_corr.values[np.triu_indices_from(selected_corr.values, k=1)]
            avg_correlation = np.mean(np.abs(upper_triangle))

            # Diversification score = 1 - average correlation
            diversification_score = 1.0 - avg_correlation

            return max(0.0, min(1.0, diversification_score))  # Ensure 0-1 range

        except Exception as e:
            logger.error(f"Error calculating diversification score: {e}")
            return 0.0


def main():
    """Command-line interface for correlation analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze correlations between trading strategies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze correlations from ranked strategies
  python scripts/correlation_analyzer.py --rankings rankings.csv --output correlation_matrix.csv

  # Use custom correlation settings
  python scripts/correlation_analyzer.py --rankings rankings.csv --threshold 0.8 --method spearman

  # Generate heatmap visualization
  python scripts/correlation_analyzer.py --rankings rankings.csv --heatmap correlation_heatmap.png

  # Filter correlated strategies
  python scripts/correlation_analyzer.py --rankings rankings.csv --filter --output filtered_strategies.csv
        """
    )

    parser.add_argument(
        '--rankings',
        type=str,
        required=True,
        help='Path to ranked strategies CSV file'
    )

    parser.add_argument(
        '--threshold',
        type=float,
        default=0.7,
        help='Correlation threshold for filtering (default: 0.7)'
    )

    parser.add_argument(
        '--method',
        type=str,
        choices=['pearson', 'spearman', 'kendall'],
        default='pearson',
        help='Correlation method (default: pearson)'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Output file path for correlation matrix or filtered results'
    )

    parser.add_argument(
        '--format',
        type=str,
        choices=['csv', 'json', 'parquet'],
        default='csv',
        help='Output format (default: csv)'
    )

    parser.add_argument(
        '--heatmap',
        type=str,
        help='Generate and save correlation heatmap to specified path'
    )

    parser.add_argument(
        '--filter',
        action='store_true',
        help='Filter out highly correlated strategies using greedy selection'
    )

    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Only show summary statistics, no detailed output'
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
        # Load ranked strategies
        print(f"Loading ranked strategies from: {args.rankings}")
        rankings_df = pd.read_csv(args.rankings)

        if rankings_df.empty:
            print("No strategies found in rankings file")
            return 1

        # Initialize analyzer
        analyzer = CorrelationAnalyzer(
            threshold=args.threshold,
            method=args.method
        )

        # Calculate correlation matrix
        print(f"Calculating {args.method} correlation matrix...")
        corr_matrix = analyzer.calculate_correlation_matrix(rankings_df)

        if corr_matrix.empty:
            print("Could not calculate correlation matrix")
            return 1

        # Show summary
        summary = analyzer.get_correlation_summary(corr_matrix)
        print(f"\n{'='*60}")
        print("CORRELATION ANALYSIS SUMMARY")
        print(f"{'='*60}")
        print(f"Number of strategies: {summary['num_strategies']}")
        print(f"Correlation method: {summary['correlation_method']}")
        print(f"Threshold: {summary['threshold']}")
        print(".3f")
        print(".3f")
        print(".3f")
        print(".3f")
        print(f"Highly correlated pairs: {summary['highly_correlated_pairs']}/{summary['total_pairs']}")
        print(".1%")

        if not args.summary_only:
            print(f"\n{'='*80}")
            print("CORRELATION MATRIX (first 10x10)")
            print(f"{'='*80}")
            display_matrix = corr_matrix.iloc[:10, :10] if len(corr_matrix) > 10 else corr_matrix
            print(display_matrix.round(3).to_string())

        # Generate heatmap if requested
        if args.heatmap:
            print(f"\nGenerating correlation heatmap...")
            heatmap_path = analyzer.plot_correlation_heatmap(
                corr_matrix,
                save_path=args.heatmap
            )
            if heatmap_path:
                print(f"Heatmap saved to: {heatmap_path}")

        # Filter strategies if requested
        if args.filter:
            print(f"\nFiltering correlated strategies (threshold: {args.threshold})...")
            filtered_df = analyzer.filter_correlated_strategies(rankings_df)

            print(f"Selected {len(filtered_df)} uncorrelated strategies")

            if not args.summary_only:
                print(f"\n{'='*60}")
                print("FILTERED STRATEGIES")
                print(f"{'='*60}")
                print(filtered_df[['rank', 'strategy', 'symbol', 'composite_score']].to_string(index=False))

            # Export filtered results if output specified
            if args.output:
                filtered_df.to_csv(args.output, index=False)
                print(f"Filtered strategies exported to: {args.output}")
        else:
            # Export correlation matrix if output specified and not filtering
            if args.output:
                output_path = analyzer.export_correlation_matrix(corr_matrix, args.output, args.format)
                print(f"Correlation matrix exported to: {output_path}")

        return 0

    except Exception as e:
        logger.error(f"Error during correlation analysis: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())