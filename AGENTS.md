# AGENTS.md - Agent Guidelines for AI Trading Platform

## Build/Lint/Test Commands

**Environment**: Always activate venv first: `source venv/bin/activate`

**Testing**: No formal test framework - use manual validation:
- Single backtest: `python scripts/run_backtest.py --algorithm <path> --start YYYY-MM-DD --end YYYY-MM-DD`
- Data validation: `python scripts/data_quality_check.py`
- Health checks: `python scripts/health_endpoint.py`

**Build/Deploy**:
- Start platform: `./scripts/start.sh`
- Live trading: `./scripts/start_live_trading.sh`
- Stop: `./scripts/stop.sh`

## Code Style Guidelines

**Python**: Python 3.12+, strict type hints required, follow PEP 8
- Imports: Standard library first, then third-party, then local
- Classes: PascalCase, functions/variables: snake_case, Constants: UPPER_SNAKE_CASE
- Error handling: Use try/except with logging, handle None types explicitly
- File headers: Include epic/story references and purpose
- Type safety: Optional[T] for nullable parameters, never assign None to non-optional

**Docker**: Use official images, health checks required, no -f flag with logs
**Config**: YAML in config/, .env for secrets (gitignored)
**Security**: Never commit credentials, use Docker secrets for IB passwords