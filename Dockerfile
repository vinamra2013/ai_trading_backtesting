# LEAN Trading Engine Dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install LEAN CLI and dependencies
RUN pip install --upgrade pip && \
    pip install lean

# Install additional Python packages for trading
RUN pip install \
    pandas \
    numpy \
    matplotlib \
    scikit-learn \
    tables \
    h5py \
    pytz

# Create required directories
RUN mkdir -p /app/algorithms \
    /app/config \
    /app/data \
    /app/results \
    /app/logs

# Copy project files
COPY algorithms/ /app/algorithms/
COPY config/ /app/config/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LEAN_ENGINE_PATH=/app

# Expose ports (if needed for future monitoring)
EXPOSE 8080

# Default command
CMD ["lean", "live", "deploy"]
