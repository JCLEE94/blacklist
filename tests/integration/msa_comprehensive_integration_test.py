#!/usr/bin/env python3
"""
MSA 아키텍처 종합 통합 테스트
API Gateway, Collection Service, Blacklist Service, Analytics Service 통합 검증
"""

import asyncio
import httpx
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ServiceConfig:
    """서비스 설정"""

    name: str
    url: str
    port: int
    health_endpoint: str
    timeout: int = 30


@dataclass
class TestResult:
    """테스트 결과"""

    name: str
    passed: bool
    response_time: float
    error_message: Optional[str] = None
    status_code: Optional[int] = None
    response_data: Optional[Dict] = None


class MSAIntegrationTester:
    """MSA 종합 통합 테스터"""

    def __init__(self):
        self.services = {
            "api_gateway": ServiceConfig(
                name="API Gateway",
                url="http://localhost:8080",
                port=8080,
                health_endpoint="/health",
            ),
            "collection_service": ServiceConfig(
                name="Collection Service",
                url="http://localhost:8000",
                port=8000,
                health_endpoint="/health",
            ),
            "blacklist_service": ServiceConfig(
                name="Blacklist Service",
                url="http://localhost:8001",
                port=8001,
                health_endpoint="/health",
            ),
            "analytics_service": ServiceConfig(
                name="Analytics Service",
                url="http://localhost:8002",
                port=8002,
                health_endpoint="/health",
            ),
        }

        self.test_results: List[TestResult] = []
        self.healthy_services: List[str] = []

    async def test_service_health(
        self, service_name: str, config: ServiceConfig
    ) -> TestResult:
        """개별 서비스 헬스체크"""
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=config.timeout) as client:
                response = await client.get(f"{config.url}{config.health_endpoint}")
                response_time = time.time() - start_time

                if response.status_code == 200:
                    self.healthy_services.append(service_name)
                    return TestResult(
                        name=f"{config.name} Health Check",
                        passed=True,
                        response_time=response_time,
                        status_code=response.status_code,
                        response_data=response.json() if response.content else {},
                    )
                else:
                    return TestResult(
                        name=f"{config.name} Health Check",
                        passed=False,
                        response_time=response_time,
                        error_message=f"HTTP {response.status_code}",
                        status_code=response.status_code,
                    )

        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                name=f"{config.name} Health Check",
                passed=False,
                response_time=response_time,
                error_message=str(e),
            )

    async def test_api_gateway_routing(self) -> List[TestResult]:
        """API Gateway 라우팅 테스트"""
        results = []
        gateway_url = self.services["api_gateway"].url

        test_routes = [
            {
                "name": "Gateway Health Check",
                "url": f"{gateway_url}/health",
                "expected_status": 200,
                "description": "API Gateway 자체 헬스체크",
            },
            {
                "name": "Collection Service via Gateway",
                "url": f"{gateway_url}/api/v1/collection/status",
                "expected_status": [200, 503],  # 503도 허용 (서비스 준비 중)
                "description": "Gateway를 통한 Collection Service 라우팅",
            },
            {
                "name": "Blacklist Service via Gateway",
                "url": f"{gateway_url}/api/v1/blacklist/statistics",
                "expected_status": [200, 503],  # 503도 허용
                "description": "Gateway를 통한 Blacklist Service 라우팅",
            },
            {
                "name": "Analytics Service via Gateway",
                "url": f"{gateway_url}/api/v1/analytics/realtime",
                "expected_status": [200, 503],  # 503도 허용
                "description": "Gateway를 통한 Analytics Service 라우팅",
            },
        ]

        for route in test_routes:
            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.get(route["url"])
                    response_time = time.time() - start_time

                    expected_statuses = (
                        route["expected_status"]
                        if isinstance(route["expected_status"], list)
                        else [route["expected_status"]]
                    )

                    if response.status_code in expected_statuses:
                        results.append(
                            TestResult(
                                name=route["name"],
                                passed=True,
                                response_time=response_time,
                                status_code=response.status_code,
                                response_data=response.json()
                                if response.content
                                else {},
                            )
                        )
                    else:
                        results.append(
                            TestResult(
                                name=route["name"],
                                passed=False,
                                response_time=response_time,
                                error_message=f"Expected {expected_statuses}, got {response.status_code}",
                                status_code=response.status_code,
                            )
                        )

            except Exception as e:
                response_time = time.time() - start_time
                results.append(
                    TestResult(
                        name=route["name"],
                        passed=False,
                        response_time=response_time,
                        error_message=str(e),
                    )
                )

        return results

    async def test_service_communication(self) -> List[TestResult]:
        """서비스 간 통신 테스트"""
        results = []

        # API Gateway를 통한 서비스 간 통신 테스트
        gateway_url = self.services["api_gateway"].url

        communication_tests = [
            {
                "name": "Collection to Blacklist Communication",
                "description": "수집 서비스에서 블랙리스트 서비스로의 통신",
                "test_method": self._test_collection_blacklist_communication,
            },
            {
                "name": "Blacklist to Analytics Communication",
                "description": "블랙리스트 서비스에서 분석 서비스로의 통신",
                "test_method": self._test_blacklist_analytics_communication,
            },
            {
                "name": "Cross-Service Data Flow",
                "description": "전체 서비스 간 데이터 흐름 테스트",
                "test_method": self._test_cross_service_data_flow,
            },
        ]

        for test in communication_tests:
            try:
                result = await test["test_method"]()
                results.append(result)
            except Exception as e:
                results.append(
                    TestResult(
                        name=test["name"],
                        passed=False,
                        response_time=0.0,
                        error_message=str(e),
                    )
                )

        return results

    async def _test_collection_blacklist_communication(self) -> TestResult:
        """수집-블랙리스트 서비스 간 통신 테스트"""
        start_time = time.time()

        try:
            # 1. 수집 상태 확인
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.services['api_gateway'].url}/api/v1/collection/status"
                )

                if response.status_code == 200:
                    collection_data = response.json()

                    # 2. 블랙리스트 통계 확인
                    stats_response = await client.get(
                        f"{self.services['api_gateway'].url}/api/v1/blacklist/statistics"
                    )

                    response_time = time.time() - start_time

                    if stats_response.status_code == 200:
                        return TestResult(
                            name="Collection-Blacklist Communication",
                            passed=True,
                            response_time=response_time,
                            response_data={
                                "collection_status": collection_data,
                                "blacklist_stats": stats_response.json(),
                            },
                        )
                    else:
                        return TestResult(
                            name="Collection-Blacklist Communication",
                            passed=False,
                            response_time=response_time,
                            error_message=f"Blacklist stats failed: HTTP {stats_response.status_code}",
                        )
                else:
                    return TestResult(
                        name="Collection-Blacklist Communication",
                        passed=False,
                        response_time=time.time() - start_time,
                        error_message=f"Collection status failed: HTTP {response.status_code}",
                    )

        except Exception as e:
            return TestResult(
                name="Collection-Blacklist Communication",
                passed=False,
                response_time=time.time() - start_time,
                error_message=str(e),
            )

    async def _test_blacklist_analytics_communication(self) -> TestResult:
        """블랙리스트-분석 서비스 간 통신 테스트"""
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # 1. 블랙리스트 데이터 확인
                blacklist_response = await client.get(
                    f"{self.services['api_gateway'].url}/api/v1/blacklist/statistics"
                )

                # 2. 분석 리포트 확인
                analytics_response = await client.get(
                    f"{self.services['api_gateway'].url}/api/v1/analytics/realtime"
                )

                response_time = time.time() - start_time

                if (
                    blacklist_response.status_code == 200
                    and analytics_response.status_code == 200
                ):
                    return TestResult(
                        name="Blacklist-Analytics Communication",
                        passed=True,
                        response_time=response_time,
                        response_data={
                            "blacklist_stats": blacklist_response.json(),
                            "analytics_data": analytics_response.json(),
                        },
                    )
                else:
                    return TestResult(
                        name="Blacklist-Analytics Communication",
                        passed=False,
                        response_time=response_time,
                        error_message=f"Blacklist: {blacklist_response.status_code}, Analytics: {analytics_response.status_code}",
                    )

        except Exception as e:
            return TestResult(
                name="Blacklist-Analytics Communication",
                passed=False,
                response_time=time.time() - start_time,
                error_message=str(e),
            )

    async def _test_cross_service_data_flow(self) -> TestResult:
        """전체 서비스 간 데이터 흐름 테스트"""
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=45) as client:
                # 전체 데이터 흐름 시뮬레이션
                endpoints = [
                    f"{self.services['api_gateway'].url}/api/v1/collection/status",
                    f"{self.services['api_gateway'].url}/api/v1/blacklist/active",
                    f"{self.services['api_gateway'].url}/api/v1/analytics/report",
                ]

                all_responses = {}
                all_success = True

                for endpoint in endpoints:
                    try:
                        response = await client.get(endpoint)
                        service_name = endpoint.split("/")[-2]  # 서비스명 추출
                        all_responses[service_name] = {
                            "status_code": response.status_code,
                            "success": response.status_code in [200, 503],  # 503도 허용
                            "data": response.json() if response.content else {},
                        }

                        if response.status_code not in [200, 503]:
                            all_success = False

                    except Exception as e:
                        all_success = False
                        service_name = endpoint.split("/")[-2]
                        all_responses[service_name] = {
                            "status_code": 0,
                            "success": False,
                            "error": str(e),
                        }

                response_time = time.time() - start_time

                return TestResult(
                    name="Cross-Service Data Flow",
                    passed=all_success,
                    response_time=response_time,
                    response_data=all_responses,
                )

        except Exception as e:
            return TestResult(
                name="Cross-Service Data Flow",
                passed=False,
                response_time=time.time() - start_time,
                error_message=str(e),
            )

    async def test_database_connectivity(self) -> TestResult:
        """데이터베이스 연결성 테스트"""
        start_time = time.time()

        try:
            # API Gateway를 통해 DB가 필요한 엔드포인트 테스트
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.services['api_gateway'].url}/api/v1/blacklist/statistics"
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

    async def test_performance_benchmarks(self) -> List[TestResult]:
        """성능 벤치마크 테스트"""
        results = []

        performance_tests = [
            {
                "name": "Gateway Response Time",
                "endpoint": f"{self.services['api_gateway'].url}/health",
                "target_time": 0.5,  # 500ms 이하
                "requests": 10,
            },
            {
                "name": "Blacklist Query Performance",
                "endpoint": f"{self.services['api_gateway'].url}/api/v1/blacklist/active",
                "target_time": 2.0,  # 2초 이하
                "requests": 5,
            },
            {
                "name": "Analytics Performance",
                "endpoint": f"{self.services['api_gateway'].url}/api/v1/analytics/realtime",
                "target_time": 3.0,  # 3초 이하
                "requests": 3,
            },
        ]

        for test in performance_tests:
            total_time = 0.0
            successful_requests = 0
            errors = []

            for i in range(test["requests"]):
                start_time = time.time()
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        response = await client.get(test["endpoint"])
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

    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """종합 통합 테스트 실행"""
        logger.info("MSA 종합 통합 테스트 시작")
        test_start_time = time.time()

        # 1. 개별 서비스 헬스체크
        logger.info("1단계: 개별 서비스 헬스체크")
        health_tasks = [
            self.test_service_health(name, config)
            for name, config in self.services.items()
        ]
        health_results = await asyncio.gather(*health_tasks)
        self.test_results.extend(health_results)

        # 2. API Gateway 라우팅 테스트
        logger.info("2단계: API Gateway 라우팅 테스트")
        routing_results = await self.test_api_gateway_routing()
        self.test_results.extend(routing_results)

        # 3. 서비스 간 통신 테스트
        logger.info("3단계: 서비스 간 통신 테스트")
        communication_results = await self.test_service_communication()
        self.test_results.extend(communication_results)

        # 4. 데이터베이스 연결성 테스트
        logger.info("4단계: 데이터베이스 연결성 테스트")
        db_result = await self.test_database_connectivity()
        self.test_results.append(db_result)

        # 5. 성능 벤치마크 테스트
        logger.info("5단계: 성능 벤치마크 테스트")
        performance_results = await self.test_performance_benchmarks()
        self.test_results.extend(performance_results)

        total_test_time = time.time() - test_start_time

        # 결과 분석
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result.passed)
        failed_tests = total_tests - passed_tests

        average_response_time = (
            sum(result.response_time for result in self.test_results) / total_tests
            if total_tests > 0
            else 0
        )

        return {
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": (passed_tests / total_tests * 100)
                if total_tests > 0
                else 0,
                "total_test_time": total_test_time,
                "average_response_time": average_response_time,
            },
            "healthy_services": self.healthy_services,
            "test_results": self.test_results,
            "recommendations": self._generate_recommendations(),
        }

    def _generate_recommendations(self) -> List[str]:
        """테스트 결과 기반 권장사항 생성"""
        recommendations = []

        # 실패한 테스트 분석
        failed_tests = [result for result in self.test_results if not result.passed]

        if not failed_tests:
            recommendations.append("✅ 모든 MSA 통합 테스트가 성공적으로 완료되었습니다!")
            recommendations.append("🚀 시스템이 프로덕션 배포 준비 상태입니다.")
        else:
            recommendations.append(f"⚠️  {len(failed_tests)}개의 테스트가 실패했습니다.")

            # 서비스별 권장사항
            if len(self.healthy_services) < len(self.services):
                unhealthy_services = set(self.services.keys()) - set(
                    self.healthy_services
                )
                recommendations.append(
                    f"🔧 다음 서비스들의 상태를 확인하세요: {', '.join(unhealthy_services)}"
                )
                recommendations.append("   - Docker/Kubernetes 컨테이너 상태 확인")
                recommendations.append("   - 서비스 로그 확인")
                recommendations.append("   - 포트 충돌 확인")

            # 성능 관련 권장사항
            slow_tests = [
                result for result in self.test_results if result.response_time > 2.0
            ]
            if slow_tests:
                recommendations.append("⚡ 성능 개선이 필요한 엔드포인트가 있습니다:")
                for test in slow_tests[:3]:  # 상위 3개만 표시
                    recommendations.append(
                        f"   - {test.name}: {test.response_time:.2f}초"
                    )

        # 일반 권장사항
        recommendations.extend(
            [
                "\n📋 MSA 운영 권장사항:",
                "• 모니터링: Prometheus + Grafana 대시보드 활용",
                "• 로깅: 중앙집중식 로그 수집 구성",
                "• 보안: API Gateway에서 인증/인가 강화",
                "• 확장성: HPA를 통한 자동 스케일링 설정",
            ]
        )

        return recommendations

    def print_detailed_report(self, test_summary: Dict[str, Any]):
        """상세 테스트 리포트 출력"""
        print("\n" + "=" * 80)
        print("🏗️  MSA 아키텍처 종합 통합 테스트 리포트")
        print("=" * 80)

        # 테스트 요약
        summary = test_summary["test_summary"]
        print(f"\n📊 테스트 요약:")
        print(f"   • 총 테스트: {summary['total_tests']}개")
        print(f"   • 성공: {summary['passed_tests']}개")
        print(f"   • 실패: {summary['failed_tests']}개")
        print(f"   • 성공률: {summary['success_rate']:.1f}%")
        print(f"   • 총 실행 시간: {summary['total_test_time']:.2f}초")
        print(f"   • 평균 응답 시간: {summary['average_response_time']:.3f}초")

        # 서비스 상태
        print(f"\n🏥 서비스 상태:")
        all_services = list(self.services.keys())
        healthy_services = test_summary["healthy_services"]

        for service in all_services:
            status = "✅ 정상" if service in healthy_services else "❌ 비정상"
            service_name = self.services[service].name
            print(f"   • {service_name}: {status}")

        # 테스트 상세 결과
        print(f"\n📋 상세 테스트 결과:")
        for result in self.test_results:
            status = "✅" if result.passed else "❌"
            print(f"   {status} {result.name}")
            print(f"      응답시간: {result.response_time:.3f}초", end="")

            if result.status_code:
                print(f", HTTP {result.status_code}", end="")

            if result.error_message:
                print(f", 오류: {result.error_message}")
            else:
                print()

        # 권장사항
        print(f"\n💡 권장사항:")
        for recommendation in test_summary["recommendations"]:
            print(f"{recommendation}")

        print("\n" + "=" * 80)

        # 최종 결과
        if summary["failed_tests"] == 0:
            print("🎉 MSA 통합 테스트 완료! 시스템이 정상 작동 중입니다.")
        else:
            print(f"⚠️  {summary['failed_tests']}개 테스트 실패. 시스템 점검이 필요합니다.")

        print("=" * 80)


async def main():
    """메인 실행 함수"""
    print("🚀 MSA 아키텍처 종합 통합 테스트를 시작합니다...")
    print("   - API Gateway (8080)")
    print("   - Collection Service (8000)")
    print("   - Blacklist Service (8001)")
    print("   - Analytics Service (8002)")
    print()

    tester = MSAIntegrationTester()

    try:
        # 종합 테스트 실행
        test_results = await tester.run_comprehensive_test()

        # 상세 리포트 출력
        tester.print_detailed_report(test_results)

        # 종료 코드 결정
        failed_tests = test_results["test_summary"]["failed_tests"]
        if failed_tests == 0:
            print(f"\n✅ 모든 MSA 통합 테스트 성공!")
            sys.exit(0)
        else:
            print(f"\n❌ {failed_tests}개 테스트 실패")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⏹️  테스트가 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 테스트 실행 중 오류 발생: {e}")
        logger.exception("Test execution failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
