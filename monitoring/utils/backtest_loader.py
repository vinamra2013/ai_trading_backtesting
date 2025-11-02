"""
Backtest Data Loader for Streamlit Dashboard
Loads and processes backtest results from JSON files
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BacktestLoader:
    """Load and process backtest results from JSON files."""

    def __init__(self, results_dir: str = "/app/results/backtests"):
        """
        Initialize backtest loader.

        Args:
            results_dir: Directory containing backtest JSON files
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def list_backtests(self) -> List[Dict[str, Any]]:
        """
        List all available backtests.

        Returns:
            List of backtest summary dictionaries
        """
        backtests = []

        try:
            for json_file in self.results_dir.glob("*.json"):
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)

                    # Extract summary information
                    backtest_id = json_file.stem
                    summary = self._extract_summary(data, backtest_id)
                    backtests.append(summary)

                except Exception as e:
                    logger.error(f"Error loading {json_file}: {e}")
                    continue

            # Sort by date (most recent first)
            backtests.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        except Exception as e:
            logger.error(f"Error listing backtests: {e}")

        return backtests

    def load_backtest(self, backtest_id: str) -> Optional[Dict[str, Any]]:
        """
        Load full backtest data by ID.

        Args:
            backtest_id: Backtest UUID or filename

        Returns:
            Full backtest data dictionary or None
        """
        json_file = self.results_dir / f"{backtest_id}.json"

        if not json_file.exists():
            logger.error(f"Backtest file not found: {json_file}")
            return None

        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            # Add derived fields
            data['backtest_id'] = backtest_id

            return data

        except Exception as e:
            logger.error(f"Error loading backtest {backtest_id}: {e}")
            return None

    def _extract_summary(self, data: Dict, backtest_id: str) -> Dict[str, Any]:
        """
        Extract summary information from backtest data.

        Args:
            data: Full backtest data
            backtest_id: Backtest identifier

        Returns:
            Summary dictionary
        """
        # Parse metrics from data structure
        metrics = data.get('metrics', {})
        statistics = data.get('Statistics', {})
        runtime_statistics = data.get('RuntimeStatistics', {})

        # Extract key metrics (adapt based on actual LEAN output structure)
        sharpe = self._safe_float(statistics.get('Sharpe Ratio', metrics.get('sharpe_ratio', 0)))
        total_return = self._safe_float(statistics.get('Total Net Profit', metrics.get('total_return', 0)))
        max_drawdown = self._safe_float(statistics.get('Drawdown', metrics.get('max_drawdown', 0)))
        win_rate = self._safe_float(statistics.get('Win Rate', metrics.get('win_rate', 0)))

        # Extract config
        config = data.get('config', {})
        algorithm = config.get('algorithm', data.get('algorithm', 'Unknown'))
        start_date = config.get('start_date', data.get('start_date', ''))
        end_date = config.get('end_date', data.get('end_date', ''))

        # Status
        status = data.get('status', data.get('completed', False) and 'COMPLETED' or 'FAILED')

        return {
            'backtest_id': backtest_id,
            'backtest_id_short': backtest_id[:8],
            'algorithm': algorithm,
            'start_date': start_date,
            'end_date': end_date,
            'sharpe': sharpe,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'status': status,
            'created_at': data.get('created_at', data.get('timestamp', '')),
            'trade_count': self._safe_int(statistics.get('Total Trades', metrics.get('trade_count', 0))),
        }

    def get_equity_curve(self, backtest_id: str) -> Optional[pd.DataFrame]:
        """
        Extract equity curve from backtest results.

        Args:
            backtest_id: Backtest identifier

        Returns:
            DataFrame with date and equity columns
        """
        data = self.load_backtest(backtest_id)
        if not data:
            return None

        try:
            # Try multiple possible locations for equity curve data
            equity_data = data.get('equity_curve', [])

            if not equity_data:
                # Try Charts.Series
                charts = data.get('Charts', {})
                strategy_equity = charts.get('Strategy Equity', {})
                series = strategy_equity.get('Series', {})
                equity_series = series.get('Equity', {})
                equity_data = equity_series.get('Values', [])

            if not equity_data:
                # Generate mock data from portfolio value snapshots
                portfolio_values = data.get('portfolio_values', [])
                if portfolio_values:
                    equity_data = portfolio_values

            if not equity_data:
                logger.warning(f"No equity curve data found for {backtest_id}")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(equity_data)

            # Handle different possible formats
            if 'x' in df.columns and 'y' in df.columns:
                df = df.rename(columns={'x': 'date', 'y': 'equity'})
            elif 'date' not in df.columns or 'equity' not in df.columns:
                # Assume first column is date, second is equity
                df.columns = ['date', 'equity']

            # Convert date to datetime
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')

            return df

        except Exception as e:
            logger.error(f"Error extracting equity curve for {backtest_id}: {e}")
            return None

    def get_trades(self, backtest_id: str) -> Optional[pd.DataFrame]:
        """
        Extract trade log from backtest results.

        Args:
            backtest_id: Backtest identifier

        Returns:
            DataFrame with trade details
        """
        data = self.load_backtest(backtest_id)
        if not data:
            return None

        try:
            # Try multiple possible locations for trade data
            trades = data.get('trades', [])

            if not trades:
                orders = data.get('Orders', {})
                trades = orders.get('trades', [])

            if not trades:
                logger.warning(f"No trade data found for {backtest_id}")
                return None

            df = pd.DataFrame(trades)

            # Standardize column names
            column_mapping = {
                'Symbol': 'symbol',
                'EntryTime': 'entry_date',
                'EntryPrice': 'entry_price',
                'ExitTime': 'exit_date',
                'ExitPrice': 'exit_price',
                'Quantity': 'quantity',
                'Direction': 'direction',
                'ProfitLoss': 'pnl',
                'MAE': 'mae',
                'MFE': 'mfe',
                'Duration': 'duration'
            }

            df = df.rename(columns=column_mapping)

            # Calculate derived fields if not present
            if 'pnl' not in df.columns and 'entry_price' in df.columns and 'exit_price' in df.columns:
                df['pnl'] = (df['exit_price'] - df['entry_price']) * df['quantity']

            if 'return_pct' not in df.columns and 'pnl' in df.columns and 'entry_price' in df.columns:
                df['return_pct'] = (df['pnl'] / (df['entry_price'] * df['quantity'])) * 100

            if 'duration' not in df.columns and 'entry_date' in df.columns and 'exit_date' in df.columns:
                df['entry_date'] = pd.to_datetime(df['entry_date'])
                df['exit_date'] = pd.to_datetime(df['exit_date'])
                df['duration'] = (df['exit_date'] - df['entry_date']).dt.days

            return df

        except Exception as e:
            logger.error(f"Error extracting trades for {backtest_id}: {e}")
            return None

    def get_monthly_returns(self, backtest_id: str) -> Optional[pd.DataFrame]:
        """
        Calculate monthly returns from equity curve.

        Args:
            backtest_id: Backtest identifier

        Returns:
            DataFrame with year, month, and return columns
        """
        equity_df = self.get_equity_curve(backtest_id)
        if equity_df is None or equity_df.empty:
            return None

        try:
            # Resample to monthly
            equity_df = equity_df.set_index('date')
            monthly = equity_df['equity'].resample('M').last()

            # Calculate monthly returns
            returns = monthly.pct_change() * 100

            # Create DataFrame with year and month
            df = pd.DataFrame({
                'year': returns.index.year,
                'month': returns.index.month,
                'return': returns.values
            })

            # Pivot for heatmap
            heatmap_df = df.pivot(index='year', columns='month', values='return')

            return heatmap_df

        except Exception as e:
            logger.error(f"Error calculating monthly returns for {backtest_id}: {e}")
            return None

    def get_drawdown_series(self, backtest_id: str) -> Optional[pd.DataFrame]:
        """
        Calculate drawdown series from equity curve.

        Args:
            backtest_id: Backtest identifier

        Returns:
            DataFrame with date and drawdown columns
        """
        equity_df = self.get_equity_curve(backtest_id)
        if equity_df is None or equity_df.empty:
            return None

        try:
            # Calculate running maximum
            equity_df['running_max'] = equity_df['equity'].cummax()

            # Calculate drawdown
            equity_df['drawdown'] = (equity_df['equity'] - equity_df['running_max']) / equity_df['running_max'] * 100

            return equity_df[['date', 'drawdown']]

        except Exception as e:
            logger.error(f"Error calculating drawdown for {backtest_id}: {e}")
            return None

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        """Safely convert value to float."""
        try:
            if isinstance(value, str):
                # Remove % sign if present
                value = value.replace('%', '')
            return float(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        """Safely convert value to int."""
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default
