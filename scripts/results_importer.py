#!/usr/bin/env python3
"""
LEAN Optimization Results Importer
Parses LEAN optimization JSON output and imports to PostgreSQL database
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters
DB_NAME = os.getenv('POSTGRES_DB', 'trading')
DB_USER = os.getenv('POSTGRES_USER', 'postgres')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Import LEAN optimization results to PostgreSQL'
    )
    parser.add_argument(
        '--optimization-dir',
        type=str,
        required=True,
        help='Path to LEAN optimization directory (.optimization/ProjectName/)'
    )
    parser.add_argument(
        '--strategy-name',
        type=str,
        help='Strategy name from config (overrides directory name)'
    )
    parser.add_argument(
        '--config',
        type=str,
        help='Path to original optimization config (for success criteria)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Parse files but do not insert into database'
    )

    return parser.parse_args()


def find_optimization_results(optimization_dir):
    """Find all JSON result files in optimization directory"""
    opt_path = Path(optimization_dir)

    if not opt_path.exists():
        raise FileNotFoundError(f"Optimization directory not found: {optimization_dir}")

    # LEAN stores optimization results as JSON files
    # Exclude config files - only get actual result files
    json_files = [f for f in opt_path.glob('**/*.json')
                  if f.name not in ['optimizer-config.json', 'config.json']]

    if not json_files:
        raise FileNotFoundError(f"No result JSON files found in {optimization_dir}")

    return json_files


def parse_backtest_result(json_file):
    """Parse a single backtest result JSON file"""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)

        # LEAN optimization results structure may vary
        # Try to extract standard metrics
        result = {}

        # Try to find Statistics section (most common location)
        if 'Statistics' in data:
            stats = data['Statistics']
        elif 'statistics' in data:
            stats = data['statistics']
        elif 'Results' in data and 'Statistics' in data['Results']:
            stats = data['Results']['Statistics']
        else:
            # Fallback: try to find metrics directly
            stats = data

        # Extract parameters (from ParameterSet if present)
        parameters = {}
        if 'ParameterSet' in data:
            parameters = data['ParameterSet']
        elif 'Parameters' in data:
            parameters = data['Parameters']

        # Extract metrics with safe fallbacks
        result['parameters'] = parameters
        result['sharpe_ratio'] = safe_float(stats.get('Sharpe Ratio'))
        result['sortino_ratio'] = safe_float(stats.get('Sortino Ratio'))
        result['total_return'] = safe_float(stats.get('Total Net Profit', stats.get('Compounding Annual Return')))
        result['annual_return'] = safe_float(stats.get('Annual Return', stats.get('Compounding Annual Return')))
        result['compounding_annual_return'] = safe_float(stats.get('Compounding Annual Return'))
        result['max_drawdown'] = safe_float(stats.get('Drawdown', stats.get('Max Drawdown')))
        result['annual_std_dev'] = safe_float(stats.get('Annual Standard Deviation'))
        result['annual_variance'] = safe_float(stats.get('Annual Variance'))

        # Trading metrics
        result['total_trades'] = safe_int(stats.get('Total Trades', stats.get('Total Orders')))
        result['win_rate'] = safe_float(stats.get('Win Rate', stats.get('Probabilistic Sharpe Ratio')))
        result['loss_rate'] = safe_float(stats.get('Loss Rate'))
        result['avg_win'] = safe_float(stats.get('Average Win'))
        result['avg_loss'] = safe_float(stats.get('Average Loss'))
        result['profit_loss_ratio'] = safe_float(stats.get('Profit-Loss Ratio'))

        # Portfolio metrics
        result['total_fees'] = safe_float(stats.get('Total Fees'))
        result['net_profit'] = safe_float(stats.get('Net Profit', stats.get('Total Net Profit')))
        result['portfolio_turnover'] = safe_float(stats.get('Portfolio Turnover'))
        result['estimated_capacity'] = safe_float(stats.get('Estimated Strategy Capacity'))

        # Greek metrics
        result['alpha'] = safe_float(stats.get('Alpha'))
        result['beta'] = safe_float(stats.get('Beta'))

        # Metadata
        result['backtest_id'] = data.get('BacktestId', data.get('backtest-id'))
        result['backtest_name'] = data.get('Name', data.get('name'))

        return result

    except json.JSONDecodeError as e:
        print(f"⚠️  Error parsing JSON file {json_file}: {e}")
        return None
    except Exception as e:
        print(f"⚠️  Unexpected error parsing {json_file}: {e}")
        return None


def safe_float(value):
    """Safely convert value to float, return None if not possible"""
    if value is None:
        return None
    try:
        # Handle percentage strings like "15.2%"
        if isinstance(value, str):
            value = value.replace('%', '').strip()
        return float(value)
    except (ValueError, TypeError):
        return None


def safe_int(value):
    """Safely convert value to int, return None if not possible"""
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def load_success_criteria(config_path=None):
    """Load success criteria from config file"""
    if not config_path:
        # Default criteria if no config provided
        return {
            'min_trades': 100,
            'min_win_rate': 0.50,
            'min_sharpe': 1.0,
            'max_drawdown': 0.15,
            'min_avg_win': 0.01,
            'max_fee_pct': 0.30
        }

    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config.get('success_criteria', {})
    except Exception as e:
        print(f"⚠️  Could not load success criteria from config: {e}")
        return {}


def evaluate_result(result, criteria, capital=1000):
    """Evaluate backtest result against success criteria"""
    reasons = []
    meets_criteria = True

    # Total trades check
    if result['total_trades'] and criteria.get('min_trades'):
        if result['total_trades'] < criteria['min_trades']:
            reasons.append(f"Insufficient trades: {result['total_trades']} < {criteria['min_trades']}")
            meets_criteria = False

    # Win rate check
    if result['win_rate'] and criteria.get('min_win_rate'):
        if result['win_rate'] < criteria['min_win_rate']:
            reasons.append(f"Win rate too low: {result['win_rate']:.1%} < {criteria['min_win_rate']:.1%}")
            meets_criteria = False

    # Sharpe ratio check
    if result['sharpe_ratio'] and criteria.get('min_sharpe'):
        if result['sharpe_ratio'] < criteria['min_sharpe']:
            reasons.append(f"Sharpe too low: {result['sharpe_ratio']:.2f} < {criteria['min_sharpe']:.2f}")
            meets_criteria = False

    # Drawdown check
    if result['max_drawdown'] and criteria.get('max_drawdown'):
        if abs(result['max_drawdown']) > criteria['max_drawdown']:
            reasons.append(f"Drawdown too high: {abs(result['max_drawdown']):.1%} > {criteria['max_drawdown']:.1%}")
            meets_criteria = False

    # Average win check
    if result['avg_win'] and criteria.get('min_avg_win'):
        if result['avg_win'] < criteria['min_avg_win']:
            reasons.append(f"Avg win too low: {result['avg_win']:.2%} < {criteria['min_avg_win']:.2%}")
            meets_criteria = False

    # Fee percentage check
    if result['total_fees'] and criteria.get('max_fee_pct'):
        fee_pct = result['total_fees'] / capital
        if fee_pct > criteria['max_fee_pct']:
            reasons.append(f"Fees too high: {fee_pct:.1%} > {criteria['max_fee_pct']:.1%}")
            meets_criteria = False

    return meets_criteria, reasons


def get_strategy_id(conn, strategy_name):
    """Get strategy ID from database by name"""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM strategies WHERE name = %s", (strategy_name,))
    result = cursor.fetchone()
    cursor.close()

    if not result:
        raise ValueError(f"Strategy '{strategy_name}' not found in database")

    return result[0]


def get_optimization_run_id(conn, strategy_id):
    """Get most recent optimization run ID for strategy"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM optimization_runs
        WHERE strategy_id = %s
        AND status = 'running'
        ORDER BY started_at DESC
        LIMIT 1
    """, (strategy_id,))
    result = cursor.fetchone()
    cursor.close()

    return result[0] if result else None


def insert_backtest_result(conn, optimization_run_id, strategy_id, result, meets_criteria, rejection_reasons):
    """Insert backtest result into database"""
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO backtest_results (
                optimization_run_id,
                strategy_id,
                parameters,
                sharpe_ratio,
                sortino_ratio,
                total_return,
                annual_return,
                compounding_annual_return,
                max_drawdown,
                annual_std_dev,
                annual_variance,
                total_trades,
                win_rate,
                loss_rate,
                avg_win,
                avg_loss,
                profit_loss_ratio,
                total_fees,
                net_profit,
                portfolio_turnover,
                estimated_capacity,
                alpha,
                beta,
                meets_criteria,
                rejection_reasons,
                backtest_id,
                backtest_name
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            optimization_run_id,
            strategy_id,
            Json(result['parameters']),
            result['sharpe_ratio'],
            result['sortino_ratio'],
            result['total_return'],
            result['annual_return'],
            result['compounding_annual_return'],
            result['max_drawdown'],
            result['annual_std_dev'],
            result['annual_variance'],
            result['total_trades'],
            result['win_rate'],
            result['loss_rate'],
            result['avg_win'],
            result['avg_loss'],
            result['profit_loss_ratio'],
            result['total_fees'],
            result['net_profit'],
            result['portfolio_turnover'],
            result['estimated_capacity'],
            result['alpha'],
            result['beta'],
            meets_criteria,
            rejection_reasons if rejection_reasons else None,
            result['backtest_id'],
            result['backtest_name']
        ))

        conn.commit()
        cursor.close()
        return True

    except psycopg2.Error as e:
        print(f"❌ Database error inserting result: {e}")
        conn.rollback()
        cursor.close()
        return False


def update_optimization_run_status(conn, run_id, total_results, passed_results):
    """Update optimization run status to completed"""
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE optimization_runs
            SET status = 'completed',
                completed_at = NOW(),
                completed_combinations = %s,
                passed_combinations = %s
            WHERE id = %s
        """, (total_results, passed_results, run_id))

        conn.commit()
        cursor.close()
        return True

    except psycopg2.Error as e:
        print(f"❌ Database error updating optimization run: {e}")
        conn.rollback()
        cursor.close()
        return False


def main():
    """Main execution flow"""
    args = parse_args()

    print("\n" + "="*60)
    print("LEAN OPTIMIZATION RESULTS IMPORTER")
    print("="*60)

    # Find result files
    try:
        json_files = find_optimization_results(args.optimization_dir)
        print(f"\n✅ Found {len(json_files)} JSON files in {args.optimization_dir}")
    except Exception as e:
        print(f"\n❌ Error finding results: {e}")
        return 1

    # Load success criteria
    criteria = load_success_criteria(args.config)
    print(f"✅ Loaded success criteria: {criteria}")

    # Parse results
    print(f"\nParsing backtest results...")
    parsed_results = []
    for json_file in json_files:
        result = parse_backtest_result(json_file)
        if result:
            parsed_results.append(result)
            print(f"  ✅ Parsed: {json_file.name}")
        else:
            print(f"  ⚠️  Skipped: {json_file.name}")

    if not parsed_results:
        print("\n❌ No valid results parsed. Exiting.")
        return 1

    print(f"\n✅ Successfully parsed {len(parsed_results)} backtest results")

    # Evaluate results
    print(f"\nEvaluating results against success criteria...")
    passed_count = 0
    evaluations = []

    for result in parsed_results:
        meets_criteria, reasons = evaluate_result(result, criteria)
        evaluations.append((result, meets_criteria, reasons))

        if meets_criteria:
            passed_count += 1

    print(f"✅ {passed_count}/{len(parsed_results)} results passed criteria")

    # Dry run mode
    if args.dry_run:
        print("\n" + "="*60)
        print("DRY RUN MODE - No database insertion")
        print("="*60)
        return 0

    # Connect to database
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        print(f"\n✅ Connected to PostgreSQL: {DB_NAME}")
    except psycopg2.Error as e:
        print(f"\n❌ Database connection failed: {e}")
        print(f"   Connection: postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
        return 1

    # Get strategy name (from argument or infer from project directory)
    if args.strategy_name:
        strategy_name = args.strategy_name
    else:
        # Path structure: lean_projects/ProjectName/optimizations/timestamp/
        opt_path = Path(args.optimization_dir)
        strategy_name = opt_path.parent.parent.name  # Get ProjectName from path

    try:
        strategy_id = get_strategy_id(conn, strategy_name)
        print(f"✅ Found strategy ID: {strategy_id} ({strategy_name})")
    except ValueError as e:
        print(f"\n⚠️  {e}")
        print("   Creating strategy record...")
        # Could auto-create strategy here if needed
        conn.close()
        return 1

    # Get optimization run ID
    run_id = get_optimization_run_id(conn, strategy_id)
    if not run_id:
        print("\n⚠️  No active optimization run found. Results will be orphaned.")
        # Could create a run record here if needed

    # Insert results
    print(f"\nInserting {len(evaluations)} results into database...")
    inserted_count = 0

    for result, meets_criteria, reasons in evaluations:
        success = insert_backtest_result(conn, run_id, strategy_id, result, meets_criteria, reasons)
        if success:
            inserted_count += 1

    print(f"✅ Inserted {inserted_count}/{len(evaluations)} results")

    # Update optimization run status
    if run_id:
        update_optimization_run_status(conn, run_id, len(evaluations), passed_count)
        print(f"✅ Updated optimization run status")

    conn.close()

    # Print summary
    print("\n" + "="*60)
    print("IMPORT COMPLETE")
    print("="*60)
    print(f"Total results: {len(evaluations)}")
    print(f"Passed criteria: {passed_count}")
    print(f"Inserted to DB: {inserted_count}")
    print("="*60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
