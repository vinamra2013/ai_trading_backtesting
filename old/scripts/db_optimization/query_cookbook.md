# MLflow Query Cookbook
# Epic 17: US-17.15 - Query Patterns and Examples

This cookbook provides common query patterns and examples for working with the AI Research Lab's MLflow experiment tracking system.

## Setup

```python
from scripts.project_manager import ProjectManager
from scripts.mlflow_logger import MLflowBacktestLogger
import mlflow

# Initialize clients
pm = ProjectManager()
logger = MLflowBacktestLogger()
```

## Basic Query Patterns

### 1. Query by Project

Find all experiments in a specific project:

```python
# Using ProjectManager
q1_experiments = pm.query_by_project("Q1_2025")

# Using MLflow directly
import mlflow
experiments = mlflow.search_experiments(
    filter_string="name LIKE 'Q1_2025.%'"
)
```

### 2. Query by Asset Class

Find all equity or crypto strategies:

```python
# Equities
equity_experiments = pm.query_by_asset_class("Equities")

# Crypto
crypto_experiments = pm.query_by_asset_class("Crypto")

# MLflow direct
equity_experiments = mlflow.search_experiments(
    filter_string="name LIKE '%.Equities.%'"
)
```

### 3. Query by Strategy Family

Find all mean reversion or momentum strategies:

```python
mean_reversion = pm.query_by_strategy_family("MeanReversion")
momentum = pm.query_by_strategy_family("Momentum")
```

### 4. Query by Status

Find experiments by development status:

```python
research_experiments = pm.query_by_status("research")
production_experiments = pm.query_by_status("production")
archived_experiments = pm.query_by_status("archived")
```

### 5. Query Recent Experiments

Find experiments created in the last N days:

```python
# Last 7 days
recent = pm.query_recent_experiments(days=7)

# Last 30 days
recent_month = pm.query_recent_experiments(days=30)
```

### 6. Query by Team

Find experiments by responsible team:

```python
quant_experiments = pm.query_by_team("quant_research")
trading_experiments = pm.query_by_team("trading")
```

## Advanced Query Patterns

### 7. Complex Filters with MLflow

Combine multiple conditions:

```python
# Q1 2025 equity research experiments
complex_filter = """
name LIKE 'Q1_2025.Equities.%' AND
tags.status = 'research' AND
creation_time >= 1640995200000
"""

experiments = mlflow.search_experiments(
    filter_string=complex_filter,
    max_results=100
)
```

### 8. Run Queries within Experiments

Query individual runs within an experiment:

```python
# Get all runs for a specific experiment
experiment_name = "Q1_2025.Equities.MeanReversion.SMACrossover"
runs = pm.query_runs_by_experiment(experiment_name)

# Filter runs by metric value
high_sharpe_runs = [
    run for run in runs
    if run.get('metrics', {}).get('sharpe_ratio', 0) > 1.5
]
```

### 9. Compare Strategies

Compare performance across strategies in a project:

```python
# Compare all strategies in Q1_2025 by Sharpe ratio
comparison = pm.compare_strategies("Q1_2025", "sharpe_ratio")

# Sort by best performing
sorted_comparison = sorted(
    comparison.items(),
    key=lambda x: x[1]['best_metric_value'],
    reverse=True
)

for strategy, data in sorted_comparison:
    print(f"{strategy}: {data['best_metric_value']:.3f}")
```

### 10. Find Best Parameters

Get the best parameters for a strategy:

```python
experiment_name = "Q1_2025.Equities.MeanReversion.SMACrossover"
best_run = pm.get_best_run(experiment_name, "sharpe_ratio")

if best_run:
    print("Best parameters:", best_run['params'])
    print("Best Sharpe ratio:", best_run['metrics']['sharpe_ratio'])
    print("Run ID:", best_run['run_id'])
```

## Metric-Based Queries

### 11. Find High-Performance Strategies

```python
# Find strategies with Sharpe > 2.0
high_sharpe_experiments = []

experiments = pm.query_experiments()
for exp in experiments:
    best_run = pm.get_best_run(exp['name'], 'sharpe_ratio')
    if best_run and best_run['metrics'].get('sharpe_ratio', 0) > 2.0:
        high_sharpe_experiments.append({
            'experiment': exp['name'],
            'sharpe': best_run['metrics']['sharpe_ratio'],
            'params': best_run['params']
        })
```

### 12. Regime Analysis Queries

Find strategies that perform well in different market regimes:

```python
# Find strategies with good bear market performance
bear_market_experiments = []

experiments = pm.query_experiments()
for exp in experiments:
    runs = pm.query_runs_by_experiment(exp['name'])
    for run in runs:
        bear_return = run.get('metrics', {}).get('bear_market_return', 0)
        if bear_return > 0:  # Positive returns in bear markets
            bear_market_experiments.append({
                'experiment': exp['name'],
                'bear_return': bear_return,
                'run_id': run['run_id']
            })
```

## Experiment Management

### 13. Create Organized Experiments

```python
# Create experiment with proper naming
exp_id = pm.create_experiment(
    project="Q1_2025",
    asset_class="Equities",
    strategy_family="MeanReversion",
    strategy="SMACrossover",
    team="quant_research",
    status="research"
)

print(f"Created experiment: {exp_id}")
```

### 14. Bulk Experiment Creation

```python
# Create research project with multiple strategies
strategies = [
    ("Equities", "MeanReversion", "SMACrossover"),
    ("Equities", "Momentum", "RSIStrategy"),
    ("Crypto", "MeanReversion", "BollingerBands")
]

experiment_ids = pm.create_research_project("Q1_2025", strategies)
print(f"Created {len(experiment_ids)} experiments")
```

### 15. Archive Old Experiments

```python
# Archive experiments older than 90 days
archived_count = pm.archive_old_experiments(days_threshold=90)
print(f"Archived {archived_count} experiments")
```

## Utility Functions

### 16. List Available Categories

```python
# Get all projects
projects = pm.list_projects()
print("Available projects:", projects)

# Get all asset classes
asset_classes = pm.list_asset_classes()
print("Available asset classes:", asset_classes)

# Get all strategy families
strategy_families = pm.list_strategy_families()
print("Available strategy families:", strategy_families)
```

### 17. Validate Experiment Names

```python
# Check if experiment name follows convention
valid_names = [
    "Q1_2025.Equities.MeanReversion.SMACrossover",
    "Q2_2025.Crypto.Momentum.RSIStrategy"
]

for name in valid_names:
    is_valid = pm.validate_experiment_name(name)
    print(f"{name}: {'Valid' if is_valid else 'Invalid'}")
```

## Common Use Cases

### 18. Monthly Performance Review

```python
# Get all experiments from last month
recent_experiments = pm.query_recent_experiments(days=30)

# Analyze performance by asset class
performance_by_asset_class = {}
for exp in recent_experiments:
    parsed = pm.parse_experiment_name(exp['name'])
    asset_class = parsed['asset_class']

    if asset_class not in performance_by_asset_class:
        performance_by_asset_class[asset_class] = []

    best_run = pm.get_best_run(exp['name'], 'sharpe_ratio')
    if best_run:
        performance_by_asset_class[asset_class].append(
            best_run['metrics'].get('sharpe_ratio', 0)
        )

# Print average performance by asset class
for asset_class, sharpe_ratios in performance_by_asset_class.items():
    avg_sharpe = sum(sharpe_ratios) / len(sharpe_ratios)
    print(f"{asset_class}: Average Sharpe = {avg_sharpe:.3f}")
```

### 19. Strategy Optimization Tracking

```python
# Find optimization studies
optimization_experiments = mlflow.search_experiments(
    filter_string="tags.optimization_study = 'true'"
)

# Analyze optimization performance
for exp in optimization_experiments:
    runs = pm.query_runs_by_experiment(exp['name'])
    if runs:
        best_run = max(runs, key=lambda r: r['metrics'].get('sharpe_ratio', 0))
        print(f"Study: {exp['name']}")
        print(f"Best Sharpe: {best_run['metrics'].get('sharpe_ratio', 0):.3f}")
        print(f"Parameters: {best_run['params']}")
        print("---")
```

### 20. Experiment Health Check

```python
# Check for experiments with issues
experiments = pm.query_experiments()
failed_experiments = []

for exp in experiments:
    runs = pm.query_runs_by_experiment(exp['name'])
    failed_runs = [r for r in runs if r.get('status') == 'FAILED']

    if len(failed_runs) > 0:
        failed_experiments.append({
            'experiment': exp['name'],
            'failed_runs': len(failed_runs),
            'total_runs': len(runs)
        })

# Report issues
if failed_experiments:
    print("Experiments with failed runs:")
    for exp in failed_experiments:
        failure_rate = exp['failed_runs'] / exp['total_runs'] * 100
        print(f"- {exp['experiment']}: {failure_rate:.1f}% failure rate")
else:
    print("All experiments are healthy!")
```

## Tips and Best Practices

1. **Use ProjectManager for common queries** - It's optimized for the dot notation naming convention
2. **Combine filters efficiently** - Use MLflow's filter_string for complex queries
3. **Cache frequent queries** - For dashboard applications, consider caching results
4. **Use pagination** - Set max_results appropriately for large datasets
5. **Monitor query performance** - Use the database monitoring scripts for optimization
6. **Validate experiment names** - Always check naming convention compliance
7. **Archive regularly** - Keep active dataset manageable with archival strategies

## Troubleshooting

### Common Issues

1. **No experiments found**: Check MLflow server is running (`docker compose logs mlflow`)
2. **Invalid experiment names**: Use `validate_experiment_name()` to check format
3. **Slow queries**: Run database optimization scripts
4. **Missing metrics**: Ensure backtests completed successfully
5. **Permission errors**: Check MLflow server access

### Debug Queries

```python
# Debug: Check MLflow connection
try:
    experiments = mlflow.search_experiments(max_results=5)
    print(f"MLflow connection OK. Found {len(experiments)} experiments.")
except Exception as e:
    print(f"MLflow connection failed: {e}")

# Debug: Check experiment naming
experiment_name = "Q1_2025.Equities.MeanReversion.SMACrossover"
try:
    parsed = pm.parse_experiment_name(experiment_name)
    print(f"Parsed: {parsed}")
except ValueError as e:
    print(f"Invalid name: {e}")
```</content>
<parameter name="filePath">scripts/db_optimization/query_cookbook.md