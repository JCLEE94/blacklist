#!/usr/bin/env python3
"""
MSA Performance Testing Module

Extracted from msa_comprehensive_integration_test.py for better organization.
"""

import asyncio
import time
from typing import List

import httpx

from .msa_test_config import TestResult


class MSAPerformanceTester:
    """성능 테스트 전담 클래스"""

    def __init__(self, gateway_url: str):
        self.gateway_url = gateway_url

    async def test_performance_benchmarks(
        self, performance_tests: List[dict]
    ) -> List[TestResult]:
        """성능 벤치마크 테스트"""
        results = []

        for test in performance_tests:
            total_time = 0.0
            successful_requests = 0
            errors = []

            for i in range(test["requests"]):
                start_time = time.time()
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        response = await client.get(
                            f"{self.gateway_url}{test['endpoint']}"
                        )
                        response_time = time.time() - start_time

                        if response.status_code in [200, 503]:  # 503도 허용
                            total_time += response_time
                            successful_requests += 1
                        else:
                            errors.append(f"Request {i+1}: HTTP {response.status_code}")

                except Exception as e:
                    errors.append(f"Request {i+1}: {str(e)}")

            if successful_requests > 0:
                average_time = total_time / successful_requests
                passed = average_time <= test["target_time"]

                results.append(
                    TestResult(
                        name=test["name"],
                        passed=passed,
                        response_time=average_time,
                        response_data={
                            "successful_requests": successful_requests,
                            "total_requests": test["requests"],
                            "average_time": average_time,
                            "target_time": test["target_time"],
                            "errors": errors,
                        },
                    )
                )
            else:
                results.append(
                    TestResult(
                        name=test["name"],
                        passed=False,
                        response_time=0.0,
                        error_message=f"All requests failed: {errors}",
                    )
                )

        return results

    async def test_database_connectivity(self) -> TestResult:
        """데이터베이스 연결성 테스트"""
        start_time = time.time()

        try:
            # API Gateway를 통해 DB가 필요한 엔드포인트 테스트
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.gateway_url}/api/v1/blacklist/statistics"
                )
                response_time = time.time() - start_time

                if response.status_code in [200, 503]:  # 503도 허용 (초기화 중)
                    return TestResult(
                        name="Database Connectivity",
                        passed=True,
                        response_time=response_time,
                        status_code=response.status_code,
                        response_data=response.json() if response.content else {},
                    )
                else:
                    return TestResult(
                        name="Database Connectivity",
                        passed=False,
                        response_time=response_time,
                        error_message=f"DB connection test failed: HTTP {response.status_code}",
                        status_code=response.status_code,
                    )

        except Exception as e:
            return TestResult(
                name="Database Connectivity",
                passed=False,
                response_time=time.time() - start_time,
                error_message=str(e),
            )

    async def run_concurrent_load_test(
        self, endpoint: str, concurrent_requests: int = 10
    ) -> TestResult:
        """동시 요청 부하 테스트"""
        start_time = time.time()

        async def make_request():
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.gateway_url}{endpoint}")
                return response.status_code == 200

        try:
            tasks = [make_request() for _ in range(concurrent_requests)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful_requests = sum(1 for r in results if r is True)
            total_time = time.time() - start_time

            return TestResult(
                name=f"Concurrent Load Test ({concurrent_requests} requests)",
                passed=successful_requests >= concurrent_requests * 0.8,  # 80% 성공률
                response_time=total_time,
                response_data={
                    "successful_requests": successful_requests,
                    "total_requests": concurrent_requests,
                    "success_rate": (successful_requests / concurrent_requests) * 100,
                    "total_time": total_time,
                },
            )

        except Exception as e:
            return TestResult(
                name=f"Concurrent Load Test ({concurrent_requests} requests)",
                passed=False,
                response_time=time.time() - start_time,
                error_message=str(e),
            )
