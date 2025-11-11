#!/usr/bin/env python3
"""
Performance Profiler for Distributed Backtesting
Epic 20: Performance Optimization

Profiles worker startup time and execution performance.
"""

import os
import sys
import time
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, '/app')


class PerformanceProfiler:
    """Profile performance of backtesting components"""

    def profile_worker_startup(self) -> Dict[str, Any]:
        """Profile worker startup performance"""
        start_time = time.time()

        # Import worker components
        import_steps = []

        # Step 1: Basic imports
        step_start = time.time()
        import os
        import json
        import logging
        from pathlib import Path
        from typing import Dict, Any, Optional
        from dataclasses import dataclass
        import traceback
        import signal
        step_time = time.time() - step_start
        import_steps.append(('basic_imports', step_time))

        # Step 2: BacktestRunner import
        step_start = time.time()
        from scripts.run_backtest import BacktestRunner
        step_time = time.time() - step_start
        import_steps.append(('backtest_runner', step_time))

        # Step 3: Worker initialization
        step_start = time.time()
        from scripts.backtest_worker import BacktestWorker
        worker = BacktestWorker()
        step_time = time.time() - step_start
        import_steps.append(('worker_init', step_time))

        total_time = time.time() - start_time

        return {
            'total_startup_time': total_time,
            'import_steps': import_steps
        }

    def profile_single_backtest(self, symbol: str = 'SPY', strategy: str = 'strategies/sma_crossover.py') -> Dict[str, Any]:
        """Profile a single backtest execution"""
        start_time = time.time()

        try:
            from scripts.run_backtest import BacktestRunner

            runner = BacktestRunner()
            result = runner.run(
                strategy_path=strategy,
                symbols=[symbol],
                start_date='2020-01-01',
                end_date='2024-12-31'
            )

            execution_time = time.time() - start_time

            return {
                'execution_time': execution_time,
                'success': True,
                'trades': result.get('trading', {}).get('total_trades', 0),
                'return_pct': result.get('performance', {}).get('total_return', 0)
            }

        except Exception as e:
            execution_time = time.time() - start_time

            return {
                'execution_time': execution_time,
                'success': False,
                'error': str(e)
            }

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            'timestamp': time.time()
        }

        # Profile startup
        print("Profiling worker startup...")
        report['startup_profile'] = self.profile_worker_startup()

        # Profile single backtest
        print("Profiling single backtest...")
        report['backtest_profile'] = self.profile_single_backtest()

        return report

    def print_report(self, report: Dict[str, Any]) -> None:
        """Print formatted performance report"""
        print("=" * 60)
        print("PERFORMANCE PROFILING REPORT")
        print("=" * 60)

        # Startup Profile
        startup = report['startup_profile']
        print("WORKER STARTUP PROFILE:")
        print(f"  Total Time: {startup['total_startup_time']:.3f}s")
        print("  Import Steps:")
        for step_name, step_time in startup['import_steps']:
            print(f"    {step_name}: {step_time:.3f}s")
        print()

        # Backtest Profile
        backtest = report['backtest_profile']
        print("SINGLE BACKTEST PROFILE:")
        print(f"  Execution Time: {backtest['execution_time']:.3f}s")
        print(f"  Success: {'✅' if backtest['success'] else '❌'}")
        if backtest['success']:
            print(f"  Trades: {backtest.get('trades', 0)}")
            print(f"  Return: {backtest.get('return_pct', 0):.1f}%")
        else:
            print(f"  Error: {backtest.get('error', 'Unknown')}")
        print()

        # Performance Analysis
        print("PERFORMANCE ANALYSIS:")
        startup_time = startup['total_startup_time']
        backtest_time = backtest['execution_time']

        if startup_time > 2.0:
            print("⚠️  Slow startup detected (>2s)")
        else:
            print("✅ Startup time acceptable")

        if backtest_time > 10.0:
            print("⚠️  Slow backtest execution detected (>10s)")
        else:
            print("✅ Backtest execution time acceptable")

        print("=" * 60)


def main():
    """Command line interface for profiling"""
    profiler = PerformanceProfiler()
    report = profiler.generate_report()
    profiler.print_report(report)


if __name__ == "__main__":
    main()