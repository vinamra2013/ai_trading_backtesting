#!/usr/bin/env python3
"""
Backtest Parser - Extract structured metrics from Backtrader analyzer output.

Parses Backtrader Cerebro results to extract:
- Performance metrics (Sharpe, drawdown, returns)
- Trade log with entry/exit details
- Equity curve for visualization
- Monthly returns for heatmap
- Commission analysis

Epic 12: US-12.5 - Backtest Result Parser (Backtrader)
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BacktraderResultParser:
    """
    Parse Backtrader Cerebro analyzer results into structured data.

    Works with custom analyzers from scripts/backtrader_analyzers.py:
    - IBPerformanceAnalyzer: Comprehensive metrics
    - CommissionAnalyzer: Commission breakdown
    - EquityCurveAnalyzer: Portfolio value tracking
    - MonthlyReturnsAnalyzer: Monthly performance
    - TradeLogAnalyzer: Individual trade details

    Also parses standard Backtrader analyzers:
    - SharpeRatio, DrawDown, Returns, TradeAnalyzer, TimeReturn
    """

    def __init__(self):
        """Initialize parser."""
        pass

    def parse_cerebro_results(self, cerebro_results, backtest_id: str,
                             strategy_name: str, symbols: List[str],
                             start_date: str, end_date: str,
                             initial_cash: float = 100000.0) -> Dict[str, Any]:
        """
        Parse Backtrader Cerebro run() results.

        Args:
            cerebro_results: List returned by cerebro.run()
            backtest_id: Unique identifier (UUID)
            strategy_name: Strategy class name or path
            symbols: List of symbols traded
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD
            initial_cash: Initial portfolio value

        Returns:
            Structured dictionary with all metrics and trade data
        """
        logger.info(f"Parsing Backtrader results for {backtest_id}")

        try:
            # Get first strategy instance
            strategy = cerebro_results[0]

            # Extract analyzer results
            analyzers = self._extract_all_analyzers(strategy)

            # Parse different data sources
            metrics = self._parse_metrics(analyzers, initial_cash, strategy.broker.getvalue())
            trades = self._parse_trades(analyzers)
            equity_curve = self._parse_equity_curve(analyzers)
            monthly_returns = self._parse_monthly_returns(analyzers)
            commission_data = self._parse_commissions(analyzers)

            # Build comprehensive result structure
            result = {
                "backtest_id": backtest_id,
                "strategy": strategy_name,
                "symbols": symbols,
                "period": {
                    "start": start_date,
                    "end": end_date
                },
                "initial_cash": initial_cash,
                "final_value": strategy.broker.getvalue(),
                "metrics": metrics,
                "trades": trades,
                "trade_count": len(trades),
                "equity_curve": equity_curve,
                "monthly_returns": monthly_returns,
                "commissions": commission_data,
                "parsed_at": datetime.now().isoformat()
            }

            logger.info(f"✓ Parsed {len(trades)} trades and {len(metrics)} metrics")
            return result

        except Exception as e:
            logger.error(f"Failed to parse Backtrader results: {e}", exc_info=True)
            return self._generate_error_result(backtest_id, strategy_name,
                                              symbols, start_date, end_date, str(e))

    def _extract_all_analyzers(self, strategy) -> Dict[str, Any]:
        """
        Extract all analyzer results from strategy.

        Returns dict with analyzer name -> get_analysis() result
        """
        analyzers = {}

        # Iterate through all analyzers attached to strategy
        if hasattr(strategy, 'analyzers'):
            for analyzer_name in dir(strategy.analyzers):
                if not analyzer_name.startswith('_'):
                    analyzer = getattr(strategy.analyzers, analyzer_name)
                    try:
                        analysis = analyzer.get_analysis()
                        analyzers[analyzer_name] = analysis
                        logger.debug(f"Extracted analyzer: {analyzer_name}")
                    except Exception as e:
                        logger.warning(f"Failed to extract {analyzer_name}: {e}")

        return analyzers

    def _parse_metrics(self, analyzers: Dict, initial_cash: float,
                      final_value: float) -> Dict[str, Any]:
        """
        Extract performance metrics from analyzers.

        Combines data from:
        - IBPerformanceAnalyzer (custom)
        - Standard Backtrader analyzers (SharpeRatio, DrawDown, etc.)
        """
        metrics = {}

        # Try custom IBPerformanceAnalyzer first
        if 'ibperformance' in analyzers:
            ib_perf = analyzers['ibperformance']
            metrics.update({
                'total_trades': ib_perf.get('total_trades', 0),
                'winning_trades': ib_perf.get('winning_trades', 0),
                'losing_trades': ib_perf.get('losing_trades', 0),
                'win_rate': ib_perf.get('win_rate', 0.0),
                'profit_factor': ib_perf.get('profit_factor', 0.0),
                'avg_win': ib_perf.get('avg_win', 0.0),
                'avg_loss': ib_perf.get('avg_loss', 0.0),
                'sharpe_ratio': ib_perf.get('sharpe_ratio', 0.0),
                'max_drawdown': ib_perf.get('max_drawdown_pct', 0.0),
                'total_return_pct': ib_perf.get('total_return_pct', 0.0),
                'total_pnl': ib_perf.get('total_pnl', 0.0),
            })

        # Standard Sharpe Ratio analyzer
        if 'sharperatio' in analyzers:
            sharpe_analysis = analyzers['sharperatio']
            if isinstance(sharpe_analysis, dict):
                metrics['sharpe_ratio'] = sharpe_analysis.get('sharperatio', 0.0)

        # Standard DrawDown analyzer
        if 'drawdown' in analyzers:
            dd_analysis = analyzers['drawdown']
            if isinstance(dd_analysis, dict):
                max_dd = dd_analysis.get('max', {})
                if isinstance(max_dd, dict):
                    metrics['max_drawdown'] = max_dd.get('drawdown', 0.0)
                    metrics['max_drawdown_len'] = max_dd.get('len', 0)
                    metrics['max_drawdown_money'] = max_dd.get('moneydown', 0.0)

        # Standard Returns analyzer
        if 'returns' in analyzers:
            returns_analysis = analyzers['returns']
            if isinstance(returns_analysis, dict):
                metrics['total_return'] = returns_analysis.get('rtot', 0.0)
                metrics['annualized_return'] = returns_analysis.get('rnorm', 0.0)
                metrics['avg_annual_return'] = returns_analysis.get('rnorm100', 0.0)

        # Standard TradeAnalyzer
        if 'trades' in analyzers:
            trade_analysis = analyzers['trades']
            if isinstance(trade_analysis, dict):
                total = trade_analysis.get('total', {})
                won = trade_analysis.get('won', {})
                lost = trade_analysis.get('lost', {})

                if isinstance(total, dict):
                    metrics['total_trades'] = total.get('total', 0)

                if isinstance(won, dict) and isinstance(lost, dict):
                    won_count = won.get('total', 0)
                    lost_count = lost.get('total', 0)
                    total_count = won_count + lost_count

                    metrics['winning_trades'] = won_count
                    metrics['losing_trades'] = lost_count
                    metrics['win_rate'] = (won_count / total_count * 100) if total_count > 0 else 0.0

                    # Profit factor
                    won_pnl = won.get('pnl', {}).get('total', 0)
                    lost_pnl = abs(lost.get('pnl', {}).get('total', 0))
                    metrics['profit_factor'] = (won_pnl / lost_pnl) if lost_pnl > 0 else 0.0

        # Calculate total return if not already present
        if 'total_return_pct' not in metrics:
            metrics['total_return_pct'] = ((final_value / initial_cash) - 1) * 100

        # Fill in defaults for missing metrics
        return self._fill_default_metrics(metrics)

    def _parse_trades(self, analyzers: Dict) -> List[Dict[str, Any]]:
        """
        Extract individual trade records.

        Sources:
        - IBPerformanceAnalyzer.trades (preferred)
        - TradeLogAnalyzer.trades
        """
        trades = []

        # Try IBPerformanceAnalyzer first
        if 'ibperformance' in analyzers:
            ib_perf = analyzers['ibperformance']
            if 'trades' in ib_perf and isinstance(ib_perf['trades'], list):
                # Convert datetime objects to ISO strings
                for trade in ib_perf['trades']:
                    trade_copy = trade.copy()

                    # Convert datetime objects
                    if 'entry_date' in trade_copy and hasattr(trade_copy['entry_date'], 'isoformat'):
                        trade_copy['entry_date'] = trade_copy['entry_date'].isoformat()
                    if 'exit_date' in trade_copy and hasattr(trade_copy['exit_date'], 'isoformat'):
                        trade_copy['exit_date'] = trade_copy['exit_date'].isoformat()

                    trades.append(trade_copy)

                return trades

        # Try TradeLogAnalyzer
        if 'tradelog' in analyzers:
            tradelog = analyzers['tradelog']
            if 'trades' in tradelog and isinstance(tradelog['trades'], list):
                return tradelog['trades']

        logger.warning("No trade data found in analyzers")
        return []

    def _parse_equity_curve(self, analyzers: Dict) -> List[Dict[str, Any]]:
        """
        Extract equity curve data.

        Sources:
        - EquityCurveAnalyzer (preferred)
        - IBPerformanceAnalyzer.equity_curve
        - TimeReturn analyzer
        """
        equity_curve = []

        # Try EquityCurveAnalyzer
        if 'equity' in analyzers:
            equity_data = analyzers['equity']
            if 'equity_curve' in equity_data:
                for point in equity_data['equity_curve']:
                    equity_curve.append({
                        'datetime': point['datetime'].isoformat() if hasattr(point['datetime'], 'isoformat') else str(point['datetime']),
                        'value': point['value']
                    })
                return equity_curve

        # Try IBPerformanceAnalyzer
        if 'ibperformance' in analyzers:
            ib_perf = analyzers['ibperformance']
            if 'equity_curve' in ib_perf:
                for point in ib_perf['equity_curve']:
                    equity_curve.append({
                        'datetime': point['datetime'].isoformat() if hasattr(point['datetime'], 'isoformat') else str(point['datetime']),
                        'value': point['value']
                    })
                return equity_curve

        # Try TimeReturn analyzer
        if 'timereturn' in analyzers:
            tr_data = analyzers['timereturn']
            if isinstance(tr_data, dict):
                for date, ret in sorted(tr_data.items()):
                    equity_curve.append({
                        'datetime': str(date),
                        'return': ret
                    })

        return equity_curve

    def _parse_monthly_returns(self, analyzers: Dict) -> Dict[str, float]:
        """
        Extract monthly returns.

        Sources:
        - MonthlyReturnsAnalyzer (preferred)
        - Calculate from trades if available
        """
        monthly_returns = {}

        # Try MonthlyReturnsAnalyzer
        if 'monthly' in analyzers:
            monthly_data = analyzers['monthly']
            if 'monthly_returns' in monthly_data:
                return monthly_data['monthly_returns']

        # Calculate from trades if available
        if 'ibperformance' in analyzers:
            ib_perf = analyzers['ibperformance']
            if 'trades' in ib_perf:
                monthly_pnl = {}

                for trade in ib_perf['trades']:
                    exit_date = trade.get('exit_date')
                    if exit_date:
                        # Extract YYYY-MM
                        if hasattr(exit_date, 'strftime'):
                            month_key = exit_date.strftime('%Y-%m')
                        else:
                            month_key = str(exit_date)[:7]

                        if month_key not in monthly_pnl:
                            monthly_pnl[month_key] = 0.0

                        monthly_pnl[month_key] += trade.get('pnl_net', 0.0)

                # Convert to percentage (simplified)
                initial_capital = ib_perf.get('initial_value', 100000.0)
                for month, pnl in monthly_pnl.items():
                    monthly_returns[month] = round((pnl / initial_capital) * 100, 2)

        return monthly_returns

    def _parse_commissions(self, analyzers: Dict) -> Dict[str, Any]:
        """
        Extract commission data.

        Sources:
        - CommissionAnalyzer (preferred)
        - IBPerformanceAnalyzer.total_commission
        """
        commission_data = {
            'total': 0.0,
            'per_trade_avg': 0.0,
            'breakdown': []
        }

        # Try CommissionAnalyzer
        if 'commission' in analyzers:
            comm_data = analyzers['commission']
            commission_data['total'] = comm_data.get('total_commission', 0.0)
            commission_data['per_trade_avg'] = comm_data.get('avg_commission_per_trade', 0.0)
            commission_data['breakdown'] = comm_data.get('commission_breakdown', [])

        # Try IBPerformanceAnalyzer
        elif 'ibperformance' in analyzers:
            ib_perf = analyzers['ibperformance']
            commission_data['total'] = ib_perf.get('total_commission', 0.0)

            total_trades = ib_perf.get('total_trades', 0)
            if total_trades > 0:
                commission_data['per_trade_avg'] = commission_data['total'] / total_trades

        return commission_data

    def _fill_default_metrics(self, metrics: Dict) -> Dict[str, Any]:
        """Fill missing metrics with defaults."""
        defaults = {
            'total_return_pct': 0.0,
            'annualized_return': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'profit_factor': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'total_pnl': 0.0,
        }

        return {**defaults, **metrics}

    def _generate_error_result(self, backtest_id: str, strategy_name: str,
                               symbols: List[str], start_date: str,
                               end_date: str, error: str) -> Dict[str, Any]:
        """Generate minimal error result structure."""
        return {
            "backtest_id": backtest_id,
            "strategy": strategy_name,
            "symbols": symbols,
            "period": {"start": start_date, "end": end_date},
            "metrics": self._fill_default_metrics({}),
            "trades": [],
            "trade_count": 0,
            "equity_curve": [],
            "monthly_returns": {},
            "commissions": {'total': 0.0, 'per_trade_avg': 0.0, 'breakdown': []},
            "parse_error": error,
            "parsed_at": datetime.now().isoformat()
        }

    def export_to_json(self, result: Dict[str, Any], output_path: str):
        """
        Export parsed results to JSON file.

        Args:
            result: Parsed backtest result dictionary
            output_path: Path to output JSON file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)

        logger.info(f"✓ Exported results to {output_path}")

    def export_to_csv(self, result: Dict[str, Any], output_path: str):
        """
        Export trade log to CSV file.

        Args:
            result: Parsed backtest result dictionary
            output_path: Path to output CSV file
        """
        import csv

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        trades = result.get('trades', [])
        if not trades:
            logger.warning("No trades to export to CSV")
            return

        # Get all trade keys
        fieldnames = list(trades[0].keys())

        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(trades)

        logger.info(f"✓ Exported {len(trades)} trades to {output_path}")

    def generate_text_report(self, result: Dict[str, Any]) -> str:
        """
        Generate human-readable text summary.

        Args:
            result: Parsed backtest result dictionary

        Returns:
            Formatted text report string
        """
        metrics = result['metrics']

        report = f"""
========================================
BACKTEST RESULTS SUMMARY
========================================

Backtest ID: {result['backtest_id']}
Strategy: {result['strategy']}
Symbols: {', '.join(result['symbols'])}
Period: {result['period']['start']} to {result['period']['end']}
Initial Cash: ${result.get('initial_cash', 0):,.2f}
Final Value: ${result.get('final_value', 0):,.2f}

========================================
PERFORMANCE METRICS
========================================

Total Return:        {metrics.get('total_return_pct', 0):.2f}%
Annualized Return:   {metrics.get('annualized_return', 0):.2f}%
Sharpe Ratio:        {metrics.get('sharpe_ratio', 0):.2f}
Max Drawdown:        {metrics.get('max_drawdown', 0):.2f}%

========================================
TRADING STATISTICS
========================================

Total Trades:        {metrics.get('total_trades', 0)}
Winning Trades:      {metrics.get('winning_trades', 0)}
Losing Trades:       {metrics.get('losing_trades', 0)}
Win Rate:            {metrics.get('win_rate', 0):.1f}%
Profit Factor:       {metrics.get('profit_factor', 0):.2f}

Average Win:         ${metrics.get('avg_win', 0):.2f}
Average Loss:        ${metrics.get('avg_loss', 0):.2f}

========================================
COSTS
========================================

Total Commissions:   ${result.get('commissions', {}).get('total', 0):.2f}
Avg per Trade:       ${result.get('commissions', {}).get('per_trade_avg', 0):.2f}

========================================
"""

        return report


def parse_backtest_results(cerebro_results, backtest_id: str,
                          strategy_name: str, symbols: List[str],
                          start_date: str, end_date: str,
                          initial_cash: float = 100000.0) -> Dict[str, Any]:
    """
    Convenience function for parsing Backtrader results.

    Args:
        cerebro_results: Results from cerebro.run()
        backtest_id: Unique identifier
        strategy_name: Strategy class name
        symbols: List of symbols
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        initial_cash: Initial portfolio value

    Returns:
        Parsed results dictionary
    """
    parser = BacktraderResultParser()
    return parser.parse_cerebro_results(
        cerebro_results, backtest_id, strategy_name,
        symbols, start_date, end_date, initial_cash
    )


if __name__ == "__main__":
    # Test with mock data
    print("Backtrader Result Parser - Ready for use")
    print("Usage:")
    print("  from scripts.backtest_parser import parse_backtest_results")
    print("  results = cerebro.run()")
    print("  parsed = parse_backtest_results(results, uuid, strategy, symbols, start, end)")
