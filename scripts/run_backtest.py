#!/usr/bin/env python3
"""
Backtest Runner Script - Programmatic interface to LEAN backtesting.

US-4.1: Easy Backtest Execution
Track A: Enhanced with structured parsing
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import uuid

# Import backtest parser
from backtest_parser import parse_backtest

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BacktestRunner:
    """Wrapper for LEAN backtest execution."""

    def run(self, algorithm: str, start: str, end: str, cost_model: str = "ib_standard"):
        """
        Run LEAN backtest with structured parsing.

        Args:
            algorithm: Path to algorithm directory
            start: Start date YYYY-MM-DD
            end: End date YYYY-MM-DD
            cost_model: Cost model to use

        Returns:
            Result dictionary with backtest ID, parsed metrics, and trades
        """
        logger.info(f"Running backtest for {algorithm}")
        logger.info(f"Period: {start} to {end}")

        # Build LEAN CLI command
        cmd = ["lean", "backtest", algorithm]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Generate result ID
            backtest_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()

            # Parse backtest output into structured format
            logger.info("Parsing backtest output...")
            try:
                parsed_results = parse_backtest(
                    result.stdout,
                    backtest_id,
                    algorithm,
                    start,
                    end
                )
                logger.info(f"✓ Parsed {parsed_results.get('trade_count', 0)} trades")
            except Exception as e:
                logger.warning(f"Failed to parse backtest output: {e}")
                parsed_results = {
                    "backtest_id": backtest_id,
                    "algorithm": algorithm,
                    "period": {"start": start, "end": end},
                    "parse_error": str(e)
                }

            # Combine parsed results with metadata
            result_data = {
                **parsed_results,
                "cost_model": cost_model,
                "timestamp": timestamp,
                "raw_stdout": result.stdout,
                "status": "completed"
            }

            # Save results
            results_dir = Path("results/backtests")
            results_dir.mkdir(parents=True, exist_ok=True)

            result_file = results_dir / f"{backtest_id}.json"
            result_file.write_text(json.dumps(result_data, indent=2))

            logger.info(f"✓ Backtest completed: {backtest_id}")
            logger.info(f"Results saved to: {result_file}")

            # Print summary
            if "metrics" in result_data:
                metrics = result_data["metrics"]
                logger.info("=== Performance Summary ===")
                logger.info(f"Total Return: {metrics.get('total_return', 0)*100:.2f}%")
                logger.info(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
                logger.info(f"Max Drawdown: {metrics.get('max_drawdown', 0)*100:.2f}%")
                logger.info(f"Win Rate: {metrics.get('win_rate', 0)*100:.2f}%")
                logger.info(f"Total Trades: {metrics.get('trade_count', 0)}")

            return result_data

        except subprocess.CalledProcessError as e:
            logger.error(f"Backtest failed: {e}")
            logger.error(e.stderr)
            return None


def main():
    parser = argparse.ArgumentParser(description="Run LEAN backtest")
    parser.add_argument("--algorithm", required=True, help="Path to algorithm")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--cost-model", default="ib_standard", help="Cost model")
    args = parser.parse_args()

    runner = BacktestRunner()
    result = runner.run(args.algorithm, args.start, args.end, args.cost_model)

    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
