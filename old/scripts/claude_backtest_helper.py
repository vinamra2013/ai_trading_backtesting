#!/usr/bin/env python3
"""
Claude Backtest Helper - Simplified interface for Claude AI to run backtests.

This script provides an easy-to-use interface for Claude to:
1. Run backtests with simple commands
2. Parse and interpret results in a structured way
3. Provide human-readable summaries
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional


def run_backtest_simple(
    algorithm: str,
    start: str = "2020-01-01",
    end: str = "2024-12-31",
    parameters: Optional[Dict[str, any]] = None
) -> Dict:
    """
    Run a backtest with minimal configuration.

    Args:
        algorithm: Path to algorithm (e.g., "algorithms/my_strategy")
        start: Start date YYYY-MM-DD
        end: End date YYYY-MM-DD
        parameters: Optional parameters dict (e.g., {"sma_period": 20})

    Returns:
        Structured results with metrics and summary
    """
    # Build command
    cmd = ["lean", "backtest", algorithm]

    # Add parameters if provided
    if parameters:
        for param_name, param_value in parameters.items():
            cmd.extend(["--parameter", param_name, str(param_value)])

    print(f"Running: {' '.join(cmd)}")
    print(f"Period: {start} to {end}")
    if parameters:
        print(f"Parameters: {parameters}")
    print("-" * 80)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        metrics = parse_lean_output(result.stdout)

        return {
            "status": "success",
            "algorithm": algorithm,
            "period": {"start": start, "end": end},
            "parameters": parameters or {},
            "metrics": metrics,
            "summary": generate_summary(metrics),
            "raw_output": result.stdout
        }

    except subprocess.CalledProcessError as e:
        return {
            "status": "failed",
            "algorithm": algorithm,
            "error": str(e),
            "stderr": e.stderr
        }


def parse_lean_output(stdout: str) -> Dict[str, float]:
    """
    Parse LEAN backtest output to extract key metrics.

    Args:
        stdout: LEAN CLI output

    Returns:
        Dictionary of parsed metrics
    """
    metrics = {}

    # Common patterns in LEAN output
    patterns = {
        "total_return": r"Total Return:\s+([-+]?\d*\.?\d+)%?",
        "sharpe_ratio": r"Sharpe Ratio:\s+([-+]?\d*\.?\d+)",
        "sortino_ratio": r"Sortino Ratio:\s+([-+]?\d*\.?\d+)",
        "max_drawdown": r"Max(?:imum)? Drawdown:\s+([-+]?\d*\.?\d+)%?",
        "win_rate": r"Win Rate:\s+([-+]?\d*\.?\d+)%?",
        "profit_factor": r"Profit Factor:\s+([-+]?\d*\.?\d+)",
        "total_trades": r"Total (?:Number of )?Trades:\s+(\d+)",
        "average_win": r"Average Win:\s+([-+]?\d*\.?\d+)%?",
        "average_loss": r"Average Loss:\s+([-+]?\d*\.?\d+)%?",
        "compounding_annual_return": r"Compounding Annual Return:\s+([-+]?\d*\.?\d+)%?",
        "net_profit": r"Net Profit:\s+\$?([-+]?\d*\.?\d+)",
        "unrealized_profit": r"Unrealized:\s+\$?([-+]?\d*\.?\d+)",
        "total_fees": r"Total Fees:\s+\$?([-+]?\d*\.?\d+)",
    }

    for metric_name, pattern in patterns.items():
        match = re.search(pattern, stdout, re.IGNORECASE)
        if match:
            try:
                metrics[metric_name] = float(match.group(1))
            except ValueError:
                pass

    return metrics


def generate_summary(metrics: Dict[str, float]) -> str:
    """
    Generate human-readable summary of backtest results.

    Args:
        metrics: Parsed metrics dictionary

    Returns:
        Summary string
    """
    summary_parts = []

    # Performance summary
    total_return = metrics.get("total_return", 0)
    sharpe = metrics.get("sharpe_ratio", 0)
    drawdown = metrics.get("max_drawdown", 0)

    summary_parts.append(f"Performance: {total_return:+.2f}% total return")
    summary_parts.append(f"Risk-Adjusted: Sharpe ratio of {sharpe:.2f}")
    summary_parts.append(f"Risk: {drawdown:.2f}% max drawdown")

    # Trading activity
    trades = metrics.get("total_trades", 0)
    win_rate = metrics.get("win_rate", 0)

    if trades:
        summary_parts.append(f"Activity: {int(trades)} trades with {win_rate:.1f}% win rate")

    # Overall assessment
    if sharpe > 1.5:
        assessment = "Excellent risk-adjusted returns"
    elif sharpe > 1.0:
        assessment = "Good risk-adjusted returns"
    elif sharpe > 0.5:
        assessment = "Moderate risk-adjusted returns"
    else:
        assessment = "Poor risk-adjusted returns"

    summary_parts.append(f"Assessment: {assessment}")

    return " | ".join(summary_parts)


def format_results_table(results_list: list) -> str:
    """
    Format multiple backtest results as a comparison table.

    Args:
        results_list: List of result dictionaries

    Returns:
        Formatted table string
    """
    if not results_list:
        return "No results to display"

    # Extract key metrics for table
    table_rows = []
    headers = ["Parameters", "Return %", "Sharpe", "Drawdown %", "Trades", "Win Rate %"]

    for result in results_list:
        if result["status"] != "success":
            continue

        params = result.get("parameters", {})
        metrics = result.get("metrics", {})

        row = [
            str(params) if params else "Default",
            f"{metrics.get('total_return', 0):+.2f}",
            f"{metrics.get('sharpe_ratio', 0):.2f}",
            f"{metrics.get('max_drawdown', 0):.2f}",
            f"{int(metrics.get('total_trades', 0))}",
            f"{metrics.get('win_rate', 0):.1f}"
        ]
        table_rows.append(row)

    # Format as table
    col_widths = [max(len(str(r[i])) for r in [headers] + table_rows) for i in range(len(headers))]

    def format_row(row):
        return " | ".join(str(cell).ljust(width) for cell, width in zip(row, col_widths))

    lines = [
        format_row(headers),
        "-" * (sum(col_widths) + 3 * (len(headers) - 1)),
    ]
    lines.extend(format_row(row) for row in table_rows)

    return "\n".join(lines)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Claude Backtest Helper")
    parser.add_argument("--algorithm", required=True, help="Algorithm path")
    parser.add_argument("--start", default="2020-01-01", help="Start date")
    parser.add_argument("--end", default="2024-12-31", help="End date")
    parser.add_argument("--param", action="append", nargs=2, metavar=("NAME", "VALUE"),
                        help="Parameter as name value pair (can be repeated)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    # Parse parameters
    parameters = None
    if args.param:
        parameters = {}
        for name, value in args.param:
            # Try to convert to number
            try:
                if "." in value:
                    parameters[name] = float(value)
                else:
                    parameters[name] = int(value)
            except ValueError:
                parameters[name] = value

    # Run backtest
    result = run_backtest_simple(
        algorithm=args.algorithm,
        start=args.start,
        end=args.end,
        parameters=parameters
    )

    # Output
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["status"] == "success":
            print("\n" + "="*80)
            print("BACKTEST RESULTS")
            print("="*80)
            print(f"\nAlgorithm: {result['algorithm']}")
            print(f"Period: {result['period']['start']} to {result['period']['end']}")
            if result["parameters"]:
                print(f"Parameters: {result['parameters']}")
            print("\n" + result["summary"])
            print("\n" + "="*80)
            print("DETAILED METRICS:")
            print("="*80)
            for metric, value in sorted(result["metrics"].items()):
                print(f"{metric.replace('_', ' ').title():30s}: {value:>12.2f}")
        else:
            print("BACKTEST FAILED")
            print(f"Error: {result.get('error')}")
            if result.get("stderr"):
                print(f"Details: {result['stderr']}")

    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    main()
