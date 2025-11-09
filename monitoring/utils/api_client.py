# API client utility for FastAPI backend communication (Epic 25 Story 8)

import requests
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import time
import logging

logger = logging.getLogger(__name__)


class APIClient:
    """Client for communicating with FastAPI backend"""

    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """
        Initialize API client

        Args:
            base_url: Base URL of the FastAPI backend (auto-detects if None)
            timeout: Request timeout in seconds
        """
        if base_url is None:
            # Auto-detect based on environment
            import os

            # Check if running in Docker (service name available)
            if os.path.exists("/.dockerenv") or os.environ.get("FASTAPI_BACKEND_URL"):
                # Inside Docker or explicit URL set
                backend_url = os.environ.get(
                    "FASTAPI_BACKEND_URL", "http://fastapi-backend:8230"
                )
                self.base_url = backend_url.rstrip("/")
            else:
                # Local development
                self.base_url = "http://localhost:8230"
        else:
            self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            data: Request body data
            params: Query parameters
            retries: Number of retry attempts

        Returns:
            Response JSON data

        Raises:
            Exception: If request fails after all retries
        """
        url = f"{self.base_url}{endpoint}"

        for attempt in range(retries + 1):
            try:
                if method.upper() == "GET":
                    response = self.session.get(
                        url, params=params, timeout=self.timeout
                    )
                elif method.upper() == "POST":
                    response = self.session.post(
                        url, json=data, params=params, timeout=self.timeout
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                if attempt == retries:
                    logger.error(
                        f"API request failed after {retries + 1} attempts: {e}"
                    )
                    raise Exception(f"Backend API unavailable: {str(e)}")
                else:
                    logger.warning(f"API request attempt {attempt + 1} failed: {e}")
                    time.sleep(1)  # Wait before retry

    # Backtest endpoints
    def list_backtests(
        self,
        strategy: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """List backtests with optional filtering"""
        params = {"page": page, "page_size": page_size}
        if strategy:
            params["strategy"] = strategy
        if status:
            params["status"] = status
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        return self._make_request("GET", "/api/backtests", params=params)

    def get_backtest(self, backtest_id: int) -> Dict[str, Any]:
        """Get detailed backtest information"""
        return self._make_request("GET", f"/api/backtests/{backtest_id}")

    def run_backtest(
        self,
        strategy: str,
        symbols: List[str],
        parameters: Optional[Dict[str, Any]] = None,
        timeframe: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit a new backtest job"""
        data = {
            "strategy": strategy,
            "symbols": symbols,
            "parameters": parameters or {},
            "timeframe": timeframe,
        }
        if start_date:
            data["start_date"] = start_date
        if end_date:
            data["end_date"] = end_date

        return self._make_request("POST", "/api/backtests/run", data=data)

    def get_backtest_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a backtest job"""
        return self._make_request("GET", f"/api/backtests/status/{job_id}")

    # Optimization endpoints
    def run_optimization(
        self,
        strategy: str,
        parameters: Dict[str, Dict[str, Any]],
        optimization_metric: str = "sharpe_ratio",
        max_trials: int = 100,
    ) -> Dict[str, Any]:
        """Submit a new optimization job"""
        data = {
            "strategy": strategy,
            "parameters": parameters,
            "optimization_metric": optimization_metric,
            "max_trials": max_trials,
        }
        return self._make_request("POST", "/api/optimization/run", data=data)

    def list_optimizations(self) -> List[Dict[str, Any]]:
        """List all optimization jobs"""
        # Note: This endpoint might need to be added to the optimization router
        return self._make_request("GET", "/api/optimization")

    def get_optimization(self, optimization_id: int) -> Dict[str, Any]:
        """Get detailed optimization information"""
        return self._make_request("GET", f"/api/optimization/{optimization_id}")

    # Analytics endpoints
    def get_portfolio_analytics(
        self,
        strategy_filter: Optional[str] = None,
        symbol_filter: Optional[str] = None,
        days_back: int = 90,
        min_completed_backtests: int = 1,
    ) -> Dict[str, Any]:
        """Get portfolio-level analytics and strategy rankings"""
        params = {
            "days_back": days_back,
            "min_completed_backtests": min_completed_backtests,
        }
        if strategy_filter:
            params["strategy_filter"] = strategy_filter
        if symbol_filter:
            params["symbol_filter"] = symbol_filter

        return self._make_request("GET", "/api/analytics/portfolio", params=params)

    # MLflow endpoints
    def list_experiments(self) -> List[Dict[str, Any]]:
        """List MLflow experiments"""
        return self._make_request("GET", "/api/mlflow/experiments")

    def get_experiment_runs(self, experiment_id: str) -> List[Dict[str, Any]]:
        """Get runs for a specific experiment"""
        return self._make_request("GET", f"/api/mlflow/runs/{experiment_id}")

    # Health check
    def health_check(self) -> Dict[str, Any]:
        """Check backend health"""
        return self._make_request("GET", "/api/health")

    def is_available(self) -> bool:
        """Check if backend is available"""
        try:
            self.health_check()
            return True
        except Exception:
            return False


# Global client instance
_api_client = None


def get_api_client() -> APIClient:
    """Get or create API client instance"""
    global _api_client
    if _api_client is None:
        _api_client = APIClient()
    return _api_client
