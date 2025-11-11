#!/bin/bash
# Stop the AI Trading Backtesting Platform
# Usage: ./scripts/stop.sh

set -e

echo "🛑 Stopping AI Trading Backtesting Platform..."

# Stop all containers
docker compose down

echo "✅ Platform stopped successfully!"
echo ""
echo "💡 To start again: ./scripts/start.sh"
echo "💡 To remove all data: docker compose down -v"
echo ""
