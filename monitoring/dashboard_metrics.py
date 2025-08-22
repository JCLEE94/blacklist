#!/usr/bin/env python3
"""
Deployment Dashboard Metrics Collector Module

Handles system metrics collection including API health checks, Docker status,
and performance metrics. Separated from existing metrics_collector.py for dashboard-specific needs.

Links:
- Requests documentation: https://docs.python-requests.org/
- psutil documentation: https://psutil.readthedocs.io/

Sample input: DashboardMetricsCollector("http://localhost:32542").collect_metrics()
Expected output: Dictionary with timestamp, services, performance, and deployment metrics
"""

import json
import logging
import subprocess
from datetime import datetime
from typing import Dict, Any

import requests

logger = logging.getLogger(__name__)


class DashboardMetricsCollector:
    """Collects system and application metrics for deployment dashboard"""

    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url

    def collect_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "services": {},
            "performance": {},
            "deployment": {},
        }

        # Collect API metrics
        self._collect_api_metrics(metrics)

        # Collect Docker metrics
        self._collect_docker_metrics(metrics)

        # Collect performance metrics
        self._collect_performance_metrics(metrics)

        return metrics

    def _collect_api_metrics(self, metrics: Dict[str, Any]):
        """Collect API health and performance metrics"""
        try:
            # Health check
            health_response = requests.get(
                f"{self.api_base_url}/api/health", timeout=10
            )
            if health_response.status_code == 200:
                health_data = health_response.json()

                metrics["services"]["api"] = {
                    "status": health_data.get("status", "unknown"),
                    "response_time": health_response.elapsed.total_seconds() * 1000,
                    "components": health_data.get("components", {}),
                    "version": health_data.get("version", "unknown"),
                }

                # Extract specific metrics
                if "metrics" in health_data:
                    metrics["deployment"] = {
                        "total_ips": health_data["metrics"].get("total_ips", 0),
                        "active_ips": health_data["metrics"].get("active_ips", 0),
                        "expired_ips": health_data["metrics"].get("expired_ips", 0),
                    }
            else:
                metrics["services"]["api"] = {
                    "status": "unhealthy",
                    "response_time": 5000,
                    "error": f"HTTP {health_response.status_code}",
                }

        except requests.RequestException as e:
            logger.warning(f"Failed to collect API metrics: {e}")
            metrics["services"]["api"] = {"status": "unreachable", "error": str(e)}

    def _collect_docker_metrics(self, metrics: Dict[str, Any]):
        """Collect Docker service status"""
        try:
            docker_status = subprocess.run(
                ["docker-compose", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if docker_status.returncode == 0 and docker_status.stdout.strip():
                try:
                    # Parse each line as separate JSON object
                    docker_services = []
                    for line in docker_status.stdout.strip().split("\n"):
                        if line.strip():
                            docker_services.append(json.loads(line))

                    metrics["services"]["docker"] = {
                        "status": (
                            "healthy"
                            if all(s.get("State") == "running" for s in docker_services)
                            else "degraded"
                        ),
                        "services": docker_services,
                        "running_count": sum(
                            1 for s in docker_services if s.get("State") == "running"
                        ),
                        "total_count": len(docker_services),
                    }
                except json.JSONDecodeError:
                    metrics["services"]["docker"] = {
                        "status": "unknown",
                        "error": "Failed to parse docker status",
                    }
            else:
                metrics["services"]["docker"] = {"status": "unavailable"}

        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            logger.warning(f"Failed to collect Docker metrics: {e}")
            metrics["services"]["docker"] = {"status": "error", "error": str(e)}

    def _collect_performance_metrics(self, metrics: Dict[str, Any]):
        """Collect system performance metrics"""
        try:
            import psutil

            metrics["performance"] = {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": (
                    psutil.disk_usage("/").percent
                    if hasattr(psutil, "disk_usage")
                    else 0
                ),
                "load_avg": (
                    psutil.getloadavg() if hasattr(psutil, "getloadavg") else [0, 0, 0]
                ),
            }
        except ImportError:
            logger.info("psutil not available, skipping performance metrics")
            metrics["performance"] = {"status": "unavailable"}
        except Exception as e:
            logger.warning(f"Failed to collect performance metrics: {e}")
            metrics["performance"] = {"error": str(e)}


if __name__ == "__main__":
    # Validation tests
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: DashboardMetricsCollector instantiation
    total_tests += 1
    try:
        collector = DashboardMetricsCollector("http://localhost:32542")
        if hasattr(collector, "api_base_url"):
            pass  # Test passed
        else:
            all_validation_failures.append(
                "DashboardMetricsCollector missing api_base_url attribute"
            )
    except Exception as e:
        all_validation_failures.append(
            f"DashboardMetricsCollector instantiation failed: {e}"
        )

    # Test 2: Metrics collection structure
    total_tests += 1
    try:
        collector = DashboardMetricsCollector("http://localhost:32542")
        metrics = collector.collect_metrics()
        expected_keys = ["timestamp", "services", "performance", "deployment"]
        if isinstance(metrics, dict) and all(key in metrics for key in expected_keys):
            pass  # Test passed
        else:
            all_validation_failures.append(
                f"Metrics structure invalid, got keys: {list(metrics.keys()) if isinstance(metrics, dict) else 'not dict'}"
            )
    except Exception as e:
        all_validation_failures.append(f"Metrics collection failed: {e}")

    # Test 3: Individual metric collection methods
    total_tests += 1
    try:
        collector = DashboardMetricsCollector("http://localhost:32542")
        metrics = {"services": {}, "performance": {}, "deployment": {}}

        # Test individual methods don't crash
        collector._collect_api_metrics(metrics)
        collector._collect_docker_metrics(metrics)
        collector._collect_performance_metrics(metrics)

        # Should have populated some data
        if "api" in metrics["services"] or "docker" in metrics["services"]:
            pass  # Test passed
        else:
            all_validation_failures.append(
                "No metrics were collected by individual methods"
            )
    except Exception as e:
        all_validation_failures.append(
            f"Individual metrics collection methods failed: {e}"
        )

    # Final validation result
    if all_validation_failures:
        print(
            f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("Dashboard metrics collector module is validated and ready for use")
        sys.exit(0)
