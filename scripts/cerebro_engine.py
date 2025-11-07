"""
Backtrader Cerebro Engine Wrapper
Epic 12: US-12.1 - Cerebro Framework Setup

High-level wrapper around Backtrader's Cerebro engine providing:
- Easy configuration from YAML files
- IB commission model integration
- Data feed management
- Analyzer setup
- Results extraction
"""

import backtrader as bt
import yaml
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Type
from scripts.ib_commissions import load_commission_from_config, get_commission_scheme
from scripts.backtrader_data_feeds import load_csv_data, load_pandas_data


class CerebroEngine:
    """
    Backtrader Cerebro engine wrapper with YAML configuration support
    """

    def __init__(self, config_path: str = 'config/backtest_config.yaml'):
        """
        Initialize Cerebro engine

        Args:
            config_path: Path to backtest configuration YAML file
        """
        self.cerebro = bt.Cerebro()
        self.config = self._load_config(config_path)
        self.results = None
        self.strategy_class = None

        # Configure broker from config
        self._configure_broker()

        # Configure analyzers from config
        self._configure_analyzers()

    def _load_config(self, config_path: str) -> dict:
        """
        Load configuration from YAML file

        Args:
            config_path: Path to YAML config file

        Returns:
            dict: Configuration dictionary
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        return config

    def _configure_broker(self):
        """Configure broker settings from config"""
        broker_config = self.config.get('broker', {})

        # Set initial cash
        initial_cash = broker_config.get('cash', 100000)
        self.cerebro.broker.set_cash(initial_cash)

        # Set commission scheme
        commission_scheme = broker_config.get('commission_scheme', 'ib_standard')
        commission = get_commission_scheme(commission_scheme)
        self.cerebro.broker.addcommissioninfo(commission)

        # Set slippage (if configured)
        slippage_perc = broker_config.get('slippage_perc', 0)
        if slippage_perc > 0:
            self.cerebro.broker.set_slippage_perc(slippage_perc)

    def _configure_analyzers(self):
        """Add analyzers from config"""
        analyzer_names = self.config.get('analyzers', [])

        # Map analyzer names to Backtrader analyzer classes
        analyzer_map = {
            'SharpeRatio': bt.analyzers.SharpeRatio,
            'DrawDown': bt.analyzers.DrawDown,
            'Returns': bt.analyzers.Returns,
            'TradeAnalyzer': bt.analyzers.TradeAnalyzer,
            'TimeReturn': bt.analyzers.TimeReturn,
            'SQN': bt.analyzers.SQN,  # System Quality Number
            'VWR': bt.analyzers.VWR,  # Variability-Weighted Return
            'Transactions': bt.analyzers.Transactions,
        }

        for analyzer_name in analyzer_names:
            if analyzer_name in analyzer_map:
                self.cerebro.addanalyzer(
                    analyzer_map[analyzer_name],
                    _name=analyzer_name.lower()
                )

    def add_strategy(
        self,
        strategy_class: Type[bt.Strategy],
        **params
    ):
        """
        Add strategy to Cerebro

        Args:
            strategy_class: Backtrader Strategy class
            **params: Strategy parameters
        """
        self.strategy_class = strategy_class
        self.cerebro.addstrategy(strategy_class, **params)

    def add_data(
        self,
        dataname,
        name: Optional[str] = None,
        fromdate: Optional[datetime] = None,
        todate: Optional[datetime] = None
    ):
        """
        Add data feed to Cerebro

        Args:
            dataname: Data source (CSV path, DataFrame, or DataFeed)
            name: Data feed name
            fromdate: Start date filter
            todate: End date filter
        """
        # If string, assume CSV file
        if isinstance(dataname, str):
            data = load_csv_data(
                dataname,
                fromdate=fromdate,
                todate=todate,
                name=name
            )
        # If already a DataFeed, use directly
        elif isinstance(dataname, bt.DataBase):
            data = dataname
        else:
            # Try to load as pandas DataFrame
            try:
                data = load_pandas_data(
                    dataname,
                    fromdate=fromdate,
                    todate=todate,
                    name=name
                )
            except:
                raise ValueError(f"Unsupported data type: {type(dataname)}")

        self.cerebro.adddata(data)

    def add_multiple_data(
        self,
        symbols: List[str],
        data_dir: Optional[str] = None,
        resolution: str = 'Daily',
        fromdate: Optional[datetime] = None,
        todate: Optional[datetime] = None
    ):
        """
        Add multiple CSV data feeds

        Args:
            symbols: List of stock symbols
            data_dir: Directory containing CSV files (uses config if None)
            resolution: Data resolution (for filename)
            fromdate: Start date filter
            todate: End date filter
        """
        if data_dir is None:
            data_dir = self.config.get('data', {}).get('data_dir', '/app/data/csv')
        data_path = Path(str(data_dir))

        for symbol in symbols:
            # Try the organized structure first: data/csv/resolution/symbol/
            symbol_dir = data_path / resolution / symbol
            csv_file = None

            if symbol_dir.exists():
                # Find the most recent CSV file for this symbol/resolution
                csv_files = list(symbol_dir.glob(f"{symbol}_{resolution}_*.csv"))
                if csv_files:
                    # Sort by modification time (most recent first)
                    csv_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    csv_file = csv_files[0]
                else:
                    print(f"⚠️  Warning: No CSV files found in {symbol_dir}")
            else:
                # Fallback to old structure: data/csv/symbol_resolution.csv
                csv_file = data_path / f"{symbol}_{resolution}.csv"
                if not csv_file.exists():
                    csv_file = None

            if csv_file is None or not csv_file.exists():
                print(f"⚠️  Warning: Data file not found for {symbol} in {resolution} resolution")
                continue

            self.add_data(
                str(csv_file),
                name=symbol,
                fromdate=fromdate,
                todate=todate
            )

    def run(self) -> List:
        """
        Run backtest

        Returns:
            List: Strategy instances with results
        """
        print(f"\n{'='*60}")
        print(f"STARTING BACKTEST")
        print(f"{'='*60}")
        print(f"Initial Portfolio Value: ${self.cerebro.broker.getvalue():,.2f}")

        self.results = self.cerebro.run()

        final_value = self.cerebro.broker.getvalue()
        print(f"\nFinal Portfolio Value: ${final_value:,.2f}")
        print(f"{'='*60}\n")

        return self.results

    def get_analyzer_results(self) -> Dict:
        """
        Extract analyzer results from backtest

        Returns:
            dict: Analyzer results
        """
        if not self.results:
            raise ValueError("No results available. Run backtest first.")

        strategy = self.results[0]
        analysis = {}

        # Extract each analyzer's results
        for analyzer_name, analyzer in strategy.analyzers.getitems():
            try:
                analysis[analyzer_name] = analyzer.get_analysis()
            except:
                analysis[analyzer_name] = None

        return analysis

    def get_trades(self) -> List[Dict]:
        """
        Extract trade log from TradeAnalyzer

        Returns:
            List[dict]: Trade records
        """
        if not self.results:
            raise ValueError("No results available. Run backtest first.")

        strategy = self.results[0]

        # Check if TradeAnalyzer was added
        if not hasattr(strategy.analyzers, 'tradeanalyzer'):
            return []

        trade_analysis = strategy.analyzers.tradeanalyzer.get_analysis()

        # Parse trades from analysis
        trades = []
        # Note: Backtrader's TradeAnalyzer provides summary stats, not individual trades
        # For individual trades, we'd need to log them in the strategy itself

        return trades

    def plot(self, **kwargs):
        """
        Plot backtest results

        Args:
            **kwargs: Plot configuration options
        """
        # Default plot settings
        plot_config = {
            'style': 'candlestick',
            'barup': 'green',
            'bardown': 'red',
            'volume': True,
        }
        plot_config.update(kwargs)

        self.cerebro.plot(**plot_config)

    def get_performance_summary(self) -> Dict:
        """
        Get comprehensive performance summary

        Returns:
            dict: Performance metrics
        """
        if not self.results:
            raise ValueError("No results available. Run backtest first.")

        analysis = self.get_analyzer_results()
        initial_value = self.config.get('broker', {}).get('cash', 100000)
        final_value = self.cerebro.broker.getvalue()

        summary = {
            'initial_value': initial_value,
            'final_value': final_value,
            'total_return': final_value - initial_value,
            'total_return_pct': ((final_value / initial_value) - 1) * 100,
            'sharpe_ratio': None,
            'max_drawdown': None,
            'max_drawdown_pct': None,
            'trade_count': 0,
            'win_rate': 0,
        }

        # Extract Sharpe Ratio
        if 'sharperatio' in analysis and analysis['sharperatio']:
            summary['sharpe_ratio'] = analysis['sharperatio'].get('sharperatio', None)

        # Extract Drawdown
        if 'drawdown' in analysis and analysis['drawdown']:
            dd = analysis['drawdown']
            summary['max_drawdown'] = dd.get('max', {}).get('drawdown', None)
            summary['max_drawdown_pct'] = dd.get('max', {}).get('drawdown', None)

        # Extract Trade Stats
        if 'tradeanalyzer' in analysis and analysis['tradeanalyzer']:
            ta = analysis['tradeanalyzer']
            total_trades = ta.get('total', {}).get('total', 0)
            won_trades = ta.get('won', {}).get('total', 0)

            summary['trade_count'] = total_trades
            summary['win_rate'] = (won_trades / total_trades * 100) if total_trades > 0 else 0

        return summary


if __name__ == '__main__':
    """Test Cerebro engine setup"""
    print("Testing Cerebro Engine...\n")

    try:
        # Initialize engine
        engine = CerebroEngine()

        print("✅ Cerebro engine initialized")
        print(f"   Initial Cash: ${engine.cerebro.broker.getvalue():,.2f}")
        print(f"   Analyzers: {list(engine.config.get('analyzers', []))}")
        print(f"   Commission Scheme: {engine.config.get('broker', {}).get('commission_scheme', 'ib_standard')}")

        print("\n✅ Cerebro engine tested successfully!")

    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
