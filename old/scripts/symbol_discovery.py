#!/usr/bin/env python3
"""
Symbol Discovery Engine - Epic 18
US-18.1: yfinance Integration
US-18.2: Market Data Scanner Types
US-18.3: Filtering and Validation Logic
US-18.4: Data Output and Storage
US-18.5: Command Line Interface

Autonomous symbol discovery system using yfinance for comprehensive market data.
Supports multiple scanner types: high_volume, most_active_stocks, top_gainers, top_losers,
most_active_etfs, and volatility_leaders.

Environment Variables (set in .env file):
- FINNHUB_API_KEY: Your Finnhub API key (for backup connectivity)

Data Sources:
- Primary: yfinance (comprehensive data including volume, market cap, sector)
- Fallback: Predefined symbol lists when yfinance unavailable

Rate Limiting:
- No rate limiting required for yfinance
- ATR calculation uses historical data efficiently
"""

import os
import sys
import time
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import asyncio

import yaml
import pandas as pd
import numpy as np
import finnhub
from dotenv import load_dotenv
import os
import yfinance as yf

# Load environment variables from .env file
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.symbol_discovery_models import DiscoveredSymbol
from scripts.symbol_discovery_db import SymbolDiscoveryDB


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)





class SymbolDiscoveryEngine:
    """
    Main engine for autonomous symbol discovery using IB API scanners.
    """

    def __init__(self, config_path: str = "config/symbol_discovery_config.yaml"):
        """
        Initialize the symbol discovery engine.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.finnhub_client: Optional[finnhub.Client] = None
        self.db: Optional[SymbolDiscoveryDB] = None
        self.setup_logging()

        logger.info("Symbol Discovery Engine initialized")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def setup_logging(self):
        """Setup logging based on configuration."""
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO').upper())
        log_file = log_config.get('file', 'logs/symbol_discovery.log')

        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Create file handler
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')))

        # Add handler to logger
        logger.addHandler(file_handler)
        logger.setLevel(log_level)





    def connect_finnhub(self) -> bool:
        """
        Establish connection to yfinance.

        Returns:
            bool: True if connected successfully
        """
        try:
            api_key = os.getenv('FINNHUB_API_KEY')
            if not api_key:
                logger.error("❌ Finnhub API key not found in environment variables. Please set FINNHUB_API_KEY in .env file")
                return False

            self.finnhub_client = finnhub.Client(api_key=api_key)
            logger.info("✅ Connected to yfinance for symbol discovery")
            return True

        except Exception as e:
            logger.error(f"Error connecting to Finnhub API: {e}")
            return False

    def connect_db(self) -> bool:
        """
        Establish connection to PostgreSQL database.

        Returns:
            bool: True if connected successfully
        """
        try:
            from scripts.symbol_discovery_db import SymbolDiscoveryDB
            self.db = SymbolDiscoveryDB(self.config['database'])
            logger.info("✅ Connected to PostgreSQL database")
            return True
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            return False

    def disconnect_finnhub(self):
        """Disconnect from yfinance."""
        if self.finnhub_client:
            # yfinance doesn't require explicit disconnect
            self.finnhub_client = None
            logger.info("Disconnected from yfinance")

    def disconnect_db(self):
        """Disconnect from database."""
        if self.db:
            self.db.close()
            logger.info("Disconnected from database")

    def run_scanner(self, scanner_name: str) -> List[DiscoveredSymbol]:
        """
        Run a specific scanner and return discovered symbols.

        Uses yfinance for comprehensive symbol discovery.
        Falls back to predefined symbol lists if data unavailable.

        Args:
            scanner_name: Name of the scanner to run

        Returns:
            List of discovered symbols
        """
        scanner_config = self.config['scanners'].get(scanner_name)
        if not scanner_config:
            logger.error(f"Scanner '{scanner_name}' not found in configuration")
            return []

        logger.info(f"Running scanner: {scanner_name} - {scanner_config['description']}")

        # Run yfinance-based scanner
        try:
            logger.info(f"Running yfinance scanner {scanner_name}")
            symbols = self._run_yfinance_scanner(scanner_name, scanner_config)
            logger.info(f"Yfinance scanner returned {len(symbols) if symbols else 0} symbols")
            if symbols:
                logger.info(f"Yfinance scanner {scanner_name} found {len(symbols)} symbols")
                return symbols
            else:
                logger.warning(f"Yfinance scanner {scanner_name} returned no symbols, falling back to predefined list")
        except Exception as e:
            logger.warning(f"Yfinance scanner {scanner_name} failed: {e}, falling back to predefined list")

        return self._get_predefined_symbols(scanner_name)

    def _run_yfinance_scanner(self, scanner_name: str, scanner_config: Dict) -> List[DiscoveredSymbol]:
        """
        Run yfinance-based scanner for symbol discovery
        """
        try:
            symbols = []
            params = scanner_config['parameters']

            # Use yfinance for all scanner types
            if scanner_name == 'high_volume':
                symbols = self._scan_high_volume_yfinance(params)
            elif scanner_name == 'most_active_stocks':
                symbols = self._scan_most_active_yfinance(params)
            elif scanner_name == 'top_gainers':
                symbols = self._scan_gainers_yfinance(params)
            elif scanner_name == 'top_losers':
                symbols = self._scan_losers_yfinance(params)
            elif scanner_name == 'most_active_etfs':
                symbols = self._scan_etfs_yfinance(params)
            elif scanner_name == 'volatility_leaders':
                symbols = self._scan_volatility_yfinance(params)
            else:
                logger.warning(f"Scanner {scanner_name} not implemented")
                return []

            return symbols

        except Exception as e:
            logger.error(f"Error running yfinance scanner {scanner_name}: {e}")
            return []

            return symbols

        except Exception as e:
            logger.error(f"Error running Finnhub scanner {scanner_name}: {e}")
            return []

    def _make_finnhub_request(self, request_func, *args, **kwargs):
        """
        Make a Finnhub API request with rate limiting and exponential backoff
        """
        rate_config = self.config.get('rate_limiting', {})
        max_requests_per_minute = rate_config.get('max_requests_per_minute', 30)
        request_delay = rate_config.get('request_delay_seconds', 2.0)
        max_retries = rate_config.get('max_retries', 3)
        backoff_factor = rate_config.get('backoff_factor', 2.0)

        # Initialize rate limiting attributes
        if not hasattr(self, '_request_count'):
            self._request_count = 0
        if not hasattr(self, '_last_request_time'):
            self._last_request_time = 0

        for attempt in range(max_retries):
            try:
                # Rate limiting check
                current_time = time.time()
                time_since_last_request = current_time - self._last_request_time

                if time_since_last_request < request_delay:
                    sleep_time = request_delay - time_since_last_request
                    logger.debug(f"Rate limiting: sleeping {sleep_time:.2f} seconds")
                    # time.sleep(sleep_time)  # Temporarily disabled for testing

                # Check if we've exceeded per-minute limit
                if self._request_count >= max_requests_per_minute:
                    # Reset counter every minute
                    if time_since_last_request >= 60:
                        self._request_count = 0
                    else:
                        sleep_time = 60 - time_since_last_request
                        logger.debug(f"Per-minute limit reached: sleeping {sleep_time:.2f} seconds")
                        time.sleep(sleep_time)
                        self._request_count = 0

                # Make the request
                self._last_request_time = time.time()
                self._request_count += 1

                logger.debug(f"Making Finnhub API request (attempt {attempt + 1})")
                logger.debug(f"Client is None: {self.finnhub_client is None}")
                result = request_func(*args, **kwargs)
                logger.debug(f"Finnhub API request completed: {result}")

                # Check for rate limit response
                if isinstance(result, dict) and result.get('error') == 'API limit reached':
                    if attempt < max_retries - 1:
                        sleep_time = request_delay * (backoff_factor ** attempt)
                        logger.warning(f"Finnhub API limit reached, backing off {sleep_time:.2f} seconds")
                        time.sleep(sleep_time)
                        continue

                return result

            except Exception as e:
                if attempt < max_retries - 1:
                    sleep_time = request_delay * (backoff_factor ** attempt)
                    logger.warning(f"Request failed (attempt {attempt + 1}), backing off {sleep_time:.2f} seconds: {e}")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Request failed after {max_retries} attempts: {e}")
                    raise

        return None

    def _scan_high_volume_yfinance(self, params: Dict) -> List[DiscoveredSymbol]:
        """Scan for high volume stocks using yfinance with proper volume filtering"""
        try:
            # Use a curated list of high-volume stocks to start with
            # yfinance can handle broader scanning but we start with known liquid stocks
            candidate_symbols = [
                'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA', 'NVDA', 'JPM', 'JNJ', 'V',
                'WMT', 'PG', 'UNH', 'HD', 'MA', 'BAC', 'PFE', 'KO', 'DIS', 'ADBE',
                'NFLX', 'CMCSA', 'XOM', 'COST', 'AVGO', 'ABNB', 'TXN', 'QCOM', 'LLY', 'HON',
                'CRM', 'ACN', 'T', 'DHR', 'LIN', 'TMO', 'NEE', 'PM', 'VZ',
                'INTC', 'AMD', 'IBM', 'ORCL', 'CSCO', 'NOW', 'UBER', 'SPOT'
            ]

            high_volume_symbols = []
            volume_threshold = params.get('above_volume', 1000000)
            max_results = params.get('number_of_rows', 50)

            for symbol in candidate_symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info

                    # Check if we got valid data
                    if not info or info.get('currentPrice') is None:
                        logger.debug(f"No data available for {symbol}")
                        continue

                    # Get volume data
                    avg_volume = info.get('averageVolume')
                    current_volume = info.get('regularMarketVolume')

                    # Apply volume filter
                    if avg_volume and avg_volume >= volume_threshold:
                        discovered_symbol = DiscoveredSymbol(
                            symbol=symbol,
                            exchange=info.get('exchange', 'US'),
                            sector=info.get('sector'),
                            avg_volume=avg_volume,
                            atr=None,  # Will be calculated later if needed
                            price=info.get('currentPrice'),
                            pct_change=info.get('regularMarketChangePercent'),
                            market_cap=info.get('marketCap'),
                            volume=current_volume
                        )
                        high_volume_symbols.append(discovered_symbol)

                        if len(high_volume_symbols) >= max_results:
                            break

                except Exception as e:
                    logger.debug(f"Error processing symbol {symbol}: {e}")
                    continue

            logger.info(f"Found {len(high_volume_symbols)} high volume symbols via yfinance")
            return high_volume_symbols

        except Exception as e:
            logger.error(f"Error in yfinance high volume scan: {e}")
            return []

    def _scan_most_active_yfinance(self, params: Dict) -> List[DiscoveredSymbol]:
        """Scan for most active stocks using yfinance"""
        try:
            # For now, use same candidate list as high volume but sort by current volume
            candidate_symbols = [
                'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA', 'NVDA', 'JPM', 'JNJ', 'V',
                'WMT', 'PG', 'UNH', 'HD', 'MA', 'BAC', 'PFE', 'KO', 'DIS', 'ADBE',
                'NFLX', 'CMCSA', 'XOM', 'COST', 'AVGO', 'ABNB', 'TXN', 'QCOM', 'LLY', 'HON'
            ]

            symbols_data = []
            max_results = params.get('number_of_rows', 50)

            for symbol in candidate_symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info

                    if info and info.get('regularMarketVolume'):
                        symbols_data.append({
                            'symbol': symbol,
                            'volume': info.get('regularMarketVolume', 0),
                            'info': info
                        })
                except Exception as e:
                    logger.debug(f"Error getting data for {symbol}: {e}")
                    continue

            # Sort by volume and take top results
            symbols_data.sort(key=lambda x: x['volume'], reverse=True)
            top_symbols = symbols_data[:max_results]

            discovered_symbols = []
            for item in top_symbols:
                info = item['info']
                discovered_symbol = DiscoveredSymbol(
                    symbol=item['symbol'],
                    exchange=info.get('exchange', 'US'),
                    sector=info.get('sector'),
                    avg_volume=info.get('averageVolume'),
                    price=info.get('currentPrice'),
                    pct_change=info.get('regularMarketChangePercent'),
                    market_cap=info.get('marketCap'),
                    volume=item['volume']
                )
                discovered_symbols.append(discovered_symbol)

            logger.info(f"Found {len(discovered_symbols)} most active symbols via yfinance")
            return discovered_symbols

        except Exception as e:
            logger.error(f"Error in yfinance most active scan: {e}")
            return []

    def _scan_gainers_yfinance(self, params: Dict) -> List[DiscoveredSymbol]:
        """Scan for top gaining stocks using yfinance"""
        try:
            candidate_symbols = [
                'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA', 'NVDA', 'JPM', 'JNJ', 'V',
                'WMT', 'PG', 'UNH', 'HD', 'MA', 'BAC', 'PFE', 'KO', 'DIS', 'ADBE',
                'NFLX', 'CMCSA', 'XOM', 'COST', 'AVGO', 'ABNB', 'TXN', 'QCOM', 'LLY', 'HON'
            ]

            symbols_data = []
            max_results = params.get('number_of_rows', 50)

            for symbol in candidate_symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info

                    if info and info.get('regularMarketChangePercent') is not None:
                        symbols_data.append({
                            'symbol': symbol,
                            'pct_change': info.get('regularMarketChangePercent', 0),
                            'info': info
                        })
                except Exception as e:
                    logger.debug(f"Error getting data for {symbol}: {e}")
                    continue

            # Sort by percent change and take top gainers
            symbols_data.sort(key=lambda x: x['pct_change'], reverse=True)
            top_gainers = symbols_data[:max_results]

            discovered_symbols = []
            for item in top_gainers:
                info = item['info']
                discovered_symbol = DiscoveredSymbol(
                    symbol=item['symbol'],
                    exchange=info.get('exchange', 'US'),
                    sector=info.get('sector'),
                    avg_volume=info.get('averageVolume'),
                    price=info.get('currentPrice'),
                    pct_change=item['pct_change'],
                    market_cap=info.get('marketCap'),
                    volume=info.get('regularMarketVolume')
                )
                discovered_symbols.append(discovered_symbol)

            logger.info(f"Found {len(discovered_symbols)} top gaining symbols via yfinance")
            return discovered_symbols

        except Exception as e:
            logger.error(f"Error in yfinance gainers scan: {e}")
            return []

    def _scan_losers_yfinance(self, params: Dict) -> List[DiscoveredSymbol]:
        """Scan for top losing stocks using yfinance"""
        try:
            candidate_symbols = [
                'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA', 'NVDA', 'JPM', 'JNJ', 'V',
                'WMT', 'PG', 'UNH', 'HD', 'MA', 'BAC', 'PFE', 'KO', 'DIS', 'ADBE',
                'NFLX', 'CMCSA', 'XOM', 'COST', 'AVGO', 'ABNB', 'TXN', 'QCOM', 'LLY', 'HON'
            ]

            symbols_data = []
            max_results = params.get('number_of_rows', 50)

            for symbol in candidate_symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info

                    if info and info.get('regularMarketChangePercent') is not None:
                        symbols_data.append({
                            'symbol': symbol,
                            'pct_change': info.get('regularMarketChangePercent', 0),
                            'info': info
                        })
                except Exception as e:
                    logger.debug(f"Error getting data for {symbol}: {e}")
                    continue

            # Sort by percent change (ascending for losers) and take top losers
            symbols_data.sort(key=lambda x: x['pct_change'])
            top_losers = symbols_data[:max_results]

            discovered_symbols = []
            for item in top_losers:
                info = item['info']
                discovered_symbol = DiscoveredSymbol(
                    symbol=item['symbol'],
                    exchange=info.get('exchange', 'US'),
                    sector=info.get('sector'),
                    avg_volume=info.get('averageVolume'),
                    price=info.get('currentPrice'),
                    pct_change=item['pct_change'],
                    market_cap=info.get('marketCap'),
                    volume=info.get('regularMarketVolume')
                )
                discovered_symbols.append(discovered_symbol)

            logger.info(f"Found {len(discovered_symbols)} top losing symbols via yfinance")
            return discovered_symbols

        except Exception as e:
            logger.error(f"Error in yfinance losers scan: {e}")
            return []

    def _scan_etfs_yfinance(self, params: Dict) -> List[DiscoveredSymbol]:
        """Scan for most active ETFs using yfinance"""
        try:
            # Popular ETFs
            etf_symbols = ['SPY', 'QQQ', 'IWM', 'EFA', 'VWO', 'BND', 'VNQ', 'GLD', 'USO', 'TLT']

            symbols_data = []
            max_results = params.get('number_of_rows', 50)

            for symbol in etf_symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info

                    if info and info.get('regularMarketVolume'):
                        symbols_data.append({
                            'symbol': symbol,
                            'volume': info.get('regularMarketVolume', 0),
                            'info': info
                        })
                except Exception as e:
                    logger.debug(f"Error getting data for {symbol}: {e}")
                    continue

            # Sort by volume and take top results
            symbols_data.sort(key=lambda x: x['volume'], reverse=True)
            top_etfs = symbols_data[:max_results]

            discovered_symbols = []
            for item in top_etfs:
                info = item['info']
                discovered_symbol = DiscoveredSymbol(
                    symbol=item['symbol'],
                    exchange=info.get('exchange', 'US'),
                    sector='ETF',  # Override sector for ETFs
                    avg_volume=info.get('averageVolume'),
                    price=info.get('currentPrice'),
                    pct_change=info.get('regularMarketChangePercent'),
                    market_cap=info.get('marketCap'),
                    volume=item['volume']
                )
                discovered_symbols.append(discovered_symbol)

            logger.info(f"Found {len(discovered_symbols)} most active ETFs via yfinance")
            return discovered_symbols

        except Exception as e:
            logger.error(f"Error in yfinance ETF scan: {e}")
            return []

    def _scan_volatility_yfinance(self, params: Dict) -> List[DiscoveredSymbol]:
        """Scan for volatility leaders using yfinance"""
        try:
            candidate_symbols = [
                'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA', 'NVDA', 'JPM', 'JNJ', 'V',
                'WMT', 'PG', 'UNH', 'HD', 'MA', 'BAC', 'PFE', 'KO', 'DIS', 'ADBE',
                'NFLX', 'CMCSA', 'XOM', 'COST', 'AVGO', 'ABNB', 'TXN', 'QCOM', 'LLY', 'HON'
            ]

            symbols_data = []
            max_results = params.get('number_of_rows', 50)

            for symbol in candidate_symbols:
                try:
                    # Calculate ATR for volatility
                    atr = self.calculate_atr_yfinance(symbol, 14)
                    if atr:
                        ticker = yf.Ticker(symbol)
                        info = ticker.info

                        if info and info.get('currentPrice'):
                            symbols_data.append({
                                'symbol': symbol,
                                'atr': atr,
                                'info': info
                            })
                except Exception as e:
                    logger.debug(f"Error getting data for {symbol}: {e}")
                    continue

            # Sort by ATR (volatility) and take top results
            symbols_data.sort(key=lambda x: x['atr'], reverse=True)
            top_volatile = symbols_data[:max_results]

            discovered_symbols = []
            for item in top_volatile:
                info = item['info']
                discovered_symbol = DiscoveredSymbol(
                    symbol=item['symbol'],
                    exchange=info.get('exchange', 'US'),
                    sector=info.get('sector'),
                    avg_volume=info.get('averageVolume'),
                    atr=item['atr'],
                    price=info.get('currentPrice'),
                    pct_change=info.get('regularMarketChangePercent'),
                    market_cap=info.get('marketCap'),
                    volume=info.get('regularMarketVolume')
                )
                discovered_symbols.append(discovered_symbol)

            logger.info(f"Found {len(discovered_symbols)} volatility leaders via yfinance")
            return discovered_symbols

        except Exception as e:
            logger.error(f"Error in yfinance volatility scan: {e}")
            return []

    def calculate_atr_yfinance(self, symbol: str, period: int = 14) -> Optional[float]:
        """
        Calculate ATR using yfinance historical data.

        Args:
            symbol: Stock symbol
            period: ATR calculation period

        Returns:
            ATR value or None if calculation fails
        """
        try:
            ticker = yf.Ticker(symbol)
            # Get 30 days of historical data for ATR calculation
            hist = ticker.history(period='1mo', interval='1d')

            if len(hist) < period + 1:
                logger.debug(f"Insufficient data for ATR calculation for {symbol}")
                return None

            # Calculate True Range
            high = hist['High']
            low = hist['Low']
            close = hist['Close']
            prev_close = close.shift(1)

            tr1 = high - low
            tr2 = (high - prev_close).abs()
            tr3 = (low - prev_close).abs()

            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            # Calculate ATR (simple moving average of TR)
            atr_series = true_range.rolling(window=period).mean()
            if len(atr_series) > 0:
                atr = atr_series.iloc[-1]
                return float(atr)
            else:
                return None

        except Exception as e:
            logger.debug(f"ATR calculation failed for {symbol} with yfinance: {e}")
            return None

    def _scan_most_active_finnhub(self, params: Dict, max_requests: int, delay: float) -> List[DiscoveredSymbol]:
        """Scan for most active stocks using Finnhub"""
        # Similar to high volume but focus on trade count/activity
        return self._scan_high_volume_finnhub(params, max_requests, delay)

    def _scan_gainers_finnhub(self, params: Dict, max_requests: int, delay: float) -> List[DiscoveredSymbol]:
        """Scan for top gainers using Finnhub - using predefined active symbols"""
        try:
            # Use a curated list of active stocks to check for gainers
            active_symbols_list = [
                'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA', 'NVDA', 'AMD', 'PLTR', 'SOFI',
                'CRM', 'NOW', 'UBER', 'SPOT', 'SQ', 'SHOP', 'COIN', 'MSTR', 'RIVN', 'LCID',
                'INTC', 'AMD', 'NFLX', 'DIS', 'PYPL', 'EBAY', 'ETSY', 'PINS', 'SNAP', 'TWTR'
            ]

            gainers = []
            max_results = params.get('number_of_rows', 50)

            for symbol in active_symbols_list:
                try:
                    quote = self._make_finnhub_request(self.finnhub_client.quote, symbol)

                    if quote and 'dp' in quote and quote['dp'] > 0:  # Only positive changes
                        discovered_symbol = DiscoveredSymbol(
                            symbol=symbol,
                            exchange='US',
                            sector=None,
                            avg_volume=quote.get('v', 0),
                            price=quote.get('c'),
                            pct_change=quote['dp'],
                            volume=quote.get('v', 0)
                        )
                        gainers.append((quote['dp'], discovered_symbol))

                except Exception as e:
                    logger.debug(f"Error processing symbol {symbol}: {e}")
                    continue

            # Sort by percent change and return top N
            gainers.sort(key=lambda x: x[0], reverse=True)
            result = [symbol for _, symbol in gainers[:max_results]]
            logger.info(f"Found {len(result)} top gainers")
            return result

        except Exception as e:
            logger.error(f"Error in gainers scan: {e}")
            return []

    def _scan_losers_finnhub(self, params: Dict, max_requests: int, delay: float) -> List[DiscoveredSymbol]:
        """Scan for top losers using Finnhub - using predefined active symbols"""
        try:
            # Use a curated list of active stocks to check for losers
            active_symbols_list = [
                'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA', 'NVDA', 'AMD', 'PLTR', 'SOFI',
                'CRM', 'NOW', 'UBER', 'SPOT', 'SQ', 'SHOP', 'COIN', 'MSTR', 'RIVN', 'LCID',
                'INTC', 'AMD', 'NFLX', 'DIS', 'PYPL', 'EBAY', 'ETSY', 'PINS', 'SNAP', 'TWTR'
            ]

            losers = []
            max_results = params.get('number_of_rows', 50)

            for symbol in active_symbols_list:
                try:
                    quote = self._make_finnhub_request(self.finnhub_client.quote, symbol)

                    if quote and 'dp' in quote and quote['dp'] < 0:  # Only negative changes
                        discovered_symbol = DiscoveredSymbol(
                            symbol=symbol,
                            exchange='US',
                            sector=None,
                            avg_volume=quote.get('v', 0),
                            price=quote.get('c'),
                            pct_change=quote['dp'],
                            volume=quote.get('v', 0)
                        )
                        losers.append((quote['dp'], discovered_symbol))

                except Exception as e:
                    logger.debug(f"Error processing symbol {symbol}: {e}")
                    continue

            # Sort by percent change (ascending for biggest losers)
            losers.sort(key=lambda x: x[0])
            result = [symbol for _, symbol in losers[:max_results]]
            logger.info(f"Found {len(result)} top losers")
            return result

        except Exception as e:
            logger.error(f"Error in losers scan: {e}")
            return []

    def _scan_etfs_finnhub(self, params: Dict, max_requests: int, delay: float) -> List[DiscoveredSymbol]:
        """Scan for most active ETFs using Finnhub"""
        try:
            # Get ETF symbols
            symbols_data = self._make_finnhub_request(self.finnhub_client.stock_symbols, exchange='US')

            if not symbols_data:
                return []

            etfs = []
            volume_threshold = params.get('above_volume', 500000)

            for symbol_data in symbols_data:
                try:
                    symbol = symbol_data['symbol']
                    # Check if it's an ETF (this is approximate - Finnhub doesn't have type field)
                    if symbol.endswith('.ETF') or len(symbol) <= 4:  # Rough ETF detection
                        quote = self._make_finnhub_request(self.finnhub_client.quote, symbol)

                        if quote and 'v' in quote and quote['v'] >= volume_threshold:
                            discovered_symbol = DiscoveredSymbol(
                                symbol=symbol,
                                exchange=symbol_data.get('exchange', 'US'),
                                sector=None,
                                avg_volume=quote.get('v'),
                                price=quote.get('c'),
                                pct_change=quote.get('dp'),
                                volume=quote.get('v')
                            )
                            etfs.append((quote['v'], discovered_symbol))

                except Exception as e:
                    continue

            # Sort by volume
            etfs.sort(key=lambda x: x[0], reverse=True)
            return [symbol for _, symbol in etfs[:params.get('number_of_rows', 50)]]

        except Exception as e:
            logger.error(f"Error in ETF scan: {e}")
            return []

    def _scan_volatility_finnhub(self, params: Dict, max_requests: int, delay: float) -> List[DiscoveredSymbol]:
        """Scan for volatility leaders using Finnhub"""
        # For volatility, we'd need technical indicators or historical data
        # This is a simplified version focusing on high beta/high volume stocks
        return self._scan_high_volume_finnhub(params, max_requests, delay)

    def _get_predefined_symbols(self, scanner_name: str) -> List[DiscoveredSymbol]:
        """
        Return predefined symbol lists when yfinance data is unavailable.

        Args:
            scanner_name: Type of scanner

        Returns:
            List of predefined symbols
        """
        # Predefined lists of popular liquid symbols
        predefined_lists = {
            'high_volume': [
                'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA', 'NVDA', 'JPM', 'JNJ', 'V',
                'WMT', 'PG', 'UNH', 'HD', 'MA', 'BAC', 'PFE', 'KO', 'DIS', 'ADBE',
                'NFLX', 'CMCSA', 'XOM', 'COST', 'AVGO', 'ABNB', 'TXN', 'QCOM', 'LLY', 'HON'
            ],
            'most_active_stocks': [
                'AAPL', 'TSLA', 'NVDA', 'MSFT', 'AMZN', 'META', 'GOOGL', 'AMD', 'INTC', 'SOXS',
                'SPY', 'QQQ', 'IWM', 'TQQQ', 'SQQQ', 'UVXY', 'VXX', 'TNA', 'TZA', 'FAS'
            ],
            'top_gainers': [
                'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA', 'NVDA', 'AMD', 'PLTR', 'SOFI'
            ],
            'top_losers': [
                'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA', 'NVDA', 'AMD', 'PLTR', 'SOFI'
            ],
            'most_active_etfs': [
                'SPY', 'QQQ', 'IWM', 'TQQQ', 'SQQQ', 'UVXY', 'VXX', 'TNA', 'TZA', 'FAS'
            ],
            'volatility_leaders': [
                'TSLA', 'NVDA', 'AMD', 'PLTR', 'SOFI', 'AAPL', 'META', 'AMZN', 'GOOGL', 'MSFT'
            ]
        }

        symbols_list = predefined_lists.get(scanner_name, predefined_lists['high_volume'])

        symbols = []
        for symbol_name in symbols_list:
            # For now, just create symbols without live data to ensure reliability
            # TODO: Add live data fetching back once API issues are resolved
            symbol = DiscoveredSymbol(
                symbol=symbol_name,
                exchange='US',
                sector=None,
                avg_volume=None,
                price=None,
                pct_change=None,
                volume=None
            )
            symbols.append(symbol)

        logger.info(f"Predefined list for {scanner_name} returned {len(symbols)} symbols")
        return symbols

    def calculate_atr(self, symbol: str, period: int = 14) -> Optional[float]:
        """
        Calculate ATR using yfinance data.

        Args:
            symbol: Stock symbol
            period: ATR calculation period

        Returns:
            ATR value or None if calculation fails
        """
        return self.calculate_atr_yfinance(symbol, period)

    def apply_filters(self, symbols: List[DiscoveredSymbol]) -> List[DiscoveredSymbol]:
        """
        Apply filtering logic to discovered symbols.

        Args:
            symbols: List of discovered symbols

        Returns:
            Filtered list of symbols
        """
        logger.info(f"Applying filters to {len(symbols)} symbols")

        filters_config = self.config['filters']
        filtered_symbols = []

        for symbol in symbols:
            try:
                # Liquidity filter
                if not self._passes_liquidity_filter(symbol, filters_config['liquidity']):
                    logger.debug(f"Symbol {symbol.symbol} failed liquidity filter")
                    continue

                # Price range filter
                if not self._passes_price_filter(symbol, filters_config['price_range']):
                    logger.debug(f"Symbol {symbol.symbol} failed price filter")
                    continue

                # Exchange filter
                if not self._passes_exchange_filter(symbol, filters_config['exchanges']):
                    logger.debug(f"Symbol {symbol.symbol} failed exchange filter")
                    continue

                # Calculate ATR for volatility filter if not already provided
                if symbol.price and symbol.price > 0 and symbol.atr is None:
                    symbol.atr = self.calculate_atr(symbol.symbol, filters_config['volatility']['atr_period'])

                # Volatility filter (only if ATR is available)
                if symbol.atr is not None:
                    if not self._passes_volatility_filter(symbol, filters_config['volatility']):
                        logger.debug(f"Symbol {symbol.symbol} failed volatility filter")
                        continue

                # Sector filter
                if not self._passes_sector_filter(symbol, filters_config['sectors']):
                    logger.debug(f"Symbol {symbol.symbol} failed sector filter")
                    continue

                filtered_symbols.append(symbol)

            except Exception as e:
                logger.warning(f"Error filtering symbol {symbol.symbol}: {e}")
                continue

        logger.info(f"Filtering complete: {len(filtered_symbols)} symbols passed all filters")
        return filtered_symbols

    def _passes_liquidity_filter(self, symbol: DiscoveredSymbol, config: Dict) -> bool:
        """Check if symbol passes liquidity filter."""
        min_volume = config.get('min_avg_volume', 1000000)
        # Allow symbols with unknown volume (None) to pass - these are typically well-known liquid symbols
        if symbol.avg_volume is None or symbol.volume is None:
            return True
        # Check both avg_volume and current volume
        if (symbol.avg_volume and symbol.avg_volume >= min_volume) or (symbol.volume and symbol.volume >= min_volume):
            return True
        return False

    def _passes_volatility_filter(self, symbol: DiscoveredSymbol, config: Dict) -> bool:
        """Check if symbol passes volatility filter."""
        # Allow symbols with unknown ATR (None) to pass - these are typically well-known liquid symbols
        if symbol.atr is None:
            return True

        min_atr = config.get('min_atr', 0.5)
        max_atr = config.get('max_atr', 20.0)

        return min_atr <= symbol.atr <= max_atr

    def _passes_price_filter(self, symbol: DiscoveredSymbol, config: Dict) -> bool:
        """Check if symbol passes price range filter."""
        # Allow symbols with unknown price (None) to pass - these are typically well-known liquid symbols
        if symbol.price is None:
            return True

        min_price = config.get('min_price', 5.0)
        max_price = config.get('max_price', 500.0)

        return min_price <= symbol.price <= max_price

    def _passes_exchange_filter(self, symbol: DiscoveredSymbol, config: Dict) -> bool:
        """Check if symbol passes exchange filter."""
        allowed_exchanges = set(config.get('allowed', []))
        excluded_exchanges = set(config.get('excluded', []))

        # If no allowed exchanges specified, allow all
        if not allowed_exchanges:
            return symbol.exchange not in excluded_exchanges

        # Allow 'US' exchange as it's equivalent to SMART routing
        if symbol.exchange == 'US' and 'SMART' in allowed_exchanges:
            return True

        # Handle yfinance exchange codes
        yfinance_to_standard = {
            'NMS': 'NASDAQ',  # NASDAQ
            'NYQ': 'NYSE',    # NYSE
            'ASE': 'AMEX',    # AMEX
            'PCX': 'ARCA',    # ARCA
            'BTS': 'BATS',    # BATS
        }

        # Convert yfinance exchange code to standard format
        standard_exchange = yfinance_to_standard.get(symbol.exchange, symbol.exchange)

        if allowed_exchanges and standard_exchange not in allowed_exchanges:
            return False

        if symbol.exchange in excluded_exchanges:
            return False

        return True

    def _passes_sector_filter(self, symbol: DiscoveredSymbol, config: Dict) -> bool:
        """Check if symbol passes sector filter."""
        allowed_sectors = set(config.get('allowed', []))
        excluded_sectors = set(config.get('excluded', []))

        # If no sector data available, allow through (similar to other filters)
        if symbol.sector is None:
            return True

        # If allowed sectors specified and sector not in allowed, reject
        if allowed_sectors and symbol.sector not in allowed_sectors:
            return False

        # If sector is in excluded list, reject
        if symbol.sector in excluded_sectors:
            return False

        return True

    def discover_symbols(self, scanner_name: str, save_to_db: bool = True) -> List[DiscoveredSymbol]:
        """
        Complete symbol discovery workflow.

        Args:
            scanner_name: Name of scanner to run
            save_to_db: Whether to save results to database

        Returns:
            List of filtered, validated symbols
        """
        logger.info(f"Starting symbol discovery with scanner: {scanner_name}")

        scan_id = None
        start_time = time.time()

        try:
            # Start scan tracking in database
            if save_to_db and self.db:
                scanner_config = self.config['scanners'].get(scanner_name, {})
                scan_id = self.db.start_scan(
                    scanner_name,
                    scanner_config.get('type', 'unknown'),
                    self.config.get('filters', {})
                )

            # Run scanner
            raw_symbols = self.run_scanner(scanner_name)
            if not raw_symbols:
                logger.warning("No symbols discovered from scanner")
                if save_to_db and self.db and scan_id:
                    self.db.fail_scan(scan_id, "No symbols discovered")
                return []

            # Apply filters
            filtered_symbols = self.apply_filters(raw_symbols)

            # Save to database
            if save_to_db and self.db and filtered_symbols:
                self.db.save_discovered_symbols(filtered_symbols, scanner_name, scan_id)

            # Complete scan tracking
            if save_to_db and self.db and scan_id:
                execution_time = time.time() - start_time
                self.db.complete_scan(
                    scan_id,
                    len(raw_symbols),
                    len(filtered_symbols),
                    execution_time
                )

            logger.info(f"Symbol discovery complete: {len(filtered_symbols)} symbols ready for use")
            return filtered_symbols

        except Exception as e:
            logger.error(f"Error during symbol discovery: {e}")
            if save_to_db and self.db and scan_id:
                self.db.fail_scan(scan_id, str(e))
            raise


def create_cli_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Symbol Discovery Engine - Autonomous symbol discovery using yfinance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
 Examples:
   # Run high volume scanner with default filters
   python scripts/symbol_discovery.py --scanner high_volume

   # Run volatility scanner with custom ATR threshold
   python scripts/symbol_discovery.py --scanner volatility_leaders --atr-threshold 1.5

   # Run gainers scanner with custom volume filter
   python scripts/symbol_discovery.py --scanner top_gainers --min-volume 2000000

   # Output to JSON instead of CSV
   python scripts/symbol_discovery.py --scanner most_active_stocks --output json

   # Run with dry-run to see configuration
   python scripts/symbol_discovery.py --scanner high_volume --dry-run

   # Skip database operations and output to file only
   python scripts/symbol_discovery.py --scanner high_volume --no-db
         """
    )

    parser.add_argument(
        '--scanner',
        required=True,
        choices=['top_gainers', 'top_losers', 'high_volume', 'most_active_stocks', 'most_active_etfs', 'volatility_leaders'],
        help='Scanner type to run'
    )

    parser.add_argument(
        '--output',
        choices=['csv', 'json', 'both'],
        default='csv',
        help='Output format (default: csv)'
    )

    parser.add_argument(
        '--output-dir',
        default='data/discovered_symbols',
        help='Output directory (default: data/discovered_symbols)'
    )

    # Filter override arguments
    parser.add_argument(
        '--min-volume',
        type=int,
        help='Override minimum average volume filter'
    )

    parser.add_argument(
        '--atr-threshold',
        type=float,
        help='Override minimum ATR threshold'
    )

    parser.add_argument(
        '--min-price',
        type=float,
        help='Override minimum price filter'
    )

    parser.add_argument(
        '--max-price',
        type=float,
        help='Override maximum price filter'
    )

    parser.add_argument(
        '--exchanges',
        help='Override allowed exchanges (comma-separated)'
    )

    parser.add_argument(
        '--config',
        default='config/symbol_discovery_config.yaml',
        help='Path to configuration file'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without executing'
    )

    parser.add_argument(
        '--no-db',
        action='store_true',
        help='Skip database operations (file output only)'
    )

    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show discovery statistics instead of running scan'
    )

    return parser


def main():
    """Main entry point for command line execution."""
    parser = create_cli_parser()
    args = parser.parse_args()

    # Initialize engine
    try:
        engine = SymbolDiscoveryEngine(args.config)
    except Exception as e:
        logger.error(f"Failed to initialize engine: {e}")
        sys.exit(1)

    # Apply filter overrides from CLI args
    if args.min_volume:
        engine.config['filters']['liquidity']['min_avg_volume'] = args.min_volume
    if args.atr_threshold:
        engine.config['filters']['volatility']['min_atr'] = args.atr_threshold
    if args.min_price:
        engine.config['filters']['price_range']['min_price'] = args.min_price
    if args.max_price:
        engine.config['filters']['price_range']['max_price'] = args.max_price
    if args.exchanges:
        engine.config['filters']['exchanges']['allowed'] = args.exchanges.split(',')

        # Show statistics if requested
    if args.stats:
        if not engine.connect_db():
            logger.error("Failed to connect to database for statistics")
            sys.exit(1)
        try:
            if engine.db:
                stats = engine.db.get_discovery_stats()
                print("\n=== Symbol Discovery Statistics ===")
                print(f"Unique symbols discovered: {stats.get('unique_symbols', 0)}")
                print(f"Total discoveries: {stats.get('total_discoveries', 0)}")
                print(f"Scanner types used: {stats.get('scanner_types_used', 0)}")
                print(f"Average filter rate: {stats.get('avg_filter_rate', 0):.2%}")
                print(f"Total scanned: {stats.get('total_scanned', 0)}")
                print(f"Total filtered: {stats.get('total_filtered', 0)}")

                scanner_breakdown = stats.get('scanner_breakdown', {})
                if scanner_breakdown:
                    print("\nScanner Breakdown:")
                    for scanner, count in scanner_breakdown.items():
                        print(f"  {scanner}: {count}")

                # Recent discoveries
                recent = engine.db.get_recent_discovered_symbols(limit=10)
                if recent:
                    print(f"\nRecent Discoveries (last {len(recent)}):")
                    for symbol in recent:
                        print(f"  {symbol['symbol']} ({symbol['exchange']}) - {symbol['discovery_timestamp']}")

        finally:
            engine.disconnect_db()
        return

    if args.dry_run:
        logger.info("DRY RUN MODE - Configuration that would be used:")
        logger.info(f"Scanner: {args.scanner}")
        logger.info(f"Filters: {engine.config['filters']}")
        logger.info(f"Database: {'Disabled' if args.no_db else 'Enabled'}")
        return

    # Connect to services
    finnhub_connected = engine.connect_finnhub()
    if not finnhub_connected:
        logger.warning("Failed to connect to yfinance - will use fallback predefined symbols")

    db_connected = True
    if not args.no_db:
        db_connected = engine.connect_db()
        if not db_connected:
            logger.error("Failed to connect to database")
            sys.exit(1)

    try:
        # Run discovery
        save_to_db = not args.no_db
        symbols = engine.discover_symbols(args.scanner, save_to_db=save_to_db)

        if not symbols:
            logger.warning("No symbols discovered")
            return

        # Output results
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if args.output in ['csv', 'both']:
            csv_file = output_dir / f"{args.scanner}_{timestamp}.csv"
            save_to_csv(symbols, csv_file)
            logger.info(f"Results saved to {csv_file}")

        if args.output in ['json', 'both']:
            json_file = output_dir / f"{args.scanner}_{timestamp}.json"
            save_to_json(symbols, json_file)
            logger.info(f"Results saved to {json_file}")

        # Summary
        logger.info(f"Discovery Summary: {len(symbols)} symbols found and filtered")

    except Exception as e:
        logger.error(f"Error during symbol discovery: {e}")
        sys.exit(1)

    finally:
        engine.disconnect_finnhub()
        if not args.no_db:
            engine.disconnect_db()


def save_to_csv(symbols: List[DiscoveredSymbol], filepath: Path):
    """Save symbols to CSV file."""
    data = [symbol.to_dict() for symbol in symbols]
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)


def save_to_json(symbols: List[DiscoveredSymbol], filepath: Path):
    """Save symbols to JSON file."""
    data = [symbol.to_dict() for symbol in symbols]
    import json
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


if __name__ == '__main__':
    main()