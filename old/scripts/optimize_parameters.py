#!/usr/bin/env python3
"""
Parameter Optimization Script - Find the best parameters for a strategy.

US-3.1: Grid Search Optimization
"""

import argparse
import itertools
import json
import logging
import re
import subprocess
from pathlib import Path

from skopt import gp_minimize
from skopt.space import Real, Integer, Categorical

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from skopt.space import Real, Integer, Categorical
from skopt import gp_minimize

class Optimizer:
    def __init__(self, algorithm, parameters, metric):
        self.algorithm = algorithm
        self.parameters = parameters
        self.metric = metric

    def run_grid_search(self):
        results = []
        param_combinations = self._get_param_combinations()

        for params in param_combinations:
            logger.info(f"Testing parameters: {params}")
            # Here you would run the backtest with the given parameters
            # For now, we'll just simulate it
            result = self._run_backtest_with_params(params)
            if result:
                results.append(result)

        # Rank results
        ranked_results = sorted(results, key=lambda x: x['metrics'].get(self.metric, 0), reverse=True)

        return ranked_results

    def run_bayesian_search(self, n_calls=100):
        space = self._get_search_space()

        result = gp_minimize(
            self._objective_function,
            space,
            n_calls=n_calls,
            random_state=0
        )

        best_params = {space[i].name: result.x[i] for i in range(len(space))}
        best_score = -result.fun

        return best_params, best_score


    def _get_param_combinations(self):
        param_names = self.parameters.keys()
        param_values = self.parameters.values()
        return [dict(zip(param_names, v)) for v in itertools.product(*param_values)]

    def _get_search_space(self):
        space = []
        for name, values in self.parameters.items():
            if isinstance(values[0], float):
                space.append(Real(values[0], values[1], name=name))
            elif isinstance(values[0], int):
                space.append(Integer(values[0], values[1], name=name))
            else:
                space.append(Categorical(values, name=name))
        return space

    def _objective_function(self, params):
        param_dict = {self.parameters[i]['name']: params[i] for i in range(len(self.parameters))}
        result = self._run_backtest_with_params(param_dict)
        if result:
            return -result['metrics'].get(self.metric, 0)
        else:
            return 0


    def _run_backtest_with_params(self, params):
        original_content = self._read_algorithm_file()
        modified_content = self._modify_algorithm_file(original_content, params)
        self._write_algorithm_file(modified_content)

        try:
            cmd = ["python", "scripts/run_backtest.py", "--algorithm", self.algorithm, "--start", "2020-01-01", "--end", "2021-01-01", "--symbols", "SPY"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # The result of the script is a list of results, one for each symbol.
            # We are only running on one symbol, so we take the first element.
            backtest_result = json.loads(result.stdout)[0]

            return {
                'parameters': params,
                'metrics': backtest_result['metrics']
            }
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            logger.error(f"Backtest failed for parameters {params}: {e}")
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
    parser = argparse.ArgumentParser(description="Run parameter optimization")
    parser.add_argument("--algorithm", required=True, help="Path to algorithm")
    parser.add_argument("--parameters", required=True, help="JSON string of parameters to optimize")
    parser.add_argument("--metric", default="sharpe_ratio", help="Metric to optimize for")
    parser.add_argument("--optimizer", default="grid_search", choices=["grid_search", "bayesian"], help="Optimization method")
    parser.add_argument("--n_calls", type=int, default=100, help="Number of calls for Bayesian optimization")
    args = parser.parse_args()

    parameters = json.loads(args.parameters)

    optimizer = Optimizer(args.algorithm, parameters, args.metric)

    if args.optimizer == "grid_search":
        results = optimizer.run_grid_search()
    else:
        results = optimizer.run_bayesian_search(n_calls=args.n_calls)

    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()