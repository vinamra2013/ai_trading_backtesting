#!/usr/bin/env python3
"""
Backtest Parser - Extract structured metrics from LEAN backtest output.

Parses LEAN CLI backtest stdout to extract:
- Performance metrics (return, Sharpe, drawdown, etc.)
- Trade log with entry/exit details
- Equity curve for visualization
- Monthly returns for heatmap

Track A: Parser & Core Infrastructure
"""

import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BacktestParser:
    """
    Parse LEAN backtest output into structured data.

    LEAN outputs statistics in a text-based format with sections like:
    - STATISTICS
    - ORDERS
    - TRADES
    """

    def __init__(self):
        """Initialize parser with regex patterns."""
        # Common patterns for parsing LEAN output
        self.metric_pattern = re.compile(r'^\s*([^:]+):\s+(.+)$')
        self.trade_pattern = re.compile(
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(\w+)\s+(\w+)\s+([\d.]+)\s+@\s+\$([\d.]+)'
        )

    def parse(self, backtest_output: str, backtest_id: str, algorithm: str,
              start: str, end: str) -> Dict[str, Any]:
        """
        Parse complete backtest output.

        Args:
            backtest_output: Raw stdout from LEAN backtest
            backtest_id: Unique identifier for this backtest
            algorithm: Path to algorithm
            start: Start date YYYY-MM-DD
            end: End date YYYY-MM-DD

        Returns:
            Structured dictionary with metrics, trades, equity curve, etc.
        """
        logger.info(f"Parsing backtest output for {backtest_id}")

        try:
            # Extract different sections
            metrics = self._parse_statistics(backtest_output)
            trades = self._parse_trades(backtest_output)
            equity_curve = self._generate_equity_curve(trades, metrics)
            monthly_returns = self._calculate_monthly_returns(trades)

            result = {
                "backtest_id": backtest_id,
                "algorithm": algorithm,
                "period": {
                    "start": start,
                    "end": end
                },
                "metrics": metrics,
                "trades": trades,
                "trade_count": len(trades),
                "equity_curve": equity_curve,
                "monthly_returns": monthly_returns,
                "parsed_at": datetime.now().isoformat()
            }

            logger.info(f"✓ Parsed {len(trades)} trades and {len(metrics)} metrics")
            return result

        except Exception as e:
            logger.error(f"Failed to parse backtest output: {e}")
            # Return minimal structure on parse failure
            return {
                "backtest_id": backtest_id,
                "algorithm": algorithm,
                "period": {"start": start, "end": end},
                "metrics": {},
                "trades": [],
                "trade_count": 0,
                "equity_curve": [],
                "monthly_returns": {},
                "parse_error": str(e),
                "parsed_at": datetime.now().isoformat()
            }

    def _parse_statistics(self, output: str) -> Dict[str, Any]:
        """
        Extract performance metrics from STATISTICS section.

        Looks for patterns like:
        Total Trades                     123
        Average Win                      1.5%
        Sharpe Ratio                     1.82
        """
        metrics = {}

        # Find statistics section
        stats_section = self._extract_section(output, "STATISTICS")
        if not stats_section:
            logger.warning("No STATISTICS section found in output")
            return self._generate_default_metrics()

        # Parse key metrics
        metric_mappings = {
            # Returns
            'Total Net Profit': ('total_return', self._parse_percentage),
            'Net Profit': ('total_return', self._parse_percentage),
            'Compounding Annual Return': ('annualized_return', self._parse_percentage),
            'Annual Return': ('annualized_return', self._parse_percentage),

            # Risk metrics
            'Sharpe Ratio': ('sharpe_ratio', float),
            'Sortino Ratio': ('sortino_ratio', float),
            'Probabilistic Sharpe Ratio': ('prob_sharpe_ratio', self._parse_percentage),
            'Drawdown': ('max_drawdown', self._parse_percentage),
            'Max Drawdown': ('max_drawdown', self._parse_percentage),

            # Trading metrics
            'Total Trades': ('trade_count', int),
            'Win Rate': ('win_rate', self._parse_percentage),
            'Average Win': ('avg_win', self._parse_percentage),
            'Average Loss': ('avg_loss', self._parse_percentage),
            'Profit-Loss Ratio': ('profit_factor', float),
            'Profit Factor': ('profit_factor', float),

            # Other metrics
            'Alpha': ('alpha', float),
            'Beta': ('beta', float),
            'Annual Standard Deviation': ('annual_std', self._parse_percentage),
            'Information Ratio': ('information_ratio', float),
            'Tracking Error': ('tracking_error', self._parse_percentage),

            # Cost metrics
            'Total Fees': ('total_fees', self._parse_currency),
            'Average Slippage': ('average_slippage', self._parse_percentage),
            'Total Slippage': ('total_slippage', self._parse_currency),
        }

        for line in stats_section.split('\n'):
            for pattern, (key, converter) in metric_mappings.items():
                if pattern in line:
                    try:
                        # Extract value (everything after the metric name)
                        value_str = line.split(pattern)[-1].strip()
                        # Clean up common formatting
                        value_str = value_str.replace('$', '').replace(',', '').strip()

                        if value_str and value_str != '-' and value_str.lower() != 'nan':
                            metrics[key] = converter(value_str)
                            break
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Failed to parse {pattern}: {e}")
                        continue

        # Fill in missing metrics with defaults
        return self._fill_default_metrics(metrics)

    def _parse_trades(self, output: str) -> List[Dict[str, Any]]:
        """
        Extract trade log from backtest output.

        Each trade should have:
        - symbol, entry_date, entry_price, exit_date, exit_price
        - pnl, return_pct, duration_days
        """
        trades = []

        # Look for TRADES or ORDERS section
        trades_section = self._extract_section(output, "TRADES")
        if not trades_section:
            trades_section = self._extract_section(output, "ORDERS")

        if not trades_section:
            logger.warning("No TRADES/ORDERS section found")
            return []

        # Parse trade pairs (entry + exit)
        # LEAN format example:
        # 2020-01-02 09:30:00  SPY  BUY   100 @ $324.87
        # 2020-01-03 15:55:00  SPY  SELL  100 @ $325.12

        lines = trades_section.split('\n')
        open_positions = {}  # Track open positions by symbol

        for line in lines:
            match = self.trade_pattern.search(line)
            if match:
                timestamp_str, symbol, side, quantity_str, price_str = match.groups()

                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    quantity = float(quantity_str)
                    price = float(price_str)

                    if side.upper() in ['BUY', 'LONG']:
                        # Open position
                        open_positions[symbol] = {
                            'symbol': symbol,
                            'entry_date': timestamp.isoformat(),
                            'entry_price': price,
                            'quantity': quantity
                        }
                    elif side.upper() in ['SELL', 'SHORT', 'CLOSE']:
                        # Close position
                        if symbol in open_positions:
                            entry = open_positions.pop(symbol)

                            # Calculate trade metrics
                            pnl = (price - entry['entry_price']) * entry['quantity']
                            return_pct = ((price - entry['entry_price']) / entry['entry_price']) * 100
                            duration = (timestamp - datetime.fromisoformat(entry['entry_date'])).days

                            trade = {
                                'symbol': symbol,
                                'entry_date': entry['entry_date'],
                                'entry_price': entry['entry_price'],
                                'exit_date': timestamp.isoformat(),
                                'exit_price': price,
                                'quantity': entry['quantity'],
                                'pnl': round(pnl, 2),
                                'return_pct': round(return_pct, 2),
                                'duration_days': duration
                            }
                            trades.append(trade)

                except (ValueError, KeyError) as e:
                    logger.debug(f"Failed to parse trade line: {line} - {e}")
                    continue

        logger.info(f"Parsed {len(trades)} completed trades")
        return trades

    def _generate_equity_curve(self, trades: List[Dict], metrics: Dict) -> List[Dict[str, Any]]:
        """
        Generate equity curve from trade history.

        Returns list of {"date": "YYYY-MM-DD", "equity": float}
        """
        if not trades:
            return []

        # Start with initial capital (assume $100k default)
        initial_capital = 100000.0
        equity_curve = [{"date": trades[0]['entry_date'][:10], "equity": initial_capital}]

        current_equity = initial_capital

        # Build curve from cumulative P&L
        for trade in trades:
            current_equity += trade['pnl']
            equity_curve.append({
                "date": trade['exit_date'][:10],
                "equity": round(current_equity, 2)
            })

        return equity_curve

    def _calculate_monthly_returns(self, trades: List[Dict]) -> Dict[str, float]:
        """
        Calculate monthly returns for heatmap visualization.

        Returns: {"2020-01": 2.5, "2020-02": -1.2, ...}
        """
        if not trades:
            return {}

        monthly_pnl = {}

        for trade in trades:
            # Get month key (YYYY-MM)
            exit_date = trade['exit_date'][:7]  # Extract YYYY-MM

            if exit_date not in monthly_pnl:
                monthly_pnl[exit_date] = 0.0

            monthly_pnl[exit_date] += trade['pnl']

        # Convert to percentage returns (simplified - assumes constant capital)
        initial_capital = 100000.0
        monthly_returns = {}

        for month, pnl in monthly_pnl.items():
            return_pct = (pnl / initial_capital) * 100
            monthly_returns[month] = round(return_pct, 2)

        return monthly_returns

    # ===================================================================
    # Helper Methods
    # ===================================================================

    def _extract_section(self, output: str, section_name: str) -> Optional[str]:
        """
        Extract a specific section from LEAN output.

        Sections typically start with "SECTION_NAME:" or "=== SECTION_NAME ==="
        """
        # Try different section header patterns
        patterns = [
            f"=+\\s*{section_name}\\s*=+",  # === STATISTICS ===
            f"{section_name}:",  # STATISTICS:
            f"\\[{section_name}\\]",  # [STATISTICS]
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                # Extract from match to next section or end
                start_idx = match.end()

                # Find next section (or end of output)
                next_section = re.search(r'\n={3,}|\n\[', output[start_idx:])
                if next_section:
                    end_idx = start_idx + next_section.start()
                else:
                    end_idx = len(output)

                return output[start_idx:end_idx]

        return None

    def _parse_percentage(self, value: str) -> float:
        """Parse percentage string to float (e.g., '15.3%' -> 0.153)."""
        value = value.strip().replace('%', '')
        return float(value) / 100.0 if '%' in value else float(value)

    def _parse_currency(self, value: str) -> float:
        """Parse currency string to float (e.g., '$123.45' -> 123.45)."""
        return float(value.strip().replace('$', '').replace(',', ''))

    def _generate_default_metrics(self) -> Dict[str, Any]:
        """Generate default metrics structure."""
        return {
            'total_return': 0.0,
            'annualized_return': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'trade_count': 0,
            'profit_factor': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'total_fees': 0.0,
            'average_slippage': 0.0,
            'total_slippage': 0.0
        }

    def _fill_default_metrics(self, metrics: Dict) -> Dict[str, Any]:
        """Fill in missing metrics with defaults."""
        defaults = self._generate_default_metrics()
        return {**defaults, **metrics}


def parse_backtest(backtest_output: str, backtest_id: str, algorithm: str,
                   start: str, end: str) -> Dict[str, Any]:
    """
    Convenience function for parsing backtest output.

    Args:
        backtest_output: Raw LEAN stdout
        backtest_id: Unique backtest identifier
        algorithm: Algorithm path
        start: Start date YYYY-MM-DD
        end: End date YYYY-MM-DD

    Returns:
        Parsed backtest results dictionary
    """
    parser = BacktestParser()
    return parser.parse(backtest_output, backtest_id, algorithm, start, end)


if __name__ == "__main__":
    # Test parser with sample output
    sample_output = """
    === STATISTICS ===
    Total Net Profit             15.3%
    Sharpe Ratio                 1.82
    Max Drawdown                 -12.4%
    Total Trades                 45
    Win Rate                     64.5%

    === TRADES ===
    2020-01-02 09:30:00  SPY  BUY   100 @ $324.87
    2020-01-03 15:55:00  SPY  SELL  100 @ $325.12
    """

    result = parse_backtest(sample_output, "test-123", "algorithms/test",
                           "2020-01-01", "2020-12-31")

    import json
    print(json.dumps(result, indent=2))
