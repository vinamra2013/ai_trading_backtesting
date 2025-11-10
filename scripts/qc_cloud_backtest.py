#!/usr/bin/env python3
"""
QuantConnect Cloud Backtest Automation Script

This script automates the process of:
1. Pushing strategy code to QuantConnect cloud
2. Running backtests
3. Retrieving and parsing results
4. Saving results locally

Usage:
    python scripts/qc_cloud_backtest.py --strategy rsi_mean_reversion_lean --open
    python scripts/qc_cloud_backtest.py --strategy rsi_mean_reversion_lean --wait --save

Requirements:
    pip install lean

Environment Variables (in .env):
    QC_USER_ID=your_user_id
    QC_API_TOKEN=your_api_token
    QC_PROJECT_ID=your_project_id
    QC_PROJECT_NAME=your_project_name
"""

import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# QuantConnect credentials
QC_USER_ID = os.getenv("QC_USER_ID")
QC_API_TOKEN = os.getenv("QC_API_TOKEN")
QC_PROJECT_ID = os.getenv("QC_PROJECT_ID")
QC_PROJECT_NAME = os.getenv("QC_PROJECT_NAME", "RSI Mean Reversion Basic")

# GitHub repo
GITHUB_REPO = "git@github.com:vinamra2013/QuantConnectAlgoTradingStratigies.git"

# Paths
BASE_DIR = Path(__file__).parent.parent
STRATEGIES_DIR = BASE_DIR / "strategies"
RESULTS_DIR = BASE_DIR / "results" / "qc"

# Ensure results directory exists
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def run_command(cmd, capture_output=True, check=True):
    """Run shell command and return output"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            check=check
        )
        return result.stdout.strip() if capture_output else None
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"Error: {e.stderr}")
        if check:
            sys.exit(1)
        return None


def check_lean_installed():
    """Check if LEAN CLI is installed"""
    result = run_command("lean --version", check=False)
    if result is None:
        print("Error: LEAN CLI not installed")
        print("\nInstall with: pip install lean")
        print("Then login with: lean login")
        sys.exit(1)
    print(f"✓ LEAN CLI installed: {result}")


def check_credentials():
    """Check if QuantConnect credentials are configured"""
    if not QC_PROJECT_NAME:
        print("Error: QC_PROJECT_NAME not set in .env")
        print("\nAdd to .env file:")
        print('QC_PROJECT_NAME="Your Project Name"')
        sys.exit(1)

    print(f"✓ Using project: {QC_PROJECT_NAME}")


def git_commit_push(message=None):
    """Commit and push changes to GitHub"""
    if message is None:
        message = f"Update strategy: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    print("\n" + "="*60)
    print("Git: Committing and pushing changes")
    print("="*60)

    # Check if there are changes
    status = run_command("git status --porcelain")
    if not status:
        print("No changes to commit")
        return

    # Add, commit, push
    run_command("git add strategies/")
    run_command(f'git commit -m "{message}"')
    run_command("git push")

    print("✓ Pushed to GitHub")


def lean_cloud_push(project_name):
    """Push strategy to QuantConnect cloud using LEAN CLI"""
    print("\n" + "="*60)
    print("LEAN: Pushing to QuantConnect cloud")
    print("="*60)

    cmd = f'lean cloud push --project "{project_name}"'
    result = run_command(cmd, capture_output=False)

    print("✓ Pushed to QuantConnect cloud")


def lean_cloud_backtest(project_name, open_browser=False):
    """Run backtest on QuantConnect cloud"""
    print("\n" + "="*60)
    print("LEAN: Running backtest")
    print("="*60)

    cmd = f'lean cloud backtest "{project_name}"'
    if open_browser:
        cmd += " --open"

    result = run_command(cmd, capture_output=False)

    print("✓ Backtest started")


def lean_get_latest_backtest_id(project_name):
    """Get the latest backtest ID for a project"""
    print("\nFetching latest backtest ID...")

    cmd = f'lean cloud backtests "{project_name}"'
    result = run_command(cmd)

    # Parse output to get first backtest ID
    lines = result.split('\n')
    for line in lines:
        if line.strip() and not line.startswith('Backtest'):
            # First non-header line should be latest backtest
            backtest_id = line.split()[0]
            print(f"✓ Latest backtest ID: {backtest_id}")
            return backtest_id

    print("Warning: Could not find backtest ID")
    return None


def lean_get_backtest_status(project_name, backtest_id):
    """Check if backtest is complete"""
    cmd = f'lean cloud results "{backtest_id}" --project "{project_name}"'
    result = run_command(cmd, check=False)

    # If command succeeds, backtest is complete
    return result is not None


def wait_for_backtest(project_name, backtest_id, timeout=300, poll_interval=10):
    """Wait for backtest to complete"""
    print("\n" + "="*60)
    print("Waiting for backtest to complete")
    print("="*60)

    start_time = time.time()
    dots = 0

    while time.time() - start_time < timeout:
        if lean_get_backtest_status(project_name, backtest_id):
            elapsed = time.time() - start_time
            print(f"\n✓ Backtest completed in {elapsed:.1f} seconds")
            return True

        # Print progress dots
        dots = (dots + 1) % 4
        print(f"\rWaiting{'.' * dots}   ", end='', flush=True)
        time.sleep(poll_interval)

    print(f"\n⚠ Backtest timed out after {timeout} seconds")
    return False


def lean_download_results(project_name, backtest_id, output_path=None):
    """Download backtest results"""
    print("\n" + "="*60)
    print("Downloading backtest results")
    print("="*60)

    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = RESULTS_DIR / f"backtest_{timestamp}.json"

    cmd = f'lean cloud results "{backtest_id}" --project "{project_name}" --output "{output_path}"'
    run_command(cmd)

    print(f"✓ Results saved to: {output_path}")
    return output_path


def parse_results(results_path):
    """Parse and display key metrics from backtest results"""
    print("\n" + "="*60)
    print("BACKTEST RESULTS")
    print("="*60)

    try:
        with open(results_path, 'r') as f:
            data = json.load(f)

        # Extract key statistics
        stats = data.get('Statistics', {})

        metrics = {
            'Total Return': stats.get('Total Performance', 'N/A'),
            'Sharpe Ratio': stats.get('Sharpe Ratio', 'N/A'),
            'Total Orders': stats.get('Total Orders', 'N/A'),
            'Win Rate': stats.get('Win Rate', 'N/A'),
            'Loss Rate': stats.get('Loss Rate', 'N/A'),
            'Average Win': stats.get('Average Win', 'N/A'),
            'Average Loss': stats.get('Average Loss', 'N/A'),
            'Max Drawdown': stats.get('Drawdown', 'N/A'),
            'Sortino Ratio': stats.get('Sortino Ratio', 'N/A'),
            'Net Profit': stats.get('Net Profit', 'N/A'),
            'Annual Return': stats.get('Compounding Annual Return', 'N/A'),
        }

        for key, value in metrics.items():
            print(f"{key:20s}: {value}")

        # Calculate profit per trade if possible
        total_orders = stats.get('Total Orders')
        net_profit_str = stats.get('Net Profit', '').replace('%', '').replace('$', '')

        if total_orders and total_orders != 'N/A' and net_profit_str:
            try:
                total_orders_int = int(total_orders)
                if total_orders_int > 0:
                    # This is approximate, would need actual P&L data for accuracy
                    print(f"\n{'Trades Executed':20s}: {total_orders_int}")
            except (ValueError, TypeError):
                pass

        print("="*60)

        return metrics

    except Exception as e:
        print(f"Error parsing results: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Automate QuantConnect cloud backtesting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick backtest with browser open
  python scripts/qc_cloud_backtest.py --open

  # Full workflow: push, backtest, wait, save results
  python scripts/qc_cloud_backtest.py --wait --save

  # Commit to git first, then backtest
  python scripts/qc_cloud_backtest.py --commit --wait --save

  # Custom project name
  python scripts/qc_cloud_backtest.py --project "My Strategy" --open
        """
    )

    parser.add_argument(
        "--project",
        default=QC_PROJECT_NAME,
        help="QuantConnect project name (default: from .env)"
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Commit and push changes to GitHub before running backtest"
    )
    parser.add_argument(
        "--commit-message",
        help="Custom git commit message"
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open backtest results in browser"
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for backtest to complete before exiting"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Download and save backtest results locally"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds when waiting for backtest (default: 300)"
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Skip pushing to QuantConnect cloud (use existing code)"
    )

    args = parser.parse_args()

    # Validate environment
    print("="*60)
    print("QuantConnect Cloud Backtest Automation")
    print("="*60)

    check_lean_installed()
    check_credentials()

    project_name = args.project

    # Step 1: Git commit and push (optional)
    if args.commit:
        git_commit_push(args.commit_message)
        # Give GitHub a moment to process
        time.sleep(2)

    # Step 2: Push to QuantConnect cloud
    if not args.no_push:
        lean_cloud_push(project_name)
        # Give QuantConnect a moment to process
        time.sleep(2)

    # Step 3: Run backtest
    lean_cloud_backtest(project_name, args.open)

    # Step 4: Wait for completion (optional)
    backtest_id = None
    if args.wait or args.save:
        # Give backtest a moment to start
        time.sleep(5)

        backtest_id = lean_get_latest_backtest_id(project_name)

        if backtest_id and args.wait:
            completed = wait_for_backtest(
                project_name,
                backtest_id,
                timeout=args.timeout
            )

            if not completed:
                print("\n⚠ Warning: Backtest may still be running")
                print(f"Check status at: https://www.quantconnect.com/terminal")
                return

    # Step 5: Download results (optional)
    if args.save:
        if backtest_id is None:
            backtest_id = lean_get_latest_backtest_id(project_name)

        if backtest_id:
            results_path = lean_download_results(project_name, backtest_id)
            parse_results(results_path)

    # Final message
    print("\n" + "="*60)
    print("✓ COMPLETE")
    print("="*60)
    print(f"Project: {project_name}")
    if backtest_id:
        print(f"Backtest ID: {backtest_id}")
        print(f"View online: https://www.quantconnect.com/terminal")
    print("="*60)


if __name__ == "__main__":
    main()
