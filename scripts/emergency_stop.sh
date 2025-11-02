#!/bin/bash
# Emergency Stop and Liquidation for LEAN Live Trading
# Usage: ./scripts/emergency_stop.sh [algorithm_path]
# Example: ./scripts/emergency_stop.sh algorithms/live_strategy
#
# US-6.4: Emergency stop functionality with position liquidation

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$PROJECT_ROOT/logs/emergency_stop.log"
TRADE_DB="$PROJECT_ROOT/data/sqlite/trades.db"
ENV_FILE="$PROJECT_ROOT/.env"
VENV_PATH="$PROJECT_ROOT/venv"

# Ensure directories exist
mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$PROJECT_ROOT/data/sqlite"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Critical alert function
critical_alert() {
    log "🚨 CRITICAL: $1"
}

critical_alert "========================================="
critical_alert "EMERGENCY STOP INITIATED"
critical_alert "========================================="

# Load environment variables
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# Get algorithm path
ALGORITHM_PATH="${1:-$ALGORITHM_PATH}"
if [ -z "$ALGORITHM_PATH" ]; then
    ALGORITHM_PATH="algorithms/live_strategy"
    log "Using default algorithm path: $ALGORITHM_PATH"
fi

# Activate virtual environment
if [ ! -d "$VENV_PATH" ]; then
    critical_alert "Virtual environment not found at $VENV_PATH"
    critical_alert "Attempting to proceed without venv activation..."
fi

if [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
    log "Virtual environment activated"
fi

# Check if LEAN CLI is available
if ! command -v lean &> /dev/null; then
    critical_alert "LEAN CLI not found - cannot execute automated liquidation"
    critical_alert "Manual intervention required immediately"
    exit 1
fi

# Check if database exists
if [ ! -f "$TRADE_DB" ]; then
    log "⚠️  WARNING: Trade database not found at $TRADE_DB"
    log "Skipping position query, attempting direct stop..."
    HAS_DATABASE=false
else
    HAS_DATABASE=true
fi

# Step 1: Query database for open positions
if [ "$HAS_DATABASE" = true ]; then
    log "Step 1: Querying database for open positions..."

    # Query positions table for open positions
    OPEN_POSITIONS=$(sqlite3 "$TRADE_DB" \
        "SELECT symbol, quantity FROM positions WHERE status = 'open' AND quantity != 0;" \
        2>/dev/null || echo "")

    if [ -z "$OPEN_POSITIONS" ]; then
        log "No open positions found in database"
    else
        log "Found open positions:"
        echo "$OPEN_POSITIONS" | while IFS='|' read -r symbol quantity; do
            log "  - $symbol: $quantity shares"
        done
    fi
else
    OPEN_POSITIONS=""
fi

# Step 2: Liquidate all open positions
cd "$PROJECT_ROOT"

if [ -n "$OPEN_POSITIONS" ]; then
    log "Step 2: Liquidating all open positions..."

    LIQUIDATION_COUNT=0
    LIQUIDATION_FAILED=0

    echo "$OPEN_POSITIONS" | while IFS='|' read -r symbol quantity; do
        log "Liquidating $symbol ($quantity shares)..."

        if lean live liquidate "$symbol" --algorithm "$ALGORITHM_PATH" 2>&1 | tee -a "$LOG_FILE"; then
            log "✅ Successfully liquidated $symbol"
            ((LIQUIDATION_COUNT++))
        else
            critical_alert "Failed to liquidate $symbol (exit code: $?)"
            ((LIQUIDATION_FAILED++))
        fi
    done

    if [ $LIQUIDATION_FAILED -gt 0 ]; then
        critical_alert "$LIQUIDATION_FAILED position(s) failed to liquidate"
        critical_alert "Manual intervention required"
    else
        log "✅ All positions liquidated successfully ($LIQUIDATION_COUNT)"
    fi
else
    log "Step 2: No positions to liquidate"
fi

# Step 3: Stop live trading
log "Step 3: Stopping live trading algorithm..."

if lean live stop "$ALGORITHM_PATH" 2>&1 | tee -a "$LOG_FILE"; then
    log "✅ Live trading stopped successfully"
else
    critical_alert "Failed to stop live trading (exit code: $?)"
    critical_alert "Algorithm may still be running - manual intervention required"
fi

# Step 4: Log emergency stop to database
if [ "$HAS_DATABASE" = true ]; then
    log "Step 4: Logging emergency stop to database..."

    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

    sqlite3 "$TRADE_DB" <<EOF
INSERT INTO emergency_stops (timestamp, algorithm, reason, open_positions, status)
VALUES (
    '$TIMESTAMP',
    '$ALGORITHM_PATH',
    'Manual emergency stop triggered',
    COALESCE((SELECT COUNT(*) FROM positions WHERE status = 'open' AND quantity != 0), 0),
    'completed'
);
EOF

    if [ $? -eq 0 ]; then
        log "✅ Emergency stop logged to database"
    else
        critical_alert "Failed to log emergency stop to database"
    fi
else
    log "Step 4: Database not available - skipping emergency stop logging"
fi

# Step 5: Send critical alert
log "Step 5: Generating critical alert..."

ALERT_MESSAGE="EMERGENCY STOP COMPLETED
Algorithm: $ALGORITHM_PATH
Timestamp: $(date '+%Y-%m-%d %H:%M:%S')
Positions Liquidated: ${LIQUIDATION_COUNT:-0}
Liquidation Failures: ${LIQUIDATION_FAILED:-0}

Check logs for details: $LOG_FILE

Action required: Review positions and system state before restarting trading"

critical_alert "$ALERT_MESSAGE"

# Write alert to separate file for monitoring systems
ALERT_FILE="$PROJECT_ROOT/logs/CRITICAL_ALERT_$(date '+%Y%m%d_%H%M%S').txt"
echo "$ALERT_MESSAGE" > "$ALERT_FILE"
log "Critical alert written to: $ALERT_FILE"

critical_alert "========================================="
critical_alert "EMERGENCY STOP PROCEDURE COMPLETED"
critical_alert "========================================="

# Return appropriate exit code
if [ "${LIQUIDATION_FAILED:-0}" -gt 0 ]; then
    critical_alert "Exit code 1: Some liquidations failed"
    exit 1
else
    log "Exit code 0: Emergency stop completed successfully"
    exit 0
fi
