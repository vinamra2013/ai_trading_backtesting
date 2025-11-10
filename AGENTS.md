# AGENTS.md - Agent Guidelines for AI Trading Platform

## Environment Setup
**CRITICAL**: Always activate venv: `source venv/bin/activate.fish`
- Install dependencies: `source venv/bin/activate.fish && pip install -r requirements.txt`

## Epic 25: FastAPI Backend Integration (COMPLETED)
- **Backend API**: FastAPI service running on http://localhost:8230
- **API Documentation**: http://localhost:8230/docs
- **Streamlit Dashboard**: Now API-first with real-time backend integration
- **Analytics Endpoint**: GET /api/analytics/portfolio for portfolio rankings
- **Job Submission**: Submit backtests and optimizations via API
- **Real-time Status**: Polling for job status updates

## Epic 26: Quant Director API Integration (COMPLETED)
- **Symbol Discovery API**: POST /api/discovery/scan for automated symbol discovery
- **Strategy Ranking API**: POST /api/ranking/analyze for multi-criteria strategy ranking
- **Background Processing**: Redis queue with dedicated discovery and ranking workers
- **Job Status Tracking**: Real-time status monitoring for all background jobs
- **Database Integration**: PostgreSQL storage for discovery results and ranking data

## Docker Operations
- Start platform: `./scripts/start.sh`
- Stop platform: `./scripts/stop.sh`
- Run script in container: `docker exec backtrader-engine python /app/scripts/<script>.py`
- View logs: `docker compose logs backtrader` (NEVER use -f flag)
- Access container shell: `docker exec -it backtrader-engine /bin/bash`

## Backtesting
- Single backtest: `POST /api/backtests/run` with JSON payload containing strategy, symbols, parameters, and date range
- Parallel backtest: Submit multiple jobs via `POST /api/backtests/run` or use batch submission endpoints

## Data Management
- Download data: `python scripts/download_data.py --symbols SPY AAPL --start 2020-01-01 --end 2024-12-31 --validate`
- Data validation: `python scripts/data_quality_check.py`
- Symbol discovery: `POST /api/discovery/scan` with scanner parameters (high_volume, volatility_leaders, etc.)
- Discovery stats: `GET /api/discovery/jobs` for job history and `GET /api/discovery/results/{job_id}` for results

## Optimization & Analysis
- Parameter optimization: `POST /api/optimization/run` with JSON payload containing strategy, parameter space, symbols, and optimization settings
- Walk-forward analysis: Available through optimization endpoints with walk-forward configuration

## Strategy Ranking & Portfolio
- Strategy ranking: `POST /api/ranking/analyze` with input source and ranking criteria
- Ranking results: `GET /api/ranking/results/{job_id}` for detailed ranking analysis
- Portfolio analytics: `GET /api/analytics/portfolio` provides comprehensive portfolio statistics and strategy rankings
- Ranking job status: `GET /api/ranking/status/{job_id}` for real-time progress tracking

## Live Trading
- Start live trading: `./scripts/start_live_trading.sh`
- Stop live trading: `./scripts/stop_live_trading.sh`
- Emergency stop: `./scripts/emergency_stop.sh`

## Testing & Validation
- IB connection test: `python scripts/ib_connection.py`
- Health endpoint: `python scripts/health_endpoint.py`
- MLflow logging: Add `--mlflow` flag to backtest commands

## Monitoring
- Dashboard: http://localhost:8501 (now API-integrated)
- MLflow UI: http://localhost:5000 (after starting platform)
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Code Style Guidelines
**Python 3.12+**, strict type hints mandatory. Follow PEP 8. Imports alphabetical: stdlib → third-party → local. Classes PascalCase, functions snake_case, constants UPPER_SNAKE_CASE. Mandatory type hints. File headers with Epic references. Inherit from BaseStrategy for trading strategies. Never commit .env files.