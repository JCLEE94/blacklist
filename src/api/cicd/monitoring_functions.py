#!/usr/bin/env python3
"""
Monitoring Functions for CI/CD Health Checks

This module provides monitoring and verification functions for CI/CD pipelines including:
- Production endpoint verification
- Smoke test execution
- Recommendation generation based on results
- Status determination algorithms

Third-party packages:
- requests: https://docs.python-requests.org/

Sample input: URLs, verification steps, test configurations
Expected output: Verification results, recommendations, status summaries
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

# Configuration
PRODUCTION_URL = os.getenv("PRODUCTION_URL", "https://blacklist.jclee.me")


def verify_api_endpoints() -> Dict[str, Any]:
    """Verify all critical API endpoints"""
    endpoints = [
        "/health",
        "/api/health",
        "/api/blacklist/active",
        "/api/fortigate",
        "/api/collection/status",
        "/api/v2/analytics/summary",
        "/api/v2/analytics/trends",
        "/api/v2/sources/status",
    ]

    results = []
    for endpoint in endpoints:
        try:
            url = f"{PRODUCTION_URL}{endpoint}"
            response = requests.get(url, timeout=5)
            results.append(
                {
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                    "status": "success" if response.status_code == 200 else "failed",
                }
            )
        except Exception as e:
            results.append(
                {
                    "endpoint": endpoint,
                    "status_code": 0,
                    "response_time_ms": 0,
                    "status": "error",
                    "error": str(e),
                }
            )

    # Calculate overall health
    total_endpoints = len(results)
    successful_endpoints = len([r for r in results if r["status"] == "success"])
    health_percentage = (successful_endpoints / total_endpoints) * 100

    return {
        "endpoints": results,
        "summary": {
            "total_endpoints": total_endpoints,
            "successful_endpoints": successful_endpoints,
            "failed_endpoints": total_endpoints - successful_endpoints,
            "health_percentage": health_percentage,
            "overall_status": (
                "healthy"
                if health_percentage >= 90
                else "degraded" if health_percentage >= 50 else "unhealthy"
            ),
        },
        "checked_at": datetime.now().isoformat(),
    }


def run_smoke_tests() -> Dict[str, Any]:
    """Run comprehensive smoke tests"""
    smoke_tests = [
        {
            "test": "Health Endpoint",
            "url": f"{PRODUCTION_URL}/health",
            "expected_status": 200,
            "timeout": 5,
        },
        {
            "test": "API Health Endpoint",
            "url": f"{PRODUCTION_URL}/api/health",
            "expected_status": 200,
            "timeout": 5,
        },
        {
            "test": "Blacklist API",
            "url": f"{PRODUCTION_URL}/api/blacklist/active",
            "expected_status": 200,
            "timeout": 10,
        },
        {
            "test": "FortiGate API",
            "url": f"{PRODUCTION_URL}/api/fortigate",
            "expected_status": 200,
            "timeout": 10,
        },
        {
            "test": "Collection Status",
            "url": f"{PRODUCTION_URL}/api/collection/status",
            "expected_status": 200,
            "timeout": 5,
        },
    ]

    results = []
    for test in smoke_tests:
        try:
            start_time = datetime.now()
            response = requests.get(test["url"], timeout=test["timeout"])
            end_time = datetime.now()

            response_time = (end_time - start_time).total_seconds() * 1000

            results.append(
                {
                    "test": test["test"],
                    "status": (
                        "passed"
                        if response.status_code == test["expected_status"]
                        else "failed"
                    ),
                    "response_code": response.status_code,
                    "expected_code": test["expected_status"],
                    "response_time_ms": response_time,
                    "timestamp": start_time.isoformat(),
                }
            )
        except Exception as e:
            results.append(
                {
                    "test": test["test"],
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            )

    # Calculate summary
    total_tests = len(results)
    passed_tests = len([r for r in results if r["status"] == "passed"])
    failed_tests = len([r for r in results if r["status"] == "failed"])
    error_tests = len([r for r in results if r["status"] == "error"])

    return {
        "smoke_tests": results,
        "summary": {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "error_tests": error_tests,
            "success_rate": (passed_tests / total_tests) * 100,
            "overall_status": ("passed" if passed_tests == total_tests else "failed"),
        },
        "executed_at": datetime.now().isoformat(),
    }


def generate_verification_recommendations(steps: List[Dict[str, Any]]) -> List[str]:
    """Generate recommendations based on verification results"""
    recommendations = []

    for step in steps:
        if step["status"] == "failed":
            if step["step"] == "Basic Health Check":
                recommendations.append(
                    "Check application logs and restart service if needed"
                )
            elif step["step"] == "API Health Check":
                recommendations.append("Verify API endpoints are properly configured")
            elif step["step"] == "Core API Endpoints":
                recommendations.append("Check database connectivity and API routes")
            elif step["step"] == "Performance Test":
                recommendations.append(
                    "Investigate performance issues and optimize response times"
                )
        elif step["status"] == "warning":
            recommendations.append(
                f"Monitor {step['step']} - performance may be degraded"
            )

    if not recommendations:
        recommendations.append("All verification steps passed - system is healthy")

    return recommendations


def determine_overall_status(*statuses: str) -> str:
    """Determine overall system status from individual component statuses"""
    if all(status == "healthy" for status in statuses):
        return "healthy"
    elif any(status == "error" for status in statuses):
        return "unhealthy"
    else:
        return "degraded"


if __name__ == "__main__":
    import sys

    # Test monitoring functionality
    all_validation_failures = []
    total_tests = 0

    # Test 1: Verification recommendations generation
    total_tests += 1
    try:
        test_steps = [
            {"step": "Basic Health Check", "status": "failed"},
            {"step": "API Health Check", "status": "passed"},
        ]
        recommendations = generate_verification_recommendations(test_steps)
        if not recommendations:
            all_validation_failures.append("Recommendations: No recommendations generated")
        if not any("logs" in rec.lower() for rec in recommendations):
            all_validation_failures.append(
                "Recommendations: Missing expected health check recommendation"
            )
    except Exception as e:
        all_validation_failures.append(f"Recommendations: Exception occurred - {e}")

    # Test 2: Overall status determination
    total_tests += 1
    try:
        healthy_status = determine_overall_status("healthy", "healthy", "healthy")
        degraded_status = determine_overall_status("healthy", "degraded", "healthy")
        unhealthy_status = determine_overall_status("healthy", "error", "healthy")

        if healthy_status != "healthy":
            all_validation_failures.append(
                f"Status determination: Expected 'healthy', got '{healthy_status}'"
            )
        if degraded_status != "degraded":
            all_validation_failures.append(
                f"Status determination: Expected 'degraded', got '{degraded_status}'"
            )
        if unhealthy_status != "unhealthy":
            all_validation_failures.append(
                f"Status determination: Expected 'unhealthy', got '{unhealthy_status}'"
            )
    except Exception as e:
        all_validation_failures.append(f"Status determination: Exception occurred - {e}")

    # Final validation result
    if all_validation_failures:
        print(
            f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Monitoring functions module is validated and ready for use")
        sys.exit(0)