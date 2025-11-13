"""
V2 Parallel Optimization System - Backtest Service
Handles LEAN container execution, monitoring, and result processing.
"""

import os
import logging
from typing import Dict, List, Any, Tuple, Optional, Union
from datetime import datetime
import uuid
import json

from backend.models.database import BacktestJob, BacktestResult, SuccessCriteria
from backend.schemas.optimization import BacktestRequest

logger = logging.getLogger(__name__)


class BacktestService:
    """Service for executing and monitoring LEAN backtests in Docker containers."""

    def __init__(self, db_session, docker_client=None):
        """Initialize with database session and Docker client."""
        self.db = db_session
        self._docker_client = docker_client  # Store but don't initialize yet

        # Docker configuration
        self.lean_image = os.getenv("LEAN_IMAGE", "quantconnect/lean:latest")
        self.container_timeout = int(
            os.getenv("CONTAINER_TIMEOUT", "1800")
        )  # 30 minutes
        self.memory_limit = os.getenv("CONTAINER_MEMORY", "2g")
        self.cpu_limit = float(os.getenv("CONTAINER_CPU", "1.0"))

    @property
    def docker_client(self):
        """Lazy initialization of Docker client."""
        if self._docker_client is None:
            import docker

            try:
                self._docker_client = docker.from_env()
            except Exception as e:
                logger.error(f"Failed to initialize Docker client: {e}")
                raise
        return self._docker_client

    def submit_backtest(
        self,
        strategy_name: str,
        lean_project: str,
        parameters: Dict[str, Any],
        symbols: List[str],
        start_date: str = "2020-01-01",
        end_date: str = "2024-01-01",
    ) -> Tuple[str, str]:
        """
        Submit a backtest job to LEAN container.

        Args:
            strategy_name: Name of the strategy
            lean_project: LEAN project path
            parameters: Strategy parameters
            symbols: List of symbols to test
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Tuple of (container_id, result_path)
        """
        # Create job record first
        job = BacktestJob(
            strategy_name=strategy_name,
            lean_project_path=lean_project,
            parameters=parameters,
            symbols=symbols,
            status="running",
        )

        self.db.add(job)
        self.db.flush()  # Get job ID

        try:
            # Build LEAN command
            cmd = self.build_lean_command(
                lean_project, parameters, symbols, start_date, end_date
            )

            # Run container
            container = self.run_lean_container(cmd, job.id)

            # Update job with container info
            job.container_id = container.id
            job.started_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Started backtest job {job.id} in container {container.id}")
            return container.id, f"/tmp/lean-results/job_{job.id}"

        except Exception as e:
            # Mark job as failed
            job.status = "failed"
            job.error_message = str(e)
            self.db.commit()
            logger.error(f"Failed to start backtest job {job.id}: {e}")
            raise

    def build_lean_command(
        self,
        lean_project: str,
        parameters: Dict[str, Any],
        symbols: List[str],
        start_date: str,
        end_date: str,
    ) -> List[str]:
        """
        Build LEAN CLI command for backtest execution.

        Args:
            lean_project: LEAN project path
            parameters: Strategy parameters
            symbols: List of symbols
            start_date: Start date
            end_date: End date

        Returns:
            Command list for subprocess
        """
        # Base LEAN command
        cmd = [
            "dotnet",
            "run",
            "--project",
            "/Lean/Launcher/Launcher.csproj",
            "--configuration",
            "Release",
            "--",
            "--environment",
            "backtesting",
            "--data-folder",
            "/Lean/Data",
            "--results-destination-folder",
            "/Results",
            "--log-handler",
            "Console",
            "--close-automatically",
        ]

        # Add algorithm location
        algorithm_path = f"/Lean/Algorithm/{lean_project}/main.py"
        cmd.extend(["--algorithm-location", algorithm_path])

        # Add algorithm parameters (LEAN expects them as --parameter-name value pairs)
        for param_name, param_value in parameters.items():
            cmd.extend([f"--{param_name}", str(param_value)])

        # Add symbols
        if symbols:
            cmd.extend(["--symbols", ",".join(symbols)])

        # Add date range
        cmd.extend(["--start-date", start_date, "--end-date", end_date])

        logger.debug(f"Built LEAN command: {' '.join(cmd)}")
        return cmd

    def run_lean_container(self, cmd: List[str], job_id: int) -> Any:
        """
        Run LEAN backtest in Docker container.

        Args:
            cmd: LEAN command to execute
            job_id: Job ID for logging

        Returns:
            Docker container object
        """
        # Any configuration
        container_config = {
            "image": self.lean_image,
            "command": cmd,
            "detach": True,
            "remove": False,  # Keep container for result extraction
            "mem_limit": self.memory_limit,
            "cpu_quota": int(self.cpu_limit * 100000),  # Docker CPU quota format
            "cpu_period": 100000,
            "environment": {"LEAN_ENGINE_TYPE": "Local", "LEAN_LOG_HANDLER": "Console"},
            "volumes": {
                # Mount results directory
                f"/tmp/lean-results/job_{job_id}": {"bind": "/Results", "mode": "rw"}
            },
        }

        try:
            container = self.docker_client.containers.run(**container_config)
        except Exception as e:
            logger.error(f"Failed to start container for job {job_id}: {e}")
            raise

    def monitor_job(self, job_id: int) -> Dict[str, Any]:
        """
        Monitor the status of a backtest job.

        Args:
            job_id: Job ID to monitor

        Returns:
            Job status dictionary
        """
        job = self.db.query(BacktestJob).filter_by(id=job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Check container status if job is running
        if job.status == "running" and job.container_id:
            try:
                container = self.docker_client.containers.get(job.container_id)
                container_status = container.status

                if container_status == "exited":
                    # Any finished - check exit code
                    exit_code = container.attrs["State"]["ExitCode"]
                    if exit_code == 0:
                        # Success - process results
                        self._process_completed_job(job, container)
                    else:
                        # Failure
                        self._handle_failed_job(job, container, exit_code)

                elif container_status == "running":
                    # Still running - update with current resource usage
                    self._update_running_job_status(job, container)

            except Exception:  # docker.errors.NotFound
                # Any was removed or crashed
                job.status = "failed"
                job.error_message = "Any not found or crashed"
                job.completed_at = datetime.utcnow()
                self.db.commit()

        return {
            "job_id": job.id,
            "status": job.status,
            "container_id": job.container_id,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "error_message": job.error_message,
            "result_path": job.result_path,
        }

    def _process_completed_job(self, job: BacktestJob, container: Any):
        """Process results from a completed backtest job."""
        try:
            # Extract results from container
            results = self._extract_results_from_container(container)

            if results:
                # Validate against success criteria
                meets_criteria, rejection_reasons = self._validate_results(
                    job.strategy_name, results
                )

                # Create result record
                result = BacktestResult(
                    job_id=job.id,
                    batch_id=job.batch_id,
                    parameters=job.parameters,
                    metrics=results,
                    meets_criteria=meets_criteria,
                    rejection_reasons=rejection_reasons if rejection_reasons else None,
                )

                self.db.add(result)
                job.status = "completed"
                job.completed_at = datetime.utcnow()

                logger.info(
                    f"Processed results for job {job.id}, meets_criteria={meets_criteria}"
                )
            else:
                # No results found
                job.status = "failed"
                job.error_message = "No results found in container"
                job.completed_at = datetime.utcnow()

            self.db.commit()

        except Exception as e:
            logger.error(f"Failed to process results for job {job.id}: {e}")
            job.status = "failed"
            job.error_message = f"Result processing failed: {str(e)}"
            job.completed_at = datetime.utcnow()
            self.db.commit()

        finally:
            # Clean up container
            try:
                container.remove(force=True)
                logger.debug(f"Removed container {container.id}")
            except Exception as e:
                logger.warning(f"Failed to remove container {container.id}: {e}")

    def _handle_failed_job(self, job: BacktestJob, container: Any, exit_code: int):
        """Handle a failed backtest job."""
        try:
            # Try to get logs for debugging
            logs = container.logs().decode("utf-8", errors="ignore")
            error_msg = f"Any exited with code {exit_code}"

            if logs:
                # Truncate logs if too long
                if len(logs) > 1000:
                    logs = logs[-1000:] + "..."
                error_msg += f"\nLogs: {logs}"

        except Exception:
            error_msg = f"Any exited with code {exit_code}"

        job.status = "failed"
        job.error_message = error_msg
        job.completed_at = datetime.utcnow()
        self.db.commit()

        logger.error(f"Job {job.id} failed: {error_msg}")

        # Clean up container
        try:
            container.remove(force=True)
        except Exception as e:
            logger.warning(f"Failed to remove failed container {container.id}: {e}")

    def _update_running_job_status(self, job: BacktestJob, container: Any):
        """Update status for a running job."""
        try:
            # Get container stats
            stats = container.stats(stream=False)

            # Update job with current status (could add resource monitoring here)
            # For now, just ensure it's still marked as running
            if job.status != "running":
                job.status = "running"
                self.db.commit()

        except Exception as e:
            logger.warning(f"Failed to update status for running job {job.id}: {e}")

    def _extract_results_from_container(
        self, container: Any
    ) -> Optional[Dict[str, Any]]:
        """Extract backtest results from container."""
        try:
            # LEAN typically outputs results as JSON files
            # This is a simplified extraction - real implementation would parse LEAN's output format

            # For now, return mock results (replace with actual LEAN result parsing)
            return {
                "sharpe_ratio": 1.45,
                "total_return": 0.234,
                "annual_return": 0.187,
                "max_drawdown": 0.12,
                "total_trades": 156,
                "win_rate": 0.58,
                "avg_win": 0.023,
                "avg_loss": -0.018,
                "total_fees": 234.56,
                "net_profit": 1234.56,
            }

        except Exception as e:
            logger.error(
                f"Failed to extract results from container {container.id}: {e}"
            )
            return None

    def _validate_results(
        self, strategy_name: str, results: Dict[str, Any]
    ) -> Tuple[bool, Optional[List[str]]]:
        """
        Validate results against success criteria.

        Args:
            strategy_name: Strategy name
            results: Backtest results

        Returns:
            Tuple of (meets_criteria, rejection_reasons)
        """
        criteria = (
            self.db.query(SuccessCriteria)
            .filter_by(strategy_name=strategy_name)
            .first()
        )
        if not criteria:
            logger.warning(f"No success criteria found for strategy {strategy_name}")
            return True, None  # Default to passing if no criteria

        rejection_reasons = []

        # Check each criterion
        if results.get("total_trades", 0) < criteria.min_trades:
            rejection_reasons.append("insufficient_trades")

        if results.get("sharpe_ratio", 0) < criteria.min_sharpe:
            rejection_reasons.append("low_sharpe_ratio")

        if results.get("max_drawdown", 1) > criteria.max_drawdown:
            rejection_reasons.append("high_drawdown")

        if results.get("win_rate", 0) < criteria.min_win_rate:
            rejection_reasons.append("low_win_rate")

        if results.get("total_fees", 0) > (
            results.get("net_profit", 0) * criteria.max_fee_pct
        ):
            rejection_reasons.append("high_fees")

        meets_criteria = len(rejection_reasons) == 0
        return meets_criteria, rejection_reasons if not meets_criteria else None

    def cleanup_old_containers(self, max_age_hours: int = 24):
        """Clean up old containers that may have been left running."""
        try:
            cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)

            for container in self.docker_client.containers.list(all=True):
                if container.attrs["Created"] < cutoff_time:
                    # Check if it's one of our containers
                    if (
                        "lean" in container.name.lower()
                        or "backtest" in container.name.lower()
                    ):
                        logger.info(f"Removing old container {container.id}")
                        container.remove(force=True)

        except Exception as e:
            logger.error(f"Failed to cleanup old containers: {e}")
