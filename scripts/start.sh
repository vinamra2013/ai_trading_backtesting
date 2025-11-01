#!/bin/bash
# Start the AI Trading Backtesting Platform
# Usage: ./scripts/start.sh

set -e

echo "🚀 Starting AI Trading Backtesting Platform..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "📋 Creating .env from .env.example..."
    cp .env.example .env
    echo "✅ .env created. Please edit it with your IB credentials before proceeding."
    echo "   Edit: nano .env"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Create necessary directories if they don't exist
echo "📁 Creating directories..."
mkdir -p data/{raw,processed,lean,sqlite} \
         results/{backtests,optimization} \
         logs

# Build and start containers
echo "🔨 Building Docker images..."
docker compose build

echo "🚀 Starting containers..."
docker compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 5

# Check service status
echo "📊 Service Status:"
docker compose ps

echo ""
echo "✅ Platform started successfully!"
echo ""
echo "🔗 Access Points:"
echo "   - Streamlit Dashboard: http://localhost:8501"
echo "   - IB Gateway VNC: vnc://localhost:5900 (password from .env)"
echo "   - IB Gateway API: localhost:4001 (paper) / localhost:4002 (live)"
echo ""
echo "📋 Useful Commands:"
echo "   - View logs: docker compose logs -f"
echo "   - Stop platform: ./scripts/stop.sh"
echo "   - Restart: docker compose restart"
echo ""
