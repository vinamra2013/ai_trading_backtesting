#!/usr/bin/env python3
"""
Database Management Script
Safe operations for trading backtesting database

Usage:
    python scripts/reset_database.py --status              # Check database status
    python scripts/reset_database.py --strategies          # Clear optimization data only
    python scripts/reset_database.py --display leaderboard # Show top performing strategies
    python scripts/reset_database.py --display parameters  # Show parameter performance
    python scripts/reset_database.py --display fees        # Show fee analysis
    python scripts/reset_database.py --display daily       # Show daily summary

SAFE: Views and strategy definitions are ALWAYS preserved
"""

import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from tabulate import tabulate

# Load environment variables
load_dotenv()

# Database connection parameters
DB_NAME = os.getenv('POSTGRES_DB', 'trading')
DB_USER = os.getenv('POSTGRES_USER', 'mlflow')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')


def connect_db():
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed: {e}")
        print(f"   Check that PostgreSQL is running and credentials are correct:")
        print(f"   Host: {DB_HOST}:{DB_PORT}")
        print(f"   Database: {DB_NAME}")
        print(f"   User: {DB_USER}")
        sys.exit(1)


def check_database_status():
    """Display current database status"""
    conn = connect_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Get table row counts
        tables = {
            'strategies': 'SELECT COUNT(*) as count FROM strategies',
            'optimization_runs': 'SELECT COUNT(*) as count FROM optimization_runs',
            'backtest_results': 'SELECT COUNT(*) as count FROM backtest_results'
        }

        print("\n📊 DATABASE STATUS")
        print("=" * 60)
        total_rows = 0
        for table_name, query in tables.items():
            try:
                cur.execute(query)
                result = cur.fetchone()
                count = result['count'] if result else 0
                total_rows += count
                status = "✅" if count > 0 else "⚫"
                print(f"{status} {table_name:.<40} {count:>6} rows")
            except psycopg2.ProgrammingError:
                print(f"⚠️  {table_name:.<40} TABLE NOT FOUND")

        print("=" * 60)
        print(f"📈 Total data rows: {total_rows}")
        print(f"📍 Database: {DB_NAME} @ {DB_HOST}:{DB_PORT}")
        print(f"👤 User: {DB_USER}")
        print(f"✅ All views preserved (not shown in row count)")
        print()

    except Exception as e:
        print(f"❌ Error checking status: {e}")
    finally:
        cur.close()
        conn.close()


def display_leaderboard():
    """Display strategy leaderboard from view"""
    conn = connect_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        print("\n🏆 STRATEGY LEADERBOARD (Top Performers)")
        print("=" * 120)

        cur.execute("""
            SELECT
                rank,
                strategy_name,
                category,
                sharpe_ratio::numeric(6,3) as sharpe,
                total_return::numeric(8,4) as ret_pct,
                annual_return::numeric(8,4) as annual_ret,
                max_drawdown::numeric(6,4) as max_dd,
                total_trades,
                win_rate::numeric(5,2) as wr_pct,
                avg_win::numeric(8,4) as avg_win,
                avg_loss::numeric(8,4) as avg_loss,
                total_fees::numeric(10,2) as fees
            FROM strategy_leaderboard
            LIMIT 20
        """)

        results = cur.fetchall()

        if results:
            headers = [desc[0] for desc in cur.description]
            rows = [[row[col] for col in headers] for row in results]
            print(tabulate(rows, headers=headers, tablefmt="grid", floatfmt=".3f"))
            print(f"\n✅ Showing {len(results)} results from strategy_leaderboard view")
        else:
            print("⚫ No results found (no backtests passed criteria yet)")

        print()

    except psycopg2.ProgrammingError as e:
        print(f"❌ View not found or empty: {e}")
    except Exception as e:
        print(f"❌ Error displaying leaderboard: {e}")
    finally:
        cur.close()
        conn.close()


def display_parameter_performance():
    """Display parameter performance analysis"""
    conn = connect_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        print("\n📊 PARAMETER PERFORMANCE ANALYSIS")
        print("=" * 120)

        cur.execute("""
            SELECT
                strategy_name,
                parameter_name,
                parameter_value,
                avg_sharpe::numeric(6,3) as avg_sharpe,
                avg_return::numeric(8,4) as avg_ret_pct,
                avg_drawdown::numeric(6,4) as avg_dd,
                avg_win_rate::numeric(5,2) as avg_wr_pct,
                test_count
            FROM parameter_performance
            ORDER BY strategy_name, avg_sharpe DESC
            LIMIT 50
        """)

        results = cur.fetchall()

        if results:
            headers = [desc[0] for desc in cur.description]
            rows = [[row[col] for col in headers] for row in results]
            print(tabulate(rows, headers=headers, tablefmt="grid", floatfmt=".3f"))
            print(f"\n✅ Showing {len(results)} parameter combinations from parameter_performance view")
        else:
            print("⚫ No results found")

        print()

    except psycopg2.ProgrammingError as e:
        print(f"❌ View not found or empty: {e}")
    except Exception as e:
        print(f"❌ Error displaying parameters: {e}")
    finally:
        cur.close()
        conn.close()


def display_fee_analysis():
    """Display fee analysis across strategies"""
    conn = connect_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        print("\n💰 FEE ANALYSIS")
        print("=" * 100)

        cur.execute("""
            SELECT
                strategy_name,
                avg_fees::numeric(10,2) as avg_fees,
                avg_fee_pct_of_capital::numeric(6,2) as fee_pct_of_capital,
                avg_trades::numeric(8,1) as avg_trades,
                avg_fee_per_trade::numeric(8,4) as fee_per_trade,
                backtest_count
            FROM fee_analysis
            ORDER BY fee_pct_of_capital DESC
        """)

        results = cur.fetchall()

        if results:
            headers = [desc[0] for desc in cur.description]
            rows = [[row[col] for col in headers] for row in results]
            print(tabulate(rows, headers=headers, tablefmt="grid", floatfmt=".2f"))
            print(f"\n✅ Showing {len(results)} strategies from fee_analysis view")
            print("   📌 CRITICAL: Fees > 25% of $1K capital = $250 (unsustainable)")
        else:
            print("⚫ No results found")

        print()

    except psycopg2.ProgrammingError as e:
        print(f"❌ View not found or empty: {e}")
    except Exception as e:
        print(f"❌ Error displaying fees: {e}")
    finally:
        cur.close()
        conn.close()


def display_daily_summary():
    """Display daily backtesting activity"""
    conn = connect_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        print("\n📅 DAILY BACKTESTING SUMMARY")
        print("=" * 90)

        cur.execute("""
            SELECT
                date,
                total_backtests,
                passed,
                best_sharpe::numeric(6,3) as best_sharpe,
                avg_sharpe::numeric(6,3) as avg_sharpe,
                strategies_tested
            FROM daily_summary
            LIMIT 30
        """)

        results = cur.fetchall()

        if results:
            headers = [desc[0] for desc in cur.description]
            rows = [[row[col] for col in headers] for row in results]
            print(tabulate(rows, headers=headers, tablefmt="grid", floatfmt=".3f"))
            print(f"\n✅ Showing {len(results)} days from daily_summary view")
        else:
            print("⚫ No results found")

        print()

    except psycopg2.ProgrammingError as e:
        print(f"❌ View not found or empty: {e}")
    except Exception as e:
        print(f"❌ Error displaying daily summary: {e}")
    finally:
        cur.close()
        conn.close()


def clear_strategy_data(confirm=True):
    """Clear optimization_runs and backtest_results (keeps strategies and views)"""
    conn = connect_db()
    cur = conn.cursor()

    if confirm:
        check_database_status()
        response = input(
            "\n⚠️  This will DELETE all optimization runs and backtest results\n"
            "but KEEP strategy definitions and PRESERVE all views.\n"
            "Are you sure? Type 'yes' to confirm: "
        ).strip().lower()
        if response != 'yes':
            print("❌ Cancelled")
            return False

    try:
        print("\n🧹 Clearing optimization and backtest data...")

        cur.execute("TRUNCATE TABLE backtest_results CASCADE")
        print("   ✓ Cleared backtest_results")

        cur.execute("TRUNCATE TABLE optimization_runs CASCADE")
        print("   ✓ Cleared optimization_runs")

        # Reset strategy status to 'testing' for all
        cur.execute("UPDATE strategies SET status = 'testing', updated_at = NOW()")
        count = cur.rowcount
        print(f"   ✓ Reset {count} strategies to 'testing' status")

        conn.commit()
        print("\n✅ Optimization data cleared successfully!")
        print("   ✓ Strategy definitions PRESERVED")
        print("   ✓ Database views PRESERVED")
        print("   ✓ Schema PRESERVED")
        return True

    except Exception as e:
        conn.rollback()
        print(f"❌ Error clearing data: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Safe database management for trading backtesting framework',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
SAFE OPERATIONS (Views and Strategy Definitions Always Preserved):
  python scripts/reset_database.py --status              # Show database status
  python scripts/reset_database.py --strategies          # Clear optimization data
  python scripts/reset_database.py --display leaderboard # Show top strategies
  python scripts/reset_database.py --display parameters  # Show parameter analysis
  python scripts/reset_database.py --display fees        # Show fee impact
  python scripts/reset_database.py --display daily       # Show daily activity

Examples:
  python scripts/reset_database.py --status
  python scripts/reset_database.py --strategies --no-confirm
  python scripts/reset_database.py --display leaderboard
        """
    )

    parser.add_argument(
        '--status',
        action='store_true',
        help='Show current database status'
    )
    parser.add_argument(
        '--strategies',
        action='store_true',
        help='Clear optimization runs and results (keeps strategies and views)'
    )
    parser.add_argument(
        '--display',
        choices=['leaderboard', 'parameters', 'fees', 'daily'],
        help='Display data from database views'
    )
    parser.add_argument(
        '--no-confirm',
        action='store_true',
        help='Skip confirmation prompt (use with caution)'
    )

    args = parser.parse_args()

    # Default to status if no args
    if not any([args.status, args.strategies, args.display]):
        args.status = True

    try:
        if args.status:
            check_database_status()

        elif args.strategies:
            success = clear_strategy_data(confirm=not args.no_confirm)
            if success:
                check_database_status()

        elif args.display:
            if args.display == 'leaderboard':
                display_leaderboard()
            elif args.display == 'parameters':
                display_parameter_performance()
            elif args.display == 'fees':
                display_fee_analysis()
            elif args.display == 'daily':
                display_daily_summary()

    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
