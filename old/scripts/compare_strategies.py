
#!/usr/bin/env python3
"""
Strategy Comparison Script - Compare the performance of multiple strategies.

US-4.1: Compare Multiple Strategies
"""

import argparse
import json
import pandas as pd

class StrategyComparator:
    def __init__(self, result_files):
        self.result_files = result_files
        self.results = self._load_results()

    def _load_results(self):
        results = []
        for file in self.result_files:
            with open(file, 'r') as f:
                results.append(json.load(f))
        return results

    def compare_metrics(self):
        metrics = []
        for result in self.results:
            metric = {
                'algorithm': result['algorithm'],
                'symbol': result.get('symbol', 'N/A')
            }
            metric.update(result['metrics'])
            metrics.append(metric)
        
        df = pd.DataFrame(metrics)
        return df

    def rank_strategies(self, weights):
        df = self.compare_metrics()
        df['rank'] = 0

        for metric, weight in weights.items():
            df['rank'] += df[metric] * weight

        return df.sort_values(by='rank', ascending=False)

def main():
    parser = argparse.ArgumentParser(description="Compare strategies")
    parser.add_argument("result_files", nargs='+', help="List of backtest result files")
    parser.add_argument("--weights", help="JSON string of weights for ranking")
    args = parser.parse_args()

    comparator = StrategyComparator(args.result_files)

    if args.weights:
        weights = json.loads(args.weights)
        comparison = comparator.rank_strategies(weights)
    else:
        comparison = comparator.compare_metrics()

    print(comparison.to_string())

if __name__ == "__main__":
    main()
