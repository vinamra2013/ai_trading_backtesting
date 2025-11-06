# AGENTS.md - Agent Guidelines for AI Trading Platform

## Build/Lint/Test Commands

**CRITICAL**: This project uses a Python virtual environment. ALWAYS activate it before running Python commands:

**Environment Setup**:
- Activate venv: `source venv/bin/activate.fish`
- Install dependencies: `source venv/bin/activate.fish && pip install -r requirements.txt`

**Testing**: No formal test framework - use manual validation via dedicated scripts:
- **Single backtest**: `source venv/bin/activate.fish && python scripts/run_backtest.py --strategy strategies.sma_crossover.SMACrossover --start 2020-01-01 --end 2024-12-31 --symbols SPY`
- **Data validation**: `source venv/bin/activate.fish && python scripts/data_quality_check.py`
- **Health checks**: `source venv/bin/activate.fish && python scripts/health_endpoint.py`
- **IB connection test**: `source venv/bin/activate.fish && python scripts/ib_connection.py`
- **Download data**: `source venv/bin/activate.fish && python scripts/download_data.py --symbols SPY --start 2024-01-01 --end 2024-12-31`
- **Symbol discovery**: `source venv/bin/activate.fish && python scripts/symbol_discovery.py --scanner high_volume --output csv`
- **Discovery stats**: `source venv/bin/activate.fish && python scripts/symbol_discovery.py --stats`
- **Parameter optimization**: `source venv/bin/activate.fish && python scripts/optimize_strategy.py --strategy strategies.sma_crossover.SMACrossover --symbols SPY --start 2020-01-01 --end 2024-12-31 --metric sharpe_ratio --n-trials 50`
- **Walk-forward analysis**: `source venv/bin/activate.fish && python scripts/walkforward.py --strategy strategies.sma_crossover.SMACrossover --symbols SPY --start 2020-01-01 --end 2024-12-31`

**Docker Development**:
- **Run scripts in container**: `docker exec backtrader-engine python /app/scripts/<script_name>.py`
- **Access container shell**: `docker exec -it backtrader-engine /bin/bash`
- **View logs**: `docker compose logs backtrader` (NEVER use -f flag)
- **Check container health**: `docker compose ps`

**Build/Deploy**:
- **Start full platform**: `./scripts/start.sh`
- **Start live trading**: `./scripts/start_live_trading.sh`
- **Stop platform**: `./scripts/stop.sh`
- **Emergency stop**: `./scripts/emergency_stop.sh`
- **Backup data**: `./scripts/backup.sh`
- **Restore from backup**: `./scripts/restore.sh`

**Linting/Formatting**: No formal linters configured - follow PEP 8 manually

## Code Style Guidelines

**Python Version**: Python 3.12+ required, strict type hints mandatory

### Import Organization
```python
# Standard library imports (alphabetical)
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Type

# Third-party imports (alphabetical)
import backtrader as bt
import pandas as pd
import yaml

# Local imports (alphabetical, relative imports)
from scripts.cerebro_engine import CerebroEngine
from strategies.base_strategy import BaseStrategy
```

### Naming Conventions
- **Classes**: PascalCase (`BaseStrategy`, `RiskManager`, `IBConnectionManager`)
- **Functions/Methods**: snake_case (`calculate_position_size`, `get_portfolio_value`)
- **Variables**: snake_case (`initial_cash`, `position_size`, `order_history`)
- **Constants**: UPPER_SNAKE_CASE (`DEFAULT_CASH = 100000`, `MAX_DRAWDOWN = 0.2`)
- **Private members**: Leading underscore (`_validate_inputs`, `__init__`)

### Type Hints (MANDATORY)
```python
from typing import Dict, List, Optional, Type, Union

def calculate_position_size(self, price: float, pct_portfolio: Optional[float] = None) -> int:
    """Calculate position size with comprehensive type hints."""

def get_portfolio_value(self) -> float:
    """Get current portfolio value."""

def validate_config(self, config: Dict[str, Union[str, int, float]]) -> bool:
    """Validate configuration dictionary."""
```

### Error Handling
```python
import logging
logger = logging.getLogger(__name__)

try:
    # Risky operation
    result = self.ib_connection.get_positions()
except ConnectionError as e:
    logger.error(f"IB connection failed: {e}")
    raise
except ValueError as e:
    logger.warning(f"Invalid input: {e}")
    return None  # Explicit None return for optional types
```

### File Headers (MANDATORY)
```python
#!/usr/bin/env python3
"""
Module Description
Epic XX: US-XX.X - Story Title

Detailed description of module purpose and functionality.
"""

# Imports follow immediately after docstring
```

### Logging Standards
```python
# Module-level logger
logger = logging.getLogger(__name__)

# Appropriate log levels with context
logger.info(f"Strategy {self.__class__.__name__} initialized")
logger.warning(f"Order {order.ref} failed: {error_msg}")
logger.error(f"Critical error in {method_name}: {e}")
logger.debug(f"Portfolio value: ${value:,.2f}")
```

### Class Structure
```python
class MyStrategy(BaseStrategy):
    """
    Strategy description with comprehensive docstring.
    """

    params = (
        ('param1', 20),  # Parameter with default value
        ('param2', True),  # Boolean parameter
    )

    def __init__(self) -> None:
        """Initialize strategy with indicators and state."""
        super().__init__()

        # Initialize indicators
        self.sma = bt.indicators.SMA(self.data.close, period=self.params.param1)

        # Initialize state variables
        self.order_history: List[Dict[str, Union[str, float]]] = []
        self.bar_count = 0

        logger.info(f"{self.__class__.__name__} initialized")

    def next(self) -> None:
        """Main strategy logic - called for each bar."""
        self.bar_count += 1

        # Strategy implementation
        pass
```

### Strategy Development
- **Base Class**: Always inherit from `BaseStrategy` for risk management
- **Order Methods**: Use `self.buy()`, `self.sell()`, `self.close()` (Backtrader native)
- **Position Tracking**: Use `self.position`, `self.getposition(data)`
- **Portfolio Access**: Use `self.broker.getvalue()`, `self.broker.getcash()`
- **Risk Management**: Implement via `BaseStrategy` parameters and overrides

### Configuration Management
- **Application Config**: YAML files in `config/` directory
- **Secrets**: `.env` file (gitignored) for IB credentials
- **Docker Secrets**: Mount sensitive files as Docker secrets
- **Validation**: Always validate configuration inputs

### Security Practices
- **Never commit credentials**: `.env` is gitignored
- **Input validation**: Validate all external inputs
- **Error messages**: Don't expose sensitive information in errors
- **Paper trading first**: Test all strategies in paper mode before live
- **Risk limits**: Always implement position and loss limits

### Database Operations
- **Connection handling**: Use context managers for database connections
- **Error recovery**: Implement retry logic for transient failures
- **Logging**: Log all database operations for audit trails
- **Transactions**: Use transactions for multi-step operations

### Performance Considerations
- **Memory management**: Be mindful of large datasets
- **Caching**: Cache expensive computations when possible
- **Async operations**: Use async patterns for I/O operations
- **Profiling**: Profile performance-critical sections