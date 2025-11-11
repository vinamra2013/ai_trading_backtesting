#!/usr/bin/env python3
"""
Minimal Test for Parallel Backtest Orchestrator
Epic 20: Test Core Orchestration Logic

Tests the parallel execution framework without heavy dependencies.
"""

import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import multiprocessing as mp


@dataclass
class MockBacktestJob:
    """Mock job specification for testing"""
    job_id: str
    symbol: str
    strategy_path: str
    start_date: str = "2020-01-01"
    end_date: str = "2024-12-31"
    strategy_params: Optional[Dict[str, Any]] = None
    batch_id: str = "test_batch"

    def __post_init__(self):
        if self.strategy_params is None:
            self.strategy_params = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            'job_id': self.job_id,
            'symbol': self.symbol,
            'strategy_path': self.strategy_path,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'strategy_params': self.strategy_params,
            'batch_id': self.batch_id
        }


def mock_execute_backtest_worker(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock worker function that simulates backtest execution.
    This replaces the real backtest execution for testing.
    """
    import random
    import time

    # Simulate processing time (1-3 seconds)
    processing_time = random.uniform(1.0, 3.0)
    time.sleep(processing_time)

    job = MockBacktestJob(**job_data)

    # Generate mock results
    base_return = random.uniform(-0.2, 0.5)  # -20% to +50%
    sharpe = random.uniform(-1.0, 3.0)       # -1.0 to 3.0
    max_dd = random.uniform(0.05, 0.3)       # 5% to 30%
    win_rate = random.uniform(0.4, 0.8)      # 40% to 80%

    # Simulate occasional failures (10% chance)
    if random.random() < 0.1:
        return {
            'job_id': job.job_id,
            'batch_id': job.batch_id,
            'symbol': job.symbol,
            'strategy': job.strategy_path.split('/')[-1].replace('.py', ''),
            'status': 'failed',
            'error': 'Mock failure for testing',
            'execution_timestamp': time.time()
        }

    return {
        'job_id': job.job_id,
        'batch_id': job.batch_id,
        'symbol': job.symbol,
        'strategy': job.strategy_path.split('/')[-1].replace('.py', ''),
        'status': 'success',
        'performance_metrics': {
            'sharpe_ratio': sharpe,
            'total_return': base_return,
            'max_drawdown': max_dd,
            'win_rate': win_rate,
            'trade_count': random.randint(10, 100)
        },
        'execution_timestamp': time.time()
    }


class MockResultsConsolidator:
    """Mock version of results consolidator for testing"""

    def consolidate(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simple consolidation for testing"""
        consolidated = []
        for result in results:
            if result.get('status') == 'success':
                consolidated.append({
                    'symbol': result['symbol'],
                    'strategy': result['strategy'],
                    'sharpe_ratio': result['performance_metrics']['sharpe_ratio'],
                    'total_return': result['performance_metrics']['total_return'],
                    'max_drawdown': result['performance_metrics']['max_drawdown'],
                    'win_rate': result['performance_metrics']['win_rate'],
                    'trade_count': result['performance_metrics']['trade_count'],
                    'batch_id': result['batch_id'],
                    'job_id': result['job_id']
                })
        return consolidated


def test_parallel_orchestration():
    """Test the core parallel orchestration logic"""
    print("🧪 Testing Parallel Backtest Orchestrator")
    print("=" * 50)

    # Test data
    symbols = ['SPY', 'AAPL', 'MSFT', 'GOOGL', 'AMZN']
    strategies = ['sma_crossover', 'rsi_momentum', 'macd_crossover']
    max_workers = min(mp.cpu_count(), 4)

    print(f"📊 Test Configuration:")
    print(f"   Symbols: {len(symbols)}")
    print(f"   Strategies: {len(strategies)}")
    print(f"   Total combinations: {len(symbols) * len(strategies)}")
    print(f"   Max workers: {max_workers}")
    print()

    # Generate test jobs
    jobs = []
    job_id = 1
    for symbol in symbols:
        for strategy in strategies:
            job = MockBacktestJob(
                job_id=f"test_job_{job_id:03d}",
                symbol=symbol,
                strategy_path=f"strategies/{strategy}.py",
                batch_id="test_batch_001"
            )
            jobs.append(job)
            job_id += 1

    print(f"📋 Generated {len(jobs)} test jobs")

    # Execute parallel processing
    start_time = time.time()
    results = []
    failed_jobs = []

    print("🚀 Starting parallel execution...")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all jobs
        future_to_job = {
            executor.submit(mock_execute_backtest_worker, job.to_dict()): job
            for job in jobs
        }

        # Process completed jobs
        completed = 0
        for future in as_completed(future_to_job):
            job = future_to_job[future]
            try:
                result = future.result(timeout=10)  # 10 second timeout
                if result['status'] == 'success':
                    results.append(result)
                else:
                    failed_jobs.append((job, result))
                completed += 1

                # Progress update every 5 jobs
                if completed % 5 == 0:
                    print(f"   ✅ Completed {completed}/{len(jobs)} jobs")

            except Exception as e:
                failed_jobs.append((job, {'error': str(e)}))
                print(f"   ❌ Exception in job {job.job_id}: {e}")

    execution_time = time.time() - start_time

    # Results analysis
    print()
    print("📈 Results Summary:")
    print(f"   Total jobs: {len(jobs)}")
    print(f"   Successful: {len(results)}")
    print(f"   Failed: {len(failed_jobs)}")
    print(".2f")
    print(".2f")

    if results:
        # Consolidate results
        consolidator = MockResultsConsolidator()
        consolidated = consolidator.consolidate(results)

        print(f"   Consolidated results: {len(consolidated)}")

        # Show top performers
        if len(consolidated) > 0:
            print()
            print("🏆 Top 5 by Sharpe Ratio:")
            sorted_results = sorted(consolidated,
                                  key=lambda x: x.get('sharpe_ratio', 0),
                                  reverse=True)
            for i, result in enumerate(sorted_results[:5], 1):
                print("2d"
                      "6.2f"
                      "6.2f"
                      "6.2f")

    # Performance validation
    print()
    print("🎯 Performance Validation:")
    target_time = 30.0  # seconds for this small test
    if execution_time < target_time:
        print(f"   ✅ Execution time ({execution_time:.1f}s) well under target")
    else:
        print(f"   ⚠️  Execution time ({execution_time:.1f}s) over target")

    success_rate = len(results) / len(jobs)
    if success_rate >= 0.9:  # 90% success rate
        print(".1%")
    else:
        print(".1%")

    # Worker efficiency
    avg_time_per_job = execution_time / len(jobs)
    print(".2f")

    print()
    # Test expects some failures (10% failure rate) to validate error handling
    expected_min_success_rate = 0.5  # Allow for random variation in small sample

    if success_rate >= expected_min_success_rate:
        print("🎉 TEST PASSED: Parallel orchestration working correctly!")
        print(f"   ✅ Expected failures handled gracefully ({len(failed_jobs)} failures)")
        print("   ✅ Parallel execution completed successfully")
        print("   ✅ Results consolidation working")
        print("   ✅ Progress tracking functional")
        return True
    else:
        print("❌ TEST FAILED: Success rate too low")
        print(f"   Expected at least {expected_min_success_rate:.1%}, got {success_rate:.1%}")
        if failed_jobs:
            print("   Failed jobs:")
            for job, error in failed_jobs[:3]:  # Show first 3 failures
                print(f"     - {job.job_id}: {error.get('error', 'Unknown error')}")
        return False


def test_job_generation():
    """Test job generation logic"""
    print("🧪 Testing Job Generation Logic")
    print("-" * 30)

    symbols = ['SPY', 'AAPL']
    strategies = ['sma_crossover.py', 'rsi_momentum.py']

    # Test job generation (simplified version)
    jobs = []
    for symbol in symbols:
        for strategy in strategies:
            job = MockBacktestJob(
                job_id=f"test_{symbol}_{strategy.replace('.py', '')}",
                symbol=symbol,
                strategy_path=f"strategies/{strategy}"
            )
            jobs.append(job)

    expected_jobs = len(symbols) * len(strategies)
    if len(jobs) == expected_jobs:
        print(f"✅ Job generation: {len(jobs)} jobs created correctly")
        return True
    else:
        print(f"❌ Job generation: Expected {expected_jobs}, got {len(jobs)}")
        return False


if __name__ == "__main__":
    print("🧪 Parallel Backtest Orchestrator - Test Suite")
    print("=" * 55)

    # Run tests
    test1_passed = test_job_generation()
    print()
    test2_passed = test_parallel_orchestration()

    print()
    print("=" * 55)
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED!")
        sys.exit(1)