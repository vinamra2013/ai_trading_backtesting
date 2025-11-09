# AGENTS.md - Agent Guidelines for AI Trading Platform

## Environment Setup
**CRITICAL**: Always activate venv: `source venv/bin/activate.fish`
- Install dependencies: `source venv/bin/activate.fish && pip install -r requirements.txt`

## Epic 25: FastAPI Backend Integration (COMPLETED)
- **Backend API**: FastAPI service running on http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Streamlit Dashboard**: Now API-first with real-time backend integration
- **Analytics Endpoint**: GET /api/analytics/portfolio for portfolio rankings
- **Job Submission**: Submit backtests and optimizations via API
- **Real-time Status**: Polling for job status updates

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
- Symbol discovery: `python scripts/symbol_discovery.py --scanner high_volume --output csv`
- Discovery stats: `python scripts/symbol_discovery.py --stats`

## Optimization & Analysis
- Parameter optimization: `POST /api/optimization/run` with JSON payload containing strategy, parameter space, symbols, and optimization settings
- Walk-forward analysis: Available through optimization endpoints with walk-forward configuration

## Strategy Ranking & Portfolio
- Strategy ranking: `GET /api/analytics/portfolio` returns ranked strategies with performance metrics
- Portfolio optimization: Results available through analytics endpoints with allocation recommendations
- Portfolio analytics: `GET /api/analytics/portfolio` provides comprehensive portfolio statistics and strategy rankings

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