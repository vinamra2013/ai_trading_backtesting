# AI Trading Backtesting Platform

Algorithmic trading system built on QuantConnect's LEAN engine with Interactive Brokers integration.

## Architecture

- **LEAN Engine**: QuantConnect's algorithmic trading engine
- **Interactive Brokers**: Broker connectivity (paper/live trading)
- **HDF5 Storage**: Efficient historical data management
- **Streamlit Dashboard**: Real-time monitoring and analytics
- **Docker**: Containerized deployment

## System Requirements

- Python 3.11+ (Installed: 3.12.3)
- Docker 20.10+ (Installed: 28.4.0)
- Docker Compose v2.0+ (Installed: v2.39.2)
- 4+ CPU cores (Available: 32)
- 16GB+ RAM (Available: 46GB)
- 100GB+ disk space (Available: 1.6TB)

✅ All requirements met!

## Quick Start

### 1. Setup Environment

```bash
# Clone repository (if not already done)
git clone <your-repo>
cd ai_trading_backtesting

# Copy environment template
cp .env.example .env

# Edit with your IB credentials
nano .env
```

### 2. Get Interactive Brokers Credentials

You need an Interactive Brokers account (paper or live):

1. **Sign up**: https://www.interactivebrokers.com/
2. **Get credentials**:
   - Login to Client Portal: https://www.interactivebrokers.com/portal
   - Go to: Settings → User Settings → Security
   - Note your username and password
3. **Enable API access**:
   - Go to: Settings → API → Settings
   - Enable "Enable ActiveX and Socket Clients"
   - Set "Read-Only API" to "No"
4. **Add to `.env` file**:
   ```
   IB_USERNAME=your_username
   IB_PASSWORD=your_password
   IB_TRADING_MODE=paper
   ```

### 3. Start Platform

```bash
# Start all services
./scripts/start.sh

# View logs
docker compose logs -f

# Stop platform
./scripts/stop.sh
```

## Access Points

- **Streamlit Dashboard**: http://localhost:8501
- **IB Gateway VNC**: vnc://localhost:5900 (for visual debugging)
- **IB Gateway API**:
  - Paper Trading: localhost:4001
  - Live Trading: localhost:4002

## Project Structure

```
ai_trading_backtesting/
├── algorithms/          # Trading strategies (Python)
├── config/             # LEAN configuration files
├── data/               # Historical data storage
│   ├── raw/           # Downloaded market data
│   ├── processed/     # Cleaned/transformed data
│   ├── lean/          # LEAN-formatted data
│   └── sqlite/        # Trade history database
├── results/            # Backtest outputs
│   ├── backtests/     # Individual backtest results
│   └── optimization/  # Parameter optimization results
├── scripts/            # Utility scripts
├── monitoring/         # Streamlit dashboard
│   ├── static/        # Static assets
│   └── templates/     # Dashboard templates
├── tests/              # Test suite
│   ├── unit/          # Unit tests
│   └── integration/   # Integration tests
├── docs/               # Documentation
├── Dockerfile          # LEAN engine container
├── Dockerfile.monitoring  # Streamlit container
├── docker-compose.yml  # Service orchestration
└── .env               # Environment variables (gitignored)
```

## Docker Services

### lean
Main LEAN trading engine
- Port: Internal only
- Volumes: algorithms/, config/, data/, results/

### ib-gateway
Interactive Brokers Gateway (headless)
- Image: `ghcr.io/unusualcode/ib-gateway:latest`
- Ports: 4001 (paper), 4002 (live), 5900 (VNC)
- Health checks: Every 30s

### sqlite
Trade history database
- Volume: data/sqlite/

### monitoring
Streamlit dashboard
- Port: 8501
- Read-only access to data/, results/, logs/

## Development Workflow

### 1. Create Strategy

```bash
# Create new algorithm
mkdir -p algorithms/my_strategy
touch algorithms/my_strategy/main.py
```

### 2. Backtest

```bash
# Run backtest via LEAN CLI (in virtual environment)
source venv/bin/activate
lean backtest algorithms/my_strategy
```

### 3. Live Trade (Paper)

```bash
# Deploy to IB Gateway (paper trading)
lean live deploy algorithms/my_strategy
```

## LEAN CLI Commands

```bash
# Activate virtual environment first
source venv/bin/activate

# Initialize LEAN project
lean init

# Create new algorithm
lean create-python-algorithm my_algorithm

# Run backtest
lean backtest algorithms/my_algorithm

# Optimize parameters
lean optimize algorithms/my_algorithm

# Live deploy
lean live deploy algorithms/my_algorithm

# View documentation
lean --help
```

## Monitoring & Logs

```bash
# View all logs
docker compose logs -f

# View specific service
docker compose logs -f lean
docker compose logs -f ib-gateway

# Check service status
docker compose ps

# Restart service
docker compose restart lean
```

## Troubleshooting

### IB Gateway Connection Issues

1. **Check credentials in `.env`**
   ```bash
   cat .env | grep IB_
   ```

2. **Verify IB Gateway is running**
   ```bash
   docker compose ps ib-gateway
   ```

3. **Check IB Gateway logs**
   ```bash
   docker compose logs ib-gateway
   ```

4. **Test connection via VNC**
   - Connect to vnc://localhost:5900
   - Password: From `VNC_PASSWORD` in `.env`

### Docker Issues

```bash
# Rebuild containers
docker compose down
docker compose build --no-cache
docker compose up -d

# Remove all data and start fresh
docker compose down -v
./scripts/start.sh
```

### LEAN CLI Issues

```bash
# Reinstall LEAN CLI
source venv/bin/activate
pip uninstall lean
pip install lean

# Verify installation
lean --version
```

## Security Notes

- ⚠️ **Never commit `.env` file** (contains credentials)
- ✅ Always use `.env.example` as template
- ✅ Start with paper trading (`IB_TRADING_MODE=paper`)
- ✅ Test thoroughly before live trading
- ✅ Set up risk management limits (Epic 6)

## Next Steps

1. ✅ **Epic 1**: Development Environment Setup (Current)
2. **Epic 2**: Interactive Brokers Integration
3. **Epic 3**: Data Management Pipeline
4. **Epic 4**: Backtesting Infrastructure
5. **Epic 5**: Live Trading Engine
6. **Epic 6**: Risk Management System
7. **Epic 7**: Monitoring & Observability
8. **Epic 8**: Deployment & Operations
9. **Epic 9**: AI Integration Layer
10. **Epic 10**: Testing & Quality

## Resources

- LEAN Documentation: https://www.quantconnect.com/docs/
- Interactive Brokers API: https://interactivebrokers.github.io/
- IB Gateway Docker: https://github.com/unusualcode/ib-gateway-docker
- Project Stories: [stories/](stories/)

## Support

- Issues: See [stories/](stories/) for tracked work
- Documentation: See [docs/](docs/)

---

**Status**: Development Environment Setup Complete ✅
