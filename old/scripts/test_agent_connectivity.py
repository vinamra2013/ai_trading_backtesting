#!/usr/bin/env python3
"""
Agent Connectivity Test Script for FastAPI Backend (Epic 25 Story 9)
Tests both internal Docker network and external localhost access for AI agents.
"""

import requests
import json
import time
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class AgentConnectivityTest:
    """Test class for validating AI agent connectivity to FastAPI backend"""

    def __init__(self):
        self.internal_url = "http://fastapi-backend:8230"
        self.external_url = os.getenv("FASTAPI_BACKEND_URL", "http://localhost:8230")
        # If FASTAPI_BACKEND_URL is not set, use localhost as fallback
        if not os.getenv("FASTAPI_BACKEND_URL"):
            print(
                "⚠️  WARNING: FASTAPI_BACKEND_URL not set, using localhost:8230 as fallback"
            )
        self.timeout = 10

    def test_endpoint(
        self,
        url: str,
        endpoint: str,
        method: str = "GET",
        payload: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Test a specific endpoint"""
        full_url = f"{url}{endpoint}"

        try:
            if method == "GET":
                response = requests.get(full_url, timeout=self.timeout)
            elif method == "POST":
                response = requests.post(full_url, json=payload, timeout=self.timeout)
            else:
                return {"success": False, "error": f"Unsupported method: {method}"}

            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "cors_headers": {
                    "access_control_allow_origin": response.headers.get(
                        "Access-Control-Allow-Origin"
                    ),
                    "access_control_allow_methods": response.headers.get(
                        "Access-Control-Allow-Methods"
                    ),
                    "access_control_allow_headers": response.headers.get(
                        "Access-Control-Allow-Headers"
                    ),
                },
                "data": response.json()
                if response.headers.get("content-type", "").startswith(
                    "application/json"
                )
                else response.text,
            }
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}

    def test_health_endpoint(self, url: str) -> Dict[str, Any]:
        """Test health endpoint"""
        return self.test_endpoint(url, "/api/health")

    def test_backtest_submission(self, url: str) -> Dict[str, Any]:
        """Test backtest job submission"""
        payload = {
            "strategy": "sma_crossover",
            "symbols": ["SPY"],
            "parameters": {"fast_period": 10, "slow_period": 20},
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
        }
        return self.test_endpoint(url, "/api/backtests/run", "POST", payload)

    def test_optimization_submission(self, url: str) -> Dict[str, Any]:
        """Test optimization job submission"""
        payload = {
            "strategy": "sma_crossover",
            "symbols": ["SPY"],
            "parameter_space": {
                "fast_period": {"type": "int", "low": 5, "high": 20},
                "slow_period": {"type": "int", "low": 15, "high": 50},
            },
            "metric": "sharpe_ratio",
            "n_trials": 10,
        }
        return self.test_endpoint(url, "/api/optimization/run", "POST", payload)

    def test_analytics_endpoint(self, url: str) -> Dict[str, Any]:
        """Test analytics endpoint"""
        return self.test_endpoint(url, "/api/analytics/portfolio")

    def run_internal_tests(self) -> Dict[str, Any]:
        """Run tests against internal Docker network"""
        print("🔍 Testing Internal Docker Network Access (fastapi-backend:8230)")
        print("=" * 60)

        results = {
            "network_type": "internal_docker",
            "url": self.internal_url,
            "tests": {},
        }

        # Test health endpoint
        print("Testing health endpoint...")
        results["tests"]["health"] = self.test_health_endpoint(self.internal_url)
        print(
            f"  Status: {'✅ PASS' if results['tests']['health']['success'] else '❌ FAIL'}"
        )

        # Test backtest submission
        print("Testing backtest submission...")
        results["tests"]["backtest"] = self.test_backtest_submission(self.internal_url)
        print(
            f"  Status: {'✅ PASS' if results['tests']['backtest']['success'] else '❌ FAIL'}"
        )

        # Test optimization submission
        print("Testing optimization submission...")
        results["tests"]["optimization"] = self.test_optimization_submission(
            self.internal_url
        )
        print(
            f"  Status: {'✅ PASS' if results['tests']['optimization']['success'] else '❌ FAIL'}"
        )

        # Test analytics endpoint
        print("Testing analytics endpoint...")
        results["tests"]["analytics"] = self.test_analytics_endpoint(self.internal_url)
        print(
            f"  Status: {'✅ PASS' if results['tests']['analytics']['success'] else '❌ FAIL'}"
        )

        return results

    def run_external_tests(self) -> Dict[str, Any]:
        """Run tests against external access"""
        print(f"\n🔍 Testing External Access ({self.external_url})")
        print("=" * 60)

        results = {"network_type": "external", "url": self.external_url, "tests": {}}

        # Test health endpoint
        print("Testing health endpoint...")
        results["tests"]["health"] = self.test_health_endpoint(self.external_url)
        print(
            f"  Status: {'✅ PASS' if results['tests']['health']['success'] else '❌ FAIL'}"
        )

        # Test CORS headers
        if results["tests"]["health"]["success"]:
            cors_origin = (
                results["tests"]["health"]
                .get("cors_headers", {})
                .get("access_control_allow_origin")
            )
            print(f"  CORS Origin: {cors_origin}")

        # Test backtest submission (dry run - don't actually submit)
        print("Testing backtest endpoint accessibility...")
        backtest_result = self.test_endpoint(
            self.external_url, "/api/backtests/run", "POST", {}
        )
        results["tests"]["backtest_accessible"] = {
            "success": backtest_result["success"]
            or backtest_result.get("status_code")
            in [400, 422],  # 400/422 means endpoint is accessible but payload invalid
            "status_code": backtest_result.get("status_code"),
            "error": backtest_result.get("error"),
        }
        print(
            f"  Status: {'✅ PASS' if results['tests']['backtest_accessible']['success'] else '❌ FAIL'}"
        )

        return results

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all connectivity tests"""
        print("🚀 AI Agent Connectivity Test for FastAPI Backend")
        print("Epic 25 Story 9: AI Agent Integration & Network Access")
        print("=" * 60)

        all_results = {
            "timestamp": time.time(),
            "environment": {
                "internal_url": self.internal_url,
                "external_url": self.external_url,
                "fastapi_backend_url_env": os.getenv("FASTAPI_BACKEND_URL"),
            },
            "tests": {},
        }

        # Run internal tests
        all_results["tests"]["internal"] = self.run_internal_tests()

        # Run external tests
        all_results["tests"]["external"] = self.run_external_tests()

        # Summary
        print("\n📊 Test Summary")
        print("=" * 60)

        internal_pass = sum(
            1
            for test in all_results["tests"]["internal"]["tests"].values()
            if test["success"]
        )
        internal_total = len(all_results["tests"]["internal"]["tests"])
        external_pass = sum(
            1
            for test in all_results["tests"]["external"]["tests"].values()
            if test["success"]
        )
        external_total = len(all_results["tests"]["external"]["tests"])

        print(f"Internal Docker Tests: {internal_pass}/{internal_total} passed")
        print(f"External Access Tests: {external_pass}/{external_total} passed")

        all_pass = internal_pass + external_pass
        all_total = internal_total + external_total
        print(f"Overall: {all_pass}/{all_total} tests passed")

        if all_pass == all_total:
            print(
                "🎉 All tests passed! AI agents can successfully connect to FastAPI backend."
            )
        else:
            print("⚠️  Some tests failed. Check the detailed results above.")

        return all_results


def main():
    """Main test execution"""
    tester = AgentConnectivityTest()
    results = tester.run_all_tests()

    # Save results to file
    output_file = "test_agent_connectivity_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n📄 Detailed results saved to: {output_file}")


if __name__ == "__main__":
    main()
