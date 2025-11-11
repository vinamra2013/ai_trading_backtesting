#!/bin/bash
# Start LEAN Live Trading
# Usage: ./scripts/start_live_trading.sh [algorithm_path]
# Example: ./scripts/start_live_trading.sh algorithms/live_strategy

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
log "Starting LEAN Live Trading Deployment"
log "========================================="

# Pre-flight Check 1: .env file exists
if [ ! -f "$ENV_FILE" ]; then
    log "❌ ERROR: .env file not found at $ENV_FILE"
    log "Please create .env file with IB credentials"
    exit 1
fi
log "✅ .env file found"

# Load .env file
set -a
source "$ENV_FILE"
set +a

# Pre-flight Check 2: IB credentials validation
if [ -z "$IB_USERNAME" ] || [ "$IB_USERNAME" = "your_ib_username" ]; then
    log "❌ ERROR: IB_USERNAME not configured in .env"
    exit 1
fi

if [ -z "$IB_PASSWORD" ] || [ "$IB_PASSWORD" = "your_ib_password" ]; then
    log "❌ ERROR: IB_PASSWORD not configured in .env"
    exit 1
fi

if [ -z "$IB_ACCOUNT" ]; then
    log "⚠️  WARNING: IB_ACCOUNT not set in .env, using IB_USERNAME"
    IB_ACCOUNT="$IB_USERNAME"
fi
log "✅ IB credentials validated"

# Pre-flight Check 3: Algorithm path
ALGORITHM_PATH="${1:-$ALGORITHM_PATH}"
if [ -z "$ALGORITHM_PATH" ]; then
    ALGORITHM_PATH="algorithms/live_strategy"
    log "⚠️  No algorithm path provided, using default: $ALGORITHM_PATH"
fi

if [ ! -d "$PROJECT_ROOT/$ALGORITHM_PATH" ]; then
    log "❌ ERROR: Algorithm directory not found: $PROJECT_ROOT/$ALGORITHM_PATH"
    exit 1
fi
log "✅ Algorithm directory validated: $ALGORITHM_PATH"

# Pre-flight Check 4: Required config files
REQUIRED_CONFIGS=(
    "config/live_trading_config.yaml"
    "config/risk_config.yaml"
)

for config in "${REQUIRED_CONFIGS[@]}"; do
    if [ ! -f "$PROJECT_ROOT/$config" ]; then
        log "❌ ERROR: Required config file not found: $config"
        exit 1
    fi
done
log "✅ Configuration files validated"

# Pre-flight Check 5: Virtual environment
if [ ! -d "$VENV_PATH" ]; then
    log "❌ ERROR: Virtual environment not found at $VENV_PATH"
    log "Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi
log "✅ Virtual environment found"

# Activate virtual environment
log "Activating virtual environment..."
source "$VENV_PATH/bin/activate"

# Pre-flight Check 6: LEAN CLI installed
if ! command -v lean &> /dev/null; then
    log "❌ ERROR: LEAN CLI not found in virtual environment"
    log "Please install: pip install lean"
    exit 1
fi
log "✅ LEAN CLI validated ($(lean --version))"

# Pre-flight Check 7: IB Gateway connectivity
IB_PORT="${IB_GATEWAY_PORT:-4001}"
if ! nc -z localhost "$IB_PORT" 2>/dev/null; then
    log "⚠️  WARNING: IB Gateway not responding on port $IB_PORT"
    log "Please ensure IB Gateway Docker container is running: docker compose ps"
    log "Proceeding anyway - LEAN will retry connection..."
fi

# Display deployment summary
log "========================================="
log "Deployment Configuration:"
log "  Algorithm: $ALGORITHM_PATH"
log "  IB Username: $IB_USERNAME"
log "  IB Account: $IB_ACCOUNT"
log "  Trading Mode: ${IB_TRADING_MODE:-paper}"
log "  IB Gateway Port: $IB_PORT"
log "========================================="

# Execute LEAN live deploy
log "Executing LEAN live deployment..."
cd "$PROJECT_ROOT"

if lean live deploy "$ALGORITHM_PATH" \
    --detach \
    --brokerage "InteractiveBrokersBrokerage" \
    --ib-user-name "$IB_USERNAME" \
    --ib-account "$IB_ACCOUNT" \
    --ib-password "$IB_PASSWORD"; then

    log "✅ Live trading started successfully"
    log "Algorithm: $ALGORITHM_PATH"
    log "Monitor logs: tail -f $LOG_FILE"
    log "Stop trading: ./scripts/stop_live_trading.sh"
    log "Emergency stop: ./scripts/emergency_stop.sh"
    exit 0
else
    log "❌ ERROR: Failed to start live trading (exit code: $?)"
    log "Check LEAN logs for details: lean live logs $ALGORITHM_PATH"
    exit 1
fi
