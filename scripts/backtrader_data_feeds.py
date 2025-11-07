"""
Backtrader Data Feeds for IB Integration
Epic 11: US-11.4 - Data Download Pipeline

Provides custom Backtrader data feeds for:
- CSV files (downloaded from IB)
- Live IB data streaming
- Pandas DataFrame integration
"""

import os
import pandas as pd
import backtrader as bt
from datetime import datetime
from typing import Optional
from ib_insync import IB, Stock, util
from scripts.ib_connection import IBConnectionManager


class IBCSVData(bt.feeds.GenericCSVData):
    """
    Custom CSV data feed for IB-downloaded data

    Assumes CSV format from IB historical data downloads:
    timestamp,open,high,low,close,volume
    """

    params = (
        ('dtformat', '%Y-%m-%d %H:%M:%S'),
        ('datetime', 0),
        ('open', 1),
        ('high', 2),
        ('low', 3),
        ('close', 4),
        ('volume', 5),
        ('openinterest', -1),  # Not provided by IB
    )


class DatabentoCSVData(bt.feeds.GenericCSVData):
    """
    Custom CSV data feed for Databento 1-minute OHLCV data

    Assumes CSV format from Databento:
    ts_event,rtype,publisher_id,instrument_id,open,high,low,close,volume,symbol
    """

    params = (
        ('dtformat', '%Y-%m-%dT%H:%M:%S.%fZ'),  # ISO format with microseconds and Z timezone
        ('datetime', 0),      # ts_event column
        ('open', 4),          # open column
        ('high', 5),          # high column
        ('low', 6),           # low column
        ('close', 7),         # close column
        ('volume', 8),        # volume column
        ('openinterest', -1), # Not provided
    )

    def _loadline(self, linetokens):
        """
        Override to handle Databento timestamp format with variable microsecond precision
        """
        # Handle the timestamp format - Databento uses 9 digits for microseconds
        # but Python strptime expects 1-6. We'll truncate to 6 digits.
        if len(linetokens) > 0:
            ts_str = linetokens[0]
            # Replace .000000000Z with .000000Z to match %f format
            if ts_str.endswith('.000000000Z'):
                linetokens[0] = ts_str.replace('.000000000Z', '.000000Z')

        return super()._loadline(linetokens)


class IBPandasData(bt.feeds.PandasData):
    """
    Pandas DataFrame data feed for IB data

    Expects DataFrame with columns:
    - datetime (index)
    - open, high, low, close, volume
    """

    params = (
        ('datetime', None),  # Use index
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('openinterest', None),
    )


class IBLiveData(bt.DataBase):
    """
    Live data feed from Interactive Brokers

    Streams real-time market data from IB Gateway
    """

    params = (
        ('symbol', ''),
        ('exchange', 'SMART'),
        ('currency', 'USD'),
        ('sectype', 'STK'),  # Stock
        ('host', 'ib-gateway'),
        ('port', 4001),
        ('client_id', 1),
        ('timeframe', bt.TimeFrame.Ticks),  # Ticks, Minutes, Days
        ('compression', 1),
    )

    def __init__(self):
        super(IBLiveData, self).__init__()

        self.ib_manager = None
        self.contract = None
        self.live = False
        self._data_queue = []

    def start(self):
        """Called when the data feed is started"""
        super(IBLiveData, self).start()

        # Connect to IB Gateway
        self.ib_manager = IBConnectionManager(
            host=self.p.host,
            port=self.p.port,
            client_id=self.p.client_id,
            readonly=True  # Read-only for data feeds
        )

        if not self.ib_manager.connect():
            raise ConnectionError(f"Failed to connect to IB for live data: {self.p.symbol}")

        # Create contract
        self.contract = Stock(
            symbol=self.p.symbol,
            exchange=self.p.exchange,
            currency=self.p.currency
        )

        # Qualify contract
        qualified = self.ib_manager.ib.qualifyContracts(self.contract)
        if not qualified:
            raise ValueError(f"Could not qualify contract for {self.p.symbol}")

        self.contract = qualified[0]

        # Subscribe to market data
        self.ib_manager.ib.reqMktData(self.contract, '', False, False)

        self.live = True

    def stop(self):
        """Called when the data feed is stopped"""
        super(IBLiveData, self).stop()

        if self.ib_manager:
            # Unsubscribe from market data
            self.ib_manager.ib.cancelMktData(self.contract)
            self.ib_manager.disconnect()

        self.live = False

    def _load(self):
        """
        Load next data point

        Returns:
            bool: True if more data, False if done
        """
        if not self.live:
            return False

        try:
            # Get ticker data
            ticker = self.ib_manager.ib.ticker(self.contract)

            if ticker and ticker.time:
                # Update data lines
                self.lines.datetime[0] = bt.date2num(ticker.time)

                # For live ticks, use last/bid/ask to construct OHLC
                if ticker.last and ticker.last > 0:
                    self.lines.open[0] = ticker.last
                    self.lines.high[0] = ticker.last
                    self.lines.low[0] = ticker.last
                    self.lines.close[0] = ticker.last
                elif ticker.bid and ticker.ask:
                    mid = (ticker.bid + ticker.ask) / 2
                    self.lines.open[0] = mid
                    self.lines.high[0] = mid
                    self.lines.low[0] = mid
                    self.lines.close[0] = mid
                else:
                    return False  # No valid price data

                self.lines.volume[0] = ticker.volume if ticker.volume else 0
                self.lines.openinterest[0] = 0

                return True

            return False

        except Exception as e:
            print(f"Error loading live data: {e}")
            return False


def load_csv_data(
    filepath: str,
    fromdate: Optional[datetime] = None,
    todate: Optional[datetime] = None,
    name: str = None
) -> IBCSVData:
    """
    Load CSV data file into Backtrader feed

    Args:
        filepath: Path to CSV file
        fromdate: Start date filter
        todate: End date filter
        name: Data feed name

    Returns:
        IBCSVData: Configured data feed
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    data = IBCSVData(
        dataname=filepath,
        fromdate=fromdate,
        todate=todate,
        name=name or os.path.basename(filepath)
    )

    return data


def load_databento_data(
    filepath: str,
    fromdate: Optional[datetime] = None,
    todate: Optional[datetime] = None,
    name: str = None
) -> DatabentoCSVData:
    """
    Load Databento CSV data file into Backtrader feed

    Args:
        filepath: Path to Databento CSV file
        fromdate: Start date filter
        todate: End date filter
        name: Data feed name

    Returns:
        DatabentoCSVData: Configured data feed
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Databento CSV file not found: {filepath}")

    data = DatabentoCSVData(
        dataname=filepath,
        fromdate=fromdate,
        todate=todate,
        name=name or os.path.basename(filepath)
    )

    return data


def load_pandas_data(
    df: pd.DataFrame,
    fromdate: Optional[datetime] = None,
    todate: Optional[datetime] = None,
    name: str = None
) -> IBPandasData:
    """
    Load Pandas DataFrame into Backtrader feed

    Args:
        df: DataFrame with OHLCV data (datetime index)
        fromdate: Start date filter
        todate: End date filter
        name: Data feed name

    Returns:
        IBPandasData: Configured data feed
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame must have DatetimeIndex")

    required_cols = ['open', 'high', 'low', 'close', 'volume']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"DataFrame missing required columns: {missing_cols}")

    data = IBPandasData(
        dataname=df,
        fromdate=fromdate,
        todate=todate,
        name=name or 'pandas_data'
    )

    return data


def create_live_feed(
    symbol: str,
    exchange: str = 'SMART',
    currency: str = 'USD',
    host: str = 'ib-gateway',
    port: int = 4001,
    client_id: int = 1
) -> IBLiveData:
    """
    Create live IB data feed

    Args:
        symbol: Stock symbol
        exchange: Exchange code
        currency: Currency code
        host: IB Gateway host
        port: IB Gateway port
        client_id: Client identifier

    Returns:
        IBLiveData: Configured live feed
    """
    data = IBLiveData(
        symbol=symbol,
        exchange=exchange,
        currency=currency,
        host=host,
        port=port,
        client_id=client_id
    )

    return data


if __name__ == '__main__':
    """Test data feeds"""
    print("Testing Backtrader Data Feeds...")

    # Test CSV loading (if file exists)
    test_csv = '/app/data/csv/SPY_Daily.csv'
    if os.path.exists(test_csv):
        print(f"\n✅ Loading CSV: {test_csv}")
        data = load_csv_data(test_csv)
        print(f"   Data feed created: {data._name}")
    else:
        print(f"\n⚠️  Test CSV not found: {test_csv}")

    # Test Pandas loading
    print(f"\n✅ Creating test Pandas DataFrame...")
    test_df = pd.DataFrame({
        'open': [100.0, 101.0, 102.0],
        'high': [101.0, 102.0, 103.0],
        'low': [99.0, 100.0, 101.0],
        'close': [100.5, 101.5, 102.5],
        'volume': [1000000, 1100000, 1200000]
    }, index=pd.date_range('2024-01-01', periods=3, freq='D'))

    data = load_pandas_data(test_df, name='TEST')
    print(f"   Data feed created: {data._name}")

    print("\n✅ Data feeds tested successfully!")
