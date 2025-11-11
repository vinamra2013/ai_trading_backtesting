#!/usr/bin/env python3
"""
Strategy Optimization CLI (US-17.11)
Epic 17: AI-Native Research Lab

Command-line interface for Bayesian optimization of trading strategies using Optuna.
Supports parameter space JSON files, distributed execution, and MLflow integration.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.optuna_optimizer import OptunaOptimizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_param_space(param_space_file: str) -> Dict[str, Any]:
    """
    Load parameter space definition from JSON file.

    Args:
        param_space_file: Path to JSON file containing parameter space

    Returns:
        Parameter space dictionary

    Raises:
        FileNotFoundError: If parameter space file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    if not os.path.exists(param_space_file):
        raise FileNotFoundError(f"Parameter space file not found: {param_space_file}")

    with open(param_space_file, 'r') as f:
        param_space = json.load(f)

    logger.info("Loaded parameter space from %s with %d parameters", param_space_file, len(param_space))
    return param_space


def validate_param_space(param_space: Dict[str, Any]) -> None:
    """
    Validate parameter space definition.

    Args:
        param_space: Parameter space dictionary

    Raises:
        ValueError: If parameter space is invalid
    """
    if not param_space:
        raise ValueError("Parameter space cannot be empty")

    for param_name, param_config in param_space.items():
        if not isinstance(param_config, dict):
            raise ValueError(f"Parameter '{param_name}' must be a dictionary")

        param_type = param_config.get('type')
        if param_type not in ['int', 'float', 'categorical']:
            raise ValueError(f"Parameter '{param_name}' has invalid type '{param_type}'. Must be 'int', 'float', or 'categorical'")

        if param_type in ['int', 'float']:
            if 'low' not in param_config or 'high' not in param_config:
                raise ValueError(f"Parameter '{param_name}' must have 'low' and 'high' bounds")
            if param_config['low'] >= param_config['high']:
                raise ValueError(f"Parameter '{param_name}' low bound must be less than high bound")

        if param_type == 'categorical':
            if 'choices' not in param_config or not param_config['choices']:
                raise ValueError(f"Categorical parameter '{param_name}' must have non-empty 'choices' list")


def create_study_name(args: argparse.Namespace) -> str:
    """
    Create a standardized study name from command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        Study name string
    """
    # Create study name: {project}.{asset_class}.{strategy_family}.{strategy_name}_{timestamp}
    strategy_name = Path(args.strategy).stem  # Extract filename without extension

    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    study_name = f"{args.project}.{args.asset_class}.{args.strategy_family}.{strategy_name}_{timestamp}"

    return study_name


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Optimize trading strategy parameters using Bayesian optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic optimization
  python scripts/optimize_strategy.py \\
    --strategy strategies/sma_crossover.py \\
    --param-space param_spaces/sma_crossover.json \\
    --symbols SPY,AAPL \\
    --start 2020-01-01 \\
    --end 2024-12-31 \\
    --metric sharpe_ratio \\
    --n-trials 50

  # Distributed optimization with custom study name
  python scripts/optimize_strategy.py \\
    --strategy strategies/my_strategy.py \\
    --param-space params.json \\
    --study-name my_custom_study \\
    --symbols SPY \\
    --start 2020-01-01 \\
    --end 2024-12-31 \\
    --n-trials 100 \\
    --n-jobs 4 \\
    --project Q1_2025 \\
    --asset-class Equities \\
    --strategy-family MeanReversion
        """
    )

    # Required arguments
    parser.add_argument(
        "--strategy",
        required=True,
        help="Path to strategy module (e.g., strategies/sma_crossover.py)"
    )
    parser.add_argument(
        "--param-space",
        required=True,
        help="JSON file containing parameter space definition"
    )
    parser.add_argument(
        "--symbols",
        required=True,
        help="Comma-separated list of symbols to test (e.g., SPY,AAPL)"
    )
    parser.add_argument(
        "--start",
        required=True,
        help="Start date for backtesting (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end",
        required=True,
        help="End date for backtesting (YYYY-MM-DD)"
    )

    # Optional arguments
    parser.add_argument(
        "--study-name",
        help="Custom name for the optimization study (auto-generated if not provided)"
    )
    parser.add_argument(
        "--metric",
        default="sharpe_ratio",
        choices=["sharpe_ratio", "sortino_ratio", "total_return", "profit_factor", "max_drawdown", "calmar_ratio", "win_rate"],
        help="Metric to optimize (default: sharpe_ratio)"
    )
    parser.add_argument(
        "--n-trials",
        type=int,
        default=100,
        help="Number of optimization trials (default: 100)"
    )
    parser.add_argument(
        "--n-jobs",
        type=int,
        default=1,
        help="Number of parallel workers (default: 1)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        help="Timeout in seconds per study (default: no timeout)"
    )
    parser.add_argument(
        "--project",
        default="optimization",
        help="Project name for MLflow tagging (default: optimization)"
    )
    parser.add_argument(
        "--asset-class",
        default="equities",
        help="Asset class for tagging (default: equities)"
    )
    parser.add_argument(
        "--strategy-family",
        default="unknown",
        help="Strategy family for tagging (default: unknown)"
    )
    parser.add_argument(
        "--config",
        default="config/optuna_config.yaml",
        help="Path to Optuna configuration file"
    )
    parser.add_argument(
        "--output",
        help="Output file to save optimization results (JSON format)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs without running optimization"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Load and validate parameter space
        logger.info("Loading parameter space from %s", args.param_space)
        param_space = load_param_space(args.param_space)
        validate_param_space(param_space)

        # Create study name if not provided
        if not args.study_name:
            args.study_name = create_study_name(args)
            logger.info("Auto-generated study name: %s", args.study_name)

        # Parse symbols
        symbols = [s.strip() for s in args.symbols.split(',') if s.strip()]
        if not symbols:
            raise ValueError("At least one symbol must be specified")

        # Dry run mode
        if args.dry_run:
            logger.info("DRY RUN MODE - Validation only")
            logger.info("Strategy: %s", args.strategy)
            logger.info("Parameter space: %d parameters", len(param_space))
            logger.info("Symbols: %s", symbols)
            logger.info("Date range: %s to %s", args.start, args.end)
            logger.info("Study name: %s", args.study_name)
            logger.info("Metric: %s", args.metric)
            logger.info("Trials: %d", args.n_trials)
            logger.info("Parallel jobs: %d", args.n_jobs)
            logger.info("✅ Validation successful - ready for optimization")
            return

        # Initialize optimizer
        logger.info("Initializing Optuna optimizer...")
        optimizer = OptunaOptimizer(args.config)

        # Run optimization
        logger.info("Starting optimization with %d trials...", args.n_trials)
        start_time = __import__('time').time()

        results = optimizer.optimize_strategy(
            strategy_path=args.strategy,
            param_space=param_space,
            study_name=args.study_name,
            symbols=symbols,
            start_date=args.start,
            end_date=args.end,
            n_trials=args.n_trials,
            metric=args.metric,
            project=args.project,
            asset_class=args.asset_class,
            strategy_family=args.strategy_family,
            n_jobs=args.n_jobs,
            timeout=args.timeout
        )

        end_time = __import__('time').time()
        duration = end_time - start_time

        # Display results
        print("\n" + "="*80)
        print("🎯 OPTIMIZATION RESULTS")
        print("="*80)
        print(f"📊 Study: {results['study_name']}")
        print(f"🎯 Best {args.metric}: {results['best_value']:.4f}")
        print(f"🔢 Best Trial: #{results['best_trial']}")
        print(f"📈 Trials Completed: {results['n_trials']}")
        print(f"⏱️  Duration: {duration:.1f} seconds")
        print(f"⚡ Trials/second: {results['n_trials']/duration:.2f}")
        print()
        print("🏆 BEST PARAMETERS:")
        for param, value in results['best_params'].items():
            print(f"  {param}: {value}")
        print("="*80)

        # Save results if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info("Results saved to %s", args.output)

        logger.info("Optimization completed successfully!")

    except KeyboardInterrupt:
        logger.info("Optimization interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error("Optimization failed: %s", e)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()