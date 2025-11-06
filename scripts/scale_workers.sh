#!/bin/bash
# Scale Backtest Workers
# Usage: ./scale_workers.sh <num_workers>

set -e

NUM_WORKERS=${1:-1}

echo "Scaling backtest workers to $NUM_WORKERS..."

# Update docker-compose.yml with new replica count
sed -i "s/replicas: [0-9]\+/replicas: $NUM_WORKERS/" docker-compose.yml

# Restart the service with new configuration
docker compose up -d backtest-worker --scale backtest-worker=$NUM_WORKERS

echo "✅ Scaled to $NUM_WORKERS workers"
echo "Monitor with: docker compose logs -f backtest-worker"