#!/usr/bin/env python3
"""
Portfolio Analytics - Epic 21: US-21.5 - Portfolio Analytics & Reporting
Performance metrics and reporting for optimized portfolios.

This module provides comprehensive analytics for portfolio performance,
risk decomposition, and visualization of allocation results.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import sys

logger = logging.getLogger(__name__)


class PortfolioAnalytics:
    """
    Comprehensive portfolio performance analytics and reporting.

    Provides detailed performance metrics, risk decomposition, attribution analysis,
    and visualization for optimized portfolios.
    """

    def __init__(self):
        """Initialize portfolio analytics."""
        logger.info("PortfolioAnalytics initialized")

    def calculate_portfolio_metrics(self, allocation_df: pd.DataFrame,
                                  returns_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Calculate comprehensive portfolio performance metrics.

        Args:
            allocation_df: Portfolio allocation DataFrame
            returns_df: Historical returns data for strategies

        Returns:
            Dictionary with portfolio metrics
        """
        if allocation_df.empty:
            return {}

        metrics = {}

        try:
            # Basic portfolio statistics
            metrics.update(self._calculate_basic_stats(allocation_df))

            # Risk metrics
            if returns_df is not None and not returns_df.empty:
                metrics.update(self._calculate_risk_metrics(allocation_df, returns_df))

            # Performance attribution
            metrics.update(self._calculate_attribution(allocation_df))

            # Diversification metrics
            metrics.update(self._calculate_diversification_metrics(allocation_df))

        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")

        return metrics

    def _calculate_basic_stats(self, allocation_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate basic portfolio statistics."""
        stats = {
            'total_strategies': len(allocation_df),
            'total_capital': allocation_df['capital_allocated'].sum(),
            'avg_allocation': allocation_df['allocation_weight'].mean(),
            'allocation_std': allocation_df['allocation_weight'].std(),
            'max_allocation': allocation_df['allocation_weight'].max(),
            'min_allocation': allocation_df['allocation_weight'].min(),
            'allocation_method': allocation_df['allocation_method'].iloc[0] if len(allocation_df) > 0 else 'unknown'
        }

        return stats

    def _calculate_risk_metrics(self, allocation_df: pd.DataFrame,
                              returns_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate portfolio risk metrics."""
        risk_metrics = {}

        try:
            # Extract returns for allocated strategies
            portfolio_returns = []
            weights = []

            for _, strategy in allocation_df.iterrows():
                strategy_name = strategy['strategy']
                # Find matching returns column
                matching_cols = [col for col in returns_df.columns if col.startswith(f"{strategy_name}_")]
                if matching_cols:
                    returns = returns_df[matching_cols[0]].dropna()
                    if len(returns) > 30:  # Sufficient data
                        portfolio_returns.append(returns)
                        weights.append(strategy['allocation_weight'])

            if portfolio_returns:
                # Create portfolio returns
                returns_matrix = pd.concat(portfolio_returns, axis=1).dropna()
                weights_array = np.array(weights)

                if len(returns_matrix) > 0 and len(weights_array) > 0:
                    portfolio_returns = returns_matrix @ weights_array

                    # Calculate risk metrics
                    risk_metrics.update({
                        'portfolio_volatility': portfolio_returns.std() * np.sqrt(252),  # Annualized
                        'portfolio_sharpe': (portfolio_returns.mean() * 252) / (portfolio_returns.std() * np.sqrt(252)) if portfolio_returns.std() > 0 else 0,
                        'portfolio_sortino': self._calculate_sortino_ratio(portfolio_returns),
                        'max_drawdown': self._calculate_max_drawdown(portfolio_returns),
                        'var_95': np.percentile(portfolio_returns, 5),  # 95% VaR
                        'cvar_95': portfolio_returns[portfolio_returns <= np.percentile(portfolio_returns, 5)].mean(),
                        'win_rate': (portfolio_returns > 0).mean(),
                        'profit_factor': abs(portfolio_returns[portfolio_returns > 0].sum() / portfolio_returns[portfolio_returns < 0].sum()) if portfolio_returns[portfolio_returns < 0].sum() != 0 else float('inf')
                    })

        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")

        return risk_metrics

    def _calculate_sortino_ratio(self, returns: pd.Series, target_return: float = 0.0) -> float:
        """Calculate Sortino ratio."""
        try:
            excess_returns = returns - target_return
            downside_returns = excess_returns[excess_returns < 0]

            if len(downside_returns) == 0:
                return float('inf') if excess_returns.mean() > 0 else 0.0

            downside_std = downside_returns.std()
            if downside_std == 0:
                return float('inf') if excess_returns.mean() > 0 else 0.0

            return excess_returns.mean() / downside_std * np.sqrt(252)  # Annualized

        except Exception:
            return 0.0

    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown from returns."""
        try:
            # Convert to cumulative returns
            cumulative = (1 + returns).cumprod()
            peak = cumulative.expanding().max()
            drawdown = (cumulative - peak) / peak
            return abs(drawdown.min())
        except Exception:
            return 0.0

    def _calculate_attribution(self, allocation_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate performance attribution by strategy."""
        attribution = {}

        try:
            # Strategy contribution to portfolio
            total_capital = allocation_df['capital_allocated'].sum()

            attribution['strategy_contributions'] = []
            for _, strategy in allocation_df.iterrows():
                contribution = {
                    'strategy': strategy['strategy'],
                    'weight': strategy['allocation_weight'],
                    'capital': strategy['capital_allocated'],
                    'capital_pct': strategy['capital_allocated'] / total_capital * 100
                }
                attribution['strategy_contributions'].append(contribution)

            # Sort by contribution
            attribution['strategy_contributions'].sort(key=lambda x: x['capital'], reverse=True)

        except Exception as e:
            logger.error(f"Error calculating attribution: {e}")

        return attribution

    def _calculate_diversification_metrics(self, allocation_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate portfolio diversification metrics."""
        diversification = {}

        try:
            weights = allocation_df['allocation_weight'].values

            # Herfindahl-Hirschman Index (concentration measure)
            hhi = np.sum(weights ** 2)

            # Effective number of strategies (inverse of HHI)
            effective_strategies = 1.0 / hhi if hhi > 0 else len(weights)

            # Gini coefficient (inequality measure)
            gini = self._calculate_gini_coefficient(weights)

            diversification.update({
                'herfindahl_index': hhi,
                'effective_strategies': effective_strategies,
                'gini_coefficient': gini,
                'diversification_ratio': effective_strategies / len(weights) if len(weights) > 0 else 0
            })

        except Exception as e:
            logger.error(f"Error calculating diversification metrics: {e}")

        return diversification

    def _calculate_gini_coefficient(self, values: np.ndarray) -> float:
        """Calculate Gini coefficient for inequality measurement."""
        try:
            values = np.abs(values)  # Ensure positive
            values = np.sort(values)

            n = len(values)
            if n == 0 or np.sum(values) == 0:
                return 0.0

            cumsum = np.cumsum(values)
            return (n + 1 - 2 * np.sum(cumsum) / cumsum[-1]) / n

        except Exception:
            return 0.0

    def generate_portfolio_report(self, allocation_df: pd.DataFrame,
                                metrics: Dict[str, Any],
                                output_path: str) -> str:
        """
        Generate comprehensive portfolio report.

        Args:
            allocation_df: Portfolio allocation DataFrame
            metrics: Portfolio metrics dictionary
            output_path: Output file path

        Returns:
            Path to generated report
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(output_path, 'w') as f:
                f.write("# Portfolio Analysis Report\n\n")
                f.write(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                # Portfolio Overview
                f.write("## Portfolio Overview\n\n")
                f.write(f"- **Total Strategies:** {metrics.get('total_strategies', 0)}\n")
                f.write(f"- **Total Capital:** ${metrics.get('total_capital', 0):,.2f}\n")
                f.write(f"- **Allocation Method:** {metrics.get('allocation_method', 'unknown')}\n")
                f.write(f"- **Average Allocation:** {metrics.get('avg_allocation', 0):.3f}\n\n")

                # Performance Metrics
                f.write("## Performance Metrics\n\n")
                perf_metrics = ['portfolio_sharpe', 'portfolio_volatility', 'portfolio_sortino',
                              'max_drawdown', 'win_rate', 'profit_factor']
                for metric in perf_metrics:
                    value = metrics.get(metric)
                    if value is not None:
                        if metric in ['portfolio_volatility', 'max_drawdown']:
                            f.write(f"- **{metric.replace('_', ' ').title()}:** {value:.4f}\n")
                        elif metric == 'profit_factor' and value == float('inf'):
                            f.write(f"- **{metric.replace('_', ' ').title()}:** ∞\n")
                        else:
                            f.write(f"- **{metric.replace('_', ' ').title()}:** {value:.4f}\n")
                f.write("\n")

                # Risk Metrics
                f.write("## Risk Metrics\n\n")
                risk_metrics = ['var_95', 'cvar_95']
                for metric in risk_metrics:
                    value = metrics.get(metric)
                    if value is not None:
                        f.write(f"- **{metric.replace('_', ' ').upper()}:** {value:.4f}\n")
                f.write("\n")

                # Diversification
                f.write("## Diversification Analysis\n\n")
                div_metrics = ['herfindahl_index', 'effective_strategies', 'gini_coefficient', 'diversification_ratio']
                for metric in div_metrics:
                    value = metrics.get(metric)
                    if value is not None:
                        f.write(f"- **{metric.replace('_', ' ').title()}:** {value:.4f}\n")
                f.write("\n")

                # Strategy Allocation
                f.write("## Strategy Allocation\n\n")
                f.write("| Strategy | Weight | Capital | Sharpe |\n")
                f.write("|----------|--------|---------|--------|\n")

                for _, strategy in allocation_df.iterrows():
                    f.write(f"| {strategy['strategy']} | {strategy['allocation_weight']:.3f} | "
                           f"${strategy['capital_allocated']:,.0f} | {strategy.get('expected_sharpe', 0):.2f} |\n")

                f.write("\n")

                # Strategy Contributions
                if 'strategy_contributions' in metrics:
                    f.write("## Strategy Contributions\n\n")
                    for contrib in metrics['strategy_contributions'][:10]:  # Top 10
                        f.write(f"- **{contrib['strategy']}:** {contrib['capital_pct']:.1f}% "
                               f"(${contrib['capital']:,.0f})\n")
                    f.write("\n")

            logger.info(f"Portfolio report generated: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Error generating portfolio report: {e}")
            return ""

    def create_allocation_visualization(self, allocation_df: pd.DataFrame,
                                      output_path: str) -> Optional[str]:
        """
        Create portfolio allocation visualization.

        Args:
            allocation_df: Portfolio allocation DataFrame
            output_path: Output file path for chart

        Returns:
            Path to saved visualization or None if failed
        """
        if allocation_df.empty:
            return None

        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Set up the plot style
            plt.style.use('default')
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 8))

            # Pie chart of allocations
            wedges, texts, autotexts = ax1.pie(
                allocation_df['allocation_weight'],
                labels=allocation_df['strategy'],
                autopct='%1.1f%%',
                startangle=90
            )
            ax1.set_title('Portfolio Allocation by Strategy', fontsize=14, pad=20)
            ax1.axis('equal')

            # Bar chart of capital allocation
            bars = ax2.bar(
                range(len(allocation_df)),
                allocation_df['capital_allocated'],
                color='skyblue',
                edgecolor='navy',
                alpha=0.7
            )
            ax2.set_title('Capital Allocation by Strategy', fontsize=14, pad=20)
            ax2.set_xlabel('Strategy')
            ax2.set_ylabel('Capital Allocated ($)')
            ax2.set_xticks(range(len(allocation_df)))
            ax2.set_xticklabels(allocation_df['strategy'], rotation=45, ha='right')

            # Add value labels on bars
            for bar, value in zip(bars, allocation_df['capital_allocated']):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + max(allocation_df['capital_allocated']) * 0.01,
                        f'${value:,.0f}', ha='center', va='bottom', fontsize=10)

            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()

            logger.info(f"Portfolio visualization saved: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Error creating portfolio visualization: {e}")
            plt.close()
            return None

    def compare_portfolios(self, portfolio_dfs: List[Tuple[str, pd.DataFrame]],
                         metrics_list: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Compare multiple portfolio allocations.

        Args:
            portfolio_dfs: List of (name, allocation_df) tuples
            metrics_list: List of metrics dictionaries

        Returns:
            Comparison DataFrame
        """
        comparisons = []

        for (name, df), metrics in zip(portfolio_dfs, metrics_list):
            comparison = {
                'portfolio': name,
                'n_strategies': len(df),
                'total_capital': df['capital_allocated'].sum(),
                'sharpe_ratio': metrics.get('portfolio_sharpe', 0),
                'volatility': metrics.get('portfolio_volatility', 0),
                'max_drawdown': metrics.get('max_drawdown', 0),
                'win_rate': metrics.get('win_rate', 0),
                'diversification_ratio': metrics.get('diversification_ratio', 0),
                'allocation_std': df['allocation_weight'].std()
            }
            comparisons.append(comparison)

        return pd.DataFrame(comparisons)

    def export_analytics(self, allocation_df: pd.DataFrame,
                        metrics: Dict[str, Any],
                        output_path: str,
                        format: str = 'json') -> str:
        """
        Export complete analytics results.

        Args:
            allocation_df: Portfolio allocation DataFrame
            metrics: Portfolio metrics dictionary
            output_path: Output file path
            format: Export format ('json', 'csv')

        Returns:
            Path to exported file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            export_data = {
                'allocation': allocation_df.to_dict('records'),
                'metrics': metrics,
                'metadata': {
                    'generated_at': pd.Timestamp.now().isoformat(),
                    'total_strategies': len(allocation_df),
                    'total_capital': allocation_df['capital_allocated'].sum()
                }
            }

            if format.lower() == 'json':
                import json
                with open(output_path, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
            elif format.lower() == 'csv':
                # Export allocation data
                allocation_df.to_csv(output_path, index=False)
            else:
                raise ValueError(f"Unsupported format: {format}")

            logger.info(f"Analytics exported to {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Error exporting analytics: {e}")
            return ""


def main():
    """Command-line interface for portfolio analytics."""
    parser = argparse.ArgumentParser(
        description="Analyze portfolio performance and generate reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate portfolio report
  python scripts/portfolio_analytics.py --allocations allocations.csv --output portfolio_report.md

  # Create portfolio visualization
  python scripts/portfolio_analytics.py --allocations allocations.csv --chart portfolio_chart.png

  # Export analytics to JSON
  python scripts/portfolio_analytics.py --allocations allocations.csv --export analytics.json

  # Full analysis with all outputs
  python scripts/portfolio_analytics.py --allocations allocations.csv --output report.md --chart chart.png --export data.json
        """
    )

    parser.add_argument(
        '--allocations',
        type=str,
        required=True,
        help='Path to portfolio allocations CSV file'
    )

    parser.add_argument(
        '--returns-data',
        type=str,
        help='Path to historical returns data CSV (optional, for enhanced metrics)'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Output file path for portfolio report (Markdown format)'
    )

    parser.add_argument(
        '--chart',
        type=str,
        help='Output file path for portfolio visualization chart'
    )

    parser.add_argument(
        '--export',
        type=str,
        help='Output file path for analytics data export (JSON/CSV)'
    )

    parser.add_argument(
        '--export-format',
        type=str,
        choices=['json', 'csv'],
        default='json',
        help='Export format (default: json)'
    )

    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Only show summary statistics, no detailed analysis'
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
        # Load allocations
        print(f"Loading portfolio allocations from: {args.allocations}")
        allocation_df = pd.read_csv(args.allocations)

        if allocation_df.empty:
            print("No allocations found in input file")
            return 1

        # Load returns data if provided
        returns_df = None
        if args.returns_data:
            print(f"Loading returns data from: {args.returns_data}")
            returns_df = pd.read_csv(args.returns_data)
            if returns_df.empty:
                print("Warning: Returns data file is empty")
                returns_df = None

        # Initialize analytics
        analytics = PortfolioAnalytics()

        # Calculate portfolio metrics
        print(f"\nCalculating portfolio metrics for {len(allocation_df)} strategies...")
        metrics = analytics.calculate_portfolio_metrics(allocation_df, returns_df)

        if not metrics:
            print("Could not calculate portfolio metrics")
            return 1

        # Show summary
        print(f"\n{'='*60}")
        print("PORTFOLIO ANALYTICS SUMMARY")
        print(f"{'='*60}")
        print(f"Total strategies: {metrics.get('total_strategies', 0)}")
        print(f"Total capital: ${metrics.get('total_capital', 0):,.2f}")
        print(".3f")
        print(".3f")
        print(".3f")
        print(".3f")
        print(".3f")
        print(".3f")
        print(".3f")
        print(".3f")
        print(".3f")

        if not args.summary_only:
            print(f"\n{'='*80}")
            print("STRATEGY BREAKDOWN")
            print(f"{'='*80}")
            display_cols = ['strategy', 'allocation_weight', 'capital_allocated']
            if 'expected_sharpe' in allocation_df.columns:
                display_cols.append('expected_sharpe')
            print(allocation_df[display_cols].to_string(index=False, float_format='%.4f'))

        # Generate report if requested
        if args.output:
            print(f"\nGenerating portfolio report...")
            report_path = analytics.generate_portfolio_report(allocation_df, metrics, args.output)
            if report_path:
                print(f"Report generated: {report_path}")

        # Create visualization if requested
        if args.chart:
            print(f"\nCreating portfolio visualization...")
            chart_path = analytics.create_allocation_visualization(allocation_df, args.chart)
            if chart_path:
                print(f"Chart saved: {chart_path}")

        # Export analytics if requested
        if args.export:
            print(f"\nExporting analytics data...")
            export_path = analytics.export_analytics(allocation_df, metrics, args.export, args.export_format)
            if export_path:
                print(f"Analytics exported: {export_path}")

        return 0

    except Exception as e:
        logger.error(f"Error during portfolio analytics: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())