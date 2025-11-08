#!/usr/bin/env python3
"""
Backtrader Backtest Execution Script with MLflow Integration
Epic 12: US-12.4 - Backtest Execution Script
Epic 17: US-17.3 - MLflow Integration

Replaces LEAN backtest runner with Backtrader Cerebro execution + MLflow tracking.
"""

import argparse
import logging
import sys
import json
import uuid
import os
from datetime import datetime
from pathlib import Path
from typing import Type, Dict, List, Optional
import importlib.util
import backtrader as bt
import yaml
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Configure logging (will be updated based on debug flag)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from scripts.cerebro_engine import CerebroEngine
from scripts.backtrader_analyzers import (
    IBPerformanceAnalyzer,
    CommissionAnalyzer,
    EquityCurveAnalyzer,
    MonthlyReturnsAnalyzer,
    TradeLogAnalyzer,
)
from scripts.backtest_parser import BacktraderResultParser
from scripts.mlflow_logger import MLflowBacktestLogger

# Conditional imports for advanced metrics (Epic 17)
try:
    from scripts.metrics import QuantStatsAnalyzer, RegimeAnalyzer, AlphaBetaAnalyzer

    ADVANCED_METRICS_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Advanced metrics libraries not available: {e}")
    ADVANCED_METRICS_AVAILABLE = False


class BacktestRunner:
    """Backtest execution runner for Backtrader strategies with MLflow integration"""

    def __init__(
        self,
        config_path: str = "config/backtest_config.yaml",
        mlflow_config_path: str = "config/mlflow_config.yaml",
    ):
        self.config_path = config_path
        self.mlflow_config_path = mlflow_config_path
        self.results_dir = Path("results/backtests")
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Initialize MLflow logger
        self.mlflow_logger = None
        self.mlflow_enabled = False
        self.mlflow_config = {}

        try:
            with open(mlflow_config_path, "r") as f:
                self.mlflow_config = yaml.safe_load(f)
            self.mlflow_logger = MLflowBacktestLogger()
            self.mlflow_enabled = True
        except Exception as e:
            logger.debug(f"MLflow configuration not found or invalid: {e}")
            logger.debug("Continuing without MLflow integration...")

    def load_strategy_class(self, strategy_path: str) -> Type[bt.Strategy]:
        """Dynamically load strategy class from file"""
        strategy_file = Path(strategy_path)
        if not strategy_file.exists():
            strategy_file = Path("/app") / strategy_path
            if not strategy_file.exists():
                raise FileNotFoundError(f"Strategy file not found: {strategy_path}")

        # Use unique module name based on file path to avoid conflicts
        module_name = strategy_file.stem + "_strategy_module"
        spec = importlib.util.spec_from_file_location(module_name, strategy_file)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = (
            module  # Register module in sys.modules for Backtrader
        )
        spec.loader.exec_module(module)

        # Find all strategy classes defined in this module
        strategy_classes = []
        for item_name in dir(module):
            item = getattr(module, item_name)
            if (
                isinstance(item, type)
                and issubclass(item, bt.Strategy)
                and item != bt.Strategy
            ):
                # Check if this class is defined in the current module (not imported)
                if hasattr(item, "__module__") and item.__module__ == module.__name__:
                    strategy_classes.append(item)

        if not strategy_classes:
            raise ValueError(f"No strategy classes found in {strategy_path}")

        # Return the first strategy class defined in this module
        # (preferring classes defined in the file over imported ones)
        return strategy_classes[0]

        raise ImportError(f"No Strategy class found in {strategy_path}")

    def _build_experiment_name(
        self, project: str, asset_class: str, strategy_family: str, strategy_name: str
    ) -> str:
        """Build experiment name using dot notation convention."""
        return f"{project}.{asset_class}.{strategy_family}.{strategy_name}"

    def _build_tags(
        self,
        project: str,
        asset_class: str,
        strategy_family: str,
        strategy_name: str,
        team: str = "quant_research",
        status: str = "research",
        **kwargs,
    ) -> Dict:
        """Build comprehensive tagging dictionary."""
        tags = {
            "project": project,
            "asset_class": asset_class,
            "strategy_family": strategy_family,
            "strategy": strategy_name,
            "team": team,
            "status": status,
            "created_date": datetime.now().isoformat(),
            "created_by": "backtest_runner",
        }

        # Add any additional tags
        tags.update(kwargs)
        return tags

    def _prepare_artifacts(self, backtest_results: Dict, output_dir: Path) -> Dict:
        """Prepare artifacts for MLflow logging."""
        artifacts = {}

        try:
            # Equity curve artifact
            equity_curve_df = pd.DataFrame(backtest_results["equity_curve"])
            equity_csv_path = (
                output_dir / f"{backtest_results['backtest_id']}_equity_curve.csv"
            )
            equity_curve_df.to_csv(equity_csv_path, index=False)
            artifacts["equity_curve"] = str(equity_csv_path)

            # Trade log artifact
            trades_df = pd.DataFrame(backtest_results["trades"])
            trades_csv_path = (
                output_dir / f"{backtest_results['backtest_id']}_trades.csv"
            )
            trades_df.to_csv(trades_csv_path, index=False)
            artifacts["trade_log"] = str(trades_csv_path)

            # Backtest summary artifact
            summary_path = (
                output_dir / f"{backtest_results['backtest_id']}_summary.json"
            )
            with open(summary_path, "w") as f:
                json.dump(backtest_results, f, indent=2)
            artifacts["backtest_summary"] = str(summary_path)

        except Exception as e:
            logger.debug(f"Warning: Failed to prepare artifacts: {e}")

        return artifacts

    def run(
        self,
        strategy_path: str,
        symbols: List[str],
        start_date: str,
        end_date: str,
        strategy_params: Dict = None,
        resolution: str = "Daily",
        export_csv: bool = False,
        export_text: bool = False,
        # MLflow parameters
        mlflow_enabled: bool = False,
        project: str = "Default",
        asset_class: str = "Equities",
        strategy_family: str = "Unknown",
        team: str = "quant_research",
        status: str = "research",
        output_json: Optional[str] = None,
    ) -> Dict:
        """Run backtest and return results with optional MLflow logging.

        Args:
            strategy_path: Path to strategy file
            symbols: List of symbols to trade
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD
            strategy_params: Optional strategy parameters
            resolution: Data resolution (Daily, Hour, Minute)
            export_csv: Export trades to CSV
            export_text: Export text summary report
            mlflow_enabled: Enable MLflow logging
            project: Project name for MLflow experiment organization
            asset_class: Asset class for MLflow tagging
            strategy_family: Strategy family for MLflow tagging
            team: Team responsible for the experiment
            status: Experiment status (research, testing, production)

        Returns:
            Backtest results dictionary
        """

        print(f"\n{'=' * 80}\nBACKTRADER BACKTEST RUNNER + MLflow\n{'=' * 80}")

        backtest_id = str(uuid.uuid4())
        strategy_class = self.load_strategy_class(strategy_path)

        # MLflow integration
        mlflow_run_id = None
        if mlflow_enabled and self.mlflow_enabled:
            experiment_name = self._build_experiment_name(
                project, asset_class, strategy_family, strategy_class.__name__
            )
            tags = self._build_tags(
                project,
                asset_class,
                strategy_family,
                strategy_class.__name__,
                team,
                status,
                symbols=str(symbols),
                time_period=f"{start_date}_to_{end_date}",
                backtest_id=backtest_id,
            )

            print(f"🔬 MLflow Experiment: {experiment_name}")

        engine = CerebroEngine(self.config_path)
        engine.add_strategy(strategy_class, **(strategy_params or {}))

        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        engine.add_multiple_data(
            symbols=symbols,
            resolution=resolution,
            fromdate=start_dt,
            todate=end_dt,
            strategy_class=strategy_class,
        )

        engine.cerebro.addanalyzer(IBPerformanceAnalyzer, _name="ibperformance")
        engine.cerebro.addanalyzer(CommissionAnalyzer, _name="commission")
        engine.cerebro.addanalyzer(EquityCurveAnalyzer, _name="equity")
        engine.cerebro.addanalyzer(MonthlyReturnsAnalyzer, _name="monthly")
        engine.cerebro.addanalyzer(TradeLogAnalyzer, _name="tradelog")

        results = engine.run()
        strategy = results[0]

        ib_analysis = strategy.analyzers.ibperformance.get_analysis()
        commission_analysis = strategy.analyzers.commission.get_analysis()
        equity_analysis = strategy.analyzers.equity.get_analysis()
        monthly_analysis = strategy.analyzers.monthly.get_analysis()
        tradelog_analysis = strategy.analyzers.tradelog.get_analysis()

        # Build comprehensive results
        backtest_results = {
            "backtest_id": backtest_id,
            "timestamp": datetime.now().isoformat(),
            "strategy": {
                "name": strategy_class.__name__,
                "path": strategy_path,
                "parameters": strategy_params or {},
            },
            "configuration": {
                "symbols": symbols,
                "start_date": start_date,
                "end_date": end_date,
                "resolution": resolution,
                "initial_capital": engine.config.get("initial_capital", 100000),
                "commission_scheme": engine.config.get("broker", {}).get(
                    "commission_scheme", "ib_standard"
                ),
            },
            "performance": {
                "initial_value": ib_analysis["initial_value"],
                "final_value": ib_analysis["final_value"],
                "total_return": ib_analysis["total_return"],
                "total_return_pct": ib_analysis["total_return_pct"],
                "sharpe_ratio": ib_analysis["sharpe_ratio"],
                "max_drawdown": ib_analysis["max_drawdown"],
                "max_drawdown_pct": ib_analysis["max_drawdown_pct"],
            },
            "trading": {
                "total_trades": ib_analysis["total_trades"],
                "winning_trades": ib_analysis["winning_trades"],
                "losing_trades": ib_analysis["losing_trades"],
                "win_rate": ib_analysis["win_rate"],
                "avg_win": ib_analysis["avg_win"],
                "avg_loss": ib_analysis["avg_loss"],
                "profit_factor": ib_analysis["profit_factor"],
            },
            "costs": {
                "total_commission": commission_analysis["total_commission"],
                "avg_commission_per_trade": commission_analysis[
                    "avg_commission_per_trade"
                ],
                "total_pnl_gross": ib_analysis["total_pnl_gross"],
                "total_pnl_net": ib_analysis["total_pnl"],
            },
            "equity_curve": [
                {"datetime": e["datetime"].isoformat(), "value": e["value"]}
                for e in equity_analysis["equity_curve"]
            ],
            "monthly_returns": monthly_analysis["monthly_returns"],
            "trades": tradelog_analysis["trades"],
        }

        # Calculate advanced metrics (Epic 17)
        if ADVANCED_METRICS_AVAILABLE:
            try:
                # Convert equity curve to pandas Series for metrics calculation
                equity_df = pd.DataFrame(backtest_results["equity_curve"])
                if len(equity_df) > 0:
                    equity_df["datetime"] = pd.to_datetime(equity_df["datetime"])
                    equity_df = equity_df.set_index("datetime")
                    returns_series = equity_df["value"].pct_change().dropna()

                    if len(returns_series) > 0:
                        metrics_calculated = 0

                        # QuantStats metrics
                        try:
                            quantstats_analyzer = QuantStatsAnalyzer(benchmark="SPY")
                            quantstats_metrics = quantstats_analyzer.calculate_metrics(
                                returns_series
                            )
                            backtest_results["quantstats_metrics"] = quantstats_metrics
                            metrics_calculated += len(quantstats_metrics)
                        except Exception as e:
                            print(f"   ⚠️  QuantStats metrics failed: {e}")
                            backtest_results["quantstats_metrics"] = {}

                        # Regime analysis
                        try:
                            regime_analyzer = RegimeAnalyzer()
                            regimes = regime_analyzer.detect_regimes(equity_df["value"])
                            regime_metrics = regime_analyzer.calculate_regime_metrics(
                                returns_series, regimes
                            )
                            backtest_results["regime_analysis"] = {
                                "regime_breakdown": regime_metrics,
                                "regime_summary": regime_analyzer.get_regime_performance_summary(
                                    returns_series, regimes
                                ),
                            }
                            metrics_calculated += len(regime_metrics)
                        except Exception as e:
                            print(f"   ⚠️  Regime analysis failed: {e}")
                            backtest_results["regime_analysis"] = {}

                        # Alpha/Beta analysis (if benchmark data available)
                        try:
                            alpha_beta_analyzer = AlphaBetaAnalyzer()
                            # For now, skip benchmark analysis as we need to fetch SPY data
                            # This would be added when benchmark data fetching is implemented
                            backtest_results["alpha_beta_metrics"] = {}
                        except Exception as e:
                            print(f"   ⚠️  Alpha/Beta analysis failed: {e}")
                            backtest_results["alpha_beta_metrics"] = {}

                        if metrics_calculated > 0:
                            print(
                                f"   ✅ Advanced metrics calculated: {metrics_calculated} total metrics"
                            )
                        else:
                            print("   ⚠️  No advanced metrics could be calculated")
                    else:
                        print(
                            "   ⚠️  Insufficient returns data for advanced metrics calculation"
                        )
                        backtest_results["quantstats_metrics"] = {}
                        backtest_results["regime_analysis"] = {}
                        backtest_results["alpha_beta_metrics"] = {}
                else:
                    print("   ⚠️  No equity curve data for advanced metrics calculation")
                    backtest_results["quantstats_metrics"] = {}
                    backtest_results["regime_analysis"] = {}
                    backtest_results["alpha_beta_metrics"] = {}

            except Exception as e:
                print(f"   ❌ Advanced metrics calculation error: {e}")
                backtest_results["quantstats_metrics"] = {}
                backtest_results["regime_analysis"] = {}
                backtest_results["alpha_beta_metrics"] = {}
        else:
            print(
                "   ℹ️  Advanced metrics libraries not available - skipping enhanced analysis"
            )
            backtest_results["quantstats_metrics"] = {}
            backtest_results["regime_analysis"] = {}
            backtest_results["alpha_beta_metrics"] = {}

        # Save JSON results (maintain backward compatibility)
        output_file = self.results_dir / f"{backtest_id}.json"
        with open(output_file, "w") as f:
            json.dump(backtest_results, f, indent=2)

        # Output JSON results
        if output_json:
            # Write to specified file for optimizer
            print(f"Writing results to {output_json}")
            with open(output_json, "w") as f:
                json.dump(backtest_results, f, indent=2)
            print(f"Results written to {output_json}")
        else:
            # Output to stdout for backward compatibility
            # print(json.dumps(backtest_results))  # Commented out - too verbose
            pass

        # Optional exports using parser
        if export_csv or export_text:
            parser = BacktraderResultParser()

            # Parse results for advanced exports
            parsed_results = parser.parse_cerebro_results(
                results,
                backtest_id,
                strategy_class.__name__,
                symbols,
                start_date,
                end_date,
                engine.config.get("initial_capital", 100000),
            )

            if export_csv:
                csv_file = self.results_dir / f"{backtest_id}_trades.csv"
                parser.export_to_csv(parsed_results, str(csv_file))
                print(f"   CSV export: {csv_file}")

            if export_text:
                text_file = self.results_dir / f"{backtest_id}_report.txt"
                text_report = parser.generate_text_report(parsed_results)
                with open(text_file, "w") as f:
                    f.write(text_report)
                print(f"   Text report: {text_file}")

        # MLflow logging
        if mlflow_enabled and self.mlflow_enabled:
            try:
                # Prepare MLflow data

                # Map metrics for MLflow (include advanced metrics if available)
                mlflow_metrics = {
                    **backtest_results["performance"],
                    **backtest_results["trading"],
                    **backtest_results["costs"],
                }

                # Add advanced metrics to MLflow logging
                if (
                    "quantstats_metrics" in backtest_results
                    and backtest_results["quantstats_metrics"]
                ):
                    mlflow_metrics.update(backtest_results["quantstats_metrics"])
                if "regime_analysis" in backtest_results and backtest_results[
                    "regime_analysis"
                ].get("regime_breakdown"):
                    mlflow_metrics.update(
                        backtest_results["regime_analysis"]["regime_breakdown"]
                    )
                if (
                    "alpha_beta_metrics" in backtest_results
                    and backtest_results["alpha_beta_metrics"]
                ):
                    mlflow_metrics.update(backtest_results["alpha_beta_metrics"])

                # Prepare artifacts
                artifacts = self._prepare_artifacts(backtest_results, self.results_dir)

                # Log to MLflow
                mlflow_run_id = self.mlflow_logger.log_backtest(
                    experiment_name=experiment_name,
                    strategy_name=strategy_class.__name__,
                    parameters=strategy_params or {},
                    metrics=mlflow_metrics,
                    artifacts=artifacts,
                    tags=tags,
                    run_name=f"{strategy_class.__name__}_{start_date}_{end_date}",
                )

                if mlflow_run_id:
                    print(f"   ✅ MLflow Run ID: {mlflow_run_id}")
                else:
                    print(f"   ⚠️  MLflow logging failed")

            except Exception as e:
                print(f"   ❌ MLflow logging error: {e}")

        print(f"\n{'=' * 80}\nBACKTEST COMPLETE\n{'=' * 80}")
        print(
            f"\n📈 Performance: ${backtest_results['performance']['initial_value']:,.2f} → ${backtest_results['performance']['final_value']:,.2f} ({backtest_results['performance']['total_return_pct']:.2f}%)"
        )
        print(
            f"   Sharpe: {backtest_results['performance']['sharpe_ratio']:.2f} | Max DD: {backtest_results['performance']['max_drawdown_pct']:.2f}%"
        )
        print(
            f"\n📊 Trading: {backtest_results['trading']['total_trades']} trades | Win Rate: {backtest_results['trading']['win_rate']:.2f}%"
        )
        print(f"\n💾 Results: {output_file}")
        if mlflow_enabled and mlflow_run_id:
            print(f"🔬 MLflow: http://localhost:5000/experiments/{experiment_name}")
        print(f"{'=' * 80}\n")

        return backtest_results


def main():
    parser = argparse.ArgumentParser(
        description="Run Backtrader backtest with optional MLflow integration"
    )
    parser.add_argument("--strategy", required=True, help="Strategy file path")
    parser.add_argument("--symbols", nargs="+", required=True, help="Symbols")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--resolution", default="Daily", help="Resolution")
    parser.add_argument(
        "--params", type=json.loads, default={}, help="Strategy params as JSON"
    )
    parser.add_argument(
        "--params-file", help="JSON file containing strategy parameters"
    )
    parser.add_argument(
        "--config", default="config/backtest_config.yaml", help="Config file"
    )
    parser.add_argument(
        "--export-csv", action="store_true", help="Export trades to CSV"
    )
    parser.add_argument(
        "--export-text", action="store_true", help="Export text summary report"
    )

    # MLflow arguments
    parser.add_argument("--mlflow", action="store_true", help="Enable MLflow logging")
    parser.add_argument(
        "--project", default="Default", help="Project name for MLflow organization"
    )
    parser.add_argument(
        "--asset-class", default="Equities", help="Asset class for MLflow tagging"
    )
    parser.add_argument(
        "--strategy-family",
        default="Unknown",
        help="Strategy family for MLflow tagging",
    )
    parser.add_argument(
        "--team", default="quant_research", help="Team responsible for experiment"
    )
    parser.add_argument(
        "--status",
        default="research",
        help="Experiment status (research, testing, production)",
    )
    parser.add_argument(
        "--mlflow-config",
        default="config/mlflow_config.yaml",
        help="MLflow config file",
    )
    parser.add_argument(
        "--output-json", help="Output JSON file for results (for optimizer)"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Configure logging level based on debug flag
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Debug logging enabled")
    else:
        logging.getLogger().setLevel(logging.INFO)

    # Load parameters from file if specified
    if args.params_file:
        if not os.path.exists(args.params_file):
            print(f"❌ Error: Parameter file not found: {args.params_file}")
            sys.exit(1)
        try:
            with open(args.params_file, "r") as f:
                file_params = json.load(f)
            # Merge file params with command line params (command line takes precedence)
            args.params.update(file_params)
            print(f"📄 Loaded parameters from {args.params_file}")
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing parameter file {args.params_file}: {e}")
            sys.exit(1)

    runner = BacktestRunner(
        config_path=args.config, mlflow_config_path=args.mlflow_config
    )

    try:
        runner.run(
            strategy_path=args.strategy,
            symbols=args.symbols,
            start_date=args.start,
            end_date=args.end,
            strategy_params=args.params,
            resolution=args.resolution,
            export_csv=args.export_csv,
            export_text=args.export_text,
            mlflow_enabled=args.mlflow,
            project=args.project,
            asset_class=args.asset_class,
            strategy_family=args.strategy_family,
            team=args.team,
            status=args.status,
            output_json=args.output_json,
        )
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
