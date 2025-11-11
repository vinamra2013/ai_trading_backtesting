
# AI Trading Backtesting Platform

## Project Overview

This project is an AI-powered algorithmic trading platform that uses QuantConnect's LEAN engine for backtesting and live trading with Interactive Brokers. The platform is containerized using Docker and includes a Streamlit-based web dashboard for monitoring and analysis.

The architecture consists of four main services:

*   **LEAN Engine (`lean`):** The core service that runs the trading algorithms.
*   **Interactive Brokers Gateway (`ib-gateway`):** Provides the connection to the Interactive Brokers API for live trading and data.
*   **SQLite Database (`sqlite`):** Stores trade history and other relevant data.
*   **Monitoring Dashboard (`monitoring`):** A Streamlit web application for real-time monitoring of the platform, including account status, positions, orders, and backtest results.

## Building and Running

The project is managed through Docker Compose and a set of shell scripts.

**Key commands:**

*   **Start the platform:**
    ```bash
    ./scripts/start.sh
    ```
*   **Stop the platform:**
    ```bash
    ./scripts/stop.sh
    ```
*   **View logs:**
    ```bash
    docker compose logs -f
    ```
*   **Run a backtest:**
    ```bash
    # Activate virtual environment
    source venv/bin/activate

    # Run backtest
    lean backtest algorithms/<your_strategy>
    ```
    Alternatively, you can use the provided Python script:
    ```bash
    python scripts/run_backtest.py --algorithm algorithms/<your_strategy> --start <start_date> --end <end_date>
    ```

## Development Conventions

*   **Trading Algorithms:** New trading algorithms should be created in the `algorithms/` directory. Each algorithm should have its own subdirectory.
*   **Configuration:** Configuration for the LEAN engine and other services is located in the `config/` directory.
*   **Data:** Historical data is stored in the `data/` directory, with separate subdirectories for raw, processed, and LEAN-formatted data.
*   **Backtest Results:** Backtest results are saved in the `results/backtests/` directory in JSON format.
*   **Monitoring:** The Streamlit dashboard can be extended by modifying the `monitoring/app.py` file and other files in the `monitoring/` directory.
*   **Scripts:** The `scripts/` directory contains various utility scripts for managing the platform, running backtests, and other tasks.
*   **Claude Skills:** The project includes Claude Skills for programmatic automation of data management and backtesting.
