#!/bin/bash
# Stop LEAN Live Trading Gracefully
# Usage: ./scripts/stop_live_trading.sh [algorithm_path]
# Example: ./scripts/stop_live_trading.sh algorithms/live_strategy

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$PROJECT_ROOT/logs/live_trading.log"
ENV_FILE="$PROJECT_ROOT/.env"
VENV_PATH="$PROJECT_ROOT/venv"

# Ensure log directory exists
mkdir -p "$PROJECT_ROOT/logs"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "========================================="
log "Stopping LEAN Live Trading"
log "========================================="

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
    log "❌ ERROR: Virtual environment not found at $VENV_PATH"
    exit 1
fi

source "$VENV_PATH/bin/activate"

# Execute LEAN live stop
log "Stopping live trading for: $ALGORITHM_PATH"
cd "$PROJECT_ROOT"

if lean live stop "$ALGORITHM_PATH"; then
    log "✅ Live trading stopped successfully"
    log "Final status logged at: $(date '+%Y-%m-%d %H:%M:%S')"
    exit 0
else
    log "❌ ERROR: Failed to stop live trading (exit code: $?)"
    log "Manual intervention may be required"
    exit 1
fi
