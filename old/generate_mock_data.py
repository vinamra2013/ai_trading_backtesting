#!/usr/bin/env python3
"""
Generate mock data for parallel backtesting testing
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_mock_data(symbol, start_date, end_date, output_file):
    """Generate mock OHLCV data for testing"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')

    # Generate daily dates
    dates = []
    current = start
    while current <= end:
        if current.weekday() < 5:  # Monday to Friday
            dates.append(current)
        current += timedelta(days=1)

    # Generate mock prices starting from $400
    np.random.seed(42)  # For reproducible results
    n_days = len(dates)

    # Generate random walk for close prices
    returns = np.random.normal(0.0005, 0.02, n_days)  # Mean return 0.05%, std 2%
    close_prices = 400 * np.exp(np.cumsum(returns))

    # Generate OHLC from close prices
    high_mult = np.random.uniform(1.005, 1.03, n_days)
    low_mult = np.random.uniform(0.97, 0.995, n_days)
    open_prices = close_prices * np.random.uniform(0.995, 1.005, n_days)

    highs = np.maximum(close_prices * high_mult, open_prices)
    lows = np.minimum(close_prices * low_mult, open_prices)

    # Create DataFrame
    df = pd.DataFrame({
        'Date': dates,
        'Open': open_prices,
        'High': highs,
        'Low': lows,
        'Close': close_prices,
        'Volume': np.random.randint(50000000, 200000000, n_days)
    })

    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d 16:00:00')  # Add market close time
    df.to_csv(output_file, index=False)
    print(f"Generated {len(df)} rows of mock data for {symbol}")

if __name__ == "__main__":
    import os
    from pathlib import Path

    # Generate data with organized folder structure matching download_data.py
    symbols = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL']
    resolution = 'Daily'
    start_date = '2020-01-01'
    end_date = '2024-12-31'

    for symbol in symbols:
        # Create organized folder structure: data/csv_new/resolution/symbol/
        symbol_dir = Path(f'data/csv_new/{resolution}/{symbol}')
        symbol_dir.mkdir(parents=True, exist_ok=True)

        # Save with date range in filename (matching download_data.py format)
        date_suffix = f"_{start_date.replace('-', '')}_{end_date.replace('-', '')}"
        output_file = symbol_dir / f"{symbol}_{resolution}{date_suffix}.csv"

        generate_mock_data(symbol, start_date, end_date, str(output_file))
        print(f"Created: {output_file}")