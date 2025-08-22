#!/usr/bin/env python3
"""
배포 후 성능 검증 모듈

이 모듈은 배포된 시스템의 성능을 검증하고 벤치마크합니다.
- API 응답 시간 측정
- 동시 접속 테스트
- 메모리/CPU 사용량 검증
- 부하 테스트 및 성능 임계값 확인

Links:
- Requests documentation: https://docs.python-requests.org/
- Threading documentation: https://docs.python.org/3/library/threading.html
- psutil documentation: https://psutil.readthedocs.io/

Sample input: python3 performance_validation.py --concurrent-users 10 --duration 60
Expected output: Comprehensive performance report with response times, throughput, and resource usage
"""

import argparse
import asyncio
import concurrent.futures
import json
import logging
import statistics
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import psutil
import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PerformanceValidator:
    """Performance validation and benchmarking for deployment"""

    def __init__(self, base_url: str = "http://localhost:32542", timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.timeout = timeout

        # Performance thresholds
        self.thresholds = {
            "excellent_response_ms": 50,
            "good_response_ms": 200,
            "acceptable_response_ms": 1000,
            "poor_response_ms": 5000,
            "max_cpu_percent": 80,
            "max_memory_percent": 85,
            "min_success_rate": 95.0,
            "min_throughput_rps": 10,
        }

        # Test results storage
        self.results = {
            "start_time": None,
            "end_time": None,
            "endpoints": {},
            "load_test": {},
            "resource_usage": {},
            "overall_score": 0,
        }

    def log_test_result(self, test_name: str, status: str, details: str):
        """Log test result with consistent formatting"""
        status_symbols = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}
        symbol = status_symbols.get(status, "ℹ️")
        print(f"   {symbol} {test_name}: {details}")
        logger.info(f"{test_name} [{status}]: {details}")

    def measure_response_time(
        self, endpoint: str, method: str = "GET", data: Dict = None
    ) -> Dict[str, Any]:
        """Measure response time and status for a single request"""
        url = f"{self.base_url}{endpoint}"

        start_time = time.time()
        try:
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data or {})
            else:
                response = self.session.request(method, url, json=data or {})

            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds

            return {
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "success": 200 <= response.status_code < 400,
                "content_length": len(response.content) if response.content else 0,
                "headers": dict(response.headers),
            }
        except requests.RequestException as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000

            return {
                "status_code": 0,
                "response_time_ms": response_time,
                "success": False,
                "error": str(e),
                "content_length": 0,
                "headers": {},
            }

    def test_endpoint_performance(
        self, endpoint: str, description: str, iterations: int = 5
    ) -> Dict[str, Any]:
        """Test performance of a single endpoint"""
        print(f"   Testing {description}...")

        results = []
        for i in range(iterations):
            result = self.measure_response_time(endpoint)
            results.append(result)
            time.sleep(0.1)  # Brief pause between requests

        # Calculate statistics
        response_times = [r["response_time_ms"] for r in results]
        success_count = sum(1 for r in results if r["success"])
        success_rate = (success_count / iterations) * 100

        stats = {
            "endpoint": endpoint,
            "description": description,
            "iterations": iterations,
            "success_rate": success_rate,
            "response_times": {
                "min": min(response_times),
                "max": max(response_times),
                "mean": statistics.mean(response_times),
                "median": statistics.median(response_times),
                "p95": self.calculate_percentile(response_times, 95),
                "p99": self.calculate_percentile(response_times, 99),
            },
            "results": results,
        }

        # Performance assessment
        avg_time = stats["response_times"]["mean"]
        if avg_time <= self.thresholds["excellent_response_ms"]:
            performance_level = "EXCELLENT"
        elif avg_time <= self.thresholds["good_response_ms"]:
            performance_level = "GOOD"
        elif avg_time <= self.thresholds["acceptable_response_ms"]:
            performance_level = "ACCEPTABLE"
        else:
            performance_level = "POOR"

        stats["performance_level"] = performance_level

        # Log result
        self.log_test_result(
            f"Endpoint-{endpoint}",
            "PASS" if success_rate >= self.thresholds["min_success_rate"] else "FAIL",
            f"{description} - Avg: {avg_time:.1f}ms, Success: {success_rate:.1f}%, Level: {performance_level}",
        )

        return stats

    def concurrent_load_test(
        self, endpoint: str, concurrent_users: int, duration_seconds: int
    ) -> Dict[str, Any]:
        """Perform concurrent load test"""
        print(
            f"   Running concurrent load test - {concurrent_users} users for {duration_seconds}s..."
        )

        results = []
        start_time = time.time()
        end_time = start_time + duration_seconds

        def make_request():
            """Single request function for threading"""
            while time.time() < end_time:
                result = self.measure_response_time(endpoint)
                result["timestamp"] = time.time()
                results.append(result)
                time.sleep(0.1)  # Brief pause

        # Run concurrent requests
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=concurrent_users
        ) as executor:
            futures = [executor.submit(make_request) for _ in range(concurrent_users)]
            concurrent.futures.wait(futures, timeout=duration_seconds + 10)

        actual_duration = time.time() - start_time

        if not results:
            return {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "success_rate": 0.0,
                "throughput_rps": 0.0,
                "avg_response_time": 0.0,
                "error": "No requests completed",
            }

        # Calculate load test statistics
        successful_requests = sum(1 for r in results if r["success"])
        failed_requests = len(results) - successful_requests
        success_rate = (successful_requests / len(results)) * 100
        throughput_rps = len(results) / actual_duration

        response_times = [r["response_time_ms"] for r in results if r["success"]]
        avg_response_time = statistics.mean(response_times) if response_times else 0

        load_stats = {
            "concurrent_users": concurrent_users,
            "duration_seconds": duration_seconds,
            "actual_duration": actual_duration,
            "total_requests": len(results),
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": success_rate,
            "throughput_rps": throughput_rps,
            "avg_response_time": avg_response_time,
            # Store sample for analysis
            "response_times": response_times[:100],
        }

        # Performance assessment
        throughput_ok = throughput_rps >= self.thresholds["min_throughput_rps"]
        success_rate_ok = success_rate >= self.thresholds["min_success_rate"]

        status = "PASS" if throughput_ok and success_rate_ok else "FAIL"
        self.log_test_result(
            "Load-Test",
            status,
            f"RPS: {throughput_rps:.1f}, Success: {success_rate:.1f}%, Avg: {avg_response_time:.1f}ms",
        )

        return load_stats

    def monitor_resource_usage(self, duration_seconds: int = 60) -> Dict[str, Any]:
        """Monitor system resource usage during testing"""
        print(f"   Monitoring resource usage for {duration_seconds}s...")

        samples = []
        start_time = time.time()

        while time.time() - start_time < duration_seconds:
            try:
                sample = {
                    "timestamp": time.time(),
                    "cpu_percent": psutil.cpu_percent(interval=1),
                    "memory": psutil.virtual_memory()._asdict(),
                    "disk": (
                        psutil.disk_usage("/")._asdict()
                        if hasattr(psutil, "disk_usage")
                        else {}
                    ),
                    "network": (
                        psutil.net_io_counters()._asdict()
                        if hasattr(psutil, "net_io_counters")
                        else {}
                    ),
                }
                samples.append(sample)
            except Exception as e:
                logger.warning(f"Failed to collect resource sample: {e}")
                continue

        if not samples:
            return {"error": "No resource samples collected"}

        # Calculate resource statistics
        cpu_values = [s["cpu_percent"] for s in samples if "cpu_percent" in s]
        memory_values = [
            s["memory"]["percent"]
            for s in samples
            if "memory" in s and "percent" in s["memory"]
        ]

        resource_stats = {
            "duration": duration_seconds,
            "samples_count": len(samples),
            "cpu": {
                "avg": statistics.mean(cpu_values) if cpu_values else 0,
                "max": max(cpu_values) if cpu_values else 0,
                "min": min(cpu_values) if cpu_values else 0,
            },
            "memory": {
                "avg": statistics.mean(memory_values) if memory_values else 0,
                "max": max(memory_values) if memory_values else 0,
                "min": min(memory_values) if memory_values else 0,
            },
            "samples": samples[-10:],  # Store last 10 samples
        }

        # Resource usage assessment
        cpu_ok = resource_stats["cpu"]["max"] <= self.thresholds["max_cpu_percent"]
        memory_ok = (
            resource_stats["memory"]["max"] <= self.thresholds["max_memory_percent"]
        )

        status = "PASS" if cpu_ok and memory_ok else "WARN"
        self.log_test_result(
            "Resource-Usage",
            status,
            f"CPU: {resource_stats['cpu']['avg']:.1f}% avg, {resource_stats['cpu']['max']:.1f}% max | "
            f"Memory: {resource_stats['memory']['avg']:.1f}% avg, {resource_stats['memory']['max']:.1f}% max",
        )

        return resource_stats

    def validate_deployment_performance(
        self, concurrent_users: int = 5, test_duration: int = 30
    ) -> Dict[str, Any]:
        """Run comprehensive performance validation"""
        print("🚀 Starting Performance Validation")
        print("==================================")

        self.results["start_time"] = datetime.utcnow().isoformat()

        # Define test endpoints
        endpoints = [
            ("/health", "Basic health check"),
            ("/api/health", "Detailed health check"),
            ("/api/blacklist/active", "Active blacklist"),
            ("/api/fortigate", "FortiGate format"),
            ("/api/collection/status", "Collection status"),
            ("/build-info", "Build information"),
        ]

        # Test 1: Individual endpoint performance
        print("1. Individual Endpoint Performance")
        for endpoint, description in endpoints:
            stats = self.test_endpoint_performance(endpoint, description)
            self.results["endpoints"][endpoint] = stats

        # Test 2: Concurrent load test
        print("\n2. Concurrent Load Test")
        load_stats = self.concurrent_load_test(
            "/health", concurrent_users, test_duration
        )
        self.results["load_test"] = load_stats

        # Test 3: Resource monitoring
        print("\n3. Resource Usage Monitoring")
        resource_stats = self.monitor_resource_usage(test_duration)
        self.results["resource_usage"] = resource_stats

        self.results["end_time"] = datetime.utcnow().isoformat()

        # Calculate overall performance score
        self.calculate_performance_score()

        return self.results

    def calculate_performance_score(self) -> float:
        """Calculate overall performance score (0-100)"""
        scores = []

        # Endpoint performance score
        endpoint_scores = []
        for endpoint_data in self.results["endpoints"].values():
            avg_time = endpoint_data["response_times"]["mean"]
            success_rate = endpoint_data["success_rate"]

            # Time score (0-40 points)
            if avg_time <= self.thresholds["excellent_response_ms"]:
                time_score = 40
            elif avg_time <= self.thresholds["good_response_ms"]:
                time_score = 30
            elif avg_time <= self.thresholds["acceptable_response_ms"]:
                time_score = 20
            else:
                time_score = 10

            # Success rate score (0-10 points)
            success_score = (success_rate / 100) * 10

            endpoint_scores.append(time_score + success_score)

        if endpoint_scores:
            scores.append(statistics.mean(endpoint_scores))

        # Load test score
        if "success_rate" in self.results["load_test"]:
            load_success = self.results["load_test"]["success_rate"]
            load_throughput = self.results["load_test"]["throughput_rps"]

            success_score = (load_success / 100) * 25  # 0-25 points
            throughput_score = (
                min(load_throughput / self.thresholds["min_throughput_rps"], 2) * 12.5
            )  # 0-25 points

            scores.append(success_score + throughput_score)

        # Resource usage score
        if "cpu" in self.results["resource_usage"]:
            cpu_usage = self.results["resource_usage"]["cpu"]["max"]
            memory_usage = self.results["resource_usage"]["memory"]["max"]

            cpu_score = max(
                0, 15 - (cpu_usage / self.thresholds["max_cpu_percent"]) * 15
            )  # 0-15 points
            memory_score = max(
                0, 10 - (memory_usage / self.thresholds["max_memory_percent"]) * 10
            )  # 0-10 points

            scores.append(cpu_score + memory_score)

        overall_score = statistics.mean(scores) if scores else 0
        self.results["overall_score"] = round(overall_score, 1)

        return overall_score

    def generate_performance_report(self, output_file: str = None) -> str:
        """Generate comprehensive performance report"""
        report_lines = []

        report_lines.extend(
            [
                "PERFORMANCE VALIDATION REPORT",
                "============================",
                f"",
                f"Test Period: {self.results['start_time']} - {self.results['end_time']}",
                f"Overall Performance Score: {self.results['overall_score']}/100",
                f"",
            ]
        )

        # Performance level assessment
        score = self.results["overall_score"]
        if score >= 90:
            level = "EXCELLENT"
        elif score >= 75:
            level = "GOOD"
        elif score >= 60:
            level = "ACCEPTABLE"
        else:
            level = "NEEDS IMPROVEMENT"

        report_lines.append(f"Performance Level: {level}")
        report_lines.append("")

        # Endpoint performance summary
        report_lines.extend(
            ["ENDPOINT PERFORMANCE SUMMARY", "============================="]
        )

        for endpoint, data in self.results["endpoints"].items():
            avg_time = data["response_times"]["mean"]
            success_rate = data["success_rate"]
            p95_time = data["response_times"]["p95"]

            report_lines.extend(
                [
                    f"",
                    f"Endpoint: {endpoint}",
                    f"  Description: {data['description']}",
                    f"  Average Response Time: {avg_time:.1f}ms",
                    f"  95th Percentile: {p95_time:.1f}ms",
                    f"  Success Rate: {success_rate:.1f}%",
                    f"  Performance Level: {data['performance_level']}",
                ]
            )

        # Load test summary
        if self.results["load_test"]:
            load_data = self.results["load_test"]
            report_lines.extend(
                [
                    f"",
                    f"LOAD TEST SUMMARY",
                    f"================",
                    f"Concurrent Users: {load_data.get('concurrent_users', 'N/A')}",
                    f"Test Duration: {load_data.get('duration_seconds', 'N/A')}s",
                    f"Total Requests: {load_data.get('total_requests', 0)}",
                    f"Successful Requests: {load_data.get('successful_requests', 0)}",
                    f"Success Rate: {load_data.get('success_rate', 0):.1f}%",
                    f"Throughput: {load_data.get('throughput_rps', 0):.1f} req/sec",
                    f"Average Response Time: {load_data.get('avg_response_time', 0):.1f}ms",
                ]
            )

        # Resource usage summary
        if self.results["resource_usage"]:
            resource_data = self.results["resource_usage"]
            if "cpu" in resource_data:
                report_lines.extend(
                    [
                        f"",
                        f"RESOURCE USAGE SUMMARY",
                        f"=====================",
                        f"CPU Usage - Avg: {resource_data['cpu']['avg']:.1f}%, Max: {resource_data['cpu']['max']:.1f}%",
                        f"Memory Usage - Avg: {resource_data['memory']['avg']:.1f}%, Max: {resource_data['memory']['max']:.1f}%",
                    ]
                )

        # Performance thresholds
        report_lines.extend(
            [
                f"",
                f"PERFORMANCE THRESHOLDS",
                f"=====================",
                f"Excellent Response Time: ≤ {self.thresholds['excellent_response_ms']}ms",
                f"Good Response Time: ≤ {self.thresholds['good_response_ms']}ms",
                f"Acceptable Response Time: ≤ {self.thresholds['acceptable_response_ms']}ms",
                f"Minimum Success Rate: ≥ {self.thresholds['min_success_rate']}%",
                f"Minimum Throughput: ≥ {self.thresholds['min_throughput_rps']} req/sec",
                f"Maximum CPU Usage: ≤ {self.thresholds['max_cpu_percent']}%",
                f"Maximum Memory Usage: ≤ {self.thresholds['max_memory_percent']}%",
            ]
        )

        report_content = "\n".join(report_lines)

        if output_file:
            with open(output_file, "w") as f:
                f.write(report_content)
            print(f"\n📊 Performance report saved to: {output_file}")

        return report_content

    @staticmethod
    def calculate_percentile(values: List[float], percentile: float) -> float:
        """Calculate percentile value"""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)

        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower_index = int(index)
            upper_index = lower_index + 1
            weight = index - lower_index

            if upper_index >= len(sorted_values):
                return sorted_values[-1]

            return (
                sorted_values[lower_index] * (1 - weight)
                + sorted_values[upper_index] * weight
            )


def main():
    """Main function with CLI support"""
    parser = argparse.ArgumentParser(
        description="Performance validation for blacklist deployment"
    )
    parser.add_argument(
        "--base-url", default="http://localhost:32542", help="Base URL for testing"
    )
    parser.add_argument(
        "--concurrent-users",
        type=int,
        default=5,
        help="Number of concurrent users for load test",
    )
    parser.add_argument(
        "--duration", type=int, default=30, help="Test duration in seconds"
    )
    parser.add_argument("--output", help="Output file for performance report")
    parser.add_argument(
        "--timeout", type=int, default=30, help="Request timeout in seconds"
    )

    args = parser.parse_args()

    # Create validator instance
    validator = PerformanceValidator(base_url=args.base_url, timeout=args.timeout)

    try:
        # Run validation
        results = validator.validate_deployment_performance(
            concurrent_users=args.concurrent_users, test_duration=args.duration
        )

        # Generate report
        output_file = args.output or f"performance_report_{int(time.time())}.txt"
        report = validator.generate_performance_report(output_file)

        # Print summary
        print(f"\n📊 PERFORMANCE VALIDATION COMPLETE")
        print(f"Overall Score: {results['overall_score']}/100")
        print(f"Report saved: {output_file}")

        # Exit with appropriate code
        if results["overall_score"] >= 60:
            print("✅ Performance validation PASSED")
            return 0
        else:
            print("❌ Performance validation FAILED")
            return 1

    except Exception as e:
        logger.error(f"Performance validation failed: {e}")
        return 1


if __name__ == "__main__":
    # Validation tests
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: PerformanceValidator instantiation
    total_tests += 1
    try:
        validator = PerformanceValidator()
        if hasattr(validator, "base_url") and hasattr(validator, "thresholds"):
            print("✅ PerformanceValidator instantiation working")
        else:
            all_validation_failures.append(
                "PerformanceValidator missing required attributes"
            )
    except Exception as e:
        all_validation_failures.append(
            f"PerformanceValidator instantiation failed: {e}"
        )

    # Test 2: Response time measurement function
    total_tests += 1
    try:
        validator = PerformanceValidator()
        # Mock test - should handle connection error gracefully
        result = validator.measure_response_time("/nonexistent", "GET")
        if (
            isinstance(result, dict)
            and "response_time_ms" in result
            and "success" in result
        ):
            print("✅ Response time measurement function working")
        else:
            all_validation_failures.append(
                f"Response time measurement returned invalid format: {type(result)}"
            )
    except Exception as e:
        all_validation_failures.append(
            f"Response time measurement function failed: {e}"
        )

    # Test 3: Performance score calculation
    total_tests += 1
    try:
        validator = PerformanceValidator()
        validator.results = {
            "endpoints": {
                "/test": {"response_times": {"mean": 100}, "success_rate": 95}
            },
            "load_test": {"success_rate": 90, "throughput_rps": 15},
            "resource_usage": {"cpu": {"max": 50}, "memory": {"max": 60}},
        }
        score = validator.calculate_performance_score()
        if isinstance(score, (int, float)) and 0 <= score <= 100:
            print("✅ Performance score calculation working")
        else:
            all_validation_failures.append(
                f"Performance score calculation returned invalid value: {score}"
            )
    except Exception as e:
        all_validation_failures.append(f"Performance score calculation failed: {e}")

    # Test 4: Report generation
    total_tests += 1
    try:
        validator = PerformanceValidator()
        validator.results = {
            "start_time": "2023-01-01T00:00:00Z",
            "end_time": "2023-01-01T00:01:00Z",
            "overall_score": 85,
            "endpoints": {},
            "load_test": {},
            "resource_usage": {},
        }
        report = validator.generate_performance_report()
        if isinstance(report, str) and "PERFORMANCE VALIDATION REPORT" in report:
            print("✅ Report generation working")
        else:
            all_validation_failures.append("Report generation returned invalid format")
    except Exception as e:
        all_validation_failures.append(f"Report generation failed: {e}")

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
        print(
            "Performance validation module is validated and ready for deployment testing"
        )

        # If not being imported, run main
        if len(sys.argv) > 1:
            sys.exit(main())
        else:
            sys.exit(0)
