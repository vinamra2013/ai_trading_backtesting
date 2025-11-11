#!/usr/bin/env python3
"""
Portfolio Optimizer - Epic 21: US-21.3 - Portfolio Allocation Engine
Implements multiple portfolio construction methods with capital and position constraints.

This module provides systematic portfolio allocation using various methodologies:
- Equal weight allocation
- Volatility-adjusted (risk parity) allocation
- Risk parity allocation
- Capital and position limit constraints
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
from abc import ABC, abstractmethod
import yaml
import argparse
import sys

logger = logging.getLogger(__name__)


class PortfolioOptimizer:
    """
    Portfolio construction engine with multiple allocation methodologies.

    Supports various allocation methods with configurable constraints for
    capital limits, position limits, and risk management.
    """

    def __init__(self, capital: float = 1000, max_positions: int = 3,
                 min_allocation: float = 0.1, max_allocation: float = 0.5,
                 config_path: str = 'config/ranking_config.yaml'):
        """
        Initialize portfolio optimizer.

        Args:
            capital: Total portfolio capital
            max_positions: Maximum number of concurrent positions
            min_allocation: Minimum allocation per position (as fraction)
            max_allocation: Maximum allocation per position (as fraction)
            config_path: Path to configuration file
        """
        self.capital = capital
        self.max_positions = max_positions
        self.min_allocation = min_allocation
        self.max_allocation = max_allocation

        # Load configuration
        self.config = self._load_config(config_path)
        self.transaction_costs = self.config.get('portfolio', {}).get('transaction_costs', {})

        logger.info(f"PortfolioOptimizer initialized with ${capital} capital, "
                   f"max {max_positions} positions")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load portfolio configuration."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
            return {}

    def optimize_portfolio(self, strategies_df: pd.DataFrame,
                          method: str = 'equal_weight',
                          returns_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Optimize portfolio allocation using specified method.

        Args:
            strategies_df: DataFrame with ranked strategies
            method: Allocation method ('equal_weight', 'volatility_adjusted', 'risk_parity')
            returns_df: Historical returns data for risk-based methods

        Returns:
            DataFrame with allocation details
        """
        if strategies_df.empty:
            logger.warning("No strategies provided for optimization")
            return pd.DataFrame()

        # Limit to maximum positions
        selected_strategies = strategies_df.head(self.max_positions).copy()

        logger.info(f"Optimizing portfolio with {len(selected_strategies)} strategies using {method}")

        # Apply allocation method
        if method == 'equal_weight':
            allocations = self._equal_weight_allocation(selected_strategies)
        elif method == 'volatility_adjusted':
            allocations = self._volatility_adjusted_allocation(selected_strategies, returns_df)
        elif method == 'risk_parity':
            allocations = self._risk_parity_allocation(selected_strategies, returns_df)
        else:
            raise ValueError(f"Unknown allocation method: {method}")

        # Apply constraints and validate
        allocations = self._apply_constraints(allocations)

        # Calculate portfolio metrics
        portfolio_metrics = self._calculate_portfolio_metrics(allocations, returns_df)

        # Create result DataFrame
        result_df = self._create_allocation_dataframe(allocations, portfolio_metrics, method)

        logger.info(f"Portfolio optimization complete. Total allocation: ${result_df['capital_allocated'].sum():.2f}")
        return result_df

    def _equal_weight_allocation(self, strategies_df: pd.DataFrame) -> Dict[str, float]:
        """
        Equal weight allocation across all strategies.

        Args:
            strategies_df: Selected strategies DataFrame

        Returns:
            Dictionary mapping strategy names to allocation weights
        """
        n_strategies = len(strategies_df)
        if n_strategies == 0:
            return {}

        equal_weight = 1.0 / n_strategies
        allocations = {}

        for _, strategy in strategies_df.iterrows():
            strategy_name = strategy['strategy']
            allocations[strategy_name] = equal_weight

        logger.info(f"Applied equal weight allocation: {equal_weight:.3f} per strategy")
        return allocations

    def _volatility_adjusted_allocation(self, strategies_df: pd.DataFrame,
                                      returns_df: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        """
        Volatility-adjusted allocation (inverse volatility weighting).

        Args:
            strategies_df: Selected strategies DataFrame
            returns_df: Historical returns data

        Returns:
            Dictionary mapping strategy names to allocation weights
        """
        if returns_df is None or returns_df.empty:
            logger.warning("No returns data available, falling back to equal weight")
            return self._equal_weight_allocation(strategies_df)

        allocations = {}

        for _, strategy in strategies_df.iterrows():
            strategy_name = strategy['strategy']
            symbol = strategy['symbol']
            strategy_key = f"{strategy_name}_{symbol}"

            if strategy_key in returns_df.columns:
                # Calculate annualized volatility
                returns = returns_df[strategy_key].dropna()
                if len(returns) > 30:  # Need sufficient data
                    volatility = returns.std() * np.sqrt(252)  # Annualized
                    if volatility > 0:
                        # Inverse volatility weight
                        allocations[strategy_name] = 1.0 / volatility
                    else:
                        allocations[strategy_name] = 1.0
                else:
                    allocations[strategy_name] = 1.0
            else:
                logger.warning(f"No returns data for {strategy_key}, using equal weight")
                allocations[strategy_name] = 1.0

        # Normalize to sum to 1
        total_weight = sum(allocations.values())
        if total_weight > 0:
            allocations = {k: v / total_weight for k, v in allocations.items()}

        logger.info(f"Applied volatility-adjusted allocation")
        return allocations

    def _risk_parity_allocation(self, strategies_df: pd.DataFrame,
                              returns_df: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        """
        Risk parity allocation (equal risk contribution).

        Args:
            strategies_df: Selected strategies DataFrame
            returns_df: Historical returns data

        Returns:
            Dictionary mapping strategy names to allocation weights
        """
        if returns_df is None or returns_df.empty:
            logger.warning("No returns data available, falling back to equal weight")
            return self._equal_weight_allocation(strategies_df)

        try:
            # Extract returns for selected strategies
            strategy_returns = []
            strategy_names = []

            for _, strategy in strategies_df.iterrows():
                strategy_name = strategy['strategy']
                symbol = strategy['symbol']
                strategy_key = f"{strategy_name}_{symbol}"

                if strategy_key in returns_df.columns:
                    returns = returns_df[strategy_key].dropna()
                    if len(returns) > 30:
                        strategy_returns.append(returns)
                        strategy_names.append(strategy_name)

            if len(strategy_returns) < 2:
                logger.warning("Insufficient data for risk parity, using equal weight")
                return self._equal_weight_allocation(strategies_df)

            # Calculate covariance matrix
            returns_matrix = pd.concat(strategy_returns, axis=1, keys=strategy_names)
            returns_matrix = returns_matrix.dropna()
            cov_matrix = returns_matrix.cov() * 252  # Annualized

            # Risk parity optimization (simplified)
            # Target equal risk contribution
            n_assets = len(strategy_names)
            target_risk = 1.0 / n_assets

            # Initial equal weights
            weights = np.array([1.0 / n_assets] * n_assets)

            # Simple iterative optimization (can be improved with scipy.optimize)
            for _ in range(10):  # Limited iterations for simplicity
                # Calculate portfolio risk contribution
                portfolio_vol = np.sqrt(weights @ cov_matrix.values @ weights)
                marginal_risk = cov_matrix.values @ weights / portfolio_vol
                risk_contribution = weights * marginal_risk

                # Adjust weights to target equal risk contribution
                target_contribution = target_risk * portfolio_vol
                weights = weights * (target_contribution / risk_contribution)
                weights = weights / weights.sum()  # Normalize

            # Convert to dictionary
            allocations = dict(zip(strategy_names, weights))

            logger.info(f"Applied risk parity allocation")
            return allocations

        except Exception as e:
            logger.error(f"Error in risk parity optimization: {e}")
            logger.warning("Falling back to equal weight allocation")
            return self._equal_weight_allocation(strategies_df)

    def _apply_constraints(self, allocations: Dict[str, float]) -> Dict[str, float]:
        """
        Apply capital and position constraints to allocations.

        Args:
            allocations: Raw allocation weights

        Returns:
            Constrained allocation weights
        """
        if not allocations:
            return {}

        # Apply minimum and maximum allocation constraints
        constrained = {}
        for strategy, weight in allocations.items():
            constrained_weight = np.clip(weight, self.min_allocation, self.max_allocation)
            constrained[strategy] = constrained_weight

        # Re-normalize after constraints
        total_weight = sum(constrained.values())
        if total_weight > 0:
            constrained = {k: v / total_weight for k, v in constrained.items()}

        # Apply position limit (already handled by selection, but double-check)
        if len(constrained) > self.max_positions:
            # Sort by weight and keep top N
            sorted_items = sorted(constrained.items(), key=lambda x: x[1], reverse=True)
            constrained = dict(sorted_items[:self.max_positions])

            # Re-normalize
            total_weight = sum(constrained.values())
            constrained = {k: v / total_weight for k, v in constrained.items()}

        logger.info(f"Applied constraints: {len(constrained)} positions, "
                   f"weights range [{min(constrained.values()):.3f}, {max(constrained.values()):.3f}]")
        return constrained

    def _calculate_portfolio_metrics(self, allocations: Dict[str, float],
                                   returns_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Calculate expected portfolio performance metrics.

        Args:
            allocations: Allocation weights
            returns_df: Historical returns data

        Returns:
            Dictionary with portfolio metrics
        """
        metrics = {
            'expected_sharpe': 0.0,
            'expected_volatility': 0.0,
            'expected_return': 0.0,
            'diversification_ratio': 0.0,
            'transaction_costs': 0.0
        }

        if not allocations or returns_df is None or returns_df.empty:
            return metrics

        try:
            # Extract returns for allocated strategies
            portfolio_returns = []
            weights = []

            for strategy_name, weight in allocations.items():
                # Find matching strategy in returns data
                matching_columns = [col for col in returns_df.columns if col.startswith(f"{strategy_name}_")]
                if matching_columns:
                    returns = returns_df[matching_columns[0]].dropna()
                    if len(returns) > 30:
                        portfolio_returns.append(returns)
                        weights.append(weight)

            if not portfolio_returns:
                return metrics

            # Calculate portfolio metrics
            returns_matrix = pd.concat(portfolio_returns, axis=1).dropna()
            weights_array = np.array(weights)

            if len(returns_matrix) > 30 and len(weights_array) > 0:
                # Portfolio returns
                portfolio_returns = returns_matrix @ weights_array

                # Expected metrics
                expected_return = portfolio_returns.mean() * 252  # Annualized
                expected_vol = portfolio_returns.std() * np.sqrt(252)  # Annualized
                expected_sharpe = expected_return / expected_vol if expected_vol > 0 else 0

                # Diversification ratio (1 / concentration)
                herfindahl_index = sum(w**2 for w in weights_array)
                diversification_ratio = 1.0 / herfindahl_index if herfindahl_index > 0 else 0

                metrics.update({
                    'expected_sharpe': expected_sharpe,
                    'expected_volatility': expected_vol,
                    'expected_return': expected_return,
                    'diversification_ratio': diversification_ratio
                })

            # Estimate transaction costs
            metrics['transaction_costs'] = self._estimate_transaction_costs(allocations)

        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")

        return metrics

    def _estimate_transaction_costs(self, allocations: Dict[str, float]) -> float:
        """
        Estimate transaction costs for the portfolio.

        Args:
            allocations: Allocation weights

        Returns:
            Estimated transaction costs as fraction of portfolio
        """
        try:
            commission_bps = self.transaction_costs.get('commission_bps', 5)
            spread_bps = self.transaction_costs.get('spread_bps', 2)
            impact_bps = self.transaction_costs.get('impact_bps', 1)

            total_bps = commission_bps + spread_bps + impact_bps
            total_cost_fraction = total_bps / 10000  # Convert bps to fraction

            # Assume one round trip per year per position
            n_positions = len(allocations)
            annual_cost_fraction = total_cost_fraction * 2 * n_positions  # Round trip

            return annual_cost_fraction

        except Exception as e:
            logger.error(f"Error estimating transaction costs: {e}")
            return 0.01  # Default 1%

    def _create_allocation_dataframe(self, allocations: Dict[str, float],
                                   metrics: Dict[str, Any],
                                   method: str) -> pd.DataFrame:
        """
        Create allocation results DataFrame.

        Args:
            allocations: Allocation weights
            metrics: Portfolio metrics
            method: Allocation method used

        Returns:
            DataFrame with allocation details
        """
        allocation_data = []

        for strategy_name, weight in allocations.items():
            capital_allocated = weight * self.capital

            allocation_data.append({
                'strategy': strategy_name,
                'allocation_weight': weight,
                'capital_allocated': capital_allocated,
                'allocation_method': method,
                'expected_sharpe': metrics.get('expected_sharpe', 0),
                'expected_volatility': metrics.get('expected_volatility', 0),
                'expected_return': metrics.get('expected_return', 0),
                'diversification_ratio': metrics.get('diversification_ratio', 0),
                'estimated_transaction_costs_pct': metrics.get('transaction_costs', 0) * 100
            })

        df = pd.DataFrame(allocation_data)
        df = df.sort_values('capital_allocated', ascending=False).reset_index(drop=True)

        return df

    def compare_allocation_methods(self, strategies_df: pd.DataFrame,
                                 returns_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Compare different allocation methods for the same strategy set.

        Args:
            strategies_df: Selected strategies DataFrame
            returns_df: Historical returns data

        Returns:
            DataFrame comparing allocation methods
        """
        methods = ['equal_weight', 'volatility_adjusted', 'risk_parity']
        comparisons = []

        for method in methods:
            try:
                allocation_df = self.optimize_portfolio(strategies_df, method, returns_df)

                if not allocation_df.empty:
                    # Summary for this method
                    summary = {
                        'method': method,
                        'n_strategies': len(allocation_df),
                        'total_capital': allocation_df['capital_allocated'].sum(),
                        'avg_weight': allocation_df['allocation_weight'].mean(),
                        'weight_std': allocation_df['allocation_weight'].std(),
                        'expected_sharpe': allocation_df['expected_sharpe'].iloc[0],
                        'expected_volatility': allocation_df['expected_volatility'].iloc[0],
                        'expected_return': allocation_df['expected_return'].iloc[0],
                        'diversification_ratio': allocation_df['diversification_ratio'].iloc[0],
                        'transaction_costs_pct': allocation_df['estimated_transaction_costs_pct'].iloc[0]
                    }
                    comparisons.append(summary)

            except Exception as e:
                logger.error(f"Error comparing {method}: {e}")

        return pd.DataFrame(comparisons)

    def export_allocations(self, allocation_df: pd.DataFrame,
                          output_path: str,
                          format: str = 'csv') -> str:
        """
        Export allocation results to file.

        Args:
            allocation_df: Allocation DataFrame
            output_path: Output file path
            format: Export format ('csv', 'json', 'parquet')

        Returns:
            Path to exported file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format.lower() == 'csv':
            allocation_df.to_csv(output_path, index=False)
        elif format.lower() == 'json':
            allocation_df.to_json(output_path, orient='records', indent=2)
        elif format.lower() == 'parquet':
            allocation_df.to_parquet(output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info(f"Exported allocations to {output_path}")
        return str(output_path)


def main():
    """Command-line interface for portfolio optimization."""
    parser = argparse.ArgumentParser(
        description="Optimize portfolio allocations using various methods",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Equal weight allocation
  python scripts/portfolio_optimizer.py --strategies filtered_strategies.csv --method equal_weight --output allocations.csv

  # Risk parity with custom capital
  python scripts/portfolio_optimizer.py --strategies filtered_strategies.csv --method risk_parity --capital 5000

  # Compare all allocation methods
  python scripts/portfolio_optimizer.py --strategies filtered_strategies.csv --compare --output comparison.csv

  # Volatility-adjusted allocation
  python scripts/portfolio_optimizer.py --strategies filtered_strategies.csv --method volatility_adjusted --max-positions 5
        """
    )

    parser.add_argument(
        '--strategies',
        type=str,
        required=True,
        help='Path to selected strategies CSV file'
    )

    parser.add_argument(
        '--method',
        type=str,
        choices=['equal_weight', 'volatility_adjusted', 'risk_parity'],
        default='equal_weight',
        help='Allocation method (default: equal_weight)'
    )

    parser.add_argument(
        '--capital',
        type=float,
        default=1000,
        help='Total portfolio capital (default: 1000)'
    )

    parser.add_argument(
        '--max-positions',
        type=int,
        default=3,
        help='Maximum number of concurrent positions (default: 3)'
    )

    parser.add_argument(
        '--min-allocation',
        type=float,
        default=0.1,
        help='Minimum allocation per position (default: 0.1)'
    )

    parser.add_argument(
        '--max-allocation',
        type=float,
        default=0.5,
        help='Maximum allocation per position (default: 0.5)'
    )

    parser.add_argument(
        '--returns-data',
        type=str,
        help='Path to historical returns data CSV (optional, for metrics calculation)'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Output file path for allocations'
    )

    parser.add_argument(
        '--format',
        type=str,
        choices=['csv', 'json', 'parquet'],
        default='csv',
        help='Output format (default: csv)'
    )

    parser.add_argument(
        '--compare',
        action='store_true',
        help='Compare all allocation methods instead of using single method'
    )

    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Only show summary statistics, no detailed allocations'
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
        # Load strategies
        print(f"Loading strategies from: {args.strategies}")
        strategies_df = pd.read_csv(args.strategies)

        if strategies_df.empty:
            print("No strategies found in input file")
            return 1

        # Load returns data if provided
        returns_df = None
        if args.returns_data:
            print(f"Loading returns data from: {args.returns_data}")
            returns_df = pd.read_csv(args.returns_data)
            if returns_df.empty:
                print("Warning: Returns data file is empty")
                returns_df = None

        # Initialize optimizer
        optimizer = PortfolioOptimizer(
            capital=args.capital,
            max_positions=args.max_positions,
            min_allocation=args.min_allocation,
            max_allocation=args.max_allocation
        )

        if args.compare:
            # Compare all methods
            print(f"\nComparing allocation methods for {len(strategies_df)} strategies...")
            comparison_df = optimizer.compare_allocation_methods(strategies_df, returns_df)

            if comparison_df.empty:
                print("Could not generate comparison")
                return 1

            print(f"\n{'='*80}")
            print("ALLOCATION METHOD COMPARISON")
            print(f"{'='*80}")
            print(comparison_df.round(4).to_string(index=False))

            # Export comparison if requested
            if args.output:
                comparison_df.to_csv(args.output, index=False)
                print(f"\nComparison exported to: {args.output}")

        else:
            # Single method optimization
            print(f"\nOptimizing portfolio using {args.method} method...")
            allocation_df = optimizer.optimize_portfolio(strategies_df, args.method, returns_df)

            if allocation_df.empty:
                print("Could not generate portfolio allocation")
                return 1

            # Show summary
            total_capital = allocation_df['capital_allocated'].sum()
            n_strategies = len(allocation_df)
            expected_sharpe = allocation_df['expected_sharpe'].iloc[0] if 'expected_sharpe' in allocation_df.columns else 0

            print(f"\n{'='*60}")
            print("PORTFOLIO ALLOCATION SUMMARY")
            print(f"{'='*60}")
            print(f"Method: {args.method}")
            print(f"Strategies: {n_strategies}")
            print(f"Total capital: ${total_capital:,.2f}")
            print(".3f")
            print(".3f")
            print(".3f")
            print(".1f")

            if not args.summary_only:
                print(f"\n{'='*80}")
                print("STRATEGY ALLOCATIONS")
                print(f"{'='*80}")
                display_cols = ['strategy', 'allocation_weight', 'capital_allocated']
                print(allocation_df[display_cols].to_string(index=False, float_format='%.4f'))

            # Export allocations if requested
            if args.output:
                output_path = optimizer.export_allocations(allocation_df, args.output, args.format)
                print(f"\nAllocations exported to: {output_path}")

        return 0

    except Exception as e:
        logger.error(f"Error during portfolio optimization: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())