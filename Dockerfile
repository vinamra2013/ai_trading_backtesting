# Backtrader Trading Engine Dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Backtrader and core dependencies
RUN pip install --upgrade pip && \
    pip install \
    backtrader \
    ib_insync \
    pandas \
    numpy \
    matplotlib \
    scikit-learn \
    scikit-optimize \
    tables \
    h5py \
    pytz \
    pyyaml \
    requests

# Install additional packages for enhanced Backtrader functionality
RUN pip install \
    backtrader[plotting] \
    plotly \
    yfinance

# Install Epic 17: AI-Native Research Lab dependencies
RUN pip install \
    mlflow \
    psycopg2-binary \
    quantstats \
    ipython \
    scipy \
    kaleido \
    optuna \
    sqlalchemy

# Create required directories
RUN mkdir -p /app/algorithms \
    /app/strategies \
    /app/config \
    /app/data/csv \
    /app/data/processed \
    /app/data/sqlite \
    /app/data/cache \
    /app/results/backtests \
    /app/results/optimization \
    /app/logs \
    /app/scripts

# Copy project files
# Note: Ensure these directories exist before building (use ./scripts/start.sh)
COPY algorithms /app/algorithms/
COPY strategies /app/strategies/
COPY config /app/config/
COPY scripts /app/scripts/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV BACKTRADER_ENGINE_PATH=/app
ENV PYTHONPATH=/app:$PYTHONPATH

# Expose ports (if needed for future monitoring)
EXPOSE 8220

# Default command (keep container running)
CMD ["tail", "-f", "/dev/null"]
