# AGENTS.md - Agent Guidelines for AI Trading Platform

## Build/Lint/Test Commands

**Environment**: Always activate venv first: `source venv/bin/activate`

**Testing**: No formal test framework - use manual validation:
- Single backtest: `python scripts/run_backtest.py --strategy <path> --start YYYY-MM-DD --end YYYY-MM-DD --symbols SPY`
- Data validation: `python scripts/data_quality_check.py`
- Health checks: `python scripts/health_endpoint.py`
- IB connection test: `python scripts/ib_connection.py`
- Download data: `python scripts/download_data.py --symbols SPY --start 2024-01-01 --end 2024-12-31`

**Build/Deploy**:
- Start platform: `./scripts/start.sh`
- Live trading: `./scripts/start_live_trading.sh`
- Stop: `./scripts/stop.sh`
- Emergency stop: `./scripts/emergency_stop.sh`

**Docker**: NEVER use -f flag with docker logs, use official images with health checks

## Code Style Guidelines

**Python**: Python 3.12+, strict type hints required, follow PEP 8
- **Imports**: Standard library first, then third-party, then local (backtrader, ib_insync, etc.)
- **Classes**: PascalCase (BaseStrategy, RiskManager), functions/variables: snake_case, Constants: UPPER_SNAKE_CASE
- **Error handling**: Use try/except with logging, handle None types explicitly, never assign None to non-optional
- **File headers**: Include epic/story references and purpose (e.g., "Epic 12: US-12.4 - Backtest Execution Script")
- **Type safety**: Use Optional[T] for nullable parameters, comprehensive type hints for all functions
- **Logging**: Use logging module with appropriate levels, include context in messages

**Strategy Development**: Inherit from BaseStrategy for risk management, use self.buy()/sell()/close() for orders
**Config**: YAML in config/, .env for secrets (gitignored), Docker secrets for IB passwords
**Security**: Never commit credentials, validate all inputs, use paper trading for testing