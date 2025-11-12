#!/bin/bash
# Database Management Script (Bash version)
# Safe operations for trading backtesting database
#
# Usage:
#   ./scripts/reset_db.sh status              # Check database status
#   ./scripts/reset_db.sh strategies          # Clear optimization data
#   ./scripts/reset_db.sh leaderboard         # Show top performing strategies
#   ./scripts/reset_db.sh parameters          # Show parameter performance
#   ./scripts/reset_db.sh fees                # Show fee analysis
#   ./scripts/reset_db.sh daily               # Show daily summary
#
# SAFE: Views and strategy definitions are ALWAYS preserved

set -e

# Load environment variables
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Database settings (with defaults)
DB_NAME=${POSTGRES_DB:-trading}
DB_USER=${POSTGRES_USER:-mlflow}
DB_PASSWORD=${POSTGRES_PASSWORD:-}
DB_HOST=${POSTGRES_HOST:-localhost}
DB_PORT=${POSTGRES_PORT:-5432}

# Build psql command
PSQL_CMD="psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"

# Check if database is accessible
check_connection() {
    if ! $PSQL_CMD -c "SELECT 1" > /dev/null 2>&1; then
        echo "❌ Cannot connect to PostgreSQL"
        echo "   Host: $DB_HOST:$DB_PORT"
        echo "   Database: $DB_NAME"
        echo "   User: $DB_USER"
        echo ""
        echo "Check that PostgreSQL is running:"
        echo "   docker ps | grep postgres"
        exit 1
    fi
}

# Show database status
show_status() {
    echo ""
    echo "📊 DATABASE STATUS"
    echo "=================================================="

    STRATEGIES=$($PSQL_CMD -t -c "SELECT COUNT(*) FROM strategies;" 2>/dev/null || echo "0")
    RUNS=$($PSQL_CMD -t -c "SELECT COUNT(*) FROM optimization_runs;" 2>/dev/null || echo "0")
    RESULTS=$($PSQL_CMD -t -c "SELECT COUNT(*) FROM backtest_results;" 2>/dev/null || echo "0")

    TOTAL=$((STRATEGIES + RUNS + RESULTS))

    [ "$STRATEGIES" -gt 0 ] && S="✅" || S="⚫"
    [ "$RUNS" -gt 0 ] && R="✅" || R="⚫"
    [ "$RESULTS" -gt 0 ] && T="✅" || T="⚫"

    echo "$S strategies..................... $STRATEGIES rows"
    echo "$R optimization_runs............. $RUNS rows"
    echo "$T backtest_results.............. $RESULTS rows"
    echo "=================================================="
    echo "📈 Total data rows: $TOTAL"
    echo "✅ Database views: PRESERVED"
    echo "📍 Database: $DB_NAME @ $DB_HOST:$DB_PORT"
    echo "👤 User: $DB_USER"
    echo ""
}

# Clear optimization data only (SAFE)
clear_strategies() {
    check_connection
    show_status

    if [ "$FORCE" != "1" ]; then
        echo "⚠️  This will DELETE all optimization runs and backtest results"
        echo "but KEEP strategy definitions and PRESERVE all views."
        read -p "Are you sure? Type 'yes' to confirm: " response
        if [ "$response" != "yes" ]; then
            echo "❌ Cancelled"
            exit 0
        fi
    fi

    echo ""
    echo "🧹 Clearing optimization and backtest data..."

    $PSQL_CMD << EOF
TRUNCATE TABLE backtest_results CASCADE;
TRUNCATE TABLE optimization_runs CASCADE;
UPDATE strategies SET status = 'testing', updated_at = NOW();
EOF

    echo "   ✓ Cleared backtest_results"
    echo "   ✓ Cleared optimization_runs"
    echo "   ✓ Reset strategies to 'testing' status"

    echo ""
    echo "✅ Optimization data cleared successfully!"
    echo "   ✓ Strategy definitions PRESERVED"
    echo "   ✓ Database views PRESERVED"
    echo "   ✓ Schema PRESERVED"
    show_status
}

# Display strategy leaderboard
show_leaderboard() {
    check_connection
    echo ""
    echo "🏆 STRATEGY LEADERBOARD (Top Performers)"
    echo "=================================================="
    echo ""

    $PSQL_CMD -c "
    SELECT
        rank,
        strategy_name,
        category,
        ROUND(sharpe_ratio::numeric, 3) as sharpe,
        ROUND(total_return::numeric, 4) as ret_pct,
        ROUND(annual_return::numeric, 4) as annual_ret,
        ROUND(max_drawdown::numeric, 4) as max_dd,
        total_trades,
        ROUND(win_rate::numeric, 2) as wr_pct,
        ROUND(avg_win::numeric, 4) as avg_win,
        total_fees::numeric(10,2) as fees
    FROM strategy_leaderboard
    LIMIT 20
    " || echo "⚫ No leaderboard data available yet"
    echo ""
}

# Display parameter performance
show_parameters() {
    check_connection
    echo ""
    echo "📊 PARAMETER PERFORMANCE ANALYSIS"
    echo "=================================================="
    echo ""

    $PSQL_CMD -c "
    SELECT
        strategy_name,
        parameter_name,
        parameter_value,
        ROUND(avg_sharpe::numeric, 3) as avg_sharpe,
        ROUND(avg_return::numeric, 4) as avg_ret,
        ROUND(avg_drawdown::numeric, 4) as avg_dd,
        ROUND(avg_win_rate::numeric, 2) as avg_wr,
        test_count
    FROM parameter_performance
    ORDER BY strategy_name, avg_sharpe DESC
    LIMIT 30
    " || echo "⚫ No parameter data available yet"
    echo ""
}

# Display fee analysis
show_fees() {
    check_connection
    echo ""
    echo "💰 FEE ANALYSIS"
    echo "=================================================="
    echo ""

    $PSQL_CMD -c "
    SELECT
        strategy_name,
        ROUND(avg_fees::numeric, 2) as avg_fees,
        ROUND(avg_fee_pct_of_capital::numeric, 2) as fee_pct,
        ROUND(avg_trades::numeric, 1) as avg_trades,
        ROUND(avg_fee_per_trade::numeric, 4) as fee_per_trade,
        backtest_count
    FROM fee_analysis
    ORDER BY fee_pct_of_capital DESC
    " || echo "⚫ No fee data available yet"
    echo ""
    echo "📌 CRITICAL: Fees > 25% of \$1K capital = \$250 (unsustainable)"
    echo ""
}

# Display daily summary
show_daily() {
    check_connection
    echo ""
    echo "📅 DAILY BACKTESTING SUMMARY"
    echo "=================================================="
    echo ""

    $PSQL_CMD -c "
    SELECT
        date,
        total_backtests,
        passed,
        ROUND(best_sharpe::numeric, 3) as best_sharpe,
        ROUND(avg_sharpe::numeric, 3) as avg_sharpe,
        strategies_tested
    FROM daily_summary
    LIMIT 30
    " || echo "⚫ No daily summary data available yet"
    echo ""
}

# Main
COMMAND=${1:-status}
FORCE=${2}

[ "$FORCE" == "--force" ] && FORCE=1 || FORCE=0

case $COMMAND in
    status)
        check_connection
        show_status
        ;;
    strategies)
        clear_strategies
        ;;
    leaderboard)
        show_leaderboard
        ;;
    parameters)
        show_parameters
        ;;
    fees)
        show_fees
        ;;
    daily)
        show_daily
        ;;
    *)
        echo "Database Management Utility"
        echo ""
        echo "SAFE OPERATIONS (Views and Strategy Definitions Always Preserved)"
        echo ""
        echo "Usage: $0 [command] [--force]"
        echo ""
        echo "Commands:"
        echo "  status          - Show database status (default)"
        echo "  strategies      - Clear optimization data (keep strategies & views)"
        echo "  leaderboard     - Show top performing strategies from view"
        echo "  parameters      - Show parameter performance analysis from view"
        echo "  fees            - Show fee analysis from view"
        echo "  daily           - Show daily backtesting summary from view"
        echo ""
        echo "Examples:"
        echo "  ./scripts/reset_db.sh status"
        echo "  ./scripts/reset_db.sh strategies"
        echo "  ./scripts/reset_db.sh strategies --force    # No confirmation"
        echo "  ./scripts/reset_db.sh leaderboard"
        echo "  ./scripts/reset_db.sh fees"
        echo ""
        exit 1
        ;;
esac
