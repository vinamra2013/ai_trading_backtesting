# AGENTS.md - Agent Guidelines for AI Trading Platform

## Environment Setup
**CRITICAL**: Always activate venv: `source venv/bin/activate.fish`
- Install dependencies: `source venv/bin/activate.fish && pip install -r requirements.txt`

## Docker Operations
- Start platform: `./scripts/start.sh`
- Stop platform: `./scripts/stop.sh`
- Run script in container: `docker exec backtrader-engine python /app/scripts/<script>.py`
- View logs: `docker compose logs backtrader` (NEVER use -f flag)
- Access container shell: `docker exec -it backtrader-engine /bin/bash`

## Backtesting
- Single backtest: `python scripts/run_backtest.py --strategy strategies.sma_crossover.SMACrossover --symbols SPY --start 2020-01-01 --end 2024-12-31`
- Parallel backtest: `docker exec backtrader-engine python /app/scripts/parallel_backtest.py --symbols SPY AAPL MSFT --strategies /app/strategies/sma_crossover.py --start 2020-01-01 --end 2024-12-31 --show-progress`

## Data Management
- Download data: `python scripts/download_data.py --symbols SPY AAPL --start 2020-01-01 --end 2024-12-31 --validate`
- Data validation: `python scripts/data_quality_check.py`
- Symbol discovery: `python scripts/symbol_discovery.py --scanner high_volume --output csv`
- Discovery stats: `python scripts/symbol_discovery.py --stats`

## Optimization & Analysis
- Parameter optimization: `docker exec backtrader-engine python /app/scripts/optimize_strategy.py --strategy strategies/sma_crossover.py --symbols SPY --start 2020-01-01 --end 2024-12-31 --metric sharpe_ratio --n-trials 100`
- Walk-forward analysis: `docker exec backtrader-engine python /app/scripts/walk_forward_analyzer_enhanced.py --strategy strategies/sma_crossover.py --symbols SPY --start 2020-01-01 --end 2024-12-31 --window-size 12 --step-size 3`

## Strategy Ranking & Portfolio
- Save backtest results: `docker exec backtrader-engine python /app/scripts/save_backtest_results.py --input results/parallel_backtests.csv --output results/backtests/ --verbose`
- Rank strategies: `docker exec backtrader-engine python /app/scripts/strategy_ranker.py --results-dir results/backtests/ --output rankings.csv --verbose`
- Portfolio optimization: `docker exec backtrader-engine python /app/scripts/portfolio_optimizer.py --strategies rankings.csv --output portfolio_allocation.csv --method equal_weight --verbose`
- Portfolio analytics: `docker exec backtrader-engine python /app/scripts/portfolio_analytics.py --allocations portfolio_allocation.csv --output portfolio_report.md --export portfolio_analytics.json --verbose`

## Live Trading
- Start live trading: `./scripts/start_live_trading.sh`
- Stop live trading: `./scripts/stop_live_trading.sh`
- Emergency stop: `./scripts/emergency_stop.sh`

## Testing & Validation
- IB connection test: `python scripts/ib_connection.py`
- Health endpoint: `python scripts/health_endpoint.py`
- MLflow logging: Add `--mlflow` flag to backtest commands

## Monitoring
- Dashboard: http://localhost:8501
- MLflow UI: http://localhost:5000 (after starting platform)

## Code Style Guidelines
**Python 3.12+**, strict type hints mandatory. Follow PEP 8. Imports alphabetical: stdlib → third-party → local. Classes PascalCase, functions snake_case, constants UPPER_SNAKE_CASE. Mandatory type hints. File headers with Epic references. Inherit from BaseStrategy for trading strategies. Never commit .env files.