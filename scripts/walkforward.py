
#!/usr/bin/env python3
"""
Walk-Forward Analysis Script - Validate the robustness of a strategy.

US-3.3: Walk-Forward Analysis
"""

import argparse
import json
import logging
import re
import subprocess
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WalkForwardAnalysis:
    def __init__(self, algorithm, start_date, end_date, train_period, test_period, parameters, metric):
        self.algorithm = algorithm
        self.start_date = start_date
        self.end_date = end_date
        self.train_period = train_period
        self.test_period = test_period
        self.parameters = parameters
        self.metric = metric

    def run(self):
        results = []
        current_date = self.start_date

        while current_date + self.train_period + self.test_period <= self.end_date:
            train_start = current_date
            train_end = current_date + self.train_period
            test_start = train_end
            test_end = train_end + self.test_period

            logger.info(f"Running walk-forward analysis for training period: {train_start} - {train_end} and testing period: {test_start} - {test_end}")

            # 1. Optimize parameters on the training period
            optimization_result = self._optimize(train_start, train_end)
            if not optimization_result:
                continue
            
            best_params = optimization_result['parameters']
            train_result = optimization_result['metrics']

            # 2. Test the best parameters on the testing period
            test_result = self._test(test_start, test_end, best_params)

            results.append({
                'train_period': {'start': train_start.isoformat(), 'end': train_end.isoformat()},
                'test_period': {'start': test_start.isoformat(), 'end': test_end.isoformat()},
                'best_params': best_params,
                'train_result': train_result,
                'test_result': test_result,
                'degradation': self._check_overfitting(train_result, test_result)
            })

            current_date += self.test_period

        return results

    def _check_overfitting(self, train_result, test_result):
        if not train_result or not test_result:
            return None

        train_metric = train_result.get(self.metric, 0)
        test_metric = test_result.get(self.metric, 0)

        if train_metric == 0:
            return None

        degradation = (train_metric - test_metric) / abs(train_metric)
        return degradation

    def _optimize(self, start_date, end_date):
        logger.info(f"Optimizing parameters for period: {start_date} - {end_date}")
        
        cmd = [
            "python", "scripts/optimize_parameters.py",
            "--algorithm", self.algorithm,
            "--parameters", json.dumps(self.parameters),
            "--metric", self.metric,
            "--optimizer", "bayesian",
            "--n_calls", "50"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            optimization_result = json.loads(result.stdout)
            return optimization_result[0]
        except (subprocess.CalledProcessError, json.JSONDecodeError, IndexError) as e:
            logger.error(f"Optimization failed for period {start_date} - {end_date}: {e}")
            return None

    def _test(self, start_date, end_date, params):
        logger.info(f"Testing parameters {params} for period: {start_date} - {end_date}")

        original_content = self._read_algorithm_file()
        modified_content = self._modify_algorithm_file(original_content, params)
        self._write_algorithm_file(modified_content)

        try:
            cmd = ["python", "scripts/run_backtest.py", "--algorithm", self.algorithm, "--start", start_date.strftime("%Y-%m-%d"), "--end", end_date.strftime("%Y-%m-%d"), "--symbols", "SPY"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            backtest_result = json.loads(result.stdout)[0]
            return backtest_result['metrics']
        except (subprocess.CalledProcessError, json.JSONDecodeError, IndexError) as e:
            logger.error(f"Backtest failed for period {start_date} - {end_date}: {e}")
            return None
        finally:
            self._write_algorithm_file(original_content)

    def _read_algorithm_file(self):
        with open(self.algorithm, 'r') as f:
            return f.read()

    def _modify_algorithm_file(self, content, params):
        for name, value in params.items():
            content = re.sub(f'{name}\s*=\s*.*\n', f'{name} = {value}\n', content)
        return content

    def _write_algorithm_file(self, content):
        with open(self.algorithm, 'w') as f:
            f.write(content)

def main():
    parser = argparse.ArgumentParser(description="Run walk-forward analysis")
    parser.add_argument("--algorithm", required=True, help="Path to algorithm")
    parser.add_argument("--start-date", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--train-period", required=True, type=int, help="Training period in days")
    parser.add_argument("--test-period", required=True, type=int, help="Testing period in days")
    parser.add_argument("--parameters", required=True, help="JSON string of parameters to optimize")
    parser.add_argument("--metric", default="sharpe_ratio", help="Metric to optimize for")
    args = parser.parse_args()

    start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    train_period = timedelta(days=args.train_period)
    test_period = timedelta(days=args.test_period)
    parameters = json.loads(args.parameters)

    wfa = WalkForwardAnalysis(args.algorithm, start_date, end_date, train_period, test_period, parameters, args.metric)
    results = wfa.run()

    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
