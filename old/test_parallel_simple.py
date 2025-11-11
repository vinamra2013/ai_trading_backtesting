#!/usr/bin/env python3
"""
Simple test script for parallel backtesting functionality
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from concurrent.futures import ProcessPoolExecutor
import pandas as pd
import time

def run_single_backtest(strategy_name, symbol, start_date, end_date):
    """Run a single backtest job"""
    try:
        # Import here to avoid issues
        from scripts.run_backtest import BacktestRunner

        runner = BacktestRunner()
        strategy_class = strategy_name.title().replace('_', '')
        strategy_path = f"strategies.{strategy_name}.{strategy_class}"
        result = runner.run(
            strategy_path=strategy_path,
            symbols=[symbol],
            start_date=start_date,
            end_date=end_date,
            strategy_params={}
        )

        return {
            'strategy': strategy_name,
            'symbol': symbol,
            'success': True,
            'sharpe_ratio': result.get('sharpe_ratio', 0) if result else 0,
            'total_return': result.get('total_return', 0) if result else 0
        }
    except Exception as e:
        return {
            'strategy': strategy_name,
            'symbol': symbol,
            'success': False,
            'error': str(e)
        }

def main():
    print("🧪 Testing Parallel Backtesting Implementation")
    print("=" * 50)

    # Test parameters
    symbols = ['SPY', 'QQQ']
    strategies = ['sma_crossover', 'rsi_momentum']
    start_date = '2020-01-01'
    end_date = '2024-12-31'

    # Generate job combinations
    jobs = []
    for symbol in symbols:
        for strategy in strategies:
            jobs.append((strategy, symbol, start_date, end_date))

    print(f"📊 Running {len(jobs)} parallel backtests...")

    start_time = time.time()

    # Run parallel execution
    results = []
    with ProcessPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(run_single_backtest, *job) for job in jobs]

        for future in futures:
            result = future.result()
            results.append(result)
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['strategy']} on {result['symbol']}: {result.get('sharpe_ratio', 'Failed')}")

    end_time = time.time()
    duration = end_time - start_time

    # Summary
    successful = sum(1 for r in results if r['success'])
    print(f"\n📈 Results Summary:")
    print(f"   Total jobs: {len(jobs)}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {len(jobs) - successful}")
    print(f"   Execution time: {duration:.2f}s")

    if successful > 0:
        avg_sharpe = sum(r.get('sharpe_ratio', 0) for r in results if r['success']) / successful
        print(f"   Average Sharpe ratio: {avg_sharpe:.2f}")
        print("🎉 Parallel backtesting test completed successfully!")
    else:
        print("❌ All backtests failed")

if __name__ == "__main__":
    main()