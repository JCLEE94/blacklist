#!/usr/bin/env python3
"""
MSA 아키텍처 개별 서비스 상세 테스트
각 마이크로서비스의 핵심 기능을 개별적으로 검증
"""

import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass
from typing import List

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ServiceTest:
    name: str
    url: str
    expected_status: int
    description: str
    expected_keys: List[str] = None


class MSAServiceTester:
    """MSA 개별 서비스 상세 테스터"""

    def __init__(self):
        self.results = []
        self.services = {
            "api_gateway": "http://localhost:8080",
            "collection_service": "http://localhost:8000",
            "blacklist_service": "http://localhost:8001",
            "analytics_service": "http://localhost:8002",
        }

    async def test_collection_service(self):
        """Collection Service 상세 테스트"""
        print("\n🔄 Collection Service 테스트 중...")
        base_url = self.services["collection_service"]

        tests = [
            ServiceTest(
                name="Collection Health",
                url="{base_url}/health",
                expected_status=200,
                description="Collection Service 헬스체크",
                expected_keys=["status", "service"],
            ),
            ServiceTest(
                name="Collection Status",
                url="{base_url}/api/v1/status",
                expected_status=200,
                description="수집 상태 조회",
                expected_keys=["collection_enabled", "sources"],
            ),
        ]

        for test in tests:
            await self._run_single_test(test)

    async def test_blacklist_service(self):
        """Blacklist Service 상세 테스트"""
        print("\n🛡️  Blacklist Service 테스트 중...")
        base_url = self.services["blacklist_service"]

        tests = [
            ServiceTest(
                name="Blacklist Health",
                url="{base_url}/health",
                expected_status=200,
                description="Blacklist Service 헬스체크",
                expected_keys=["status", "service"],
            ),
            ServiceTest(
                name="Active IPs",
                url="{base_url}/api/v1/active-ips",
                expected_status=200,
                description="활성 IP 목록 조회",
            ),
            ServiceTest(
                name="IP Statistics",
                url="{base_url}/api/v1/statistics",
                expected_status=200,
                description="IP 통계 조회",
                expected_keys=["total_ips", "by_source"],
            ),
            ServiceTest(
                name="FortiGate Format",
                url="{base_url}/api/v1/fortigate",
                expected_status=200,
                description="FortiGate 형식 조회",
            ),
        ]

        for test in tests:
            await self._run_single_test(test)

    async def test_analytics_service(self):
        """Analytics Service 상세 테스트"""
        print("\n📊 Analytics Service 테스트 중...")
        base_url = self.services["analytics_service"]

        tests = [
            ServiceTest(
                name="Analytics Health",
                url="{base_url}/health",
                expected_status=200,
                description="Analytics Service 헬스체크",
                expected_keys=["status", "service"],
            ),
            ServiceTest(
                name="Realtime Metrics",
                url="{base_url}/api/v1/realtime",
                expected_status=200,
                description="실시간 메트릭 조회",
            ),
            ServiceTest(
                name="Trends Analysis",
                url="{base_url}/api/v1/trends",
                expected_status=200,
                description="트렌드 분석 조회",
            ),
            ServiceTest(
                name="Geographic Distribution",
                url="{base_url}/api/v1/geographic",
                expected_status=200,
                description="지리적 분포 조회",
            ),
            ServiceTest(
                name="Threat Types",
                url="{base_url}/api/v1/threat-types",
                expected_status=200,
                description="위협 유형 분석",
            ),
        ]

        for test in tests:
            await self._run_single_test(test)

    async def test_api_gateway(self):
        """API Gateway 상세 테스트"""
        print("\n🚪 API Gateway 테스트 중...")
        base_url = self.services["api_gateway"]

        tests = [
            ServiceTest(
                name="Gateway Health",
                url="{base_url}/health",
                expected_status=200,
                description="API Gateway 헬스체크",
                expected_keys=["status", "service", "services"],
            ),
            # Collection 라우팅
            ServiceTest(
                name="Collection via Gateway",
                url="{base_url}/api/v1/collection/status",
                expected_status=200,
                description="Gateway를 통한 Collection 접근",
            ),
            # Blacklist 라우팅
            ServiceTest(
                name="Blacklist Active via Gateway",
                url="{base_url}/api/v1/blacklist/active",
                expected_status=200,
                description="Gateway를 통한 Blacklist 활성 IP 접근",
            ),
            ServiceTest(
                name="Blacklist Statistics via Gateway",
                url="{base_url}/api/v1/blacklist/statistics",
                expected_status=200,
                description="Gateway를 통한 Blacklist 통계 접근",
            ),
            ServiceTest(
                name="FortiGate via Gateway",
                url="{base_url}/api/v1/blacklist/fortigate",
                expected_status=200,
                description="Gateway를 통한 FortiGate 형식 접근",
            ),
            # Analytics 라우팅
            ServiceTest(
                name="Analytics Realtime via Gateway",
                url="{base_url}/api/v1/analytics/realtime",
                expected_status=200,
                description="Gateway를 통한 Analytics 실시간 메트릭 접근",
            ),
            ServiceTest(
                name="Analytics Trends via Gateway",
                url="{base_url}/api/v1/analytics/trends",
                expected_status=200,
                description="Gateway를 통한 Analytics 트렌드 접근",
            ),
        ]

        for test in tests:
            await self._run_single_test(test)

    async def test_service_performance(self):
        """서비스 성능 테스트"""
        print("\n⚡ 서비스 성능 테스트 중...")

        performance_tests = [
            ("API Gateway", "{self.services['api_gateway']}/health", 0.1),
            (
                "Collection Service",
                "{self.services['collection_service']}/health",
                0.1,
            ),
            ("Blacklist Service", "{self.services['blacklist_service']}/health", 0.1),
            ("Analytics Service", "{self.services['analytics_service']}/health", 0.1),
        ]

        for service_name, url, target_time in performance_tests:
            await self._test_performance(service_name, url, target_time)

    async def test_database_integration(self):
        """데이터베이스 통합 테스트"""
        print("\n🗄️  데이터베이스 통합 테스트 중...")

        # Blacklist Service를 통한 DB 테스트
        db_tests = [
            ServiceTest(
                name="DB - Statistics Query",
                url="{self.services['blacklist_service']}/api/v1/statistics",
                expected_status=200,
                description="데이터베이스 통계 쿼리 테스트",
            ),
            ServiceTest(
                name="DB - Active IPs Query",
                url="{self.services['blacklist_service']}/api/v1/active-ips",
                expected_status=200,
                description="데이터베이스 활성 IP 쿼리 테스트",
            ),
        ]

        for test in db_tests:
            await self._run_single_test(test)

    async def test_inter_service_communication(self):
        """서비스 간 통신 테스트"""
        print("\n🔗 서비스 간 통신 테스트 중...")

        # API Gateway를 통한 모든 서비스 연동 테스트
        gateway_url = self.services["api_gateway"]

        inter_service_tests = [
            ServiceTest(
                name="Gateway → Collection",
                url="{gateway_url}/api/v1/collection/status",
                expected_status=200,
                description="Gateway에서 Collection Service로의 라우팅",
            ),
            ServiceTest(
                name="Gateway → Blacklist",
                url="{gateway_url}/api/v1/blacklist/statistics",
                expected_status=200,
                description="Gateway에서 Blacklist Service로의 라우팅",
            ),
            ServiceTest(
                name="Gateway → Analytics",
                url="{gateway_url}/api/v1/analytics/realtime",
                expected_status=200,
                description="Gateway에서 Analytics Service로의 라우팅",
            ),
        ]

        for test in inter_service_tests:
            await self._run_single_test(test)

    async def _run_single_test(self, test: ServiceTest):
        """단일 테스트 실행"""
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(test.url)
                response_time = time.time() - start_time

                success = response.status_code == test.expected_status

                result = {
                    "name": test.name,
                    "url": test.url,
                    "description": test.description,
                    "expected_status": test.expected_status,
                    "actual_status": response.status_code,
                    "response_time": response_time,
                    "success": success,
                    "error": None,
                    "data": None,
                }

                if success:
                    try:
                        data = response.json()
                        result["data"] = data

                        # 예상 키 검증
                        if test.expected_keys:
                            missing_keys = [
                                key for key in test.expected_keys if key not in data
                            ]
                            if missing_keys:
                                result["success"] = False
                                result["error"] = "Missing keys: {missing_keys}"
                    except json.JSONDecodeError:
                        # JSON이 아닌 응답도 허용 (예: plain text)
                        result["data"] = (
                            response.text[:200] + "..."
                            if len(response.text) > 200
                            else response.text
                        )
                else:
                    result[
                        "error"
                    ] = "Status {response.status_code}: {response.text[:200]}"

                self.results.append(result)

                status_emoji = "✅" if success else "❌"
                print(
                    "   {status_emoji} {test.name}: {response.status_code} ({response_time:.3f}s)"
                )

                if not success:
                    print(f"      오류: {result['error']}")

        except Exception as e:
            response_time = time.time() - start_time
            result = {
                "name": test.name,
                "url": test.url,
                "description": test.description,
                "expected_status": test.expected_status,
                "actual_status": 0,
                "response_time": response_time,
                "success": False,
                "error": str(e),
                "data": None,
            }
            self.results.append(result)
            print(f"   ❌ {test.name}: 연결 실패 ({response_time:.3f}s)")
            print(f"      오류: {str(e)}")

    async def _test_performance(self, service_name: str, url: str, target_time: float):
        """성능 테스트"""
        times = []

        for i in range(5):  # 5회 테스트
            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(url)
                    response_time = time.time() - start_time

                    if response.status_code == 200:
                        times.append(response_time)
            except Exception as e:
                pass

        if times:
            avg_time = sum(times) / len(times)
            max_time = max(times)
            min_time = min(times)
            success = avg_time <= target_time

            result = {
                "name": "{service_name} Performance",
                "url": url,
                "description": "{service_name} 성능 테스트 (목표: {target_time}s)",
                "expected_status": 200,
                "actual_status": 200,
                "response_time": avg_time,
                "success": success,
                "error": (
                    None
                    if success
                    else "Target: {target_time}s, Actual: {avg_time:.3f}s"
                ),
                "data": {
                    "avg_time": avg_time,
                    "min_time": min_time,
                    "max_time": max_time,
                    "target_time": target_time,
                    "tests": len(times),
                },
            }

            self.results.append(result)

            status_emoji = "✅" if success else "❌"
            print(
                "   {status_emoji} {service_name} Performance: {avg_time:.3f}s (목표: {target_time}s)"
            )
        else:
            result = {
                "name": "{service_name} Performance",
                "url": url,
                "description": "{service_name} 성능 테스트",
                "expected_status": 200,
                "actual_status": 0,
                "response_time": 0,
                "success": False,
                "error": "모든 성능 테스트 실패",
                "data": None,
            }
            self.results.append(result)
            print(f"   ❌ {service_name} Performance: 테스트 실패")

    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("🔬 MSA 아키텍처 상세 서비스 테스트 시작")
        print("=" * 80)

        test_start_time = time.time()

        # 개별 서비스 테스트
        await self.test_collection_service()
        await self.test_blacklist_service()
        await self.test_analytics_service()
        await self.test_api_gateway()

        # 통합 테스트
        await self.test_service_performance()
        await self.test_database_integration()
        await self.test_inter_service_communication()

        total_time = time.time() - test_start_time

        # 결과 분석
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["success"])
        failed_tests = total_tests - passed_tests

        print("\n" + "=" * 80)
        print("📊 MSA 상세 테스트 결과 요약")
        print("=" * 80)
        print(f"• 총 테스트: {total_tests}개")
        print(f"• 성공: {passed_tests}개")
        print(f"• 실패: {failed_tests}개")
        print(f"• 성공률: {(passed_tests/total_tests*100):.1f}%")
        print(f"• 총 실행 시간: {total_time:.2f}초")

        if failed_tests > 0:
            print("\n❌ 실패한 테스트:")
            for result in self.results:
                if not result["success"]:
                    print(f"   • {result['name']}: {result['error']}")

        # 성능 분석
        performance_results = [
            r for r in self.results if "Performance" in r["name"] and r["success"]
        ]
        if performance_results:
            avg_response_time = sum(
                r["response_time"] for r in performance_results
            ) / len(performance_results)
            print(f"\n⚡ 평균 응답 시간: {avg_response_time:.3f}초")

        print("\n" + "=" * 80)

        if failed_tests == 0:
            print("🎉 모든 MSA 서비스가 정상적으로 작동합니다!")
            return True
        else:
            print(f"⚠️  {failed_tests}개의 테스트가 실패했습니다. 시스템 점검이 필요합니다.")
            return False


async def main():
    """메인 실행 함수"""
    tester = MSAServiceTester()

    try:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n⏹️  테스트가 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 테스트 실행 중 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
