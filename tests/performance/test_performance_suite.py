"""
Performance test suite for Blacklist Management System
Comprehensive performance benchmarking and load testing
"""

import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

import pytest
import requests


class PerformanceTester:
    """Performance testing utilities"""

    def __init__(self, base_url: str = "http://localhost:8541"):
        self.base_url = base_url
        self.results = []

    def time_function(self, func, *args, **kwargs) -> Dict[str, Any]:
        """Time a function execution"""
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)

        end_time = time.time()
        duration = end_time - start_time

        return {
            "duration": duration,
            "success": success,
            "result": result,
            "error": error,
        }

    def load_test_endpoint(
        self, endpoint: str, concurrent_requests: int = 10, total_requests: int = 100
    ) -> Dict[str, Any]:
        """Load test an endpoint"""

        def make_request():
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                return {
                    "status_code": response.status_code,
                    "duration": response.elapsed.total_seconds(),
                    "success": response.status_code < 400,
                }
            except Exception as e:
                return {
                    "status_code": 0,
                    "duration": 0,
                    "success": False,
                    "error": str(e),
                }

        results = []
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [executor.submit(make_request) for _ in range(total_requests)]

            for future in as_completed(futures):
                results.append(future.result())

        end_time = time.time()
        total_duration = end_time - start_time

        # Calculate statistics
        successful_requests = [r for r in results if r["success"]]
        durations = [r["duration"] for r in successful_requests]

        return {
            "endpoint": endpoint,
            "total_requests": total_requests,
            "successful_requests": len(successful_requests),
            "failed_requests": total_requests - len(successful_requests),
            "success_rate": len(successful_requests) / total_requests * 100,
            "total_duration": total_duration,
            "requests_per_second": total_requests / total_duration,
            "avg_response_time": statistics.mean(durations) if durations else 0,
            "min_response_time": min(durations) if durations else 0,
            "max_response_time": max(durations) if durations else 0,
            "median_response_time": statistics.median(durations) if durations else 0,
            "p95_response_time": self._percentile(durations, 95) if durations else 0,
            "p99_response_time": self._percentile(durations, 99) if durations else 0,
        }

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


@pytest.fixture
def performance_tester():
    """Performance tester fixture"""
    return PerformanceTester()


@pytest.mark.performance
class TestAPIPerformance:
    """API endpoint performance tests"""

    def test_health_endpoint_performance(self, performance_tester):
        """Test health endpoint performance"""
        result = performance_tester.load_test_endpoint(
            "/health", concurrent_requests=5, total_requests=50
        )

        # Performance assertions
        assert (
            result["success_rate"] >= 99.0
        ), f"Health endpoint success rate too low: {result['success_rate']}%"
        assert (
            result["avg_response_time"] < 0.1
        ), f"Health endpoint too slow: {result['avg_response_time']}s"
        assert (
            result["p95_response_time"] < 0.2
        ), f"Health endpoint P95 too slow: {result['p95_response_time']}s"

        print(f"\n🚀 Health Endpoint Performance:")
        print(f"   Success Rate: {result['success_rate']:.1f}%")
        print(f"   Avg Response Time: {result['avg_response_time']:.3f}s")
        print(f"   P95 Response Time: {result['p95_response_time']:.3f}s")
        print(f"   Requests/Second: {result['requests_per_second']:.1f}")

    def test_blacklist_api_performance(self, performance_tester):
        """Test blacklist API performance"""
        result = performance_tester.load_test_endpoint(
            "/api/blacklist/active", concurrent_requests=10, total_requests=100
        )

        # Performance assertions
        assert (
            result["success_rate"] >= 95.0
        ), f"Blacklist API success rate too low: {result['success_rate']}%"
        assert (
            result["avg_response_time"] < 0.5
        ), f"Blacklist API too slow: {result['avg_response_time']}s"
        assert (
            result["p99_response_time"] < 2.0
        ), f"Blacklist API P99 too slow: {result['p99_response_time']}s"

        print(f"\n📋 Blacklist API Performance:")
        print(f"   Success Rate: {result['success_rate']:.1f}%")
        print(f"   Avg Response Time: {result['avg_response_time']:.3f}s")
        print(f"   P99 Response Time: {result['p99_response_time']:.3f}s")
        print(f"   Requests/Second: {result['requests_per_second']:.1f}")

    def test_collection_status_performance(self, performance_tester):
        """Test collection status API performance"""
        result = performance_tester.load_test_endpoint(
            "/api/collection/status", concurrent_requests=5, total_requests=50
        )

        # Performance assertions
        assert (
            result["success_rate"] >= 90.0
        ), f"Collection status success rate too low: {result['success_rate']}%"
        assert (
            result["avg_response_time"] < 1.0
        ), f"Collection status too slow: {result['avg_response_time']}s"

        print(f"\n📊 Collection Status Performance:")
        print(f"   Success Rate: {result['success_rate']:.1f}%")
        print(f"   Avg Response Time: {result['avg_response_time']:.3f}s")
        print(f"   P95 Response Time: {result['p95_response_time']:.3f}s")
        print(f"   Requests/Second: {result['requests_per_second']:.1f}")


@pytest.mark.performance
class TestDatabasePerformance:
    """Database operation performance tests"""

    def test_ip_lookup_performance(self, performance_tester, enhanced_mock_container):
        """Test IP lookup performance"""
        # Create simple test data inline
        sample_ips = [
            "192.168.1.100",
            "192.168.1.101",
            "192.168.1.102",
            "10.0.0.100",
            "10.0.0.101",
            "172.16.1.100",
            "203.0.113.100",
            "198.51.100.100",
        ]

        blacklist_manager = enhanced_mock_container.get("blacklist_manager")

        def lookup_ip(ip):
            return blacklist_manager.get_active_ips()

        # Time multiple lookups
        durations = []
        for ip in sample_ips[:10]:  # Test first 10 IPs
            result = performance_tester.time_function(lookup_ip, ip)
            durations.append(result["duration"])

        avg_duration = statistics.mean(durations)
        max_duration = max(durations)

        # Performance assertions
        assert avg_duration < 0.01, f"IP lookup too slow: {avg_duration:.3f}s average"
        assert max_duration < 0.05, f"IP lookup max too slow: {max_duration:.3f}s"

        print(f"\n🔍 IP Lookup Performance:")
        print(f"   Average Duration: {avg_duration:.3f}s")
        print(f"   Max Duration: {max_duration:.3f}s")
        print(f"   Lookups/Second: {1/avg_duration:.1f}")

    def test_bulk_ip_operations(self, performance_tester, enhanced_mock_container):
        """Test bulk IP operations performance"""
        blacklist_manager = enhanced_mock_container.get("blacklist_manager")

        # Generate test IPs
        test_ips = [f"192.168.{i//255}.{i%255}" for i in range(1000)]

        def bulk_add_ips(ips):
            for ip in ips:
                blacklist_manager.add_ip(ip, source="PERFORMANCE_TEST")

        # Time bulk operation
        result = performance_tester.time_function(bulk_add_ips, test_ips)

        # Performance assertions
        assert result["success"], f"Bulk IP operation failed: {result['error']}"
        assert (
            result["duration"] < 10.0
        ), f"Bulk operation too slow: {result['duration']:.1f}s"

        ips_per_second = len(test_ips) / result["duration"]

        print(f"\n💾 Bulk IP Operations Performance:")
        print(f"   Total IPs: {len(test_ips)}")
        print(f"   Duration: {result['duration']:.1f}s")
        print(f"   IPs/Second: {ips_per_second:.1f}")


@pytest.mark.performance
class TestCachePerformance:
    """Cache performance tests"""

    def test_cache_operations_performance(
        self, performance_tester, enhanced_mock_container
    ):
        """Test cache operations performance"""
        cache = enhanced_mock_container.get("cache_manager")

        # Test data
        test_keys = [f"test_key_{i}" for i in range(1000)]
        test_values = [f"test_value_{i}" for i in range(1000)]

        def cache_set_operations():
            for key, value in zip(test_keys, test_values):
                cache.set(key, value, ttl=300)

        def cache_get_operations():
            for key in test_keys:
                cache.get(key)

        # Time set operations
        set_result = performance_tester.time_function(cache_set_operations)

        # Time get operations
        get_result = performance_tester.time_function(cache_get_operations)

        # Performance assertions
        assert set_result[
            "success"
        ], f"Cache set operations failed: {set_result['error']}"
        assert get_result[
            "success"
        ], f"Cache get operations failed: {get_result['error']}"

        set_ops_per_second = len(test_keys) / set_result["duration"]
        get_ops_per_second = len(test_keys) / get_result["duration"]

        print(f"\n🗄️  Cache Performance:")
        print(
            f"   Set Operations: {len(test_keys)} in {set_result['duration']:.1f}s ({set_ops_per_second:.0f} ops/sec)"
        )
        print(
            f"   Get Operations: {len(test_keys)} in {get_result['duration']:.1f}s ({get_ops_per_second:.0f} ops/sec)"
        )


@pytest.mark.performance
@pytest.mark.slow
def test_comprehensive_performance_benchmark(performance_tester):
    """Comprehensive performance benchmark"""
    print(f"\n🏁 종합 성능 벤치마크 시작...")

    endpoints_to_test = [
        ("/health", 5, 25),
        ("/api/blacklist/active", 10, 50),
        ("/api/collection/status", 5, 25),
        ("/api/fortigate", 10, 50),
    ]

    results = []
    for endpoint, concurrent, total in endpoints_to_test:
        print(f"\n테스트 중: {endpoint}")
        result = performance_tester.load_test_endpoint(endpoint, concurrent, total)
        results.append(result)

        print(f"  ✅ 성공률: {result['success_rate']:.1f}%")
        print(f"  ⚡ 평균 응답시간: {result['avg_response_time']:.3f}s")
        print(f"  📈 RPS: {result['requests_per_second']:.1f}")

    # Overall performance summary
    overall_success_rate = sum(r["success_rate"] for r in results) / len(results)
    overall_avg_response = sum(r["avg_response_time"] for r in results) / len(results)
    overall_rps = sum(r["requests_per_second"] for r in results)

    print(f"\n🎯 전체 성능 요약:")
    print(f"   평균 성공률: {overall_success_rate:.1f}%")
    print(f"   평균 응답시간: {overall_avg_response:.3f}s")
    print(f"   총 RPS: {overall_rps:.1f}")

    # Performance assertions
    assert (
        overall_success_rate >= 90.0
    ), f"Overall success rate too low: {overall_success_rate:.1f}%"
    assert (
        overall_avg_response < 1.0
    ), f"Overall response time too slow: {overall_avg_response:.3f}s"

    print(f"\n✅ 성능 벤치마크 완료!")
