#!/usr/bin/env python3
"""
QuantConnect Optimization Runner
Automates LEAN optimization workflow: config → lean optimize → results import → summary
"""

import argparse
import os
import sys
import subprocess
import yaml
import time
import re
from pathlib import Path
from datetime import datetime
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters (with defaults)
DB_NAME = os.getenv("POSTGRES_DB", "trading")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
LEAN_PROJECTS_DIR = PROJECT_ROOT / "lean_projects"
CONFIG_DIR = PROJECT_ROOT / "configs"


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Run LEAN optimization and import results to PostgreSQL"
    )
    parser.add_argument(
        "--config", type=str, help="Path to optimization config YAML file"
    )
    parser.add_argument(
        "--batch", type=str, help="Path to batch config file (multiple optimizations)"
    )
    parser.add_argument(
        "--estimate", action="store_true", help="Estimate fee impact only (dry run)"
    )
    parser.add_argument(
        "--no-import", action="store_true", help="Skip results import to database"
    )

    args = parser.parse_args()

    if not args.config and not args.batch:
        parser.error("Either --config or --batch must be specified")

    return args


def load_config(config_path):
    """Load and validate YAML configuration file"""
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    # Validate required sections
    required_sections = ["strategy", "optimization", "success_criteria"]
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required section '{section}' in config")

    # Validate strategy fields
    required_strategy_fields = ["name", "lean_project_path"]
    for field in required_strategy_fields:
        if field not in config["strategy"]:
            raise ValueError(f"Missing required strategy field '{field}'")

    # Validate optimization fields
    required_opt_fields = ["type", "target_metric", "target_direction", "parameters"]
    for field in required_opt_fields:
        if field not in config["optimization"]:
            raise ValueError(f"Missing required optimization field '{field}'")

    return config


def calculate_combinations(parameters):
    """Calculate total number of parameter combinations"""
    total = 1
    for param_name, param_config in parameters.items():
        # Handle two parameter types: range-based and discrete values
        if "values" in param_config:
            # Discrete values parameter (e.g., require_trend: [true, false])
            num_values = len(param_config["values"])
        elif (
            "start" in param_config and "end" in param_config and "step" in param_config
        ):
            # Range-based parameter (e.g., rsi_period: start=10, end=20, step=5)
            start = param_config["start"]
            end = param_config["end"]
            step = param_config["step"]
            num_values = int((end - start) / step) + 1
        else:
            raise ValueError(
                f"Parameter '{param_name}' missing required config: either 'values' or 'start/end/step'"
            )

        total *= num_values

    return total


def estimate_fees(config):
    """Estimate fee impact based on configuration (simplified)"""
    print("\n" + "=" * 60)
    print("FEE ESTIMATION (Dry Run)")
    print("=" * 60)

    strategy_name = config["strategy"]["name"]
    parameters = config["optimization"]["parameters"]
    total_combinations = calculate_combinations(parameters)

    print(f"\nStrategy: {strategy_name}")
    print(f"Total Parameter Combinations: {total_combinations}")

    # Rough estimation (would need actual strategy logic for precise estimate)
    print(f"\n⚠️  WARNING: Fee estimation requires running actual backtests")
    print(f"   This is a DRY RUN. To get fee estimates, remove --estimate flag.")
    print(f"\n   Expected combinations to test: {total_combinations}")
    print(
        f"   Estimated time (@ 30 sec/backtest): {(total_combinations * 30) / 60:.1f} minutes"
    )

    print("\n" + "=" * 60)


def build_lean_optimize_command(config):
    """Build the lean optimize command from config (local execution)"""
    project_name = config["strategy"]["lean_project_path"]
    opt_config = config["optimization"]

    # Base command - using LOCAL optimize (not cloud)
    cmd = [
        "lean",
        "optimize",
        project_name,
        "--target",
        opt_config["target_metric"],
        "--target-direction",
        opt_config["target_direction"],
        "--detach",  # Run in detached mode to avoid hanging
        "--verbose",  # Enable debug logging to identify hanging issues
    ]

    # Add optimizer strategy (required for non-interactive mode)
    # Valid values: "grid search" or "euler search" (lowercase)
    if "type" in opt_config:
        strategy = opt_config["type"].lower()
        cmd.extend(["--strategy", strategy])

    # Add parameters
    for param_name, param_config in opt_config["parameters"].items():
        # Always use range format (start/end/step) for Lean CLI compatibility
        # The 'values' field is used for documentation and validation, not CLI syntax
        if "start" in param_config and "end" in param_config and "step" in param_config:
            # Range parameter (numeric)
            cmd.extend(
                [
                    "--parameter",
                    param_name,
                    str(param_config["start"]),
                    str(param_config["end"]),
                    str(param_config["step"]),
                ]
            )
        elif "values" in param_config:
            # Fallback: for truly discrete parameters, use first value as fixed parameter
            # Note: Lean CLI doesn't support true discrete optimization, so this is a limitation
            cmd.extend(["--parameter", param_name, str(param_config["values"][0])])
        else:
            raise ValueError(
                f"Parameter '{param_name}' missing required config: need either 'start/end/step' or 'values'"
            )

    # Add constraints if present
    if "constraints" in opt_config:
        for constraint in opt_config["constraints"]:
            cmd.extend(["--constraint", constraint])

    return cmd


def ensure_strategy_in_db(config):
    """Ensure strategy exists in database, create if not"""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
        )
        cursor = conn.cursor()

        strategy = config["strategy"]

        # Check if strategy exists
        cursor.execute("SELECT id FROM strategies WHERE name = %s", (strategy["name"],))
        result = cursor.fetchone()

        if result:
            strategy_id = result[0]
        else:
            # Insert new strategy
            cursor.execute(
                """
                INSERT INTO strategies (name, category, asset_class, lean_project_path, description, status)
                VALUES (%s, %s, %s, %s, %s, 'testing')
                RETURNING id
            """,
                (
                    strategy["name"],
                    strategy.get("category", "unknown"),
                    strategy.get("asset_class", "unknown"),
                    strategy["lean_project_path"],
                    strategy.get("description", ""),
                ),
            )
            strategy_id = cursor.fetchone()[0]
            conn.commit()

        cursor.close()
        conn.close()

        return strategy_id

    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        print(f"   Connection: postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
        return None


def create_optimization_run_record(config, strategy_id):
    """Create optimization run record in database"""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
        )
        cursor = conn.cursor()

        opt_config = config["optimization"]
        total_combinations = calculate_combinations(opt_config["parameters"])

        cursor.execute(
            """
            INSERT INTO optimization_runs
            (strategy_id, optimization_type, target_metric, target_direction, total_combinations, status)
            VALUES (%s, %s, %s, %s, %s, 'running')
            RETURNING id
        """,
            (
                strategy_id,
                opt_config["type"],
                opt_config["target_metric"],
                opt_config["target_direction"],
                total_combinations,
            ),
        )

        run_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()

        return run_id

    except psycopg2.Error as e:
        print(f"❌ Database error creating optimization run: {e}")
        return None


def extract_optimization_id(output):
    """Extract optimization ID from lean cloud optimize output"""
    # Look for patterns like "Optimization '12345' started" or "optimization-id: 12345"
    patterns = [
        r"Optimization '(\w+)' started",
        r"optimization[- ]id[:\s]+(\w+)",
        r"Optimization ID[:\s]+(\w+)",
        r"Started optimization (\w+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def check_optimization_status(project_name):
    """Check status of running optimization via lean cloud status"""
    try:
        result = subprocess.run(
            ["lean", "cloud", "status", project_name],
            cwd=LEAN_PROJECTS_DIR,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            output = result.stdout.lower()

            # Check for completion indicators
            if "completed" in output or "finished" in output:
                return "completed"
            elif "running" in output or "in progress" in output:
                return "running"
            elif "failed" in output or "error" in output:
                return "failed"

        return "unknown"

    except subprocess.TimeoutExpired:
        return "unknown"
    except Exception as e:
        print(f"⚠️  Error checking status: {e}")
        return "unknown"


def wait_for_optimization_completion(
    project_name, optimization_id=None, poll_interval=30, max_wait_minutes=120
):
    """Poll optimization status until completion"""
    print(f"\n⏳ Waiting for optimization to complete...")
    print(f"   Poll interval: {poll_interval}s | Max wait: {max_wait_minutes} minutes")

    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60

    while True:
        elapsed = time.time() - start_time

        if elapsed > max_wait_seconds:
            print(f"\n⚠️  Timeout: Optimization exceeded {max_wait_minutes} minutes")
            return False

        # Check status
        status = check_optimization_status(project_name)

        elapsed_str = f"{int(elapsed / 60)}m {int(elapsed % 60)}s"

        if status == "completed":
            print(f"\n✅ Optimization completed after {elapsed_str}")
            return True
        elif status == "failed":
            print(f"\n❌ Optimization failed after {elapsed_str}")
            return False
        elif status == "running":
            print(f"   [{elapsed_str}] Status: Running...")
        else:
            print(f"   [{elapsed_str}] Status: Unknown (continuing...)")

        time.sleep(poll_interval)

    return False


def run_optimization(config):
    """Execute LEAN local optimization in detached mode"""
    strategy_name = config["strategy"]["name"]
    project_path = config["strategy"]["lean_project_path"]

    print("\n" + "=" * 60)
    print(f"RUNNING LOCAL OPTIMIZATION: {strategy_name}")
    print("=" * 60)

    # Ensure strategy exists in database
    strategy_id = ensure_strategy_in_db(config)
    if not strategy_id:
        print("❌ Failed to ensure strategy in database. Continuing anyway...")
    else:
        # Create optimization run record
        run_id = create_optimization_run_record(config, strategy_id)
        if run_id:
            print(f"✅ Created optimization run record (ID: {run_id})")

    # Build command
    cmd = build_lean_optimize_command(config)

    print(f"\nCommand: {' '.join(cmd)}")
    print(f"\nWorking directory: {LEAN_PROJECTS_DIR}")
    print(
        f"\nTotal combinations: {calculate_combinations(config['optimization']['parameters'])}"
    )
    print("\n⚠️  NOTE: Running in DETACHED mode.")
    print("   LEAN optimize will start in background and script will exit immediately.")
    print("   Container will continue running until optimization completes.")
    print("\n" + "-" * 60)

    # Execute optimization (detached mode - exits immediately)
    try:
        result = subprocess.run(
            cmd,
            cwd=LEAN_PROJECTS_DIR,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,  # Short timeout since detached mode exits immediately
        )

        # Display output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        if result.returncode != 0:
            print(f"\n❌ Failed to start optimization (exit code {result.returncode})")
            return False

        print("\n✅ Optimization started successfully in detached container")

        # Extract container name and output directory from output
        container_match = re.search(r"'([^']+)' container", result.stdout)
        output_match = re.search(r"stored in '([^']+)'", result.stdout)

        container_name = None
        if container_match:
            container_name = container_match.group(1)
            print(f"\n⏳ Monitoring container: {container_name}")
            print(f"   Docker logs: docker logs -f {container_name}")
        else:
            print("⚠️  Could not extract container name from output")
            print(f"   Output was: {result.stdout}")

        results_dir = None
        if output_match:
            output_dir = output_match.group(1)
            print(f"   Results will be in: {output_dir}")
            results_dir = LEAN_PROJECTS_DIR / output_dir

        # Monitor for completion regardless of container name extraction
        print("\n   Waiting for optimization to complete...")
        dots = 0
        total_combinations = calculate_combinations(
            config["optimization"]["parameters"]
        )
        stall_count = 0
        stall_threshold = 12  # 12 checks with no progress = 2 minutes

        last_result_count = 0
        start_time = time.time()

        while True:
            # Check if result files exist
            result_count = 0
            if results_dir and results_dir.exists():
                # Count summary JSON files (completed backtests that passed constraints)
                json_files = [
                    f
                    for f in results_dir.glob("**/*.json")
                    if f.name not in ["optimizer-config.json", "config.json"]
                    and "-summary.json" in f.name  # More specific pattern
                ]
                result_count = len(json_files)

                if result_count > 0:
                    progress = f"{result_count}/{total_combinations}"
                    elapsed = time.time() - start_time
                    rate = (
                        result_count / max(elapsed, 1) * 3600
                    )  # combinations per hour
                    eta_hours = (total_combinations - result_count) / max(rate, 0.1)
                    print(
                        f"\r   Progress: {progress} combinations | {rate:.1f}/hour | ETA: {eta_hours:.1f}h",
                        end="",
                        flush=True,
                    )

            # Check if optimization is complete (all combinations processed)
            # For constrained optimizations, we can't rely on result count alone
            if container_name:
                check_result = subprocess.run(
                    [
                        "docker",
                        "ps",
                        "-a",
                        "--filter",
                        f"name={container_name}",
                        "--format",
                        "{{.Status}}",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                status = check_result.stdout.strip()
                if "Exited" in status:
                    print(f"\n\n✅ Optimization container exited: {status}")
                    print(
                        f"   Final results: {result_count} combinations passed constraints"
                    )
                    return True

            # Check for stall (no progress for extended period)
            # For constrained optimizations, allow longer stalls since many combinations may fail constraints
            if result_count == last_result_count:
                stall_count += 1
                if stall_count >= stall_threshold:
                    print(
                        f"\n\n⚠️  No new results for {stall_threshold * 10}s - checking optimization status..."
                    )
                    if container_name:
                        # Check if optimization is still actively processing
                        logs_result = subprocess.run(
                            ["docker", "logs", "--tail", "10", container_name],
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        recent_logs = logs_result.stdout

                        # Look for signs of active processing
                        if (
                            "Analysis Complete" in recent_logs
                            or "launched backtest" in recent_logs
                        ):
                            print(
                                "   ✅ Optimization still active - continuing to wait..."
                            )
                            stall_count = stall_threshold // 2  # Reset partially
                        elif "Error" in recent_logs or "Exception" in recent_logs:
                            print("   ❌ Errors detected in container logs")
                            return False
                        else:
                            print(
                                "   ⚠️  Optimization may be stalled - continuing to monitor..."
                            )
            else:
                stall_count = 0  # Reset stall counter on progress

            last_result_count = result_count

            # Print progress dots when no results yet
            if result_count == 0:
                print(".", end="", flush=True)
                dots += 1
                if dots >= 60:  # New line every 60 dots (10 minutes)
                    print()
                    dots = 0

            time.sleep(10)  # Check every 10 seconds

    except subprocess.TimeoutExpired:
        print("\n⚠️  Command timed out (this shouldn't happen in detached mode)")
        return False
    except Exception as e:
        print(f"\n❌ Error running optimization: {e}")
        return False


def import_results(config):
    """Import optimization results to database"""
    project_name = config["strategy"]["lean_project_path"]

    # LEAN stores results in project/optimizations/<timestamp>/
    # Find the most recent optimization directory
    project_dir = LEAN_PROJECTS_DIR / project_name
    optimizations_dir = project_dir / "optimizations"

    if not optimizations_dir.exists():
        print(f"\n⚠️  Optimizations directory not found: {optimizations_dir}")
        print("   Skipping results import.")
        return False

    # Get most recent optimization run
    optimization_runs = sorted(
        optimizations_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True
    )
    if not optimization_runs:
        print(f"\n⚠️  No optimization runs found in: {optimizations_dir}")
        print("   Skipping results import.")
        return False

    optimization_dir = optimization_runs[0]
    print(f"\n📂 Using most recent optimization: {optimization_dir.name}")

    # Call results_importer.py
    importer_script = PROJECT_ROOT / "scripts" / "results_importer.py"

    if not importer_script.exists():
        print(f"\n⚠️  Results importer script not found: {importer_script}")
        print("   Skipping results import.")
        return False

    print(f"\nImporting results from: {optimization_dir}")

    # Get strategy name from config to pass to importer
    strategy_name = config["strategy"]["name"]

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(importer_script),
                "--optimization-dir",
                str(optimization_dir),
                "--strategy-name",
                strategy_name,
            ],
            capture_output=False,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print(f"\n❌ Results import failed with exit code {result.returncode}")
            return False

        return True

    except Exception as e:
        print(f"\n❌ Error importing results: {e}")
        return False


def print_summary(config):
    """Print short summary from database"""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
        )
        cursor = conn.cursor()

        strategy_name = config["strategy"]["name"]

        # Get summary from most recent optimization run
        cursor.execute(
            """
            SELECT
                COUNT(*) as total_runs,
                SUM(CASE WHEN meets_criteria THEN 1 ELSE 0 END) as passed,
                MAX(sharpe_ratio) as best_sharpe
            FROM backtest_results b
            JOIN strategies s ON b.strategy_id = s.id
            WHERE s.name = %s
              AND b.completed_at >= NOW() - INTERVAL '1 hour'
        """,
            (strategy_name,),
        )

        result = cursor.fetchone()

        if result and result[0] > 0:
            total_runs, passed, best_sharpe = result
            print("\n" + "=" * 60)
            print("SUMMARY")
            print("=" * 60)
            print(
                f"{total_runs} runs complete, {passed or 0} passed, best Sharpe: {best_sharpe or 0:.2f}"
            )
            print("=" * 60)
        else:
            print("\n⚠️  No results found in database (recent 1 hour)")

        cursor.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"\n⚠️  Could not fetch summary from database: {e}")


def main():
    """Main execution flow"""
    args = parse_args()

    # Auto-detect if we should run in Docker
    if not os.path.exists("/.dockerenv"):
        # We're on the host - check if Docker is available and container exists
        print("🐳 Detected host environment - checking for Docker container...")

        try:
            # Check if lean-optimizer container exists
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "-a",
                    "--filter",
                    "name=lean-optimizer",
                    "--format",
                    "{{.Names}}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            if "lean-optimizer" in result.stdout:
                print("✅ Found lean-optimizer container - delegating to Docker...")

                # Ensure container is running
                subprocess.run(
                    ["docker", "compose", "up", "-d", "lean-optimizer"],
                    cwd=PROJECT_ROOT,
                    check=False,
                )

                # Build docker exec command
                # Use absolute host paths since container mounts at same path
                docker_cmd = [
                    "docker",
                    "exec",
                    "-it",
                    "lean-optimizer",
                    "python",
                    str(PROJECT_ROOT / "scripts" / "optimize_runner.py"),
                ]

                # Pass through all original arguments with absolute paths
                if args.config:
                    config_abs = PROJECT_ROOT / args.config
                    docker_cmd.extend(["--config", str(config_abs)])
                if args.batch:
                    batch_abs = PROJECT_ROOT / args.batch
                    docker_cmd.extend(["--batch", str(batch_abs)])
                if args.estimate:
                    docker_cmd.append("--estimate")
                if args.no_import:
                    docker_cmd.append("--no-import")

                # Execute in container
                result = subprocess.run(docker_cmd)
                return result.returncode
            else:
                print("⚠️  lean-optimizer container not found - running on host")
                print(
                    "   Run 'docker compose up -d lean-optimizer' to enable Docker mode"
                )

        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  Docker not available - running on host")
    else:
        print("🐳 Running inside Docker container")

    # Handle batch mode (not implemented yet - would loop through multiple configs)
    if args.batch:
        print(
            "❌ Batch mode not yet implemented. Use --config for single optimization."
        )
        return 1

    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return 1

    # Estimate mode
    if args.estimate:
        estimate_fees(config)
        return 0

    # Run optimization
    success = run_optimization(config)

    if not success:
        print("\n❌ Optimization failed. Exiting.")
        return 1

    # Import results (unless --no-import)
    if not args.no_import:
        import_results(config)

        # Print summary
        print_summary(config)

    return 0


if __name__ == "__main__":
    sys.exit(main())
