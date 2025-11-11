#!/usr/bin/env python3
"""
Backtrader Backtest Execution Script
Epic 12: US-12.4 - Backtest Execution Script

Replaces LEAN backtest runner with Backtrader Cerebro execution
"""

import argparse
import sys
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Type, Dict, List
import importlib.util
import backtrader as bt

from scripts.cerebro_engine import CerebroEngine
from scripts.backtrader_analyzers import (
    IBPerformanceAnalyzer, CommissionAnalyzer, EquityCurveAnalyzer,
    MonthlyReturnsAnalyzer, TradeLogAnalyzer
)
from scripts.backtest_parser import BacktraderResultParser


class BacktestRunner:
    """Backtest execution runner for Backtrader strategies"""

    def __init__(self, config_path: str = '/app/config/backtest_config.yaml'):
        self.config_path = config_path
        self.results_dir = Path('/app/results/backtests')
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def load_strategy_class(self, strategy_path: str) -> Type[bt.Strategy]:
        """Dynamically load strategy class from file"""
        strategy_file = Path(strategy_path)
        if not strategy_file.exists():
            strategy_file = Path('/app') / strategy_path
            if not strategy_file.exists():
                raise FileNotFoundError(f"Strategy file not found: {strategy_path}")

        # Use unique module name based on file path to avoid conflicts
        module_name = strategy_file.stem + "_strategy_module"
        spec = importlib.util.spec_from_file_location(module_name, strategy_file)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module  # Register module in sys.modules for Backtrader
        spec.loader.exec_module(module)

        for item_name in dir(module):
            item = getattr(module, item_name)
            if isinstance(item, type) and issubclass(item, bt.Strategy) and item != bt.Strategy:
                return item

        raise ImportError(f"No Strategy class found in {strategy_path}")

    def run(self, strategy_path: str, symbols: List[str], start_date: str,
            end_date: str, strategy_params: Dict = None, resolution: str = 'Daily',
            export_csv: bool = False, export_text: bool = False) -> Dict:
        """Run backtest and return results

        Args:
            strategy_path: Path to strategy file
            symbols: List of symbols to trade
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD
            strategy_params: Optional strategy parameters
            resolution: Data resolution (Daily, Hour, Minute)
            export_csv: Export trades to CSV
            export_text: Export text summary report

        Returns:
            Backtest results dictionary
        """

        print(f"\n{'='*80}\nBACKTRADER BACKTEST RUNNER\n{'='*80}")

        backtest_id = str(uuid.uuid4())
        strategy_class = self.load_strategy_class(strategy_path)

        engine = CerebroEngine(self.config_path)
        engine.add_strategy(strategy_class, **(strategy_params or {}))

        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        engine.add_multiple_data(symbols=symbols, resolution=resolution,
                                fromdate=start_dt, todate=end_dt)

        engine.cerebro.addanalyzer(IBPerformanceAnalyzer, _name='ibperformance')
        engine.cerebro.addanalyzer(CommissionAnalyzer, _name='commission')
        engine.cerebro.addanalyzer(EquityCurveAnalyzer, _name='equity')
        engine.cerebro.addanalyzer(MonthlyReturnsAnalyzer, _name='monthly')
        engine.cerebro.addanalyzer(TradeLogAnalyzer, _name='tradelog')

        results = engine.run()
        strategy = results[0]

        ib_analysis = strategy.analyzers.ibperformance.get_analysis()
        commission_analysis = strategy.analyzers.commission.get_analysis()
        equity_analysis = strategy.analyzers.equity.get_analysis()
        monthly_analysis = strategy.analyzers.monthly.get_analysis()
        tradelog_analysis = strategy.analyzers.tradelog.get_analysis()

        backtest_results = {
            'backtest_id': backtest_id,
            'timestamp': datetime.now().isoformat(),
            'strategy': {
                'name': strategy_class.__name__,
                'path': strategy_path,
                'parameters': strategy_params or {},
            },
            'configuration': {
                'symbols': symbols,
                'start_date': start_date,
                'end_date': end_date,
                'resolution': resolution,
                'initial_capital': engine.config.get('initial_capital', 100000),
                'commission_scheme': engine.config.get('broker', {}).get('commission_scheme', 'ib_standard'),
            },
            'performance': {
                'initial_value': ib_analysis['initial_value'],
                'final_value': ib_analysis['final_value'],
                'total_return': ib_analysis['total_return'],
                'total_return_pct': ib_analysis['total_return_pct'],
                'sharpe_ratio': ib_analysis['sharpe_ratio'],
                'max_drawdown': ib_analysis['max_drawdown'],
                'max_drawdown_pct': ib_analysis['max_drawdown_pct'],
            },
            'trading': {
                'total_trades': ib_analysis['total_trades'],
                'winning_trades': ib_analysis['winning_trades'],
                'losing_trades': ib_analysis['losing_trades'],
                'win_rate': ib_analysis['win_rate'],
                'avg_win': ib_analysis['avg_win'],
                'avg_loss': ib_analysis['avg_loss'],
                'profit_factor': ib_analysis['profit_factor'],
            },
            'costs': {
                'total_commission': commission_analysis['total_commission'],
                'avg_commission_per_trade': commission_analysis['avg_commission_per_trade'],
                'total_pnl_gross': ib_analysis['total_pnl_gross'],
                'total_pnl_net': ib_analysis['total_pnl'],
            },
            'equity_curve': [
                {'datetime': e['datetime'].isoformat(), 'value': e['value']}
                for e in equity_analysis['equity_curve']
            ],
            'monthly_returns': monthly_analysis['monthly_returns'],
            'trades': tradelog_analysis['trades'],
        }

        output_file = self.results_dir / f"{backtest_id}.json"
        with open(output_file, 'w') as f:
            json.dump(backtest_results, f, indent=2)

        # Optional exports using parser
        if export_csv or export_text:
            parser = BacktraderResultParser()

            # Parse results for advanced exports
            parsed_results = parser.parse_cerebro_results(
                results, backtest_id, strategy_class.__name__, symbols,
                start_date, end_date, engine.config.get('initial_capital', 100000)
            )

            if export_csv:
                csv_file = self.results_dir / f"{backtest_id}_trades.csv"
                parser.export_to_csv(parsed_results, str(csv_file))
                print(f"   CSV export: {csv_file}")

            if export_text:
                text_file = self.results_dir / f"{backtest_id}_report.txt"
                text_report = parser.generate_text_report(parsed_results)
                with open(text_file, 'w') as f:
                    f.write(text_report)
                print(f"   Text report: {text_file}")

        print(f"\n{'='*80}\nBACKTEST COMPLETE\n{'='*80}")
        print(f"\n📈 Performance: ${backtest_results['performance']['initial_value']:,.2f} → ${backtest_results['performance']['final_value']:,.2f} ({backtest_results['performance']['total_return_pct']:.2f}%)")
        print(f"   Sharpe: {backtest_results['performance']['sharpe_ratio']:.2f} | Max DD: {backtest_results['performance']['max_drawdown_pct']:.2f}%")
        print(f"\n📊 Trading: {backtest_results['trading']['total_trades']} trades | Win Rate: {backtest_results['trading']['win_rate']:.2f}%")
        print(f"\n💾 Results: {output_file}\n{'='*80}\n")

        return backtest_results


def main():
    parser = argparse.ArgumentParser(description='Run Backtrader backtest')
    parser.add_argument('--strategy', required=True, help='Strategy file path')
    parser.add_argument('--symbols', nargs='+', required=True, help='Symbols')
    parser.add_argument('--start', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--resolution', default='Daily', help='Resolution')
    parser.add_argument('--params', type=json.loads, default={}, help='Strategy params as JSON')
    parser.add_argument('--config', default='/app/config/backtest_config.yaml', help='Config file')
    parser.add_argument('--export-csv', action='store_true', help='Export trades to CSV')
    parser.add_argument('--export-text', action='store_true', help='Export text summary report')

    args = parser.parse_args()
    runner = BacktestRunner(config_path=args.config)

    try:
        runner.run(strategy_path=args.strategy, symbols=args.symbols,
                  start_date=args.start, end_date=args.end,
                  strategy_params=args.params, resolution=args.resolution,
                  export_csv=args.export_csv, export_text=args.export_text)
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
